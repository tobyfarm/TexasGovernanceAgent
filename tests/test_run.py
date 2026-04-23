"""Streaming orchestration tests. Mock the Agent SDK so we never hit the model."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agent import run as run_mod
from agent.audit import _target_path  # noqa: F401 — referenced indirectly via env override
from agent.run import AnalysisError, analyze_pdf, analyze_pdf_stream
from agent.types import AgendaItem, AnalysisResult


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    yield


@pytest.fixture
def audit_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "citations.jsonl"
    monkeypatch.setenv("CITATION_LOG_PATH", str(target))
    return target


def _fake_items() -> list[AgendaItem]:
    return [
        AgendaItem(
            item_id="A", title="Call to Order", pages=(1, 1), raw_text="...", item_type="DISCUSSION"
        ),
        AgendaItem(item_id="B", title="Minutes", pages=(2, 2), raw_text="...", item_type="CONSENT"),
        AgendaItem(item_id="C", title="Budget", pages=(3, 3), raw_text="...", item_type="ACTION"),
    ]


def _fake_response(item_id: str) -> str:
    return json.dumps(
        {
            "summary": f"summary for {item_id}",
            "key_data": "",
            "legal_framework": "",
            "flags": [],
            "questions": ["q1?"],
            "citations": [{"authority": f"TEC §{item_id}", "quoted_text": None, "verified": False}],
        }
    )


async def _fake_invoke(prompt: str, *, cwd: Path) -> str:
    # crude: pull item_id out of the prompt formatting
    for line in prompt.splitlines():
        if line.startswith("item_id:"):
            return _fake_response(line.split(":", 1)[1].strip())
    return _fake_response("X")


async def test_stream_emits_ingest_and_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, audit_path: Path
):
    items = _fake_items()
    monkeypatch.setattr(run_mod, "extract_agenda_items", lambda *a, **kw: items)
    monkeypatch.setattr(run_mod, "_invoke", _fake_invoke)

    events = []
    async for event in analyze_pdf_stream(tmp_path / "nonexistent.pdf"):
        events.append(event)

    names = [e.name for e in events]
    assert names[0] == "ingest_done"
    assert names[-1] == "result_done"
    assert names.count("item_start") == 3
    assert names.count("item_done") == 3

    # citations were logged (one per item)
    assert audit_path.exists()
    assert len(audit_path.read_text().strip().splitlines()) == 3


async def test_analyze_pdf_returns_final_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, audit_path: Path
):
    items = _fake_items()
    monkeypatch.setattr(run_mod, "extract_agenda_items", lambda *a, **kw: items)
    monkeypatch.setattr(run_mod, "_invoke", _fake_invoke)

    result = await analyze_pdf(tmp_path / "x.pdf")
    assert isinstance(result, AnalysisResult)
    assert [a.item.item_id for a in result.items] == ["A", "B", "C"]
    assert all(a.citations for a in result.items)


async def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(AnalysisError) as excinfo:
        async for _ in analyze_pdf_stream(tmp_path / "x.pdf"):
            pass
    assert excinfo.value.code == "missing_api_key"


async def test_ingestion_failure_wrapped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    def _blow_up(*a, **kw):
        raise RuntimeError("corrupt xref")

    monkeypatch.setattr(run_mod, "extract_agenda_items", _blow_up)
    with pytest.raises(AnalysisError) as excinfo:
        async for _ in analyze_pdf_stream(tmp_path / "x.pdf"):
            pass
    assert excinfo.value.code == "ingestion_failed"


async def test_per_item_error_becomes_event(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, audit_path: Path
):
    items = _fake_items()
    monkeypatch.setattr(run_mod, "extract_agenda_items", lambda *a, **kw: items)

    async def _flaky(prompt: str, *, cwd: Path) -> str:
        if "item_id: B" in prompt:
            raise RuntimeError("model timeout")
        return await _fake_invoke(prompt, cwd=cwd)

    monkeypatch.setattr(run_mod, "_invoke", _flaky)

    events = []
    async for event in analyze_pdf_stream(tmp_path / "x.pdf"):
        events.append(event)

    errors = [e for e in events if e.name == "item_error"]
    assert len(errors) == 1
    assert errors[0].data["item_id"] == "B"
    # Final result still present — error items get placeholder analysis
    result_event = next(e for e in events if e.name == "result_done")
    assert len(result_event.data["items"]) == 3


async def test_concurrency_is_bounded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, audit_path: Path
):
    items = _fake_items() * 3  # 9 items
    monkeypatch.setattr(run_mod, "extract_agenda_items", lambda *a, **kw: items)

    in_flight = 0
    max_in_flight = 0
    start_event = asyncio.Event()

    async def _slow(prompt: str, *, cwd: Path) -> str:
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return await _fake_invoke(prompt, cwd=cwd)

    monkeypatch.setattr(run_mod, "_invoke", _slow)
    start_event.set()

    events = []
    async for event in analyze_pdf_stream(tmp_path / "x.pdf", concurrency=2):
        events.append(event)

    assert max_in_flight <= 2
    assert max_in_flight >= 1

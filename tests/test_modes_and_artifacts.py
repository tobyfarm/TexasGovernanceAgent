"""Tests for SAMCO_LOQ mode, run artifacts, and introspection endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent import run as run_mod
from agent.run import _persist_run, _system_prompt
from agent.types import AgendaItem, AnalysisResult, ItemAnalysis
from api import server as server_mod


def test_system_prompt_switches_on_mode():
    brock = _system_prompt("BROCK_FULL")
    samco = _system_prompt("SAMCO_LOQ")
    assert "Board Book Red Team" in brock
    assert "SAMCO" in samco
    assert brock != samco


async def test_stream_persists_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, runs_dir: Path
):
    items = [
        AgendaItem(item_id="A", title="Call", pages=(1, 1), raw_text="...", item_type="DISCUSSION"),
    ]

    async def _fake(prompt: str, *, cwd: Path, mode: str = "BROCK_FULL") -> str:
        return json.dumps(
            {
                "summary": f"mode={mode}",
                "key_data": "",
                "legal_framework": "",
                "flags": [],
                "questions": ["q?"],
                "citations": [],
            }
        )

    monkeypatch.setattr(run_mod, "extract_agenda_items", lambda *a, **kw: items)
    monkeypatch.setattr(run_mod, "_invoke", _fake)

    async for _ in run_mod.analyze_pdf_stream(tmp_path / "x.pdf", mode="SAMCO_LOQ"):
        pass

    created_runs = list(runs_dir.iterdir())
    assert len(created_runs) == 1
    run_dir = created_runs[0]
    assert (run_dir / "result.json").exists()
    assert (run_dir / "result.md").exists()
    assert (run_dir / "meta.json").exists()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["mode"] == "SAMCO_LOQ"
    assert meta["item_count"] == 1


def test_runs_endpoint_lists_meta(runs_dir: Path):
    runs_dir.mkdir(parents=True)
    (runs_dir / "abc123").mkdir()
    (runs_dir / "abc123" / "meta.json").write_text(
        json.dumps(
            {"run_id": "abc123", "source_pdf": "p.pdf", "mode": "BROCK_FULL", "item_count": 3}
        )
    )

    client = TestClient(server_mod.app)
    r = client.get("/runs")
    assert r.status_code == 200
    payload = r.json()
    assert len(payload["runs"]) == 1
    assert payload["runs"][0]["run_id"] == "abc123"


def test_run_detail_endpoint_returns_analysis(runs_dir: Path):
    run_dir = runs_dir / "deadbeef"
    run_dir.mkdir(parents=True)
    dummy = AnalysisResult(
        source_pdf="p.pdf",
        generated_at="2026-04-13T00:00:00+00:00",
        items=[
            ItemAnalysis(
                item=AgendaItem(
                    item_id="A",
                    title="x",
                    pages=(1, 1),
                    raw_text="...",
                    item_type="DISCUSSION",
                ),
                summary="s",
                key_data="",
                legal_framework="",
            )
        ],
    )
    (run_dir / "result.json").write_text(dummy.model_dump_json())

    client = TestClient(server_mod.app)
    r = client.get("/runs/deadbeef")
    assert r.status_code == 200
    assert r.json()["source_pdf"] == "p.pdf"


def test_run_detail_rejects_traversal(runs_dir: Path):
    client = TestClient(server_mod.app)
    r = client.get("/runs/..%2F..%2Fetc")
    assert r.status_code in (400, 404)


def test_analyze_rejects_unknown_mode(monkeypatch: pytest.MonkeyPatch, runs_dir: Path):
    client = TestClient(server_mod.app)
    pdf_bytes = b"%PDF-1.4\nfake\n%%EOF"
    r = client.post(
        "/analyze",
        files={"pdf": ("x.pdf", pdf_bytes, "application/pdf")},
        data={"mode": "NOT_A_MODE"},
    )
    assert r.status_code == 400


def test_persist_run_direct(runs_dir: Path):
    result = AnalysisResult(
        source_pdf="p.pdf",
        generated_at="2026-04-13T00:00:00+00:00",
        items=[],
        output_mode="SAMCO_LOQ",
    )
    run_dir = _persist_run("deadbeef", result)
    assert run_dir.exists()
    assert (run_dir / "meta.json").exists()

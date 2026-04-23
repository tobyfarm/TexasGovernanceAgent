"""API surface tests.

/health is unauthenticated. /analyze validates content-type, enforces the
size cap, respects X-API-Key when configured, and streams SSE events.

The Agent SDK is mocked out — tests never hit the real model.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent import run as run_mod
from agent.types import AgendaItem
from api import server as server_mod


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    server_mod.rate_limiter.reset()
    yield
    server_mod.rate_limiter.reset()


@pytest.fixture(autouse=True)
def _api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("BROCK_API_KEY", raising=False)
    yield


@pytest.fixture
def audit_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "citations.jsonl"
    monkeypatch.setenv("CITATION_LOG_PATH", str(target))
    return target


@pytest.fixture
def client() -> TestClient:
    return TestClient(server_mod.app)


def _stub_pipeline(monkeypatch: pytest.MonkeyPatch):
    items = [
        AgendaItem(
            item_id="A", title="Call to Order", pages=(1, 1), raw_text="...", item_type="DISCUSSION"
        ),
    ]

    async def _fake_invoke(prompt: str, *, cwd: Path, mode: str = "BROCK_FULL") -> str:
        return json.dumps(
            {
                "summary": "s",
                "key_data": "",
                "legal_framework": "",
                "flags": [],
                "questions": ["q?"],
                "citations": [{"authority": "TEC §X", "quoted_text": None, "verified": False}],
            }
        )

    monkeypatch.setattr(run_mod, "extract_agenda_items", lambda *a, **kw: items)
    monkeypatch.setattr(run_mod, "_invoke", _fake_invoke)


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    event = None
    data_lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
        elif line == "":
            if event is not None:
                payload = "\n".join(data_lines)
                try:
                    out.append((event, json.loads(payload) if payload else {}))
                except json.JSONDecodeError:
                    out.append((event, {"_raw": payload}))
            event = None
            data_lines = []
    return out


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_analyze_rejects_non_pdf_content_type(client: TestClient):
    r = client.post("/analyze", files={"pdf": ("note.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_analyze_rejects_oversized_upload(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(server_mod, "MAX_UPLOAD_BYTES", 1024)
    big = b"%PDF-1.4\n" + b"x" * 4096
    r = client.post("/analyze", files={"pdf": ("big.pdf", big, "application/pdf")})
    assert r.status_code == 413


def test_analyze_streams_sse_events(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, audit_path: Path
):
    _stub_pipeline(monkeypatch)
    pdf_bytes = b"%PDF-1.4\nfake\n%%EOF"
    r = client.post("/analyze", files={"pdf": ("x.pdf", pdf_bytes, "application/pdf")})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse(r.text)
    names = [e for e, _ in events]
    assert "ingest_done" in names
    assert "item_start" in names
    assert "item_done" in names
    assert names[-1] == "result_done"


def test_analyze_missing_api_key_emits_error_event(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    _stub_pipeline(monkeypatch)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    pdf_bytes = b"%PDF-1.4\nfake\n%%EOF"
    r = client.post("/analyze", files={"pdf": ("x.pdf", pdf_bytes, "application/pdf")})
    assert r.status_code == 200
    events = _parse_sse(r.text)
    assert any(name == "error" for name, _ in events)


def test_analyze_requires_api_key_when_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("BROCK_API_KEY", "secret")
    pdf_bytes = b"%PDF-1.4\nfake\n%%EOF"
    r = client.post("/analyze", files={"pdf": ("x.pdf", pdf_bytes, "application/pdf")})
    assert r.status_code == 401
    r = client.post(
        "/analyze",
        files={"pdf": ("x.pdf", pdf_bytes, "application/pdf")},
        headers={"X-API-Key": "wrong"},
    )
    assert r.status_code == 401


def test_analyze_rate_limited(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    _stub_pipeline(monkeypatch)
    monkeypatch.setattr(server_mod.rate_limiter, "limit", 2)
    pdf_bytes = b"%PDF-1.4\nfake\n%%EOF"
    for _ in range(2):
        client.post("/analyze", files={"pdf": ("x.pdf", pdf_bytes, "application/pdf")})
    r = client.post("/analyze", files={"pdf": ("x.pdf", pdf_bytes, "application/pdf")})
    assert r.status_code == 429

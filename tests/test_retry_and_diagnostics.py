"""Tests for retry, PDF magic validation, diagnostic health, citations
endpoint, and JSON Schema export CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent import run as run_mod
from agent.run import _invoke_with_retry
from api import server as server_mod

# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------


async def test_retry_succeeds_after_transient_failure(monkeypatch: pytest.MonkeyPatch):
    calls = {"n": 0}

    async def _flaky(prompt: str, *, cwd: Path, mode: str = "BROCK_FULL") -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("transient")
        return '{"summary": "ok", "key_data": "", "legal_framework": "", "flags": [], "questions": [], "citations": []}'

    monkeypatch.setattr(run_mod, "_invoke", _flaky)
    monkeypatch.setattr(run_mod, "RETRY_BASE_SECONDS", 0)

    text = await _invoke_with_retry("prompt", cwd=Path("."), mode="BROCK_FULL", attempts=2)
    assert "ok" in text
    assert calls["n"] == 2


async def test_retry_gives_up_after_n_attempts(monkeypatch: pytest.MonkeyPatch):
    calls = {"n": 0}

    async def _always_fails(prompt: str, *, cwd: Path, mode: str = "BROCK_FULL") -> str:
        calls["n"] += 1
        raise RuntimeError("perma-broken")

    monkeypatch.setattr(run_mod, "_invoke", _always_fails)
    monkeypatch.setattr(run_mod, "RETRY_BASE_SECONDS", 0)

    with pytest.raises(RuntimeError, match="perma-broken"):
        await _invoke_with_retry("prompt", cwd=Path("."), mode="BROCK_FULL", attempts=2)
    assert calls["n"] == 3  # initial + 2 retries


# ---------------------------------------------------------------------------
# PDF magic-byte validation
# ---------------------------------------------------------------------------


def test_analyze_rejects_non_pdf_bytes(monkeypatch: pytest.MonkeyPatch):
    client = TestClient(server_mod.app)
    r = client.post(
        "/analyze",
        files={"pdf": ("x.pdf", b"not a pdf at all, just garbage", "application/pdf")},
    )
    assert r.status_code == 400
    assert "PDF" in r.json()["detail"]


def test_analyze_rejects_empty_upload():
    client = TestClient(server_mod.app)
    # TestClient coalesces zero-byte files; send a single space + correct MIME
    # then validate header check still triggers for non-PDF start.
    r = client.post(
        "/analyze",
        files={"pdf": ("x.pdf", b"", "application/pdf")},
    )
    # Either 400 (empty) or 400 (non-PDF magic) — both acceptable.
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Diagnostic health
# ---------------------------------------------------------------------------


def test_health_detailed_reports_api_key_and_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    client = TestClient(server_mod.app)
    r = client.get("/health/detailed")
    assert r.status_code == 200
    body = r.json()
    assert body["anthropic_api_key_present"] is True
    assert body["skills_dir"].endswith("skills")
    assert "skills" in body  # per-skill SKILL.md presence map
    assert "rate_limit" in body


def test_health_detailed_flags_missing_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = TestClient(server_mod.app)
    r = client.get("/health/detailed")
    assert r.status_code == 200
    assert r.json()["anthropic_api_key_present"] is False
    assert r.json()["status"] == "degraded"


# ---------------------------------------------------------------------------
# Citations endpoint
# ---------------------------------------------------------------------------


def test_citations_endpoint_filters_by_run(audit_path: Path):
    # Seed the audit log with two runs
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {"run_id": "aaa", "item_id": "1", "authority": "TEC §11.151", "verified": True}
                ),
                json.dumps(
                    {
                        "run_id": "bbb",
                        "item_id": "1",
                        "authority": "TGC §551.074",
                        "verified": False,
                    }
                ),
                json.dumps(
                    {"run_id": "aaa", "item_id": "2", "authority": "TAC §61.1", "verified": True}
                ),
                "",  # blank line mid-file
                "not valid json",  # tolerated
            ]
        )
    )
    client = TestClient(server_mod.app)
    r = client.get("/runs/aaa/citations")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == "aaa"
    assert [row["authority"] for row in body["citations"]] == ["TEC §11.151", "TAC §61.1"]


def test_citations_endpoint_rejects_traversal():
    client = TestClient(server_mod.app)
    r = client.get("/runs/..%2F..%2Fx/citations")
    # FastAPI / Starlette normalizes some traversal attempts to 404; either
    # the 400 isalnum guard or a 404 is acceptable defence.
    assert r.status_code in (400, 404)


# ---------------------------------------------------------------------------
# JSON Schema CLI
# ---------------------------------------------------------------------------


def test_schema_cli_emits_analysis_result_schema():
    result = subprocess.run(
        [sys.executable, "-m", "agent.types", "--model", "AnalysisResult"],
        capture_output=True,
        text=True,
        check=True,
    )
    schema = json.loads(result.stdout)
    assert schema["title"] == "AnalysisResult"
    assert "items" in schema["properties"]


def test_schema_cli_emits_combined_schema():
    result = subprocess.run(
        [sys.executable, "-m", "agent.types", "--schema"],
        capture_output=True,
        text=True,
        check=True,
    )
    combined = json.loads(result.stdout)
    assert set(combined["$defs"].keys()) == {
        "AgendaItem",
        "Flag",
        "Citation",
        "ItemAnalysis",
        "AnalysisResult",
    }

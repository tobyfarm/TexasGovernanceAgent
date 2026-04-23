"""Shared pytest fixtures. Keeps per-test files focused on assertions."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agent import run as run_mod
from api import server as server_mod


@pytest.fixture(autouse=True)
def _api_key(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    """Guarantee ANTHROPIC_API_KEY is set and BROCK_API_KEY is not for unit tests.

    The Brock integration test (`tests/test_brock_april_13.py`) runs against
    the live Agent SDK when both the PDF and a real API key are present — we
    must not clobber the real key in that file. Everywhere else, a test-key
    stub is fine because the SDK is monkeypatched out.
    """
    if "test_brock_april_13" not in request.node.nodeid:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    elif not os.getenv("ANTHROPIC_API_KEY"):
        # Keep the env empty so the integration test's skipif triggers cleanly.
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("BROCK_API_KEY", raising=False)
    yield


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Prevent cross-test rate-limit bleed-through."""
    server_mod.rate_limiter.reset()
    yield
    server_mod.rate_limiter.reset()


@pytest.fixture
def audit_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate the citation audit log to a per-test temp file."""
    target = tmp_path / "citations.jsonl"
    monkeypatch.setenv("CITATION_LOG_PATH", str(target))
    return target


@pytest.fixture
def runs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the run artifacts directory to a per-test temp path."""
    target = tmp_path / "runs"
    monkeypatch.setattr(run_mod, "RUNS_DIR", target)
    monkeypatch.setattr(server_mod, "RUNS_DIR", target)
    return target

"""Shared pytest fixtures. Keeps per-test files focused on assertions."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent import run as run_mod
from api import server as server_mod


@pytest.fixture(autouse=True)
def _api_key(monkeypatch: pytest.MonkeyPatch):
    """Guarantee ANTHROPIC_API_KEY is set and BROCK_API_KEY is not.

    Individual tests can override by re-setting or deleting these within the
    test body — monkeypatch reverts automatically at teardown.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
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

"""Audit log unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.audit import log_citations
from agent.types import Citation


@pytest.fixture
def audit_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "citations.jsonl"
    monkeypatch.setenv("CITATION_LOG_PATH", str(target))
    return target


def test_noop_on_empty_list(audit_path: Path):
    log_citations(run_id="r", source_pdf="p.pdf", item_id="A", citations=[])
    assert not audit_path.exists()


def test_writes_one_line_per_citation(audit_path: Path):
    log_citations(
        run_id="r1",
        source_pdf="brock.pdf",
        item_id="4B",
        citations=[
            Citation(authority="TEC §11.151(b)", verified=True),
            Citation(authority="TGC §551.074", quoted_text="Personnel matters.", verified=False),
        ],
    )
    lines = audit_path.read_text().strip().splitlines()
    assert len(lines) == 2
    rows = [json.loads(line) for line in lines]
    assert {r["authority"] for r in rows} == {"TEC §11.151(b)", "TGC §551.074"}
    assert rows[0]["run_id"] == "r1"
    assert rows[0]["item_id"] == "4B"
    assert rows[1]["quoted_text"] == "Personnel matters."


def test_appends_across_calls(audit_path: Path):
    log_citations(
        run_id="r", source_pdf="p.pdf", item_id="A", citations=[Citation(authority="TEC §11.151")]
    )
    log_citations(
        run_id="r", source_pdf="p.pdf", item_id="B", citations=[Citation(authority="TGC §551.071")]
    )
    assert len(audit_path.read_text().strip().splitlines()) == 2

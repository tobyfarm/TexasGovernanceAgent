"""Ingestion tests. Does not require the Brock PDF to exist."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.ingestion import _classify_item, _find_boundaries


def test_find_boundaries_letter_dot():
    pages = [
        "Some preamble\nA. Call to Order\nB. Roll Call\nC. Approve Minutes from 3/15\n",
        "D. Superintendent Report with financial update and curriculum notes\n",
    ]
    boundaries = _find_boundaries(pages)
    ids = [b[0] for b in boundaries]
    assert "C" in ids
    assert "D" in ids


def test_classify_closed_session():
    assert _classify_item("Executive Session per §551.074") == "CLOSED_SESSION"


def test_classify_consent():
    assert _classify_item("Consent Agenda: minutes, bills, personnel") == "CONSENT"


def test_classify_action_defaults_when_no_keywords():
    assert _classify_item("Plain text with nothing recognizable") == "DISCUSSION"


def test_missing_pdf_raises():
    from agent.ingestion import extract_agenda_items

    with pytest.raises(FileNotFoundError):
        extract_agenda_items(Path("/nonexistent/x.pdf"))

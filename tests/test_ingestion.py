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


def test_classify_closed_session_from_title():
    assert _classify_item("Executive Session per §551.074") == "CLOSED_SESSION"


def test_classify_closed_session_from_body_when_title_silent():
    assert _classify_item("Item K", "The board convenes in executive session per §551.074.") == "CLOSED_SESSION"


def test_classify_consent():
    assert _classify_item("Consent Agenda: minutes, bills, personnel") == "CONSENT"


def test_classify_action_title_prevails_over_body_noise():
    # Body mentions "approve" but the title is a discussion item — title wins.
    assert (
        _classify_item("Business Discussion", "Staff will approve the plan eventually.")
        == "DISCUSSION"
    )


def test_classify_ceremonial_procedural_items_as_discussion():
    for title in (
        "CALL TO ORDER",
        "INVOCATION",
        "PLEDGE OF ALLEGIANCE AND TEXAS PLEDGE",
        "ESTABLISH QUORUM",
        "ADJOURN",
    ):
        assert _classify_item(title) == "DISCUSSION", title


def test_classify_action_title():
    assert _classify_item("Consider approval of teacher contracts for 2026-2027") == "ACTION"
    assert _classify_item("Discuss and consider approval of TIA payouts") == "ACTION"


def test_classify_defaults_to_discussion_when_no_keywords():
    assert _classify_item("Plain text with nothing recognizable") == "DISCUSSION"


def test_missing_pdf_raises():
    from agent.ingestion import extract_agenda_items

    with pytest.raises(FileNotFoundError):
        extract_agenda_items(Path("/nonexistent/x.pdf"))

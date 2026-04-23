"""Brock April 13 2026 eval test.

Day 1 bar: pipeline does not crash; emits a valid AnalysisResult.
Day 2 bar: ingestion correctly identifies the A–M top-level agenda items.
Day 3 (eval day) will tighten this against the hand version in
`examples/brock_april_13_2026_prereadhand.md`.

The source PDF is dropped in by Toby on main. Skip until it exists so
older branches and CI without the PDF stay green.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

BROCK_PDF = Path(__file__).resolve().parent.parent / "examples" / "brock_april_13_2026.pdf"

# What we know about the April 13 2026 agenda:
#   A. CALL TO ORDER
#   B. INVOCATION
#   C. PLEDGE OF ALLEGIANCE AND TEXAS PLEDGE
#   D. ESTABLISH QUORUM
#   E. BROCK SPOTLIGHT
#   F. PUBLIC COMMENT
#   G. CONSENT AGENDA
#   H. SUPERINTENDENT REPORT
#   I. BUSINESS DISCUSSION
#   J. BUSINESS ACTION
#   K. CLOSED SESSION, PURSUANT TO TEXAS GOVERNMENT CODE, SECTIONS 551.071 THROUGH 551.087
#   L. RECONVENE FROM CLOSED SESSION …
#   M. ADJOURN
EXPECTED_TOP_LEVEL = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"]


@pytest.mark.skipif(not BROCK_PDF.exists(), reason="Brock PDF not present yet")
def test_ingestion_identifies_all_top_level_items():
    from agent.ingestion import extract_agenda_items

    items = extract_agenda_items(BROCK_PDF)
    ids = [i.item_id for i in items]
    assert ids == EXPECTED_TOP_LEVEL, f"unexpected agenda structure: {ids}"

    # Every item should have a title and a page range.
    for item in items:
        assert item.raw_text, f"item {item.item_id} has no raw_text"
        assert item.pages[0] >= 1 and item.pages[1] >= item.pages[0]
        assert item.title, f"item {item.item_id} has no title"

    # K should be recognised as CLOSED_SESSION either directly or by title.
    k = next(i for i in items if i.item_id == "K")
    assert "closed session" in k.title.lower()


@pytest.mark.skipif(not BROCK_PDF.exists(), reason="Brock PDF not present yet")
@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
@pytest.mark.asyncio
async def test_full_pipeline_smoke():
    from agent.run import analyze_pdf
    from agent.types import AnalysisResult

    result = await analyze_pdf(BROCK_PDF)
    assert isinstance(result, AnalysisResult)
    assert result.source_pdf
    assert result.items, "expected at least one ItemAnalysis"

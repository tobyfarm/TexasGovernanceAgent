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
#   A. CALL TO ORDER ... M. ADJOURN
# Plus these substantive sub-items with independent body sections:
#   J.1 Series 2016/2017 Bond Refunding
#   J.2 Teacher contracts 2026-2027
#   J.3 TIA payouts
#   J.4 Fund 491 amendment
#   J.5 School bus purchase
EXPECTED_TOP_LEVEL = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"]
EXPECTED_SUBITEMS_REQUIRED = {"J.1", "J.2", "J.3", "J.4", "J.5"}


@pytest.mark.skipif(not BROCK_PDF.exists(), reason="Brock PDF not present yet")
def test_ingestion_identifies_all_top_level_items():
    from agent.ingestion import extract_agenda_items

    items = extract_agenda_items(BROCK_PDF)
    ids = [i.item_id for i in items]

    # Every top-level letter A–M must be present in order.
    letter_ids = [i for i in ids if "." not in i]
    assert letter_ids == EXPECTED_TOP_LEVEL, f"unexpected top-level structure: {letter_ids}"

    # The J.* action sub-items are each substantive and must be ingested
    # separately so the agent can analyze them with their own body pages.
    assert EXPECTED_SUBITEMS_REQUIRED.issubset(ids), (
        f"missing required sub-items: {EXPECTED_SUBITEMS_REQUIRED - set(ids)}"
    )

    # Every item should have a title and a page range.
    for item in items:
        assert item.raw_text, f"item {item.item_id} has no raw_text"
        assert item.pages[0] >= 1 and item.pages[1] >= item.pages[0]
        assert item.title, f"item {item.item_id} has no title"

    # J.1 (bond refunding) is the biggest substantive item in the packet —
    # it should claim a broad page range, not just the TOC entry.
    j1 = next(i for i in items if i.item_id == "J.1")
    assert j1.pages[1] - j1.pages[0] >= 20, (
        f"J.1 bond refunding range too narrow: {j1.pages}"
    )

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

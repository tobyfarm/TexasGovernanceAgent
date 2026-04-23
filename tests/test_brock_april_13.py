"""Brock April 13 2026 eval test.

Day 1 bar: pipeline does not crash; emits a valid AnalysisResult.
Day 3 (eval day) will tighten this against the hand version in
`examples/brock_april_13_2026_prereadhand.md`.

The source PDF is dropped in by Toby after the initial commit. Skip until it
exists so CI and local `pytest` runs stay green.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

BROCK_PDF = Path(__file__).resolve().parent.parent / "examples" / "brock_april_13_2026.pdf"


@pytest.mark.skipif(not BROCK_PDF.exists(), reason="Brock PDF not present yet")
def test_ingestion_produces_items():
    from agent.ingestion import extract_agenda_items

    items = extract_agenda_items(BROCK_PDF)
    assert len(items) >= 1, "expected at least one agenda item"
    for item in items:
        assert item.raw_text, f"item {item.item_id} has no raw_text"
        assert item.pages[0] >= 1 and item.pages[1] >= item.pages[0]


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

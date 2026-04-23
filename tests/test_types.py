"""Contract tests for agent/types.py. The interface is public — changes here
break Agents B/C/D/E/F. Keep these lightweight but enforce the shape."""

from __future__ import annotations

from datetime import UTC, datetime

from agent.types import AgendaItem, AnalysisResult, Citation, Flag, ItemAnalysis


def _item() -> AgendaItem:
    return AgendaItem(
        item_id="4B",
        title="Check Register",
        pages=(8, 29),
        raw_text="...",
        item_type="CONSENT",
    )


def test_agenda_item_roundtrip():
    item = _item()
    loaded = AgendaItem.model_validate_json(item.model_dump_json())
    assert loaded.pages == (8, 29)
    assert loaded.item_type == "CONSENT"


def test_flag_defaults():
    f = Flag(severity="WATCH", pattern_id="blanket_citation", summary="s", detail="d")
    assert f.citations == []


def test_citation_optional_quoted_text():
    c = Citation(authority="TEC §11.151(b)")
    assert c.quoted_text is None
    assert c.verified is False


def test_analysis_result_minimal():
    r = AnalysisResult(
        source_pdf="x.pdf",
        generated_at=datetime.now(UTC),
        items=[
            ItemAnalysis(
                item=_item(),
                summary="s",
                key_data="",
                legal_framework="",
            )
        ],
    )
    assert r.output_mode == "BROCK_FULL"
    assert len(r.items) == 1

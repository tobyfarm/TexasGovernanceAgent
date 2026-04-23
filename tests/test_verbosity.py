"""Verbosity knob tests — full vs standard vs brief rendering."""

from __future__ import annotations

from datetime import UTC, datetime

from agent.run import _render_markdown
from agent.types import AgendaItem, AnalysisResult, Flag, ItemAnalysis


def _make_result() -> AnalysisResult:
    def item(item_id: str, item_type: str, flags: list[Flag]) -> ItemAnalysis:
        return ItemAnalysis(
            item=AgendaItem(
                item_id=item_id,
                title=f"title-for-{item_id}",
                pages=(1, 1),
                raw_text="...",
                item_type=item_type,
            ),
            summary=f"summary for {item_id}",
            key_data="",
            legal_framework="legal framework",
            flags=flags,
            questions=["q?"],
        )

    return AnalysisResult(
        source_pdf="p.pdf",
        generated_at=datetime.now(UTC),
        items=[
            item("A", "DISCUSSION", []),  # procedural, no flags
            item("B", "DISCUSSION", [Flag(severity="POSITIVE", pattern_id="x", summary="s", detail="d")]),  # procedural, POSITIVE only
            item("C", "DISCUSSION", [Flag(severity="WATCH", pattern_id="x", summary="s", detail="d")]),  # procedural WATCH
            item("G", "CONSENT", []),  # consent, no flags
            item("J.1", "ACTION", []),  # action, no flags
            item("K", "CLOSED_SESSION", [Flag(severity="RED_FLAG", pattern_id="x", summary="s", detail="d")]),
        ],
    )


def test_full_renders_every_item():
    md = _render_markdown(_make_result(), verbosity="full")
    for item_id in ("A", "B", "C", "G", "J.1", "K"):
        assert f"Item {item_id}:" in md, f"missing {item_id} in full"


def test_standard_collapses_procedural_positive_only():
    md = _render_markdown(_make_result(), verbosity="standard")
    # A (no flags) and B (POSITIVE only) should be title + summary; C has WATCH so full.
    assert "Item A:" in md
    assert "Item B:" in md
    # Legal framework only appears in expanded form.
    a_section = md.split("Item A:")[1].split("Item ")[0]
    assert "legal framework" not in a_section
    b_section = md.split("Item B:")[1].split("Item ")[0]
    assert "legal framework" not in b_section
    # C has a WATCH flag → full render with legal framework.
    c_section = md.split("Item C:")[1].split("Item ")[0]
    assert "legal framework" in c_section


def test_brief_drops_non_action_items_without_red_flag():
    md = _render_markdown(_make_result(), verbosity="brief")
    # A, B, C are DISCUSSION without RED_FLAG — dropped.
    assert "Item A:" not in md
    assert "Item B:" not in md
    assert "Item C:" not in md
    # G is CONSENT — dropped in brief (only ACTION/CLOSED_SESSION kept).
    assert "Item G:" not in md
    # J.1 is ACTION — kept.
    assert "Item J.1:" in md
    # K has RED_FLAG — kept.
    assert "Item K:" in md


def test_brief_keeps_discussion_items_with_red_flags():
    result = _make_result()
    # Add a DISCUSSION item with a RED_FLAG — should survive brief.
    result.items.append(
        ItemAnalysis(
            item=AgendaItem(
                item_id="Z",
                title="Item Z",
                pages=(1, 1),
                raw_text="...",
                item_type="DISCUSSION",
            ),
            summary="s",
            key_data="",
            legal_framework="",
            flags=[Flag(severity="RED_FLAG", pattern_id="x", summary="s", detail="d")],
        )
    )
    md = _render_markdown(result, verbosity="brief")
    assert "Item Z:" in md

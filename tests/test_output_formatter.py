"""Tests for the Agent F output formatter (skills/output-formatter/render.py).

Scope: template contract + adapter normalization. The acceptance test for
prose/voice fidelity against examples/brock_april_13_2026_prereadhand.md is
a human eval, not a unit test.
"""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skills" / "output-formatter"
sys.path.insert(0, str(SKILL_DIR))

from _dummy_data import (  # noqa: E402  (deliberately after sys.path shim)
    AGENT_A_SHAPED_DUMMY,
    BROCK_APRIL_13_DUMMY,
    SAMCO_LOQ_DUMMY,
)
from render import (  # noqa: E402
    _DEFAULT_LIMITS,
    _SEVERITY_TO_RISK_LEVEL,
    _normalize_executive_summary_row,
    _normalize_meeting_metadata,
    _strip_question_prefix,
    _trim_legal_framework,
    render,
)


# ---------------------------------------------------------------------------
# Adapter: meeting_metadata defaults + overrides.
# ---------------------------------------------------------------------------


def test_meeting_metadata_defaults_when_raw_is_sparse() -> None:
    meta = _normalize_meeting_metadata({"source": "foo.pdf", "run_id": "abc"}, None)
    assert meta["district_name_upper"] == "DISTRICT"
    assert meta["meeting_date"] == "(meeting date not provided)"
    assert meta["source"] == "foo.pdf"  # raw fields carried through
    assert meta["run_id"] == "abc"


def test_meeting_metadata_overrides_win_over_raw_and_defaults() -> None:
    raw = {"district_name_upper": "OLD", "meeting_type": "Special"}
    overrides = {"district_name_upper": "NEW", "trustee_name": "Toby Farmer"}
    meta = _normalize_meeting_metadata(raw, overrides)
    assert meta["district_name_upper"] == "NEW"
    assert meta["trustee_name"] == "Toby Farmer"
    assert meta["meeting_type"] == "Special"  # raw wins over default when override absent


# ---------------------------------------------------------------------------
# Adapter: executive_summary_table row shape.
# ---------------------------------------------------------------------------


def test_template_shape_rows_are_passthrough() -> None:
    row = {"item_title": "Bond", "key_finding": "Not savings.", "risk_level": "HIGH"}
    out = _normalize_executive_summary_row(row, item_by_id={})
    assert out == row


@pytest.mark.parametrize(
    ("severity", "expected_level"),
    [
        ("RED_FLAG", "HIGH"),
        ("WATCH", "MEDIUM"),
        ("POSITIVE", "LOW"),
        ("NONE", "LOW"),
    ],
)
def test_severity_to_risk_level_mapping(severity: str, expected_level: str) -> None:
    assert _SEVERITY_TO_RISK_LEVEL[severity] == expected_level


def test_agent_a_row_shape_is_mapped_to_template_shape() -> None:
    agent_a_row = {
        "item_id": "7",
        "title": "Bond Series 2026 (pp. 87-127)",
        "type": "ACTION",
        "pages": "87-127",
        "risk": "RED_FLAG",
    }
    item = {
        "item": {"item_id": "7"},
        "summary": "Bond restructuring item.",
        "flags": [{"severity": "RED_FLAG", "summary": "Hold harmless is $32.2M", "detail": ""}],
    }
    out = _normalize_executive_summary_row(agent_a_row, item_by_id={"7": item})
    assert out["item_title"] == "Bond Series 2026 (pp. 87-127)"
    assert out["risk_level"] == "HIGH"
    assert out["key_finding"] == "Hold harmless is $32.2M"


def test_row_without_matching_item_gets_placeholder_key_finding() -> None:
    row = {"item_id": "Z", "title": "Ghost Item", "type": "ACTION", "pages": "0-0", "risk": "NONE"}
    out = _normalize_executive_summary_row(row, item_by_id={})
    assert out["key_finding"] == "(no analyst finding)"
    assert out["risk_level"] == "LOW"


# ---------------------------------------------------------------------------
# Rendering end-to-end.
# ---------------------------------------------------------------------------


def test_render_rejects_empty_items_in_brock_mode() -> None:
    data = deepcopy(BROCK_APRIL_13_DUMMY)
    data["items"] = []
    with pytest.raises(ValueError, match="at least one item"):
        render(data)


def test_render_brock_full_returns_markdown() -> None:
    out = render(BROCK_APRIL_13_DUMMY)
    assert "# **Executive Summary: Top Issues Tonight**" in out
    assert "# **Item K: Closed Session" in out
    assert "# **Meeting Preparation Checklist**" in out
    assert out.rstrip().endswith(
        "Confirm closed session is properly posted and recorded.*"
    )


def test_render_samco_loq_returns_markdown() -> None:
    out = render(SAMCO_LOQ_DUMMY)
    assert "Line of Questioning:" in out
    assert "# **Documented Timeline of Events**" in out
    assert "# **Read-Aloud Statement (Short Version)**" in out


def test_agent_a_shaped_input_renders_cleanly() -> None:
    out = render(
        AGENT_A_SHAPED_DUMMY,
        metadata_overrides={
            "district_name_upper": "BROCK ISD",
            "trustee_name": "Toby Farmer",
            "meeting_date": "April 13, 2026",
            "page_count": 166,
        },
    )
    assert "**BROCK ISD**" in out
    assert "Prepared for: Trustee Toby Farmer" in out
    # Adapter mapped raw risk → HIGH/MEDIUM/LOW and table rendered correctly.
    assert "| **HIGH** |" in out
    assert "| **MEDIUM** |" in out


# ---------------------------------------------------------------------------
# Template heuristics.
# ---------------------------------------------------------------------------


def test_simple_item_gets_what_is_happening_scaffold() -> None:
    out = render(BROCK_APRIL_13_DUMMY)
    # Item K's summary is plain prose → scaffold wraps it.
    item_k_block = out.split("# **Item K:")[1].split("# **Item")[0]
    assert "## **What Is Happening**" in item_k_block


def test_complex_item_skips_what_is_happening_scaffold() -> None:
    out = render(BROCK_APRIL_13_DUMMY)
    # Item 5's summary already has "## **Enrollment Trend:" → scaffold suppressed.
    item_5_block = out.split("# **Item 5:")[1].split("# **Item")[0]
    assert "## **What Is Happening**" not in item_5_block
    assert "## **Enrollment Trend:" in item_5_block


def test_prep_checklist_section_is_skipped_when_empty() -> None:
    data = deepcopy(BROCK_APRIL_13_DUMMY)
    data["prep_checklist"] = []
    out = render(data)
    assert "# **Meeting Preparation Checklist**" not in out
    # TOMA footer still present.
    assert "*Remember: Under TOMA" in out


def test_governance_questions_are_numbered_continuously_across_items() -> None:
    out = render(BROCK_APRIL_13_DUMMY)
    # K has 4 questions → Item 4C starts at 5; Item 5 at 8; Item 7 at 10; Item 11 at 15.
    # Locate the first numbered question in Item 4C.
    item_4c_block = out.split("# **Item 4C:")[1].split("# **Item")[0]
    assert "\n5. *" in item_4c_block
    item_5_block = out.split("# **Item 5:")[1].split("# **Item")[0]
    assert "\n8. *" in item_5_block


# ---------------------------------------------------------------------------
# Compression: question prefix strip + caps + flag detail drop + LF trim.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "stripped"),
    [
        ("1. Will the board post the agenda?", "Will the board post the agenda?"),
        ("  12.  Is quorum established?", "Is quorum established?"),
        ("3) Short form prefix?", "Short form prefix?"),
        ("No prefix at all.", "No prefix at all."),
        ("2.3 Not a plain numeric prefix.", "2.3 Not a plain numeric prefix."),
        ("", ""),
    ],
)
def test_strip_question_prefix(raw: str, stripped: str) -> None:
    assert _strip_question_prefix(raw) == stripped


def test_no_double_numbering_when_questions_have_numeric_prefix() -> None:
    data = deepcopy(BROCK_APRIL_13_DUMMY)
    # Simulate Agent A emitting questions with their own `N. ` prefix.
    data["items"][0]["questions"] = [
        "1. Will the board state specific TGC sections?",
        "2. Is the certified agenda maintained?",
    ]
    out = render(data)
    # Template emits "1. *Will..." not "1. *1. Will..."
    assert "\n1. *Will the board state specific TGC sections?*" in out
    assert "\n1. *1." not in out


def test_questions_cap_applied_from_default_limits() -> None:
    data = deepcopy(BROCK_APRIL_13_DUMMY)
    # 6 questions → should render 4 under default cap.
    data["items"][0]["questions"] = [f"Question {i}?" for i in range(6)]
    out = render(data)
    item_block = out.split("# **Item K:")[1].split("# **Item")[0]
    assert "*Question 0?*" in item_block
    assert "*Question 3?*" in item_block
    assert "*Question 4?*" not in item_block
    assert "*Question 5?*" not in item_block


def test_questions_cap_can_be_raised() -> None:
    data = deepcopy(BROCK_APRIL_13_DUMMY)
    data["items"][0]["questions"] = [f"Question {i}?" for i in range(6)]
    out = render(data, limits={"max_questions_per_item": 10})
    item_block = out.split("# **Item K:")[1].split("# **Item")[0]
    assert "*Question 5?*" in item_block


def test_flags_cap_applied_from_default_limits() -> None:
    data = deepcopy(BROCK_APRIL_13_DUMMY)
    # 8 WATCH flags → should render 6 under default cap.
    data["items"][0]["flags"] = [
        {"severity": "WATCH", "pattern_id": "x", "summary": f"Flag {i}.", "detail": "", "citations": []}
        for i in range(8)
    ]
    out = render(data)
    item_block = out.split("# **Item K:")[1].split("# **Item")[0]
    assert "**WATCH:** Flag 0." in item_block
    assert "**WATCH:** Flag 5." in item_block
    assert "**WATCH:** Flag 6." not in item_block


def test_flag_detail_is_dropped_by_default() -> None:
    data = deepcopy(BROCK_APRIL_13_DUMMY)
    data["items"][0]["flags"] = [
        {
            "severity": "WATCH",
            "pattern_id": "x",
            "summary": "One-liner summary.",
            "detail": "Multi-sentence detail. Should not appear by default.",
            "citations": [],
        }
    ]
    out = render(data)
    assert "**WATCH:** One-liner summary." in out
    assert "Should not appear by default." not in out


def test_flag_detail_can_be_included() -> None:
    data = deepcopy(BROCK_APRIL_13_DUMMY)
    data["items"][0]["flags"] = [
        {
            "severity": "WATCH",
            "pattern_id": "x",
            "summary": "Summary.",
            "detail": "Verbose detail.",
            "citations": [],
        }
    ]
    out = render(data, limits={"include_flag_detail": True})
    assert "**WATCH:** Summary. Verbose detail." in out


def test_legal_framework_trim_skips_items_with_redflag() -> None:
    item = {
        "flags": [{"severity": "RED_FLAG"}],
        "legal_framework": "P1.\n\nP2.\n\nP3.",
    }
    _trim_legal_framework(item, max_paragraphs=1)
    assert item["legal_framework"] == "P1.\n\nP2.\n\nP3."  # unchanged


def test_legal_framework_trim_applies_to_non_redflag_items() -> None:
    item = {
        "flags": [{"severity": "WATCH"}, {"severity": "POSITIVE"}],
        "legal_framework": "P1 relevant.\n\nP2 also relevant.\n\nP3 boilerplate.",
    }
    _trim_legal_framework(item, max_paragraphs=1)
    assert item["legal_framework"] == "P1 relevant."


def test_legal_framework_trim_is_noop_when_cap_is_zero_or_none() -> None:
    original = "P1.\n\nP2.\n\nP3."
    for cap in (None, 0):
        item = {"flags": [{"severity": "WATCH"}], "legal_framework": original}
        _trim_legal_framework(item, max_paragraphs=cap)
        assert item["legal_framework"] == original


def test_default_limits_shape_is_stable() -> None:
    # Locks in the public default contract — changes here should be deliberate.
    assert _DEFAULT_LIMITS == {
        "max_questions_per_item": 4,
        "max_flags_per_item": 6,
        "include_flag_detail": False,
        "legal_framework_paragraphs_non_redflag": 1,
    }

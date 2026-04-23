"""Unit tests for voice.context_loader.

These tests do not open any network session. They exercise the pure-Python
parts: section splitting, doctrine block assembly with §IV preservation,
and the echo_test short-circuit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from context_loader import (
    BUDGET_DOCTRINE_CHARS,
    ContextBlock,
    _split_sections,
    build_doctrine_block,
    load_session_context,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PRINCIPLES_PATH = REPO_ROOT / "skills" / "governance-principles" / "principles.md"


def test_split_sections_finds_all_top_level_sections():
    src = PRINCIPLES_PATH.read_text(encoding="utf-8")
    sections = _split_sections(src)
    # principles.md v1 has §I–§V.
    assert set(sections) == {"I", "II", "III", "IV", "V"}
    assert sections["I"].startswith("## I. Core governance principles")
    assert sections["IV"].startswith("## IV. Voice and tone notes")


def test_doctrine_block_includes_both_I_and_IV():
    block = build_doctrine_block(PRINCIPLES_PATH)
    assert "## I. Core governance principles" in block.text
    assert "## IV. Voice and tone notes" in block.text
    assert "BLOCK 3 OF 3" in block.label


def test_doctrine_block_preserves_IV_when_I_is_truncated():
    # Build a fake principles file where §I is enormous so the loader is
    # forced to truncate §I while preserving §IV in full.
    big = "x" * (BUDGET_DOCTRINE_CHARS * 2)
    fake = (
        "# Fake principles\n\n"
        f"## I. Big\n\n{big}\n\n"
        "## IV. Voice and tone notes\n\n"
        "The voice rules live here. Quote adopted text verbatim.\n"
    )
    tmp = Path(__file__).with_name("_fake_principles.md")
    tmp.write_text(fake, encoding="utf-8")
    try:
        block = build_doctrine_block(tmp)
    finally:
        tmp.unlink(missing_ok=True)

    # §IV must be intact even though §I overflowed the budget.
    assert "The voice rules live here. Quote adopted text verbatim." in block.text
    assert "## IV. Voice and tone notes" in block.text
    # §I should show a truncation marker.
    assert "truncated" in block.text


def test_doctrine_block_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        build_doctrine_block(Path("/nonexistent/principles.md"))


def test_context_block_as_turn_round_trip():
    block = ContextBlock(label="BLOCK X: demo", text="hello world")
    turn = block.as_turn()
    assert turn["role"] == "user"
    assert "BLOCK X: demo" in turn["parts"][0]["text"]
    assert "hello world" in turn["parts"][0]["text"]


@pytest.mark.parametrize("doc_id", ["", "unknown", "echo_test"])
def test_load_session_context_short_circuits_on_harness_ids(doc_id):
    assert load_session_context(doc_id) == []


def test_load_session_context_loads_doctrine_when_other_sources_missing(tmp_path):
    # When the PDF and pre-read are not on disk but principles.md is,
    # the loader returns just the doctrine block with a warning.
    blocks = load_session_context("brock_april_13_2026")
    labels = [b.label for b in blocks]
    assert any("DOCTRINE EXCERPT" in lbl for lbl in labels)

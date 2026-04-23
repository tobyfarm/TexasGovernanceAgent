"""Unit tests for eval.compare."""

from __future__ import annotations

from pathlib import Path

from eval.compare import _normalize_citation, compare


def test_identical_texts_are_perfectly_similar(tmp_path: Path):
    text = "# Brock Pre-Read\n\n## Executive Summary\n\nTEC §11.151(b) applies here.\nRED_FLAG on item B.\n"
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text(text)
    b.write_text(text)
    report = compare(a, b)
    assert report.header_overlap == 1.0
    assert report.word_count_ratio == 1.0
    assert report.citations_only_in_hand == []
    assert report.citations_only_in_generated == []
    assert report.flag_counts_generated == {"RED_FLAG": 1, "WATCH": 0, "POSITIVE": 0}


def test_missing_citations_detected(tmp_path: Path):
    hand = "Hand version invokes TEC §11.151(b) and TGC §551.074."
    gen = "Generated version only mentions TEC §11.151(b)."
    (tmp_path / "g.md").write_text(gen)
    (tmp_path / "h.md").write_text(hand)
    report = compare(tmp_path / "g.md", tmp_path / "h.md")
    assert any("551.074" in c for c in report.citations_only_in_hand)


def test_flag_count_ratio(tmp_path: Path):
    hand = "RED FLAG: bad. WATCH: tbd. POSITIVE: good. WATCH: also."
    gen = "WATCH only."
    (tmp_path / "g.md").write_text(gen)
    (tmp_path / "h.md").write_text(hand)
    report = compare(tmp_path / "g.md", tmp_path / "h.md")
    assert report.flag_counts_hand["RED_FLAG"] == 1
    assert report.flag_counts_hand["WATCH"] == 2
    assert report.flag_counts_generated["WATCH"] == 1


def test_score_is_in_unit_range(tmp_path: Path):
    (tmp_path / "a.md").write_text("# x\n\nTEC §1.1")
    (tmp_path / "b.md").write_text("# x\n\nTEC §1.1")
    report = compare(tmp_path / "a.md", tmp_path / "b.md")
    assert 0.0 <= report.score() <= 1.0


def test_citation_normalization_collapses_punctuation_variants():
    # Trailing period, presence/absence of §, extra whitespace, all collapse.
    assert _normalize_citation("TEC §11.151(b).") == _normalize_citation("TEC §11.151(b)")
    assert _normalize_citation("TEC 11.151(b)") == _normalize_citation("TEC §11.151(b)")
    assert _normalize_citation("  TEC   §11.151(b)  ") == _normalize_citation("TEC §11.151(b)")


def test_citation_normalization_aliases_verbose_names():
    assert _normalize_citation("TEX. EDUC. CODE §11.151(b)") == _normalize_citation("TEC §11.151(b)")
    assert _normalize_citation("TEX. GOV. CODE §551.074") == _normalize_citation("TGC §551.074")


def test_compare_dedups_punctuation_variants(tmp_path: Path):
    hand = "TEC §11.151(b) governs. Later cited as TEC §11.151(b)."
    gen = "TEC 11.151(b) applies."
    (tmp_path / "g.md").write_text(gen)
    (tmp_path / "h.md").write_text(hand)
    report = compare(tmp_path / "g.md", tmp_path / "h.md")
    # With normalization, the same citation regardless of punctuation should
    # count as present in both.
    assert report.citations_only_in_hand == []
    assert report.citations_only_in_generated == []

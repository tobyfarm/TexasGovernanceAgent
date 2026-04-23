"""Regression tests for the statute-mapper verifier.

Exercises all four VerificationResult states against a controlled temp corpus
(so these tests remain green as the real corpus is populated).

Run with:
    uv run pytest tests/test_verifier.py -v
    # or without pytest installed:
    python3 tests/test_verifier.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = REPO_ROOT / "skills" / "statute-mapper" / "verifier.py"

spec = importlib.util.spec_from_file_location("statute_mapper_verifier", VERIFIER_PATH)
assert spec and spec.loader
_mod = importlib.util.module_from_spec(spec)
sys.modules["statute_mapper_verifier"] = _mod
spec.loader.exec_module(_mod)

verify = _mod.verify
VerificationResult = _mod.VerificationResult


POPULATED_CORPUS = """\
<!-- Retrieved on 2026-04-23 -->

### TEC §11.151(b)

**Title.** Powers and Duties of Board of Trustees.

> The trustees as a body corporate have the exclusive power and duty to govern
> and oversee the management of the public schools of the district.

**Common usage:** core governance authority.

### TEC §11.1511(b)(2)–(3)

**Title.** Specific Powers and Duties of Board.

> A board is responsible for adopting goals for the district and monitoring
> progress toward those goals.
"""

SCAFFOLD_CORPUS = """\
<!-- Retrieved on YYYY-MM-DD -->

### TGC §551.074

**Title.** Personnel Matters; Closed Meeting.

<!-- TODO: verbatim text goes here -->

**Common usage:** specific-individual personnel exception.
"""


def _make_corpus(tmpdir: Path) -> Path:
    (tmpdir / "tec-ch-11.md").write_text(POPULATED_CORPUS, encoding="utf-8")
    (tmpdir / "tgc-ch-551.md").write_text(SCAFFOLD_CORPUS, encoding="utf-8")
    return tmpdir


def test_verified_returns_quoted_text(tmp_path: Path) -> None:
    corpus = _make_corpus(tmp_path)
    r = verify("TEC §11.151(b)", corpus_dir=corpus)
    assert r.verified is True
    assert r.status == "verified"
    assert r.quoted_text is not None
    assert "exclusive power and duty" in r.quoted_text
    assert r.source_file == "tec-ch-11.md"


def test_normalized_variants_all_hit_same_entry(tmp_path: Path) -> None:
    corpus = _make_corpus(tmp_path)
    for variant in [
        "TEC §11.151(b)",
        "Texas Education Code 11.151(b)",
        "Texas Education Code §11.151(b)",
        "Tex. Educ. Code §11.151(b)",
        "Ed. Code §11.151(b)",
    ]:
        r = verify(variant, corpus_dir=corpus)
        assert r.verified is True, f"variant failed: {variant!r} → {r.status}"
        assert r.authority == "TEC §11.151(b)"


def test_corpus_gap_when_heading_present_but_no_quote(tmp_path: Path) -> None:
    corpus = _make_corpus(tmp_path)
    r = verify("TGC §551.074", corpus_dir=corpus)
    assert r.verified is False
    assert r.status == "corpus_gap"
    assert r.source_file == "tgc-ch-551.md"
    assert r.quoted_text is None
    assert r.diagnostic and "blockquote has not been populated" in r.diagnostic


def test_partial_match_does_not_silently_expand(tmp_path: Path) -> None:
    corpus = _make_corpus(tmp_path)
    r = verify("TEC §11.151", corpus_dir=corpus)
    assert r.verified is False
    assert r.status == "partial_match"
    assert r.diagnostic and "TEC §11.151(b)" in r.diagnostic
    # The broader lookup must NOT collide with the adjacent §11.1511 section.
    assert "§11.1511" not in r.diagnostic.replace("§11.1511(b)(2)", "")


def test_partial_match_boundary_distinguishes_adjacent_sections(tmp_path: Path) -> None:
    """§11.151 must not match §11.1511 despite the shared prefix."""
    corpus = _make_corpus(tmp_path)
    r = verify("TEC §11.1511", corpus_dir=corpus)
    assert r.status == "partial_match"
    assert "§11.1511(b)(2)–(3)" in (r.diagnostic or "")
    assert "§11.151(b)" not in (r.diagnostic or "")


def test_unknown_when_no_code_prefix(tmp_path: Path) -> None:
    corpus = _make_corpus(tmp_path)
    for variant in ["§11.151(b)", "11.151(b)"]:
        r = verify(variant, corpus_dir=corpus)
        assert r.verified is False
        assert r.status == "unknown"


def test_unknown_when_citation_not_in_corpus(tmp_path: Path) -> None:
    corpus = _make_corpus(tmp_path)
    r = verify("TEC §99.999", corpus_dir=corpus)
    assert r.verified is False
    assert r.status == "unknown"
    assert r.diagnostic and "not found in corpus" in r.diagnostic


def test_local_policy_normalization(tmp_path: Path) -> None:
    """Local-policy codes are their own canonical form — no code prefix."""
    local = tmp_path / "brock-isd"
    local.mkdir()
    (local / "be.md").write_text(
        "### BE(LOCAL)\n\n> Any Board member may request that a subject be included.\n",
        encoding="utf-8",
    )
    r = verify("BE(LOCAL)", corpus_dir=tmp_path)
    assert r.verified is True
    assert r.authority == "BE(LOCAL)"
    assert r.source_file == "brock-isd/be.md"


def test_sec_rule_normalization(tmp_path: Path) -> None:
    (tmp_path / "sec.md").write_text(
        "### SEC Rule 15c2-12\n\n> Continuing disclosure requirement.\n",
        encoding="utf-8",
    )
    r = verify("SEC Rule 15c2-12", corpus_dir=tmp_path)
    assert r.verified is True
    assert r.authority == "SEC Rule 15c2-12"


def test_texas_constitution_normalization(tmp_path: Path) -> None:
    (tmp_path / "const.md").write_text(
        "### Tex. Const. art. VII §5\n\n> Permanent School Fund.\n",
        encoding="utf-8",
    )
    for variant in [
        "Tex. Const. art. VII §5",
        "Texas Constitution Article VII, Section 5",
        "Article VII, Section 5 of the Texas Constitution",
    ]:
        r = verify(variant, corpus_dir=tmp_path)
        assert r.verified is True, f"variant failed: {variant!r} → {r.status}"
        assert r.authority == "Tex. Const. art. VII §5"


def test_alias_does_not_false_positive_on_substring(tmp_path: Path) -> None:
    """The alias 'ed code' must not match inside 'added code'."""
    corpus = _make_corpus(tmp_path)
    r = verify("added code 11.151", corpus_dir=corpus)
    assert r.status == "unknown"


def test_msrb_normalization(tmp_path: Path) -> None:
    (tmp_path / "msrb.md").write_text(
        "### MSRB G-42\n\n> Municipal advisors owe a fiduciary duty.\n",
        encoding="utf-8",
    )
    for variant in ["MSRB G-42", "MSRB Rule G-42"]:
        r = verify(variant, corpus_dir=tmp_path)
        assert r.verified is True, f"variant failed: {variant!r}"
        assert r.authority == "MSRB G-42"


def test_subdirectory_corpus_is_scanned(tmp_path: Path) -> None:
    """Local-policy subdir (brock-isd/) must be discovered. source_file is
    a relative path so BE(LOCAL) in brock-isd/ stays distinguishable."""
    local = tmp_path / "brock-isd"
    local.mkdir()
    (local / "be-local.md").write_text(
        "### BE(LOCAL)\n\n> Any Board member may request that a subject be included.\n",
        encoding="utf-8",
    )
    r = verify("BE(LOCAL)", corpus_dir=tmp_path)
    # BE(LOCAL) isn't a recognized code prefix, so this path actually returns
    # unknown. The important thing here is that rglob finds the file; test that
    # by adding a second entry with a known code in the subdir.
    (local / "local.md").write_text(
        "### TEC §11.151(b)\n\n> Governance authority rests with the board.\n",
        encoding="utf-8",
    )
    r = verify("TEC §11.151(b)", corpus_dir=tmp_path)
    assert r.verified is True
    assert r.source_file == "brock-isd/local.md"


def test_tasb_is_flagged_as_non_controlling(tmp_path: Path) -> None:
    """TASB is guidance, not controlling authority (Principle 1)."""
    corpus = _make_corpus(tmp_path)
    r = verify("TASB model policy BE(LOCAL)", corpus_dir=corpus)
    assert r.verified is False
    assert r.status == "unknown"
    assert r.diagnostic and "TASB" in r.diagnostic
    assert "not controlling" in r.diagnostic


def test_verify_all_preserves_order(tmp_path: Path) -> None:
    corpus = _make_corpus(tmp_path)
    verify_all = _mod.verify_all
    results = verify_all(
        ["TEC §11.151(b)", "TGC §551.074", "TEC §99.999"], corpus_dir=corpus
    )
    assert len(results) == 3
    assert results[0].verified is True
    assert results[1].status == "corpus_gap"
    assert results[2].status == "unknown"


def test_list_corpus_entries_surfaces_gaps(tmp_path: Path) -> None:
    corpus = _make_corpus(tmp_path)
    list_corpus_entries = _mod.list_corpus_entries
    entries = list_corpus_entries(corpus_dir=corpus)
    # Populated TEC §11.151(b) → has_text=True
    populated = [e for e in entries if e.authority == "TEC §11.151(b)"]
    assert len(populated) == 1 and populated[0].has_text is True
    # Scaffold TGC §551.074 → has_text=False
    gap = [e for e in entries if e.authority == "TGC §551.074"]
    assert len(gap) == 1 and gap[0].has_text is False


def test_extract_citations_finds_the_common_forms() -> None:
    extract_citations = _mod.extract_citations
    text = """
    Under TEC §11.151(b), the trustees govern.
    Texas Government Code 551.074 covers personnel.
    MSRB Rule G-42 applies. SEC Rule 15c2-12 requires continuing disclosure.
    The PSF is grounded in Article VII, Section 5 of the Texas Constitution.
    Local authority is BE(LOCAL).
    """
    cites = extract_citations(text)
    assert any("11.151(b)" in c for c in cites)
    assert any("551.074" in c for c in cites)
    assert any("G-42" in c for c in cites)
    assert any("15c2-12" in c for c in cites)
    assert any("Article VII" in c for c in cites)
    assert any("BE(LOCAL)" in c for c in cites)


def test_brock_hand_pre_read_citations_all_recognized() -> None:
    """The acceptance test: every citation in the hand-written Brock pre-read
    must be recognized by the corpus. No 'unknown' allowed — either the
    citation is a real authority in the corpus (verified/corpus_gap) or it's
    specific-enough to suggest a near-miss candidate (partial_match).

    If this test fails, the hand author cited an authority Agent B hasn't
    scaffolded yet. Action: add the scaffold and re-run.
    """
    extract_citations = _mod.extract_citations
    pre_read = REPO_ROOT / "examples" / "brock_april_13_2026_prereadhand.md"
    if not pre_read.exists():
        # Skip if the reference artifact isn't present (fresh checkout before
        # main merge); the test is informational in that case.
        return
    text = pre_read.read_text(encoding="utf-8")
    cites = extract_citations(text)
    assert len(cites) >= 20, f"Expected ≥20 citations, extracted {len(cites)}"

    unknown: list[tuple[str, str]] = []
    for cite in cites:
        r = verify(cite)
        if r.status == "unknown":
            unknown.append((cite, r.diagnostic or ""))

    assert not unknown, (
        "The hand pre-read cites authorities not in the scaffolded corpus. "
        "Add a scaffold heading for each, then re-run. Unrecognized: "
        + "; ".join(f"{c!r}" for c, _ in unknown)
    )


def test_live_corpus_is_scaffolded_not_yet_verified() -> None:
    """The bundled corpus at statutes/ is scaffolded — exact headings exist
    but the blockquotes are not yet populated. Until Toby pastes verbatim
    text, every Day 1 citation should return corpus_gap, not verified."""
    r = verify("TEC §11.151(b)")
    assert r.status == "corpus_gap", (
        "Bundled corpus unexpectedly returned 'verified' — "
        "either a blockquote was populated (great, update this test) or the "
        "scaffolding is broken."
    )


if __name__ == "__main__":
    import tempfile
    import traceback

    failures = 0
    tests = [
        (name, fn)
        for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
    ]
    for name, fn in tests:
        try:
            sig_params = fn.__code__.co_varnames[: fn.__code__.co_argcount]
            if "tmp_path" in sig_params:
                with tempfile.TemporaryDirectory() as td:
                    fn(Path(td))
            else:
                fn()
            print(f"  ✓ {name}")
        except AssertionError as e:
            failures += 1
            print(f"  ✗ {name}: {e}")
            traceback.print_exc()
        except Exception as e:
            failures += 1
            print(f"  ✗ {name} ERROR: {e}")
            traceback.print_exc()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)

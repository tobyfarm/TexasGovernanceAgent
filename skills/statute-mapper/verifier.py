"""Citation verifier for the statute-mapper Skill.

The agent passes every authority claim through `verify()` before emitting it
in trustee-facing output. A wrong TEC citation destroys trust permanently, so
the verifier is strict: it never silently expands a citation and never invents
quoted text.

Public contract
---------------

    from skills.statute_mapper.verifier import verify

    result = verify("TEC §11.151(b)")
    if result.verified:
        render_with_quote(result.quoted_text)
    elif result.status == "corpus_gap":
        render_cited_but_not_quoted(result.authority, note=result.diagnostic)
    else:
        soften_or_drop(result.authority, note=result.diagnostic)

The four states of `VerificationResult.status`:

    "verified"      — heading matched AND blockquote text is populated
    "corpus_gap"    — heading matched but text not yet bundled (scaffold TODO)
    "partial_match" — incoming citation is broader/narrower than corpus indexes
    "unknown"       — no match; likely hallucination or not yet bundled

`verified` is True ONLY for the "verified" state. The other three are all
`verified=False` so the binary contract with Agent A's lead loop stays clean.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

CORPUS_DIR = Path(__file__).parent / "statutes"

# --- Normalization ----------------------------------------------------------

# Map common code aliases → canonical short code.
_CODE_ALIASES: dict[str, str] = {
    "tec": "TEC",
    "texas education code": "TEC",
    "tex. educ. code": "TEC",
    "tex educ code": "TEC",
    "ed. code": "TEC",
    "ed code": "TEC",
    "education code": "TEC",
    "tgc": "TGC",
    "texas government code": "TGC",
    "tex. gov't code": "TGC",
    "tex gov't code": "TGC",
    "gov't code": "TGC",
    "govt code": "TGC",
    "government code": "TGC",
    "tac": "TAC",
    "texas administrative code": "TAC",
    "msrb": "MSRB",
    "msrb rule": "MSRB",
    "sec": "SEC",
    "sec rule": "SEC",
    "tex. const.": "TXCONST",
    "texas const.": "TXCONST",
    "texas constitution": "TXCONST",
    # Texas Tax Code — distinct from TAC (Administrative Code).
    "tax code": "TAX",
    "texas tax code": "TAX",
    "tex. tax code": "TAX",
    # Texas Health and Safety Code.
    "hsc": "HSC",
    "health and safety code": "HSC",
    "health & safety code": "HSC",
    "h&s code": "HSC",
    "texas health and safety code": "HSC",
    "tex. health & safety code": "HSC",
    # Texas House Bills (session laws) — recognize short forms.
    "hb": "TXHB",
    "h.b.": "TXHB",
    "h. b.": "TXHB",
    "house bill": "TXHB",
    "tex. h.b.": "TXHB",
}

# Section numbers look like 11.151, 11.151(b), 11.1511(b)(2), 551.0821, etc.
# Also handles ranges like "45.051-45.063" (em-dash or hyphen).
# Note: the subsection char class excludes BOTH `-` and `–` so that the
# range-extender (em-dash OR hyphen) can claim them; otherwise greedy
# matching would truncate the range like "45.051-45" (missing ".063").
_SECTION_RE = re.compile(r"(\d+\.\d+[A-Za-z0-9()]*(?:[–\-]\d+\.\d+[A-Za-z0-9()]*)?)")
# MSRB rule numbers look like G-17, G-42, D-1, etc.
_MSRB_RE = re.compile(r"\b([A-Z]-\d+)\b")
# SEC rule numbers look like 15c2-12, 15Ba1-1, etc.
_SEC_RULE_RE = re.compile(r"\b(\d+[A-Za-z]+\d+(?:-\d+)?)\b")
# Texas Constitution article and section: "art. VII §5" or "Article VII, Section 5".
_CONST_RE = re.compile(
    r"(?:art(?:icle|\.)?)\s*([IVX]+)[,\s]*(?:§|section|sec\.)\s*(\d+)",
    re.IGNORECASE,
)
# Local-policy citations are their own canonical form: BE(LOCAL), BED(LOCAL),
# BOP, CQD, etc. A leading short uppercase code, optionally followed by a
# parenthesized qualifier. Anchored end-to-end so we don't match e.g. "TEC"
# as if it were a local-policy code.
_LOCAL_POLICY_RE = re.compile(r"^([A-Z]{2,5})(\([A-Z]+\))?$")


@dataclass
class VerificationResult:
    """Result of a citation lookup against the bundled corpus."""

    verified: bool
    authority: str  # canonical normalized citation
    quoted_text: str | None
    source_file: str | None
    status: str  # "verified" | "corpus_gap" | "partial_match" | "unknown"
    diagnostic: str | None = None


def _normalize(citation: str) -> tuple[str | None, str | None]:
    """Normalize a raw citation to (code, section_or_rule).

    Returns (None, None) if the citation is a bare section number without
    a code prefix — those are ambiguous and not auto-expanded. Local-policy
    codes (BE(LOCAL), BED(LOCAL), CQD, BOP, ...) are their own canonical
    form and are returned as code="LOCAL".
    """
    raw = citation.strip()
    lower = raw.lower()

    # Early short-circuit: Texas House Bill citations like "HB3" (no space
    # between "HB" and the number) fail the standard alias boundary because
    # `(?=\W|$)` rejects the immediate digit. Match the whole pattern here.
    hb_m = re.match(
        r"\s*(?:HB|H\.B\.|H\. B\.|House\s+Bill)\s*(\d+)",
        raw,
        re.IGNORECASE,
    )
    if hb_m:
        return "TXHB", f"HB{hb_m.group(1)}"

    # Match the longest code alias that appears as a prefix-ish token.
    # Use non-word boundaries that work even when the alias ends in "." —
    # \b fails on trailing punctuation because \b requires a \w/\W transition.
    code: str | None = None
    for alias in sorted(_CODE_ALIASES, key=len, reverse=True):
        start = r"(?:^|(?<=\W))"
        end = r"(?=\W|$)"
        if re.search(rf"{start}{re.escape(alias)}{end}", lower):
            code = _CODE_ALIASES[alias]
            break

    if code is None:
        # Local-policy path: the whole citation is the canonical code
        # (BE(LOCAL), BED(LOCAL), CQD, BOP, etc.).
        lp = _LOCAL_POLICY_RE.match(raw)
        if lp:
            return "LOCAL", raw
        return None, None

    if code == "MSRB":
        m = _MSRB_RE.search(raw)
        return (code, m.group(1)) if m else (code, None)

    if code == "SEC":
        m = _SEC_RULE_RE.search(raw)
        return (code, m.group(1)) if m else (code, None)

    if code == "TXCONST":
        m = _CONST_RE.search(raw)
        return (code, f"art. {m.group(1).upper()} §{m.group(2)}") if m else (code, None)

    if code == "TXHB":
        # Texas House Bill: "HB3", "HB 3", "H.B. 3", optional session suffix
        # like "(86R, 2019)" or "(2019)". Normalize to "HB<N>".
        m = re.search(
            r"\b(?:HB|H\.B\.|H\. B\.|House\s+Bill)\s*(\d+)", raw, re.IGNORECASE
        )
        return (code, f"HB{m.group(1)}") if m else (code, None)

    if code == "HSC":
        # HSC may be cited as "Chapter 390" (chapter-level) or "§390.001" (section).
        m = _SECTION_RE.search(raw)
        if m:
            return (code, m.group(1).replace("–", "-"))
        m = re.search(r"(?:Chapter|Ch\.)\s*(\d+)", raw, re.IGNORECASE)
        return (code, m.group(1)) if m else (code, None)

    m = _SECTION_RE.search(raw)
    if not m:
        return (code, None)
    # Normalize em-dash → hyphen so ranges match consistently with headings.
    return (code, m.group(1).replace("–", "-"))


def _canonical(code: str, section: str) -> str:
    if code == "MSRB":
        return f"MSRB {section}"
    if code == "SEC":
        return f"SEC Rule {section}"
    if code == "TXCONST":
        return f"Tex. Const. {section}"
    if code == "TXHB":
        return section  # e.g., "HB3"
    if code == "HSC":
        # HSC headings use a chapter-level form for now ("HSC Chapter 390").
        # A bare chapter number like "390" normalizes to "HSC Chapter 390";
        # a section like "390.001" stays as "HSC §390.001".
        if "." not in section:
            return f"HSC Chapter {section}"
        return f"HSC §{section}"
    if code == "LOCAL":
        return section  # BE(LOCAL), BED(LOCAL), CQD, ... are their own canonical
    if code == "TAX":
        return f"Tax Code §{section}"
    return f"{code} §{section}"


# --- Corpus scan ------------------------------------------------------------

# Matches a level-3 heading like "### TEC §11.151(b)".
_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)

# A real blockquote begins with "> " (possibly after whitespace) and is not
# an HTML comment. The scaffolded placeholders are HTML comments only, so a
# section with no "> " line is a corpus gap.
_BLOCKQUOTE_LINE_RE = re.compile(r"^>\s?(.*)$")


def _extract_blockquote(text: str, start: int) -> str | None:
    """Extract the verbatim blockquote that follows a matched heading.

    Scans from `start` until the next level-3 heading or end-of-file, pulls
    the first contiguous `> ` block. Returns None if no blockquote is
    present (corpus gap).
    """
    # End at the next heading of the same level or deeper-up.
    next_heading = re.search(r"^##+\s", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    section = text[start:end]

    lines = section.splitlines()
    quote_lines: list[str] = []
    in_quote = False
    for line in lines:
        m = _BLOCKQUOTE_LINE_RE.match(line)
        if m:
            in_quote = True
            quote_lines.append(m.group(1).rstrip())
        elif in_quote and line.strip() == "":
            # Blank line inside a quote block — keep the block together.
            quote_lines.append("")
        elif in_quote:
            # Non-blockquote, non-blank line ends the quote.
            break

    # Trim trailing blank lines.
    while quote_lines and quote_lines[-1] == "":
        quote_lines.pop()

    if not quote_lines:
        return None
    return "\n".join(quote_lines).strip()


def verify(citation: str, corpus_dir: Path | None = None) -> VerificationResult:
    """Verify a citation against the bundled corpus.

    Accepted variants include:
        "TEC §11.151(b)"
        "Texas Education Code 11.151(b)"
        "Tex. Educ. Code §11.151(b)"
        "TGC §551.074"
        "Government Code §551.074"
        "MSRB Rule G-42"
        "MSRB G-42"

    Bare section numbers without a code prefix (e.g., "§11.151(b)" or
    "11.151(b)") return "unknown" — the verifier does not guess which code.

    Pass `corpus_dir` to point at an alternate directory (tests, Brock ISD
    local policy subdir). Defaults to the bundled corpus.
    """
    corpus = corpus_dir if corpus_dir is not None else CORPUS_DIR

    # TASB guidance is not controlling authority. Short-circuit with a
    # diagnostic that steers the caller to board-adopted policy or statute.
    # See principles.md §I Principle 1.
    if re.search(r"\bTASB\b", citation):
        return VerificationResult(
            verified=False,
            authority=citation.strip(),
            quoted_text=None,
            source_file=None,
            status="unknown",
            diagnostic=(
                "TASB is guidance from a member organization, not controlling "
                "authority. Cite the board-adopted local policy (e.g., BE(LOCAL)) "
                "or the underlying statute instead. See principles.md §I "
                "Principle 1 (policy controls over procedure)."
            ),
        )

    code, section = _normalize(citation)

    if code is None or section is None:
        return VerificationResult(
            verified=False,
            authority=citation.strip(),
            quoted_text=None,
            source_file=None,
            status="unknown",
            diagnostic=(
                "Citation is missing a recognized code prefix (TEC, TGC, TAC, "
                "MSRB) or a section/rule number. Do not silently expand; ask "
                "the caller to supply the specific authority."
            ),
        )

    canonical = _canonical(code, section)

    if not corpus.exists():
        return VerificationResult(
            verified=False,
            authority=canonical,
            quoted_text=None,
            source_file=None,
            status="unknown",
            diagnostic=f"Corpus directory not found at {corpus}.",
        )

    # § and §§ are fungible in headings — "§§45.051-45.063" and "§45.051-45.063"
    # refer to the same authority. Also accept a descriptive parenthetical
    # suffix on the heading (e.g., "HB3 (86R, 2019)", "TEC §§45.051-45.063
    # (Subchapter C: PSF Bond Guarantee Program)"). The suffix MUST be
    # preceded by whitespace — that prevents silent expansion of a bare
    # section citation into a subsection citation like "(b)".
    # NOTE: re.escape does NOT backslash `§` — replace the raw character.
    flex = re.escape(canonical).replace("§", "§§?")
    exact_heading_re = re.compile(rf"^###\s+{flex}(?:\s+\(.*\))?\s*$", re.MULTILINE)

    partial_candidates: list[tuple[str, str]] = []  # (heading, source_file)

    for md_file in sorted(corpus.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        # Use relative path so "brock-isd/be-local.md" stays distinguishable.
        rel = md_file.relative_to(corpus).as_posix()

        m = exact_heading_re.search(text)
        if m:
            quote = _extract_blockquote(text, m.end())
            if quote:
                return VerificationResult(
                    verified=True,
                    authority=canonical,
                    quoted_text=quote,
                    source_file=rel,
                    status="verified",
                )
            return VerificationResult(
                verified=False,
                authority=canonical,
                quoted_text=None,
                source_file=rel,
                status="corpus_gap",
                diagnostic=(
                    f"Heading for {canonical} is present in {rel} "
                    f"but the verbatim blockquote has not been populated. "
                    f"Log to logs/corpus_gaps.log; the agent may name the "
                    f"authority but must not invent text to quote."
                ),
            )

        # Look for near-miss headings under the same code prefix (e.g., the
        # incoming citation is TEC §11.151 but the corpus only has §11.151(b)).
        for heading_match in _HEADING_RE.finditer(text):
            heading = heading_match.group(1)
            if heading.startswith(f"{code} §") and section in heading:
                partial_candidates.append((heading, rel))
            elif code == "MSRB" and heading.startswith("MSRB ") and section in heading:
                partial_candidates.append((heading, rel))

    # Catch near-misses at the section-number level with a proper boundary,
    # so "TEC §11.151" matches "TEC §11.151(b)" but NOT "TEC §11.1511(...)".
    # A section-number boundary is anything that isn't a digit.
    section_root = re.match(r"(\d+\.\d+)", section)
    if section_root:
        root = section_root.group(1)
        partial_candidates = []  # reset; we want only boundary-correct matches
        root_re = re.compile(rf"^{re.escape(code)}\s+§{re.escape(root)}(?!\d)")
        for md_file in sorted(corpus.rglob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            rel = md_file.relative_to(corpus).as_posix()
            for heading_match in _HEADING_RE.finditer(text):
                heading = heading_match.group(1)
                if root_re.match(heading) and heading != canonical:
                    partial_candidates.append((heading, rel))

    if partial_candidates:
        # Deduplicate while preserving order.
        seen: set[str] = set()
        unique = [
            (h, f) for h, f in partial_candidates if not (h in seen or seen.add(h))
        ]
        candidates_str = "; ".join(f"{h} (in {f})" for h, f in unique)
        return VerificationResult(
            verified=False,
            authority=canonical,
            quoted_text=None,
            source_file=None,
            status="partial_match",
            diagnostic=(
                f"No exact heading for {canonical}. Near-miss candidates in "
                f"corpus: {candidates_str}. Do not silently expand — the "
                f"caller must choose a specific authority or soften the claim."
            ),
        )

    return VerificationResult(
        verified=False,
        authority=canonical,
        quoted_text=None,
        source_file=None,
        status="unknown",
        diagnostic=(
            f"{canonical} not found in corpus. Log to "
            f"logs/unverified_citations.log for Day 3 eval review."
        ),
    )


# --- Batch and introspection helpers ----------------------------------------


def verify_all(
    citations: list[str], corpus_dir: Path | None = None
) -> list[VerificationResult]:
    """Verify a batch of citations. Preserves order."""
    return [verify(c, corpus_dir=corpus_dir) for c in citations]


# Citation-extraction patterns. Ordered most-specific to least-specific so
# that "Texas Education Code 11.151(b)" matches before bare "§11.151(b)".
_CITATION_PATTERNS: list[re.Pattern[str]] = [
    # Texas Constitution — e.g. "Tex. Const. art. VII §5", "Article VII, Section 5"
    re.compile(
        r"(?:Tex(?:as)?\.?\s+)?Const(?:itution|\.)?\s+art(?:icle|\.)?\s+[IVX]+[,\s]*"
        r"(?:§|Section|Sec\.)\s*\d+",
        re.IGNORECASE,
    ),
    re.compile(
        r"Article\s+[IVX]+[,\s]+(?:§|Section|Sec\.)\s*\d+"
        r"(?:\s+of\s+the\s+Texas\s+Constitution)?",
        re.IGNORECASE,
    ),
    # SEC Rule — e.g. "SEC Rule 15c2-12"
    re.compile(r"SEC\s+Rule\s+\d+[A-Za-z]+\d+(?:-\d+)?", re.IGNORECASE),
    # MSRB Rule — e.g. "MSRB Rule G-42", "MSRB G-42"
    re.compile(r"MSRB(?:\s+Rule)?\s+[A-Z]-\d+"),
    # Texas Tax Code — "Tax Code §26.06"
    re.compile(
        r"(?:Tex(?:as)?\.?\s+)?Tax\s+Code\s+§?\s*\d+\.\d+[A-Za-z0-9()]*",
        re.IGNORECASE,
    ),
    # Texas Health & Safety Code — "HSC Chapter 390", "Health & Safety Code Ch. 390"
    re.compile(
        r"(?:Tex(?:as)?\.?\s+)?Health\s*(?:and|&)\s*Safety\s+Code\s+"
        r"(?:Chapter|Ch\.)\s*\d+",
        re.IGNORECASE,
    ),
    re.compile(r"\bHSC\s+(?:Chapter|Ch\.)\s*\d+", re.IGNORECASE),
    # Texas House Bills — "HB3", "HB 3", "H.B. 3", "House Bill 3" (with optional session suffix)
    re.compile(
        r"\b(?:HB|H\.B\.|H\. B\.|House\s+Bill)\s*\d+"
        r"(?:\s*\(\d+R?(?:,\s*\d{4})?\))?",
        re.IGNORECASE,
    ),
    # Qualified code + section — e.g. "Texas Education Code 11.151(b)",
    # "Tex. Educ. Code §11.151(b)", "TEC §11.151(b)", "Government Code 551.074"
    re.compile(
        r"(?:Tex(?:as)?\.?\s+)?"
        r"(?:Ed(?:ucation|uc)?\.?|Gov(?:ernment|t|'t)?\.?|Admin(?:istrative)?\.?)?\s*"
        r"Code\s+§{0,2}\s*\d+\.\d+[A-Za-z0-9()]*(?:[–\-]\d+\.\d+[A-Za-z0-9()]*)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:TEC|TGC|TAC)\s+§{0,2}\s*\d+\.\d+[A-Za-z0-9()]*"
        r"(?:[–\-]\d+\.\d+[A-Za-z0-9()]*)?"
    ),
    # Local-policy codes — BE(LOCAL), BED(LOCAL), etc.
    re.compile(r"\b[A-Z]{2,5}\([A-Z]+\)"),
]


def extract_citations(text: str) -> list[str]:
    """Find citation-like strings in arbitrary text.

    Used by the Day 3 eval harness to diff what the agent cited against
    what the hand version cites. Ordered dedupe: preserves first-occurrence
    order across the input text.
    """
    found: list[tuple[int, str]] = []  # (position, matched_string)
    for pat in _CITATION_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(0).strip(" ,.;:")
            # Balance parens: drop a lone trailing ")" that has no matching "(",
            # but keep "(b)" / "(a)(5)" etc.
            while raw.endswith(")") and raw.count("(") < raw.count(")"):
                raw = raw[:-1].rstrip(" ,.;:")
            found.append((m.start(), raw))

    # Sort by position, then dedupe while preserving first-occurrence order.
    found.sort(key=lambda x: x[0])
    seen: set[str] = set()
    out: list[str] = []
    for _, s in found:
        key = re.sub(r"\s+", " ", s).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


@dataclass
class CorpusEntry:
    """One heading in the bundled corpus."""

    authority: str
    source_file: str
    has_text: bool  # True iff a populated blockquote follows the heading


def list_corpus_entries(corpus_dir: Path | None = None) -> list[CorpusEntry]:
    """Enumerate every authority heading in the corpus.

    Used by the Day 3 eval harness to diff the corpus against the set of
    citations emitted during a pre-read, surfacing: (a) entries with
    scaffold headings but no text (`has_text=False`), so Toby can prioritize
    which to populate; and (b) authorities named in output that don't
    correspond to any corpus entry.
    """
    corpus = corpus_dir if corpus_dir is not None else CORPUS_DIR
    entries: list[CorpusEntry] = []
    if not corpus.exists():
        return entries
    for md_file in sorted(corpus.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        rel = md_file.relative_to(corpus).as_posix()
        for m in _HEADING_RE.finditer(text):
            authority = m.group(1)
            quote = _extract_blockquote(text, m.end())
            entries.append(
                CorpusEntry(
                    authority=authority,
                    source_file=rel,
                    has_text=quote is not None,
                )
            )
    return entries


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]

    if args and args[0] == "--list":
        # Snapshot of corpus coverage — used by the eval harness and by Toby
        # to see at a glance which headings still need verbatim text.
        entries = list_corpus_entries()
        by_file: dict[str, list[CorpusEntry]] = {}
        for e in entries:
            by_file.setdefault(e.source_file, []).append(e)
        total = len(entries)
        populated = sum(1 for e in entries if e.has_text)
        print(
            f"Corpus: {len(by_file)} files, {total} headings, "
            f"{populated} with text, {total - populated} scaffolded"
        )
        print()
        for f in sorted(by_file):
            print(f"  {f}:")
            for e in by_file[f]:
                flag = "✓ text" if e.has_text else "· scaffold"
                print(f"    {flag:12}  {e.authority}")
        sys.exit(0)

    cites = args or [
        "TEC §11.151(b)",
        "Texas Education Code 11.151(b)",
        "TGC §551.074",
        "§11.151(b)",
        "TEC §11",
        "TEC §99.999",
        "MSRB G-42",
        "BE(LOCAL)",
        "TASB model policy",
    ]
    for c in cites:
        r = verify(c)
        print(f"{c!r:40} → status={r.status:14} verified={r.verified}")
        if r.diagnostic:
            print(f"   note: {r.diagnostic}")

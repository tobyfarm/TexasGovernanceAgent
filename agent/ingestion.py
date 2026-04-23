"""PDF ingestion → list[AgendaItem].

Strategy per AGENT_A.md §"PDF ingestion strategy":
    1. pypdf first. If density < 100 words/page avg, fall back to pdfplumber.
    2. Regex-based agenda-item boundary detection (Brock/TASB patterns).
    3. --manual-split YAML escape hatch: {item_id: [start_page, end_page]}.
    4. If nothing parses, emit a single 'full_packet' item so the pipeline
       still runs. Ingestion quality is Day-2 work.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pdfplumber
import yaml
from pypdf import PdfReader

from agent.types import AgendaItem, ItemType

logger = logging.getLogger(__name__)

MIN_WORDS_PER_PAGE = 100

# Candidate patterns for top-level agenda markers. Titles must start with a
# letter and have substantive content so we don't pick up dollar amounts in
# a check register (`138.40  N`) or row labels in a table.
_MIN_TITLE_CHARS = 5
_ITEM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "numbered_letter",
        re.compile(r"^\s*(?P<id>\d+[A-Z])\.\s+(?P<title>[A-Za-z].{4,200}?)\s*$", re.MULTILINE),
    ),
    (
        "letter_dot",
        re.compile(r"^\s*(?P<id>[A-Z])\.\s+(?P<title>[A-Z][A-Za-z].{4,200}?)\s*$", re.MULTILINE),
    ),
    (
        "item_kw",
        re.compile(
            r"^\s*Item\s+(?P<id>\d+[A-Z]?)[\.\:\s]+(?P<title>[A-Za-z].{4,200}?)\s*$",
            re.MULTILINE | re.IGNORECASE,
        ),
    ),
    (
        # 1-2 digits, dot, 1-2 digits (blocks 3-digit decimals like 138.40).
        # Title must start with a letter. Fits real sub-item numbering (1.1,
        # 2.3) without matching financial figures or statute citations.
        "dotted",
        re.compile(
            r"^\s*(?P<id>\d{1,2}\.\d{1,2})(?!\d)\s+(?P<title>[A-Za-z].{4,200}?)\s*$",
            re.MULTILINE,
        ),
    ),
]

# Agenda listings are concentrated at the start of a board book. If a
# pattern's first match is past this fraction of the document, that pattern
# is likely matching body content (tables, statute citations, check lines),
# not the agenda — skip it.
_AGENDA_HEAD_FRACTION = 0.2

_TYPE_KEYWORDS: list[tuple[ItemType, tuple[str, ...]]] = [
    ("CLOSED_SESSION", ("closed session", "executive session", "§551.071", "§551.072", "§551.074")),
    ("CONSENT", ("consent agenda", "consent item")),
    ("ACTION", ("action item", "motion", "board action", "approve", "adopt", "authorize")),
    ("INFORMATIONAL", ("informational", "for information only", "report")),
    ("DISCUSSION", ("discussion", "presentation", "update")),
]


def _extract_text_pypdf(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]


def _extract_text_pdfplumber(pdf_path: Path) -> list[str]:
    pages: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text(layout=True) or "")
    return pages


def _should_fall_back(pages: list[str]) -> bool:
    if not pages:
        return True
    total_words = sum(len(p.split()) for p in pages)
    avg = total_words / len(pages)
    return avg < MIN_WORDS_PER_PAGE


def extract_pages(pdf_path: Path) -> list[str]:
    """Return one string per page. Falls back from pypdf to pdfplumber on sparse output."""
    pages = _extract_text_pypdf(pdf_path)
    if _should_fall_back(pages):
        logger.info(
            "pypdf extraction sparse (avg < %d wpp); falling back to pdfplumber", MIN_WORDS_PER_PAGE
        )
        pages = _extract_text_pdfplumber(pdf_path)
    return pages


def _classify_item(text: str) -> ItemType:
    lower = text.lower()
    for item_type, keywords in _TYPE_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return item_type
    return "DISCUSSION"


def _find_boundaries(pages: list[str]) -> list[tuple[str, str, int, int]]:
    """Find agenda item boundaries across pages.

    Returns list of (item_id, title, start_page_1indexed, end_page_1indexed).
    Page numbers are 1-indexed to match PDF convention.

    Selection strategy:
      1. Evaluate every candidate regex family against the full document.
      2. Drop any family whose first match is past _AGENDA_HEAD_FRACTION of
         the doc — the real agenda is at the top.
      3. Require each match's title to be substantive (letter-leading, min
         length enforced in the regex).
      4. Pick the family with the most surviving matches; ties broken by
         declaration order in _ITEM_PATTERNS.
    """
    full_text = "\n".join(pages)
    doc_len = max(len(full_text), 1)
    head_cutoff = int(doc_len * _AGENDA_HEAD_FRACTION)

    best: list[tuple[str, str, int]] = []
    best_name = ""
    for name, pattern in _ITEM_PATTERNS:
        matches: list[tuple[str, str, int]] = []
        seen_ids: set[str] = set()
        for m in pattern.finditer(full_text):
            title = m.group("title").strip()
            if len(title) < _MIN_TITLE_CHARS:
                continue
            item_id = m.group("id")
            # Keep only the first occurrence of each ID — body content often
            # repeats the agenda letter alongside fuller item text.
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            matches.append((item_id, title, m.start()))
        if not matches:
            continue
        if matches[0][2] > head_cutoff:
            logger.debug(
                "pattern=%s: first match at offset %d > cutoff %d; skipping",
                name,
                matches[0][2],
                head_cutoff,
            )
            continue
        if len(matches) > len(best):
            best = matches
            best_name = name

    if len(best) < 2:
        return []

    logger.info("matched %d agenda boundaries using pattern=%s", len(best), best_name)

    toc_end_page = _infer_toc_end(pages, best)
    return _assign_body_ranges(pages, best, toc_end_page)


def _infer_toc_end(pages: list[str], toc_entries: list[tuple[str, str, int]]) -> int:
    """Last page that contains TOC entries. Content pages start after."""
    offsets: list[int] = []
    cumulative = 0
    for page in pages:
        offsets.append(cumulative)
        cumulative += len(page) + 1
    last_page = 1
    for _, _, off in toc_entries:
        for i, page_off in enumerate(offsets):
            if off >= page_off:
                last_page = max(last_page, i + 1)
    return last_page


def _assign_body_ranges(
    pages: list[str],
    toc_entries: list[tuple[str, str, int]],
    toc_end_page: int,
) -> list[tuple[str, str, int, int]]:
    """For each TOC item, locate where its body content begins in pages after
    the TOC and return page ranges that span to the next item's body start.

    When an item's body can't be located (line-wrapped titles, missing body,
    etc.) the item is placed sequentially between the previous and next
    located items so nothing collapses back to page 1."""
    body_search_start = toc_end_page + 1
    body_starts: list[int | None] = [
        _find_body_start(pages, title, from_page=body_search_start)
        for _, title, _ in toc_entries
    ]

    # Fill gaps: if item i has no body start, interpolate between the nearest
    # neighbor matches on either side.
    resolved = list(body_starts)
    for i, start in enumerate(resolved):
        if start is not None:
            continue
        prev = next((resolved[j] for j in range(i - 1, -1, -1) if resolved[j] is not None), None)
        nxt = next((resolved[j] for j in range(i + 1, len(resolved)) if resolved[j] is not None), None)
        if prev is not None and nxt is not None:
            resolved[i] = min(prev + 1, nxt)
        elif prev is not None:
            resolved[i] = min(prev + 1, len(pages))
        elif nxt is not None:
            resolved[i] = max(nxt - 1, body_search_start)
        else:
            # Nothing located at all — fall back to the body start.
            resolved[i] = body_search_start

    boundaries: list[tuple[str, str, int, int]] = []
    for i, (item_id, title, _offset) in enumerate(toc_entries):
        start = resolved[i]
        assert start is not None
        if i + 1 < len(toc_entries):
            nxt_start = resolved[i + 1] or len(pages)
            end = max(start, nxt_start - 1)
        else:
            end = len(pages)
        boundaries.append((item_id, title, start, end))
    return boundaries


def _find_body_start(pages: list[str], title: str, *, from_page: int) -> int | None:
    """Return the 1-indexed page where the given title first appears starting
    at from_page. Match is case-insensitive and tolerant of layout whitespace."""
    # Titles often have a mid-word split due to line wraps; normalise both
    # sides by collapsing runs of whitespace.
    norm_title = re.sub(r"\s+", " ", title).strip().lower()
    if len(norm_title) < _MIN_TITLE_CHARS:
        return None
    for idx in range(max(from_page - 1, 0), len(pages)):
        norm_page = re.sub(r"\s+", " ", pages[idx]).lower()
        if norm_title in norm_page:
            return idx + 1
    return None


def _slice_pages(pages: list[str], start: int, end: int) -> str:
    return "\n\n".join(pages[start - 1 : end])


def _load_manual_split(path: Path) -> dict[str, tuple[int, int]]:
    data = yaml.safe_load(path.read_text())
    out: dict[str, tuple[int, int]] = {}
    for item_id, span in (data or {}).items():
        start, end = span
        out[str(item_id)] = (int(start), int(end))
    return out


def extract_agenda_items(
    pdf_path: Path,
    *,
    manual_split: Path | None = None,
) -> list[AgendaItem]:
    """Parse a board book PDF into agenda items.

    If `manual_split` is provided (YAML mapping item_id → [start, end]), use that
    instead of regex detection. If regex detection finds nothing, fall back to a
    single 'full_packet' item spanning the whole document.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = extract_pages(pdf_path)
    if not pages:
        raise ValueError(f"No text extracted from {pdf_path}")

    if manual_split is not None:
        split = _load_manual_split(manual_split)
        items: list[AgendaItem] = []
        for item_id, (start, end) in split.items():
            raw = _slice_pages(pages, start, end)
            title = raw.splitlines()[0].strip()[:200] if raw.strip() else item_id
            items.append(
                AgendaItem(
                    item_id=item_id,
                    title=title,
                    pages=(start, end),
                    raw_text=raw,
                    item_type=_classify_item(raw),
                )
            )
        return items

    boundaries = _find_boundaries(pages)

    if not boundaries:
        logger.warning("no agenda boundaries detected; returning whole packet as one item")
        return [
            AgendaItem(
                item_id="full_packet",
                title=pdf_path.stem,
                pages=(1, len(pages)),
                raw_text="\n\n".join(pages),
                item_type="DISCUSSION",
            )
        ]

    items = []
    for item_id, title, start, end in boundaries:
        raw = _slice_pages(pages, start, end)
        items.append(
            AgendaItem(
                item_id=item_id,
                title=title[:200],
                pages=(start, end),
                raw_text=raw,
                item_type=_classify_item(raw),
            )
        )
    return items

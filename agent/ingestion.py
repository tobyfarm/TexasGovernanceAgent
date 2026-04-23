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

# Ordered by specificity. First match wins per line.
_ITEM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("numbered_letter", re.compile(r"^\s*(?P<id>\d+[A-Z])\.\s+(?P<title>.+?)\s*$", re.MULTILINE)),
    ("letter_dot", re.compile(r"^\s*(?P<id>[A-Z])\.\s+(?P<title>.{5,200})\s*$", re.MULTILINE)),
    (
        "item_kw",
        re.compile(
            r"^\s*Item\s+(?P<id>\d+[A-Z]?)[\.\:\s]+(?P<title>.+?)\s*$", re.MULTILINE | re.IGNORECASE
        ),
    ),
    ("dotted", re.compile(r"^\s*(?P<id>\d+\.\d+)\s+(?P<title>.+?)\s*$", re.MULTILINE)),
]

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
    """
    full_text = "\n".join(pages)

    # Find the pattern family that yields the most matches — keeps us from
    # mixing e.g. list letters with real agenda letters.
    best: list[tuple[str, str, int]] = []
    best_name = ""
    for name, pattern in _ITEM_PATTERNS:
        matches: list[tuple[str, str, int]] = []
        for m in pattern.finditer(full_text):
            matches.append((m.group("id"), m.group("title").strip(), m.start()))
        if len(matches) > len(best):
            best = matches
            best_name = name

    if len(best) < 2:
        return []

    logger.info("matched %d agenda boundaries using pattern=%s", len(best), best_name)

    # Map character offset → page number.
    page_offsets: list[int] = []
    cumulative = 0
    for page in pages:
        page_offsets.append(cumulative)
        cumulative += len(page) + 1

    def page_for_offset(offset: int) -> int:
        page = 1
        for i, po in enumerate(page_offsets):
            if offset >= po:
                page = i + 1
        return page

    boundaries: list[tuple[str, str, int, int]] = []
    for i, (item_id, title, offset) in enumerate(best):
        start_page = page_for_offset(offset)
        if i + 1 < len(best):
            next_offset = best[i + 1][2]
            end_page = max(start_page, page_for_offset(next_offset - 1))
        else:
            end_page = len(pages)
        boundaries.append((item_id, title, start_page, end_page))
    return boundaries


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

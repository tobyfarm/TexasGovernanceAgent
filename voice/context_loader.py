"""Load board book + pre-read + doctrine excerpt for a Gemini Live session.

The Gemini 3.1 Flash Live context window is 128k tokens. We target ≤60k at
session start, leaving ~68k for the back-and-forth conversation.

Three blocks, emitted as seeded user-role turns before the first real user
input. In order:

    BLOCK 1 OF 3  BOARD BOOK
    BLOCK 2 OF 3  GENERATED PRE-READ
    BLOCK 3 OF 3  DOCTRINE EXCERPT (principles.md §I + §IV)

Budget (tokens, using the ~4-chars-per-token heuristic):
    board book       ≤ 40_000
    pre-read         ≤ 15_000
    doctrine excerpt ≤  4_000
    ----------------------------
    total seed       ≤ 59_000
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover — pypdf is a project dependency
    PdfReader = None  # type: ignore[assignment]

log = logging.getLogger("voice.context_loader")

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"
PRINCIPLES_PATH = REPO_ROOT / "skills" / "governance-principles" / "principles.md"

# Token-ish budgets. Characters, not true tokens — keeps the loader
# dependency-free. 4 chars ≈ 1 token is a stable GPT-family heuristic.
CHARS_PER_TOKEN = 4
BUDGET_BOARDBOOK_CHARS = 40_000 * CHARS_PER_TOKEN
BUDGET_PREREAD_CHARS = 15_000 * CHARS_PER_TOKEN
# §IV (voice notes) is small (~1.7k chars) and always preserved in full;
# §I (16 principles) is truncated to fit the remainder of this budget.
BUDGET_DOCTRINE_CHARS = 6_000 * CHARS_PER_TOKEN


@dataclass
class ContextBlock:
    """One seeded history turn. Rendered as a user message with a header."""

    label: str
    text: str

    def as_turn(self) -> dict:
        header = f"--- {self.label} ---"
        return {
            "role": "user",
            "parts": [{"text": f"{header}\n{self.text}"}],
        }


# ---------------------------------------------------------------------------
# Document resolution
# ---------------------------------------------------------------------------


def resolve_paths(document_id: str) -> tuple[Path, Path]:
    """Return (board_book_pdf, generated_preread_md) for a document id.

    Naming convention in examples/: {document_id}.pdf and
    {document_id}_output.md (the generated pre-read is gitignored).
    """
    return (
        EXAMPLES_DIR / f"{document_id}.pdf",
        EXAMPLES_DIR / f"{document_id}_output.md",
    )


# ---------------------------------------------------------------------------
# Block builders
# ---------------------------------------------------------------------------


def _truncate(text: str, limit: int, label: str) -> str:
    if len(text) <= limit:
        return text
    head = text[:limit]
    omitted = len(text) - limit
    log.warning("%s truncated: dropped %d chars (budget %d)", label, omitted, limit)
    return (
        head
        + f"\n\n[... truncated: {omitted} characters omitted to respect token budget ...]"
    )


def _extract_pdf(pdf_path: Path) -> str:
    if PdfReader is None:
        raise RuntimeError("pypdf is not installed")
    if not pdf_path.exists():
        raise FileNotFoundError(f"board book PDF not found: {pdf_path}")
    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001 — per-page extraction errors
            log.warning("pdf page %d extraction failed: %s", i, exc)
            continue
        if text.strip():
            parts.append(f"[Page {i}]\n{text.strip()}")
    return "\n\n".join(parts)


def build_board_book_block(
    document_id: str, pdf_path: Path | None = None
) -> ContextBlock:
    pdf_path = pdf_path or EXAMPLES_DIR / f"{document_id}.pdf"
    text = _extract_pdf(pdf_path)
    text = _truncate(text, BUDGET_BOARDBOOK_CHARS, "board book")
    return ContextBlock(
        label=f"BLOCK 1 OF 3: BOARD BOOK ({document_id})",
        text=text,
    )


def build_preread_block(document_id: str, md_path: Path | None = None) -> ContextBlock:
    md_path = md_path or EXAMPLES_DIR / f"{document_id}_output.md"
    if not md_path.exists():
        raise FileNotFoundError(f"generated pre-read not found: {md_path}")
    text = md_path.read_text(encoding="utf-8").strip()
    text = _truncate(text, BUDGET_PREREAD_CHARS, "pre-read")
    return ContextBlock(
        label=f"BLOCK 2 OF 3: GENERATED PRE-READ ({document_id})",
        text=text,
    )


_SECTION_HEADING_RE = re.compile(r"^## +([IVX]+)\. .+", re.MULTILINE)


def _split_sections(source: str) -> dict[str, str]:
    """Split principles.md into a {numeral: section_text} dict."""
    matches = list(_SECTION_HEADING_RE.finditer(source))
    if not matches:
        raise ValueError("no `## <ROMAN>. ...` sections found in principles.md")
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        numeral = match.group(1)
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(source)
        sections[numeral] = source[start:end].rstrip()
    return sections


def build_doctrine_block(principles_path: Path = PRINCIPLES_PATH) -> ContextBlock:
    """Build the §I + §IV excerpt, preserving §IV in full.

    §IV (voice and tone notes) is the voice guardrail and must not be
    truncated — it's tiny. §I is the full principles catalog and may be
    truncated tail-first when the combined excerpt exceeds the budget.
    """
    if not principles_path.exists():
        raise FileNotFoundError(f"principles file not found: {principles_path}")
    sections = _split_sections(principles_path.read_text(encoding="utf-8"))
    part_iv = sections.get("IV", "")
    part_i = sections.get("I", "")

    remaining = max(BUDGET_DOCTRINE_CHARS - len(part_iv), 0)
    part_i = _truncate(part_i, remaining, "doctrine §I")
    excerpt = f"{part_i}\n\n{part_iv}".strip()

    return ContextBlock(
        label="BLOCK 3 OF 3: DOCTRINE EXCERPT (principles.md §I + §IV)",
        text=excerpt,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def load_session_context(document_id: str) -> list[ContextBlock]:
    """Return the three seed blocks for a given document.

    Any block whose source file is missing is skipped with a warning. This
    keeps the bridge usable for bare echo tests (no PDF on disk) while
    returning the full three-block seed when the inputs exist.
    """
    if document_id in ("", "unknown", "echo_test"):
        # Day-1 echo test harness — skip context to keep the session minimal.
        return []

    blocks: list[ContextBlock] = []
    try:
        blocks.append(build_board_book_block(document_id))
    except FileNotFoundError as exc:
        log.warning("board book block skipped: %s", exc)
    try:
        blocks.append(build_preread_block(document_id))
    except FileNotFoundError as exc:
        log.warning("pre-read block skipped: %s", exc)
    try:
        blocks.append(build_doctrine_block())
    except FileNotFoundError as exc:
        log.warning("doctrine block skipped: %s", exc)

    total_chars = sum(len(b.text) for b in blocks)
    log.info(
        "loaded %d block(s) for %s: ~%d chars (~%d tokens)",
        len(blocks),
        document_id,
        total_chars,
        total_chars // CHARS_PER_TOKEN,
    )
    return blocks

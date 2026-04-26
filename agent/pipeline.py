"""End-to-end pipeline orchestrator.

Stages:
    1. generator (Claude Opus, streaming)
    2. legal     (citation validator, regex + httpx)
    3. red_team  (Claude Opus, streaming)

Yields SSE-ready dict events. The final event carries the run_id and the
written markdown.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from agent.citation_validator import validate_citations
from agent.generator import stream_generator
from agent.pdf import extract_text
from agent.red_team import stream_red_team

REPO_ROOT = Path(__file__).resolve().parent.parent
PRINCIPLES_PATH = REPO_ROOT / "skills" / "governance-principles" / "principles.md"
GOLD_STANDARD_PATH = REPO_ROOT / "examples" / "brock_april_13_2026_prereadhand.md"
RUNS_DIR = REPO_ROOT / "runs"

# Cap PDF text to keep prompts under context window
MAX_PDF_CHARS = 250_000


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _trim_pdf(pdf_text: str) -> str:
    if len(pdf_text) <= MAX_PDF_CHARS:
        return pdf_text
    return pdf_text[:MAX_PDF_CHARS] + "\n\n[... PDF truncated for context window ...]"


async def run_pipeline(pdf_bytes: bytes) -> AsyncIterator[dict]:
    """Run the full 3-stage pipeline. Yields SSE-shaped dict events."""
    # Lazy-load env vars (in case the API server didn't already)
    load_dotenv(dotenv_path=REPO_ROOT / ".env", override=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Prep ----
    try:
        raw_pdf_text = extract_text(pdf_bytes)
        pdf_text = _trim_pdf(raw_pdf_text)
        principles_md = _read_text(PRINCIPLES_PATH)
        gold_standard_md = _read_text(GOLD_STANDARD_PATH)
    except Exception as exc:
        yield {
            "event": "error",
            "data": {"stage": "ingest", "message": f"PDF/asset load failed: {exc!s}"},
        }
        return

    # =====================================================================
    # Stage 1 — generator
    # =====================================================================
    yield {
        "event": "stage_start",
        "data": {"stage": "generator", "label": "Reading the packet"},
    }

    stage_1_md = ""
    try:
        async for ev in stream_generator(pdf_text, principles_md, gold_standard_md):
            if ev.get("event") == "_final_markdown":
                stage_1_md = ev["data"]["markdown"]
            else:
                yield ev
    except Exception as exc:
        yield {
            "event": "error",
            "data": {"stage": "generator", "message": str(exc)},
        }
        return

    if not stage_1_md.strip():
        yield {
            "event": "error",
            "data": {"stage": "generator", "message": "Generator produced empty output"},
        }
        return

    yield {
        "event": "stage_complete",
        "data": {"stage": "generator", "summary": "draft complete"},
    }

    # =====================================================================
    # Stage 2 — legal / citation validation
    # =====================================================================
    yield {
        "event": "stage_start",
        "data": {"stage": "legal", "label": "Verifying citations"},
    }

    stage_2_md = stage_1_md
    verified_count = 0
    flagged_count = 0
    try:
        async for ev in validate_citations(stage_1_md):
            if ev.get("event") == "_repaired_markdown":
                stage_2_md = ev["data"]["markdown"]
                verified_count = ev["data"].get("verified", 0)
                flagged_count = ev["data"].get("flagged", 0)
            else:
                yield ev
    except Exception as exc:
        # Stage-2 fallback: pass Stage 1 markdown through
        yield {
            "event": "thinking",
            "data": {
                "stage": "legal",
                "text": (
                    f"Citation validator crashed ({exc!s}); skipping verification. "
                    "Manual citation check recommended."
                ),
            },
        }
        stage_2_md = stage_1_md

    yield {
        "event": "stage_complete",
        "data": {
            "stage": "legal",
            "summary": f"{verified_count} verified, {flagged_count} flagged",
        },
    }

    # =====================================================================
    # Stage 3 — red team
    # =====================================================================
    yield {
        "event": "stage_start",
        "data": {
            "stage": "red_team",
            "label": "Stress-testing against district goals",
        },
    }

    final_md = stage_2_md
    try:
        async for ev in stream_red_team(stage_2_md, pdf_text, principles_md):
            if ev.get("event") == "_final_markdown":
                candidate = ev["data"]["markdown"]
                if candidate.strip():
                    final_md = candidate
            else:
                yield ev
    except Exception as exc:
        # Stage-3 fallback per spec: skip, keep stage-2 markdown
        yield {
            "event": "thinking",
            "data": {
                "stage": "red_team",
                "text": f"Red-team stage failed ({exc!s}); using Stage 2 output as final.",
            },
        }
        final_md = stage_2_md

    yield {
        "event": "stage_complete",
        "data": {"stage": "red_team", "summary": "questions augmented"},
    }

    # =====================================================================
    # Persist + final event
    # =====================================================================
    run_id = uuid4().hex[:8]
    out_path = RUNS_DIR / f"{run_id}.md"
    try:
        out_path.write_text(final_md, encoding="utf-8")
    except Exception as exc:
        yield {
            "event": "error",
            "data": {"stage": "persist", "message": f"Failed to write run: {exc!s}"},
        }
        return

    yield {
        "event": "final",
        "data": {"run_id": run_id, "markdown": final_md},
    }

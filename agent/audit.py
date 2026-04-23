"""Structured citation audit log.

Every citation emitted by the lead agent is written as a JSONL line so Agent B
can diff the agent's citations against the bundled statute corpus and flag
hallucinations. Path is configurable via the CITATION_LOG_PATH env var;
defaults to <repo>/logs/citations.jsonl.

Schema (agreed with Agent B):
    {
        "ts": ISO-8601 UTC,
        "run_id": str,           # one per analyze_pdf invocation
        "source_pdf": str,
        "item_id": str,
        "authority": str,        # e.g. "TEC §11.151(b)"
        "verified": bool,        # whether the agent claims a corpus match
        "quoted_text": str|null, # verbatim quote the agent attributed
        "source": "agent"        # future: "flag" when emitted from a Flag
    }
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import UTC, datetime
from pathlib import Path

from agent.types import Citation

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "logs" / "citations.jsonl"
_LOCK = threading.Lock()


def _target_path() -> Path:
    override = os.getenv("CITATION_LOG_PATH")
    return Path(override) if override else _DEFAULT_PATH


def log_citations(
    *,
    run_id: str,
    source_pdf: str,
    item_id: str,
    citations: list[Citation],
    source: str = "agent",
) -> None:
    """Append one JSONL line per citation. Safe across threads."""
    if not citations:
        return
    path = _target_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat()
    lines = [
        json.dumps(
            {
                "ts": now,
                "run_id": run_id,
                "source_pdf": source_pdf,
                "item_id": item_id,
                "authority": c.authority,
                "verified": c.verified,
                "quoted_text": c.quoted_text,
                "source": source,
            },
            ensure_ascii=False,
        )
        for c in citations
    ]
    with _LOCK, path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    logger.debug("audit: wrote %d citation(s) for item=%s to %s", len(citations), item_id, path)

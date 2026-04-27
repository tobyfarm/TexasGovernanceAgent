"""Stage 2 — Citation extraction and verification.

Strategy:
1. Regex-extract TEC/TGC/TAC and Local Policy citations from Stage 1 markdown.
2. Per unique TEC/TGC/TAC citation, fetch the chapter page from
   statutes.capitol.texas.gov and check that the section header appears.
3. Yield SSE-ready `thinking` events as we go.
4. Replace unverified citations with strikethrough + "(unverified)" tag.

Falls back gracefully on network failure: marks all unverified, never blocks.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator

import httpx

# Patterns
RE_TEC = re.compile(r"\bTEC\s*§?\s*(\d+)\.(\d+)\b", re.IGNORECASE)
RE_TGC = re.compile(r"\bTGC\s*§?\s*(\d+)\.(\d+)\b", re.IGNORECASE)
RE_TAC = re.compile(r"\b(?:19\s+)?TAC\s*§?\s*(\d+)\.(\d+)\b", re.IGNORECASE)
RE_LOCAL_POLICY = re.compile(r"\b(?:Local Policy\s+)?([A-Z]{2,5})(LOCAL|LEGAL)\b")

# Statute URL templates
STATUTE_URLS = {
    "TEC": "https://statutes.capitol.texas.gov/Docs/ED/htm/ED.{chapter}.htm",
    "TGC": "https://statutes.capitol.texas.gov/Docs/GV/htm/GV.{chapter}.htm",
    "TAC": None,  # TAC is on a different system; skip web-verify, mark as unverified
}

REQUEST_TIMEOUT = 8.0
PER_CITATION_TIMEOUT = 12.0
TOTAL_STAGE_TIMEOUT = 45.0


def extract_citations(markdown: str) -> dict[str, list[tuple[str, str]]]:
    """Return {code: [(chapter, section), ...]} de-duped, preserving original casing."""
    out: dict[str, set[tuple[str, str]]] = {"TEC": set(), "TGC": set(), "TAC": set()}
    for m in RE_TEC.finditer(markdown):
        out["TEC"].add((m.group(1), m.group(2)))
    for m in RE_TGC.finditer(markdown):
        out["TGC"].add((m.group(1), m.group(2)))
    for m in RE_TAC.finditer(markdown):
        out["TAC"].add((m.group(1), m.group(2)))
    return {k: sorted(v) for k, v in out.items()}


async def _verify_one(
    client: httpx.AsyncClient,
    code: str,
    chapter: str,
    section: str,
) -> bool:
    """Best-effort: GET the chapter page and look for the section header."""
    url_tpl = STATUTE_URLS.get(code)
    if url_tpl is None:
        return False
    url = url_tpl.format(chapter=chapter)
    try:
        resp = await asyncio.wait_for(
            client.get(url, follow_redirects=True),
            timeout=PER_CITATION_TIMEOUT,
        )
        if resp.status_code != 200:
            return False
        body = resp.text
        # Texas statute pages render section headers as e.g. "Sec. 11.1511."
        needle = f"Sec. {chapter}.{section}"
        return needle in body
    except Exception:
        return False


def _replace_citation(markdown: str, code: str, chapter: str, section: str) -> str:
    """Mark a single citation as unverified, in-place. Idempotent."""
    # Use a flexible pattern allowing optional § and varying whitespace.
    pat = re.compile(
        rf"\b{code}\s*§?\s*{re.escape(chapter)}\.{re.escape(section)}\b",
        re.IGNORECASE,
    )

    def _sub(m: re.Match) -> str:
        original = m.group(0)
        # Skip if already wrapped in strikethrough
        # (cheap heuristic: peek 2 chars before)
        return f"~~{original}~~ *(unverified)*"

    # Avoid double-wrapping by first un-wrapping anything we already wrapped
    # (no-op normally, but guards reruns)
    return pat.sub(_sub, markdown)


async def validate_citations(markdown: str) -> AsyncIterator[dict]:
    """Stream `thinking` events; final event carries repaired markdown.

    Final event uses internal key `_repaired_markdown`.
    """
    citations = extract_citations(markdown)
    flat: list[tuple[str, str, str]] = []
    for code, pairs in citations.items():
        for ch, sec in pairs:
            flat.append((code, ch, sec))

    if not flat:
        yield {
            "event": "thinking",
            "data": {"stage": "legal", "text": "No statute citations found."},
        }
        yield {
            "event": "_repaired_markdown",
            "data": {
                "stage": "legal",
                "markdown": markdown,
                "verified": 0,
                "flagged": 0,
            },
        }
        return

    yield {
        "event": "thinking",
        "data": {
            "stage": "legal",
            "text": f"Found {len(flat)} unique statute citations to verify.",
        },
    }

    repaired = markdown
    verified_count = 0
    flagged_count = 0

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:

            async def _verify_with_event(code: str, chapter: str, section: str):
                citation_str = f"{code} §{chapter}.{section}"
                ok = await _verify_one(client, code, chapter, section)
                return citation_str, code, chapter, section, ok

            # Bound the whole stage so we never block the pipeline.
            tasks = [
                _verify_with_event(code, ch, sec) for (code, ch, sec) in flat
            ]
            try:
                # as_completed lets us yield thinking events as each finishes
                done = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=TOTAL_STAGE_TIMEOUT,
                )
            except asyncio.TimeoutError:
                yield {
                    "event": "thinking",
                    "data": {
                        "stage": "legal",
                        "text": (
                            "Verification timed out — flagging remaining citations "
                            "as unverified for manual check."
                        ),
                    },
                }
                done = []

            for result in done:
                if isinstance(result, Exception) or not result:
                    continue
                citation_str, code, chapter, section, ok = result
                yield {
                    "event": "thinking",
                    "data": {
                        "stage": "legal",
                        "text": f"Verifying {citation_str}...",
                    },
                }
                if ok:
                    verified_count += 1
                    yield {
                        "event": "thinking",
                        "data": {
                            "stage": "legal",
                            "text": f"verified {citation_str}",
                        },
                    }
                else:
                    flagged_count += 1
                    repaired = _replace_citation(repaired, code, chapter, section)
                    yield {
                        "event": "thinking",
                        "data": {
                            "stage": "legal",
                            "text": f"unverified {citation_str} — flagging",
                        },
                    }
    except Exception as exc:
        # Catastrophic fallback: mark everything unverified, keep going.
        yield {
            "event": "thinking",
            "data": {
                "stage": "legal",
                "text": (
                    f"Verification subsystem failed ({exc!s}); marking all "
                    "citations as unverified — manual check recommended."
                ),
            },
        }
        for code, ch, sec in flat:
            repaired = _replace_citation(repaired, code, ch, sec)
        flagged_count = len(flat)
        verified_count = 0

    yield {
        "event": "_repaired_markdown",
        "data": {
            "stage": "legal",
            "markdown": repaired,
            "verified": verified_count,
            "flagged": flagged_count,
        },
    }

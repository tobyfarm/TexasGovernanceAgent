"""Lead agent — the Claude Agent SDK orchestration loop.

For each agenda item in a board book PDF, ask the lead agent to produce an
ItemAnalysis grounded in the four repo Skills (statute-mapper, governance-
principles, risk-flagger, output-formatter). Collect outputs and emit a final
AnalysisResult as JSON + a Brock-format markdown pre-read.

Two entry points:
    analyze_pdf()         — returns a final AnalysisResult (blocking).
    analyze_pdf_stream()  — async generator yielding AnalyzeEvent objects for
                            SSE-backed UIs.

Per-item calls run under a bounded semaphore (default 4 concurrent). Skills
auto-load from `.claude/skills`, which is a symlink to the repo-root `skills/`
directory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

from agent.audit import log_citations
from agent.ingestion import extract_agenda_items
from agent.types import (
    AgendaItem,
    AnalysisResult,
    Citation,
    Flag,
    ItemAnalysis,
    OutputMode,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
RUNS_DIR = REPO_ROOT / "logs" / "runs"
DEFAULT_CONCURRENCY = 4
DEFAULT_RETRY_ATTEMPTS = int(os.getenv("BROCK_RETRY_ATTEMPTS", "2"))
RETRY_BASE_SECONDS = 0.5

_JSON_SCHEMA_TAIL = """Return *only* a JSON object with this shape:
{
  "summary": "one-paragraph What Is Happening",
  "key_data": "markdown tables / figures",
  "legal_framework": "What the law says, with citations",
  "flags": [{"severity": "WATCH|RED_FLAG|POSITIVE", "pattern_id": "...", "summary": "...", "detail": "...", "citations": ["TEC §11.151(b)"]}],
  "questions": ["numbered governance question"],
  "citations": [{"authority": "TEC §11.151(b)", "quoted_text": null, "verified": false}]
}
No prose before or after the JSON.
"""

_BROCK_PROMPT = (
    """You are the Board Book Red Team lead agent for a Texas school board trustee.

For each agenda item you are handed:
1. Map every authority invoked in the item to statute using the statute-mapper Skill.
2. Check every objective, action, or decision against the governance-principles Skill.
3. Apply the risk-flagger Skill to produce WATCH / RED_FLAG / POSITIVE flags.
4. Generate 2-5 trustee-ready questions per item.
5. Return a single JSON object matching the ItemAnalysis schema (see below).

Do not invent citations. If the statute-mapper cannot verify an authority, omit it.
Preserve the voice patterns from skills/governance-principles/principles.md §IV:
- Quote adopted text verbatim. Never paraphrase "shall".
- Cite the controlling authority on every governance claim.
- Numbered points for arguments. One point per section.
- No corporate filler. No stacked em-dash qualifiers.
- Warm only on students.

"""
    + _JSON_SCHEMA_TAIL
)

_SAMCO_PROMPT = (
    """You are a trustee preparing a SAMCO-style line of questioning for the finance
adviser on each agenda item you are handed.

Your output emphasises QUESTIONS over analysis. For each item:
1. Read the item. Identify the decision the board is being asked to make.
2. Pull the two or three most consequential unknowns — the ones a trustee must
   surface before voting.
3. Phrase each unknown as a direct, respectful question to the adviser or staff.
4. Attach only the citations you are certain of (statute-mapper verified).

The `summary` should be one sentence naming the decision. `questions` is the
primary output: 3-7 precise, numbered questions. `legal_framework`, `flags`,
and `key_data` may be empty when nothing is material.

"""
    + _JSON_SCHEMA_TAIL
)


def _system_prompt(mode: OutputMode) -> str:
    return _SAMCO_PROMPT if mode == "SAMCO_LOQ" else _BROCK_PROMPT


# ---------------------------------------------------------------------------
# Streaming events — shape consumed by the FastAPI SSE endpoint and CLI.
# ---------------------------------------------------------------------------


EventName = Literal["ingest_done", "item_start", "item_done", "item_error", "result_done", "error"]


@dataclass
class AnalyzeEvent:
    name: EventName
    data: dict = field(default_factory=dict)

    def to_sse_payload(self) -> dict:
        return {"event": self.name, "data": json.dumps(self.data, default=str)}


class AnalysisError(Exception):
    """Raised for user-facing failure modes (missing key, malformed PDF)."""

    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Model invocation
# ---------------------------------------------------------------------------


def _user_prompt(item: AgendaItem) -> str:
    truncated = item.raw_text[:20000]
    return (
        f"Analyze this agenda item.\n\n"
        f"item_id: {item.item_id}\n"
        f"title: {item.title}\n"
        f"pages: {item.pages[0]}-{item.pages[1]}\n"
        f"type: {item.item_type}\n\n"
        f"raw_text:\n{truncated}\n"
    )


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a possibly-chatty response."""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in model output")
    return json.loads(text[start : end + 1])


async def _invoke_agent(prompt: str, *, cwd: Path, mode: OutputMode = "BROCK_FULL") -> str:
    """Drive one Agent SDK query turn and return the concatenated assistant text."""
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        TextBlock,
        query,
    )

    options = ClaudeAgentOptions(
        system_prompt=_system_prompt(mode),
        cwd=str(cwd),
        setting_sources=["project"],
    )

    parts: list[str] = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    parts.append(block.text)
    return "\n".join(parts)


# Test seam: tests can monkeypatch this to avoid hitting the SDK.
_invoke = _invoke_agent


async def _invoke_with_retry(
    prompt: str, *, cwd: Path, mode: OutputMode, attempts: int = DEFAULT_RETRY_ATTEMPTS
) -> str:
    """Call the agent with transient-error retries. Parse failures are handled
    by the caller since they may indicate a structural model issue, not flakiness."""
    last_exc: Exception | None = None
    for attempt in range(attempts + 1):
        try:
            return await _invoke(prompt, cwd=cwd, mode=mode)
        except Exception as exc:  # noqa: BLE001 — retry on any SDK-side failure
            last_exc = exc
            if attempt >= attempts:
                break
            delay = RETRY_BASE_SECONDS * (2**attempt)
            logger.warning(
                "agent invocation failed (attempt %d/%d): %s — retrying in %.1fs",
                attempt + 1,
                attempts + 1,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc


async def _run_item(
    item: AgendaItem,
    *,
    cwd: Path,
    run_id: str,
    source_pdf: str,
    mode: OutputMode = "BROCK_FULL",
) -> ItemAnalysis:
    text = await _invoke_with_retry(_user_prompt(item), cwd=cwd, mode=mode)

    try:
        parsed = _extract_json(text)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("item %s: could not parse JSON, using raw text. %s", item.item_id, exc)
        return ItemAnalysis(
            item=item,
            summary=text[:1000] if text else "(no model output)",
            key_data="",
            legal_framework="",
        )

    flags = [Flag(**f) for f in parsed.get("flags", [])]
    citations = [Citation(**c) for c in parsed.get("citations", [])]
    log_citations(
        run_id=run_id,
        source_pdf=source_pdf,
        item_id=item.item_id,
        citations=citations,
    )

    return ItemAnalysis(
        item=item,
        summary=parsed.get("summary", ""),
        key_data=parsed.get("key_data", ""),
        legal_framework=parsed.get("legal_framework", ""),
        flags=flags,
        questions=parsed.get("questions", []),
        citations=citations,
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _highest_severity(flags: list[Flag]) -> str:
    order = {"RED_FLAG": 3, "WATCH": 2, "POSITIVE": 1}
    if not flags:
        return "NONE"
    return max(flags, key=lambda f: order.get(f.severity, 0)).severity


def _exec_summary_row(a: ItemAnalysis) -> dict:
    return {
        "item_id": a.item.item_id,
        "title": a.item.title,
        "type": a.item.item_type,
        "pages": f"{a.item.pages[0]}-{a.item.pages[1]}",
        "risk": _highest_severity(a.flags),
    }


def _placeholder_analysis(item: AgendaItem, error: str) -> ItemAnalysis:
    return ItemAnalysis(
        item=item,
        summary=f"(analysis failed: {error})",
        key_data="",
        legal_framework="",
    )


def _check_api_key() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise AnalysisError(
            "ANTHROPIC_API_KEY is not set; the lead agent cannot run.",
            code="missing_api_key",
        )


async def analyze_pdf_stream(
    pdf_path: Path,
    *,
    manual_split: Path | None = None,
    concurrency: int | None = None,
    mode: OutputMode = "BROCK_FULL",
) -> AsyncIterator[AnalyzeEvent]:
    """Drive the full pipeline, yielding AnalyzeEvent objects.

    Raises AnalysisError for up-front failures (missing API key, malformed PDF).
    Per-item failures are surfaced as `item_error` events and the corresponding
    ItemAnalysis is a placeholder so the downstream contract stays intact.
    """
    _check_api_key()

    try:
        items = extract_agenda_items(pdf_path, manual_split=manual_split)
    except FileNotFoundError:
        raise
    except Exception as exc:
        logger.exception("ingestion failed on %s", pdf_path)
        raise AnalysisError(f"failed to parse PDF: {exc}", code="ingestion_failed") from exc

    run_id = uuid.uuid4().hex[:12]
    source_pdf = str(pdf_path)

    yield AnalyzeEvent(
        "ingest_done",
        {"run_id": run_id, "item_count": len(items), "source_pdf": source_pdf, "mode": mode},
    )

    sem = asyncio.Semaphore(concurrency or DEFAULT_CONCURRENCY)
    # Queue is the fan-in point so items complete in any order but we emit as
    # they finish. Preserving input order is a post-gather concern.
    queue: asyncio.Queue[AnalyzeEvent] = asyncio.Queue()
    results: list[ItemAnalysis | None] = [None] * len(items)

    async def _worker(idx: int, item: AgendaItem) -> None:
        async with sem:
            await queue.put(AnalyzeEvent("item_start", {"idx": idx, "item_id": item.item_id}))
            try:
                analysis = await _run_item(
                    item, cwd=REPO_ROOT, run_id=run_id, source_pdf=source_pdf, mode=mode
                )
                results[idx] = analysis
                await queue.put(
                    AnalyzeEvent(
                        "item_done",
                        {
                            "idx": idx,
                            "item_id": item.item_id,
                            "analysis": analysis.model_dump(mode="json"),
                        },
                    )
                )
            except Exception as exc:  # noqa: BLE001 — per-item isolation is intentional
                logger.exception("item %s failed", item.item_id)
                results[idx] = _placeholder_analysis(item, str(exc))
                await queue.put(
                    AnalyzeEvent(
                        "item_error",
                        {"idx": idx, "item_id": item.item_id, "error": str(exc)},
                    )
                )

    workers = [asyncio.create_task(_worker(i, it)) for i, it in enumerate(items)]

    async def _drain() -> None:
        await asyncio.gather(*workers)
        await queue.put(AnalyzeEvent("__done__"))  # sentinel

    drainer = asyncio.create_task(_drain())

    while True:
        event = await queue.get()
        if event.name == "__done__":
            break
        yield event

    await drainer  # propagate exceptions from workers

    ordered = [r for r in results if r is not None]
    final = AnalysisResult(
        source_pdf=source_pdf,
        generated_at=datetime.now(UTC),
        meeting_metadata={"source": Path(pdf_path).name, "run_id": run_id},
        executive_summary_table=[_exec_summary_row(a) for a in ordered],
        items=ordered,
        prep_checklist=[],
        output_mode=mode,
    )

    _persist_run(run_id, final)

    yield AnalyzeEvent("result_done", final.model_dump(mode="json"))


def _persist_run(run_id: str, result: AnalysisResult) -> Path:
    """Write result.json + result.md + meta.json to logs/runs/{run_id}/."""
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "result.json").write_text(result.model_dump_json(indent=2))
    (run_dir / "result.md").write_text(_render_markdown(result))
    meta = {
        "run_id": run_id,
        "source_pdf": result.source_pdf,
        "generated_at": result.generated_at.isoformat(),
        "mode": result.output_mode,
        "item_count": len(result.items),
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    return run_dir


async def analyze_pdf(
    pdf_path: Path,
    *,
    manual_split: Path | None = None,
    concurrency: int | None = None,
    mode: OutputMode = "BROCK_FULL",
) -> AnalysisResult:
    """Non-streaming wrapper. Collects stream events and returns the final result."""
    final: AnalysisResult | None = None
    async for event in analyze_pdf_stream(
        pdf_path, manual_split=manual_split, concurrency=concurrency, mode=mode
    ):
        if event.name == "result_done":
            final = AnalysisResult.model_validate(event.data)
    if final is None:
        raise AnalysisError("pipeline produced no result_done event", code="no_result")
    return final


# ---------------------------------------------------------------------------
# Markdown renderer + CLI entry
# ---------------------------------------------------------------------------


def _render_markdown(result: AnalysisResult) -> str:
    """Day-2 renderer. Agent F's output-formatter Skill authors the final
    templates; until that ships end-to-end, emit a structure that mirrors the
    hand version's header hierarchy (# Executive Summary / # Item X / ## What
    Is Happening / ## What the Law Says / ## Governance Questions) so the
    eval comparator picks up a real header overlap score."""
    lines: list[str] = []
    lines.append(f"# Pre-Read — {result.meeting_metadata.get('source', result.source_pdf)}")
    lines.append("")
    lines.append(f"_Generated {result.generated_at.isoformat()} — mode: {result.output_mode}_")
    lines.append("")
    lines.append("# Executive Summary")
    lines.append("")
    lines.append("| Item | Title | Type | Pages | Risk |")
    lines.append("|---|---|---|---|---|")
    for row in result.executive_summary_table:
        lines.append(
            f"| {row['item_id']} | {row['title']} | {row['type']} | {row['pages']} | {row['risk']} |"
        )
    lines.append("")
    for a in result.items:
        # Letter-only items get H1 ("# Item J: BUSINESS ACTION"); sub-items
        # get H2 ("## Item J.1: Series 2016 Bond Refunding") so the eval's
        # structural comparison against the hand format sees nested headers.
        header = "##" if "." in a.item.item_id else "#"
        lines.append(f"{header} Item {a.item.item_id}: {a.item.title}")
        lines.append("")
        lines.append("## What Is Happening")
        lines.append("")
        lines.append(a.summary or "_(none)_")
        lines.append("")
        if a.key_data:
            lines.append("## Key Data")
            lines.append("")
            lines.append(a.key_data)
            lines.append("")
        if a.legal_framework:
            lines.append("## What the Law Says")
            lines.append("")
            lines.append(a.legal_framework)
            lines.append("")
        if a.flags:
            lines.append("## Flags")
            lines.append("")
            for f in a.flags:
                lines.append(f"- **{f.severity}** ({f.pattern_id}): {f.summary}")
                if f.detail:
                    lines.append(f"  {f.detail}")
            lines.append("")
        if a.questions:
            lines.append("## Governance Questions")
            lines.append("")
            for i, q in enumerate(a.questions, 1):
                # Strip any leading "N." or "N)" the model may have prefixed
                # so we don't emit "1. 1. …".
                clean = re.sub(r"^\s*\d+\s*[.)]\s*", "", q)
                lines.append(f"{i}. {clean}")
            lines.append("")
    return "\n".join(lines)


async def _run_cli(args) -> tuple[int, AnalysisResult | None, str | None]:
    """Drive the stream in the CLI with live progress. Returns (exit_code, result, run_id)."""
    run_id: str | None = None
    item_count = 0
    done = 0
    result: AnalysisResult | None = None

    try:
        async for event in analyze_pdf_stream(
            args.pdf,
            manual_split=args.manual_split,
            concurrency=args.concurrency,
            mode=args.mode,
        ):
            if event.name == "ingest_done":
                run_id = event.data["run_id"]
                item_count = event.data["item_count"]
                print(f"[ingest] run_id={run_id}  items={item_count}  mode={event.data['mode']}")
            elif event.name == "item_start":
                print(f"[start ] item {event.data['item_id']}")
            elif event.name == "item_done":
                done += 1
                print(f"[done  ] item {event.data['item_id']}  ({done}/{item_count})")
            elif event.name == "item_error":
                done += 1
                print(
                    f"[error ] item {event.data['item_id']}: {event.data['error']}",
                    file=sys.stderr,
                )
            elif event.name == "result_done":
                result = AnalysisResult.model_validate(event.data)
    except AnalysisError as exc:
        print(f"error ({exc.code}): {exc}", file=sys.stderr)
        return 1, None, run_id

    return 0, result, run_id


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Run the Board Book Red Team agent on a PDF.")
    parser.add_argument("pdf", type=Path, help="Path to board-book PDF.")
    parser.add_argument(
        "--manual-split",
        type=Path,
        default=None,
        help="Optional YAML item_id→[start,end] page map.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Where to write the markdown pre-read (defaults next to the PDF).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Max parallel item analyses (default: {DEFAULT_CONCURRENCY}).",
    )
    parser.add_argument(
        "--mode",
        choices=["BROCK_FULL", "SAMCO_LOQ"],
        default="BROCK_FULL",
        help="Output mode (default: BROCK_FULL).",
    )
    args = parser.parse_args(argv)

    if not args.pdf.exists():
        print(f"error: pdf not found: {args.pdf}", file=sys.stderr)
        return 2

    exit_code, result, run_id = asyncio.run(_run_cli(args))
    if exit_code != 0 or result is None:
        return exit_code or 1

    out_md = args.output or args.pdf.with_name(args.pdf.stem + "_output.md")
    out_md.write_text(_render_markdown(result))
    out_json = out_md.with_suffix(".json")
    out_json.write_text(result.model_dump_json(indent=2))

    print(f"wrote {out_md}")
    print(f"wrote {out_json}")
    if run_id:
        print(f"run_id: {run_id}  (artifacts in logs/runs/{run_id}/)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

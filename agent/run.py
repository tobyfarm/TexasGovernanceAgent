"""Lead agent — the Claude Agent SDK orchestration loop.

For each agenda item in a board book PDF, ask the lead agent to produce an
ItemAnalysis grounded in the four repo Skills (statute-mapper, governance-
principles, risk-flagger, output-formatter). Collect outputs and emit a final
AnalysisResult as JSON + a Brock-format markdown pre-read.

Day 1: rough end-to-end. Output quality is poor — that is expected.
Day 2: stabilize streaming, parallelism, citation logging.

Skills live in `./skills/` at the repo root per CLAUDE.md. The SDK's default
skill-loading path is `.claude/skills/`; until that is reconciled (Day 2), the
system prompt explicitly points the agent at the repo-root location.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from agent.ingestion import extract_agenda_items
from agent.types import (
    AgendaItem,
    AnalysisResult,
    Citation,
    Flag,
    ItemAnalysis,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

SYSTEM_PROMPT = """You are the Board Book Red Team lead agent for a Texas school board trustee.

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

Skills are stored in the repo at `./skills/` (not `.claude/skills/`). Read them
directly from disk if they have not been auto-loaded as tools.

Return *only* a JSON object with this shape:
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


async def _run_item(item: AgendaItem, *, cwd: Path) -> ItemAnalysis:
    """Call the Agent SDK once per item; collect the assistant's final text."""
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        query,
    )

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        cwd=str(cwd),
        setting_sources=["project"],
    )

    final_text_parts: list[str] = []
    async for message in query(prompt=_user_prompt(item), options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    final_text_parts.append(block.text)
        elif isinstance(message, ResultMessage):
            # Includes final usage + stop reason; nothing we need to capture here.
            pass

    text = "\n".join(final_text_parts)

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
    for c in citations:
        logger.info(
            "citation emitted: item=%s authority=%s verified=%s",
            item.item_id,
            c.authority,
            c.verified,
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


async def analyze_pdf(pdf_path: Path, *, manual_split: Path | None = None) -> AnalysisResult:
    items = extract_agenda_items(pdf_path, manual_split=manual_split)
    logger.info("ingested %d agenda items from %s", len(items), pdf_path)

    # Day 1: sequential. Day 2: asyncio.gather with a concurrency cap.
    analyses: list[ItemAnalysis] = []
    for item in items:
        logger.info("analyzing item %s (%s)", item.item_id, item.item_type)
        analysis = await _run_item(item, cwd=REPO_ROOT)
        analyses.append(analysis)

    exec_summary = [
        {
            "item_id": a.item.item_id,
            "title": a.item.title,
            "type": a.item.item_type,
            "pages": f"{a.item.pages[0]}-{a.item.pages[1]}",
            "risk": _highest_severity(a.flags),
        }
        for a in analyses
    ]

    return AnalysisResult(
        source_pdf=str(pdf_path),
        generated_at=datetime.now(UTC),
        meeting_metadata={"source": pdf_path.name},
        executive_summary_table=exec_summary,
        items=analyses,
        prep_checklist=[],
        output_mode="BROCK_FULL",
    )


def _highest_severity(flags: list[Flag]) -> str:
    order = {"RED_FLAG": 3, "WATCH": 2, "POSITIVE": 1}
    if not flags:
        return "NONE"
    return max(flags, key=lambda f: order.get(f.severity, 0)).severity


def _render_markdown(result: AnalysisResult) -> str:
    """Minimal Day-1 renderer. Agent F owns the real templates."""
    lines: list[str] = []
    lines.append(f"# Pre-Read — {result.meeting_metadata.get('source', result.source_pdf)}")
    lines.append("")
    lines.append(f"_Generated {result.generated_at.isoformat()} — mode: {result.output_mode}_")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Item | Title | Type | Pages | Risk |")
    lines.append("|---|---|---|---|---|")
    for row in result.executive_summary_table:
        lines.append(
            f"| {row['item_id']} | {row['title']} | {row['type']} | {row['pages']} | {row['risk']} |"
        )
    lines.append("")
    for a in result.items:
        lines.append(f"## Item {a.item.item_id} — {a.item.title}")
        lines.append("")
        lines.append("**What Is Happening**")
        lines.append("")
        lines.append(a.summary or "_(none)_")
        lines.append("")
        if a.key_data:
            lines.append("**Key Data**")
            lines.append("")
            lines.append(a.key_data)
            lines.append("")
        if a.legal_framework:
            lines.append("**Legal Framework**")
            lines.append("")
            lines.append(a.legal_framework)
            lines.append("")
        if a.flags:
            lines.append("**Flags**")
            lines.append("")
            for f in a.flags:
                lines.append(f"- **{f.severity}** ({f.pattern_id}): {f.summary}")
                if f.detail:
                    lines.append(f"  {f.detail}")
            lines.append("")
        if a.questions:
            lines.append("**Governance Questions**")
            lines.append("")
            for i, q in enumerate(a.questions, 1):
                lines.append(f"{i}. {q}")
            lines.append("")
    return "\n".join(lines)


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
        "--output", type=Path, default=None, help="Where to write the markdown pre-read."
    )
    args = parser.parse_args(argv)

    if not args.pdf.exists():
        print(f"error: pdf not found: {args.pdf}", file=sys.stderr)
        return 2

    result = asyncio.run(analyze_pdf(args.pdf, manual_split=args.manual_split))

    out_md = args.output or args.pdf.with_name(args.pdf.stem + "_output.md")
    out_md.write_text(_render_markdown(result))
    out_json = out_md.with_suffix(".json")
    out_json.write_text(result.model_dump_json(indent=2))

    print(f"wrote {out_md}")
    print(f"wrote {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

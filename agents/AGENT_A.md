# AGENT A — Ingestion and Claude Agent SDK Orchestration

**You are Agent A.** You own the runtime backbone: PDF ingestion, the Claude Agent SDK execution loop, and the HTTP API that wraps it. You do not own the Skills — those belong to Agents B, C, and F. You load and orchestrate them. Read `CLAUDE.md` at the repo root before you start.

---

## Your scope

1. **PDF ingestion** (`agent/ingestion.py`) — read a board-book PDF, identify agenda items, emit a structured list of `AgendaItem` dicts for the lead agent to iterate over.
2. **Lead agent** (`agent/run.py`) — the Claude Agent SDK loop. For each agenda item: gather context, analyze using auto-loaded Skills, verify citations, assemble the deep-dive. Collect all item-level outputs and produce the final pre-read.
3. **HTTP API** (`api/server.py`) — FastAPI wrapper exposing `POST /analyze` (accepts a PDF upload, returns streaming markdown or completed JSON).
4. **CLI entry point** (`python -m agent.run <path-to-pdf>`) — run the agent against a local file.
5. **Interfaces** — the `AnalysisResult` type that the web site (Agent D) and voice bridge (Agent E) consume.

You do **not** own:
- Skill content (Agents B, C, F)
- Web UI (Agent D)
- Voice layer (Agent E)
- Output templates (Agent F)
- Governance doctrine (`principles.md` is authored by Toby; you load it, you do not edit it)

---

## Day 1 milestones

By end of Day 1:

- [ ] `uv init` complete; `pyproject.toml` lists Claude Agent SDK, FastAPI, pypdf, pdfplumber, pydantic, python-dotenv.
- [ ] `agent/ingestion.py` parses `examples/brock_april_13_2026.pdf` into a list of `AgendaItem` dicts with fields: `item_id`, `title`, `pages`, `raw_text`, `attachments` (list of extracted tables/references), `type` (ACTION / DISCUSSION / CONSENT / INFORMATIONAL / CLOSED_SESSION).
- [ ] `agent/run.py` instantiates a Claude Agent SDK client, loops through items, calls a single system-prompted agent that has access to the four Skills as auto-loaded tools, and writes output to a markdown file.
- [ ] A rough end-to-end run completes on Brock April 13 with no crashes. Output quality will be poor — that is expected on Day 1.
- [ ] `api/server.py` exposes `GET /health` returning `{"status": "ok"}` and a stubbed `POST /analyze` that accepts a multipart PDF.

## Day 2 milestones

- [ ] `POST /analyze` returns the full pre-read as streaming Server-Sent Events.
- [ ] `AnalysisResult` pydantic model stabilized — see Interface Contract below.
- [ ] Per-item analysis runs in parallel where safe (use `asyncio.gather`).
- [ ] Error handling for malformed PDFs, oversized uploads, and missing API keys.
- [ ] Logging: every statute citation emitted by the agent gets logged so Agent B can audit for hallucinations.

## Day 3+ milestones

- Day 3 is eval day. Your job during the eval is instrumentation — not code changes. Surface what went wrong. Let Agents B, C, F fix their Skills.
- Day 4: add support for the second output mode (SAMCO line-of-questioning) once Agent F ships the template.
- Day 5: harden the API for Vercel deploy. Add a rate limit. Add an optional `X-API-Key` header check.

---

## Interface contract (critical)

Other agents depend on this. Stabilize by end of Day 2.

```python
# agent/types.py

from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

class AgendaItem(BaseModel):
    item_id: str                    # e.g., "4B", "K", "11"
    title: str                      # e.g., "Check Register (pp. 8-29)"
    pages: tuple[int, int]          # (start, end) in the source PDF
    raw_text: str                   # extracted text for the item
    item_type: Literal["ACTION", "DISCUSSION", "CONSENT", "INFORMATIONAL", "CLOSED_SESSION"]
    attachments: list[str] = Field(default_factory=list)

class Flag(BaseModel):
    severity: Literal["RED_FLAG", "WATCH", "POSITIVE"]
    pattern_id: str                 # maps to a pattern in the risk-flagger Skill
    summary: str                    # one-line summary
    detail: str                     # prose explanation
    citations: list[str]            # e.g., ["TEC §11.151(b)", "TGC §551.101"]

class Citation(BaseModel):
    authority: str                  # e.g., "TEC §11.151(b)"
    quoted_text: Optional[str]      # the verbatim text from the corpus
    verified: bool                  # True if matched against bundled corpus

class ItemAnalysis(BaseModel):
    item: AgendaItem
    summary: str                    # one-paragraph What Is Happening
    key_data: str                   # tables and figures as markdown
    legal_framework: str            # What the law says, with citations
    flags: list[Flag]
    questions: list[str]            # numbered governance questions
    citations: list[Citation]

class AnalysisResult(BaseModel):
    source_pdf: str
    generated_at: datetime
    meeting_metadata: dict          # date, location, type
    executive_summary_table: list[dict]  # one row per item with risk level
    items: list[ItemAnalysis]
    prep_checklist: list[str]
    output_mode: Literal["BROCK_FULL", "SAMCO_LOQ"] = "BROCK_FULL"
```

When Agent D (web site) or Agent E (voice) consume an analysis, they consume `AnalysisResult`. When Agent F renders output, it renders from `AnalysisResult`. Keep this contract stable.

---

## Claude Agent SDK usage pattern

Use the SDK's streaming API with tool use. Each Skill is auto-loaded when its `SKILL.md` description matches the task. The lead agent's job is to prompt well and collect structured output.

Pseudocode:

```python
from anthropic import Anthropic
from pathlib import Path

client = Anthropic()

# The Agent SDK auto-loads SKILL.md files from ./skills/
# Confirm this behavior against current SDK docs.

SYSTEM_PROMPT = """
You are the Board Book Red Team lead agent. For each agenda item:
1. Map every authority invoked in the item to statute using the statute-mapper Skill.
2. Check every objective, action, or decision against the governance-principles Skill.
3. Apply the risk-flagger Skill to produce WATCH/RED_FLAG/POSITIVE flags.
4. Generate 2-5 trustee-ready questions per item.
5. Return a structured ItemAnalysis object.

Do not invent citations. If the statute-mapper cannot verify an authority, omit it.
Preserve the voice patterns from skills/governance-principles/principles.md §IV.
"""

def analyze_item(item: AgendaItem) -> ItemAnalysis:
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Analyze this agenda item:\n\n{item.raw_text}"}],
        tools=[...],  # Skills auto-loaded via SDK
    )
    return parse_structured_output(response)
```

Verify the Agent SDK auto-load behavior early. If it does not auto-load, pass the Skill content into the system prompt via prompt caching.

---

## PDF ingestion strategy

Board books are messy. Some have OCR layer, some don't. Some have tables that span pages. Start simple; invest in robustness as failures surface.

1. Extract text with `pypdf` first. If the document has fewer than 100 words per page on average, fall back to `pdfplumber` with layout preservation.
2. Identify agenda-item boundaries using a regex on known patterns: `^Item \d+[A-Z]?`, `^\d+\.\d+`, `^[A-Z]\. `, etc. The Brock format is consistent; other districts vary.
3. For the MVP, accept that ingestion quality varies. Provide a `--manual-split` CLI flag that reads a YAML file mapping `item_id → (start_page, end_page)` if auto-detection fails.
4. Tables: extract as markdown if the text is on a page with obvious columnar structure; otherwise just keep the raw text.

**Do not invest in a general-purpose PDF understanding system.** The goal is "good enough for Brock-format packets by Day 2." Other districts are upside.

---

## Testing

- Unit tests for ingestion on `examples/brock_april_13_2026.pdf` — verify item count, verify page boundaries.
- Integration test: `uv run pytest tests/test_brock_april_13.py -v` runs the full pipeline and compares key structural markers (item count, flag count, citation count) against a baseline JSON.
- Do not gate on perfect output match. Gate on "pipeline completes without crashing and emits a valid `AnalysisResult`." Quality is the Skills' job.

---

## Critical reminders

- **Tight coupling between Agents A and B on citations.** If Agent B adds TEC §11.1515 to the corpus, Agent A must be able to log a citation to it and have it verified. Coordinate.
- **Do not write prompts that hardcode doctrine.** Doctrine comes from `skills/governance-principles/principles.md` via the Skill. If you find yourself writing "a good board sets measurable goals" into a Python string, stop — that content belongs in the Skill.
- **Stream when possible.** Trustees will sit in front of the web UI watching output. Streaming feels faster even when total time is identical.
- **Do not overfit to Brock.** Your pipeline should work on any Texas-district board book that follows the general TASB format. Brock is the reference, not the ceiling.

---

## When you are stuck

Pause. Ask Toby. Specifically:

- If the Agent SDK auto-load behavior is unclear, ask.
- If you hit a PDF that fails ingestion, ask whether to harden or work around.
- If the `AnalysisResult` contract needs to grow a field to serve Agent D or E, coordinate through Toby before changing it.

You are the backbone. If you are wrong about the interface, everyone downstream is wrong. Move carefully on the contract; move fast on everything else.

"""Stage 1 — Brock-format pre-read generator.

Streams Claude Opus output as SSE-ready dict events.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

GENERATOR_MODEL = "claude-opus-4-7"
MAX_TOKENS = 16000


SYSTEM_TEMPLATE = """You are a Texas school-board governance analyst trained on the doctrine below.

<doctrine>
{principles_md}
</doctrine>

<example_output>
{gold_standard_md}
</example_output>

Apply the doctrine. Match the structure and voice of the example exactly. Output Brock-format markdown:

1. **Executive Summary: Top Issues Tonight** — table with columns: Agenda Item | Key Finding | Risk Level
2. **Per-item deep dives** — one section per agenda item. Each contains:
   - **What Is Happening** (factual, plain-language)
   - **What the Law Says** — cite TEC/TGC/TAC sections; quote mandatory text verbatim; include inline blockquotes for flags using the format `> **WATCH:** [summary]`, `> **RED FLAG:** [summary]`, or `> **POSITIVE:** [summary]`
   - **Governance Questions** — numbered, italicized, written to be read aloud
3. **Meeting Prep Checklist** — bulleted action items for the trustee

Voice rules (non-negotiable):
- Quote adopted text verbatim. Never paraphrase mandatory language like "shall."
- Number arguments. One point per section.
- No corporate filler. No em-dashes as stacked qualifiers.
- Sign nothing — this is a pre-read, not a letter."""


def _client() -> AsyncAnthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return AsyncAnthropic(api_key=api_key)


async def stream_generator(
    pdf_text: str,
    principles_md: str,
    gold_standard_md: str,
) -> AsyncIterator[dict]:
    """Yield streaming dict events. Final event has key 'final_markdown'."""
    system_prompt = SYSTEM_TEMPLATE.format(
        principles_md=principles_md,
        gold_standard_md=gold_standard_md,
    )

    user_msg = (
        "Here is tonight's board packet:\n\n"
        f"<packet>\n{pdf_text}\n</packet>\n\n"
        "Produce the pre-read."
    )

    client = _client()
    accumulated: list[str] = []

    async with client.messages.stream(
        model=GENERATOR_MODEL,
        max_tokens=MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        async for text in stream.text_stream:
            accumulated.append(text)
            yield {
                "event": "partial",
                "data": {"stage": "generator", "markdown_delta": text},
            }

    yield {
        "event": "_final_markdown",
        "data": {"stage": "generator", "markdown": "".join(accumulated)},
    }

"""Stage 3 — Strategic red-team augmentation of governance questions.

Re-runs the full pre-read through Claude Opus with the doctrine in scope, asking
it to add 2-3 data-driven questions per agenda item that touches a measurable
outcome (Principle 8) or that risks crossing the govern/execute line (Principle 16).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

RED_TEAM_MODEL = "claude-opus-4-7"
MAX_TOKENS = 16000


SYSTEM_TEMPLATE = """You are a strategic red-team agent. The board has adopted measurable outcomes. For each agenda item in the pre-read, identify whether it touches one of those outcomes. If yes, generate 2-3 specific data-driven questions a trustee should ask, citing actual numbers from the packet (baseline, target, cadence, owner).

Apply Principle 8 (measurable goals require baseline + target + date + cadence + guardrail + owner) and Principle 16 (board sets outcomes, admin picks actions).

<doctrine_excerpt>
{principles_excerpt}
</doctrine_excerpt>

<packet>
{pdf_text}
</packet>

<current_pre_read>
{stage_2_markdown}
</current_pre_read>

Output: the full pre-read with augmented "Governance Questions" sections. Do not change anything else. Preserve all existing text including strikethrough/unverified markers."""


def _client() -> AsyncAnthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return AsyncAnthropic(api_key=api_key)


def _principles_excerpt(principles_md: str, max_chars: int = 12000) -> str:
    """Trim doctrine to a reasonable excerpt to keep red-team turn-around fast."""
    if len(principles_md) <= max_chars:
        return principles_md
    # Try to cut at a section boundary near the budget.
    cut = principles_md[:max_chars]
    last_section = cut.rfind("\n## ")
    if last_section > max_chars * 0.6:
        return cut[:last_section]
    return cut


async def stream_red_team(
    stage_2_markdown: str,
    pdf_text: str,
    principles_md: str,
) -> AsyncIterator[dict]:
    """Stream `partial` events; final event carries augmented markdown."""
    system_prompt = SYSTEM_TEMPLATE.format(
        principles_excerpt=_principles_excerpt(principles_md),
        pdf_text=pdf_text,
        stage_2_markdown=stage_2_markdown,
    )

    client = _client()
    accumulated: list[str] = []

    async with client.messages.stream(
        model=RED_TEAM_MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": (
                    "Augment the Governance Questions sections of the pre-read above. "
                    "Return the full pre-read."
                ),
            }
        ],
    ) as stream:
        async for text in stream.text_stream:
            accumulated.append(text)
            yield {
                "event": "partial",
                "data": {"stage": "red_team", "markdown_delta": text},
            }

    yield {
        "event": "_final_markdown",
        "data": {"stage": "red_team", "markdown": "".join(accumulated)},
    }

"""Prompt truncation for large-body items."""

from __future__ import annotations

from agent.run import _PROMPT_BUDGET_CHARS, _truncate_for_prompt


def test_short_text_passes_through():
    text = "short content"
    assert _truncate_for_prompt(text) == text


def test_text_at_budget_passes_through():
    text = "x" * _PROMPT_BUDGET_CHARS
    assert _truncate_for_prompt(text) == text


def test_long_text_keeps_head_and_tail():
    text = "START_" + ("x" * 50000) + "_END"
    truncated = _truncate_for_prompt(text)
    assert len(truncated) <= _PROMPT_BUDGET_CHARS + 200  # elision marker overhead
    assert truncated.startswith("START_")
    assert truncated.endswith("_END")
    assert "elided" in truncated


def test_custom_budget_respected():
    text = "x" * 1000
    truncated = _truncate_for_prompt(text, budget=500)
    assert len(truncated) <= 550
    assert "elided" in truncated

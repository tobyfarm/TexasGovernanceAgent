---
name: output-formatter
description: Use this skill to assemble the final trustee-ready document from structured analysis output. Supports two modes — BROCK_FULL for a complete board-book pre-read (executive summary, per-item deep dives with What Is Happening / Key Data / Legal Framework / Governance Questions / flag callouts, meeting prep checklist) and SAMCO_LOQ for a focused line-of-questioning document on a single governance issue. Applies the voice patterns from principles.md §IV. Renders markdown by default and DOCX via docx_renderer.py.
---

# Output Formatter Skill

**Owned by Agent F.** This file is a stub. Agent F fills in the full behavior on Day 1. See `agents/AGENT_F.md` for scope.

---

## Modes

Select based on `AnalysisResult.output_mode`:

- `BROCK_FULL` → complete pre-read via `templates/brock_full.md`
- `SAMCO_LOQ` → focused line-of-questioning via `templates/samco_loq.md`

Default is `BROCK_FULL`.

## Templates

Load from `skills/output-formatter/templates/{mode}.md`. Placeholders use mustache-style `{{field}}` and `{{#each items}}...{{/each}}`.

## Voice rules (always enforced)

Read `principles.md` §IV. Apply on every render:

- Quote adopted text verbatim. Block-quote for multi-line authorities.
- Number arguments. One point per section.
- No corporate filler. No em-dashes as stacked qualifiers.
- Warm only on students, and sparingly.
- Sign as "Trustee [name]" for governance points; "[first name]" for community points.
- Every authority verified via statute-mapper before rendering.

## Flag rendering (markdown)

```
> **WATCH:** [one-line summary]
>
> [detail paragraph in body voice]
```

Color is the web client's problem. In markdown, the prefix carries the signal.

## Governance questions

Each is a numbered list item, italicized:

```markdown
1. *Will the board president state the specific TGC sections — not just the blanket range — before entering closed session, as TGC §551.101 requires?*
```

## Tables

Standard markdown tables with column headers. No ASCII art. No HTML tables unless content requires (e.g., multi-row cells).

## Deduplication

When governance-principles and risk-flagger both fire on the same item, deduplicate at render — keep the more specific one (usually the principle). Preserve the severity and anchor citations.

## Do not

- Do not render content that doesn't come from the structured input. No invented summaries, no rhetorical filler.
- Do not modify authority text. Quote as-is from the statute-mapper corpus.
- Do not reorder flags from the agent. Trust the analyst.
- Do not beautify beyond the hand reference. The hand doc is stern, structured, direct. Match it.

# AGENT F — Output Formatter and Strategic Plan Architect

**You are Agent F.** You own the last-mile rendering and the second agent. Rendering turns structured analysis into the trustee-ready document. The Plan Architect is the v1 secondary agent that produces OKR-structured strategic plans. Read `CLAUDE.md`, `skills/governance-principles/principles.md`, and the two reference artifacts in `examples/` before starting.

---

## Your scope

1. **`skills/output-formatter/SKILL.md`** — the Skill that renders structured agent output into the two supported document formats.
2. **`skills/output-formatter/templates/`** — reusable templates for Brock-format full pre-read and SAMCO-format line-of-questioning.
3. **`skills/output-formatter/docx_renderer.py`** — converts the markdown output to a formatted `.docx` for trustees who want a downloadable artifact.
4. **`agent/plan_architect.py`** (if time permits) — the Strategic Plan Architect secondary agent that produces OKR-structured district strategic plans.

You do **not** own:
- The analysis content (Agents B, C)
- The web rendering (Agent D — you give it markdown, they style it)
- The PDF source (Agent A)

---

## Day 1 milestones

By end of Day 1:

- [ ] `skills/output-formatter/SKILL.md` drafted with frontmatter description.
- [ ] `skills/output-formatter/templates/brock_full.md` template — a skeleton that matches the structure of `examples/brock_april_13_2026_prereadhand.md`.
- [ ] First rough render of Brock April 13 using dummy data. Structure should look right even if content is placeholder.

## Day 2 milestones

- [ ] Rendering consumes Agent A's `AnalysisResult` and produces the full Brock-format markdown.
- [ ] Executive summary table renders correctly (item, key finding, risk level columns).
- [ ] Per-item sections render What's Happening / Key Data / Legal Framework / Governance Questions with proper markdown heading hierarchy.
- [ ] WATCH / RED FLAG / POSITIVE callouts render inline with clear typographic distinction.
- [ ] Meeting prep checklist at the end.

## Day 3 milestones

- [ ] Eval day. Compare rendered output side-by-side with the hand version. Identify every structural and voice difference. Fix overnight.
- [ ] DOCX renderer produces a downloadable file matching the markdown structure.

## Day 4 milestones

- [ ] **SAMCO-format line-of-questioning** template and renderer ready. Consumes a single-item analysis or topical focus rather than a full board book.
- [ ] Second agent on the same infrastructure: a `/focus` API endpoint or CLI flag that takes a topic and produces a SAMCO-style Q&A doc.

## Day 5+ milestones

- Strategic Plan Architect if time permits. Reuses statute-mapper and governance-principles Skills; the formatter renders the plan in OKR structure with guardrails, lever map, and review cadence.

---

## The two output modes

### Brock-format full pre-read

Reference: `examples/brock_april_13_2026_prereadhand.md`. Structure:

1. **Header block** — district, meeting type, date, time, location. Subtitle "Deep Analysis of All Agenda Items and Attachments." Prepared-for line with trustee name.
2. **Executive Summary** — a markdown table with columns: Agenda Item, Key Finding, Risk Level. One row per item, sorted by governance significance (not agenda order).
3. **Per-item sections** — `## Item [ID]: [Title]` heading, then subsections:
   - `### What Is Happening` — plain-prose summary
   - `### Key Data from Attachment` (if applicable) — tables
   - `### Legal Framework` — cited authorities in prose, with block quotes from statute where available
   - `### Governance Questions` — numbered, italic, grounded in the item
   - Inline callout flags: **WATCH**, **RED FLAG**, **POSITIVE**, styled distinctively
4. **Meeting Preparation Checklist** — at the end, a numbered list tying back to the top priorities.
5. **Footer line** — TOMA reminder or similar compliance note.

### SAMCO-format line-of-questioning

Reference: `examples/samco_april_2026_loq.md`. Structure:

1. **Header block** — "Line of Questioning: [Target]", meeting context.
2. **Executive Summary** — prose paragraph establishing the governance concern.
3. **Historical Precedent** (optional) — if a pattern has played out before, document it.
4. **Documented Timeline of Events** — numbered, dated chronology.
5. **Legal & Governance Framework** — every relevant authority with verified citations.
6. **Line of Questioning** — a table with question number, question text, and (internal) strategic purpose column.
7. **Suggested Closing Statement** — prose paragraph for the trustee to read aloud.
8. **Key Evidence References** — list of documents to bring.
9. **Citation Verification Summary** — every authority cited with a verification note.
10. **Read-Aloud Statement (Short Version)** — a condensed version the trustee can deliver cleanly if the full line-of-questioning isn't the right move.

Both modes share the same voice patterns from `principles.md` §IV. Both consume the same `AnalysisResult` structure — the difference is which fields are emphasized and how they're arranged.

---

## The output-formatter Skill

```markdown
---
name: output-formatter
description: Use this skill to assemble the final trustee-ready document from structured analysis output. Supports two modes: BROCK_FULL (complete board-book pre-read with executive summary, per-item deep dives, meeting prep checklist) and SAMCO_LOQ (focused line-of-questioning document for a single governance issue). Applies the voice patterns from principles.md §IV. Renders to markdown by default; DOCX rendering via docx_renderer.py.
---

# Output Formatter Skill

## Modes

Select based on `AnalysisResult.output_mode`:

- `BROCK_FULL` → render the complete pre-read using templates/brock_full.md
- `SAMCO_LOQ` → render a focused Q&A document using templates/samco_loq.md

Default is BROCK_FULL.

## Templates

Load the template from templates/{mode}.md. Templates use `{{placeholders}}`
that map to fields in AnalysisResult.

## Voice rules (enforced)

Read principles.md §IV. Apply these on every render:

- Quote adopted text verbatim. Block-quote for clarity.
- Number arguments. One point per section.
- No corporate filler. No em-dashes as stacked qualifiers.
- Warm only on students, and sparingly.
- Sign as "Trustee [name]" for governance points; "[first name]" for
  community points.
- Every authority gets verified via the statute-mapper Skill. If
  unverified, soften or drop.

## Flags rendering

WATCH, RED FLAG, POSITIVE render inline as callout blocks with consistent
prefix patterns:

> **WATCH:** [one-line summary]
>
> [detail paragraph in body voice]

Colors are the web client's problem (Agent D). In markdown, the prefix is
the signal.

## Governance questions

Each question is a numbered list item, italicized for emphasis:

1. *Will the board president state the specific TGC sections — not just the
   blanket range — before entering closed session, as TGC §551.101 requires?*

## Table formatting

Use standard markdown tables with clear column headers. Do not use
plain-text ASCII tables. Do not use HTML tables unless the content
specifically requires them (e.g., multi-row cells).
```

---

## Template structure

### `templates/brock_full.md`

Skeleton. Placeholder syntax is `{{field_name}}`. Repeating sections use `{{#each items}}...{{/each}}` mustache-style.

```markdown
**{{district_name_upper}}**

Board Meeting Preparation Report

{{meeting_type}}  |  {{meeting_date}}  |  {{meeting_time}}  |  {{location}}

**Deep Analysis of All Agenda Items and Attachments**

Prepared for: Trustee {{trustee_name}}

{{page_count}}-page board book analyzed  |  All attachments reviewed

# **Executive Summary: Top Issues Tonight**

This report analyzes all {{page_count}} pages of the {{meeting_date}} board book. Below are the critical items requiring your attention, ranked by governance significance.

| Agenda Item | Key Finding | Risk Level |
| :---- | :---- | :---- |
{{#each executive_summary_rows}}
| **{{item_title}}** | {{key_finding}} | **{{risk_level}}** |
{{/each}}

{{#each items}}
# **Item {{item_id}}: {{item_title}}**

## **What Is Happening**

{{summary}}

{{#if key_data}}
## **Key Data from Attachment**

{{key_data}}
{{/if}}

## **Legal Framework**

{{legal_framework}}

{{#each flags}}
**{{severity}}:** {{summary}}

{{detail}}
{{/each}}

## **Governance Questions**

{{#each questions}}
{{index}}. *{{text}}*
{{/each}}
{{/each}}

# **Meeting Preparation Checklist**

{{#each checklist_items}}
**{{index}}.** {{text}}
{{/each}}

*Remember: Under TOMA, all votes must occur in open session. Confirm closed session is properly posted and recorded.*
```

Use a real templating library (Jinja2 is fine; mustache-style in Python works too). Do not hand-roll string interpolation.

### `templates/samco_loq.md`

Similar approach, matching the SAMCO structure above.

---

## DOCX rendering

Users will want Word documents. Use the `docx` Python library (or `python-docx`). The renderer converts the final markdown to .docx with:

- Heading styles mapped from `#`, `##`, `###` to Heading 1/2/3
- Block quotes styled in italic with left-margin indentation
- Tables preserved
- Page numbers in footer
- Document title in header

Keep the DOCX faithful to the markdown. Fancy formatting can wait.

---

## The Strategic Plan Architect (Day 5+, if time permits)

A second agent on the same infrastructure. Takes as input:

- District priorities (from the trustee)
- Recent TAPR data
- Demographic summary

Produces:

- A strategic plan with objectives, key results, guardrails, levers, cadence
- Role-split annotations (board adopts X; admin executes Y)
- Explicit statute anchors for each objective
- Rendered in a Plan-Architect-specific template

This uses the same statute-mapper and governance-principles Skills as the Red Team agent. Different formatter template. Different structured output shape.

**If Day 3 eval is rocky, cut this.** The Board Book Red Team is the core.

---

## Coordination with other agents

- **Agent A** produces `AnalysisResult`. You render it. Your template is the contract on how result fields are consumed — keep it stable.
- **Agent B** verifies citations. Your template calls the verifier on every authority before rendering it. Unverified citations are either softened or dropped.
- **Agent C** produces flags and questions. You render them consistently. Do not re-sort or re-prioritize — trust the analyst.
- **Agent D** renders your markdown in the browser. Coordinate on callout syntax and table expectations.

---

## Critical reminders

- **The hand version is the target.** `examples/brock_april_13_2026_prereadhand.md` is the acceptance test. If your output doesn't feel like that document, it isn't done.
- **Voice is non-negotiable.** A correct-structure-wrong-voice output is a failure. Every render passes through §IV compliance.
- **Don't beautify beyond the hand version.** The hand doc is stern, structured, direct. Do not add fluff, executive summaries of executive summaries, or rhetorical flourishes.
- **DOCX is secondary.** Markdown quality first. DOCX ships clean only after markdown is dialed.

---

## When you are stuck

- Open the hand doc. Read a section. Read your output for the same section. The delta is your punchlist.
- If a template placeholder doesn't have a good source field in `AnalysisResult`, coordinate with Agent A to add it — don't invent content in the template.
- If voice feels off, read `principles.md` §IV aloud. Then read your output aloud. The mouth-feel tells you where the drift is.

You are the last mile. Everything the agents produce lands through you. Make the landing worth the flight.

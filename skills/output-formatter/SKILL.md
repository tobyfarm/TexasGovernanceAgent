---
name: output-formatter
description: Use this skill to assemble the final trustee-ready document from structured analysis output. Supports two modes — BROCK_FULL for a complete board-book pre-read (executive summary, per-item deep dives with What Is Happening / Key Data / Legal Framework / flag callouts / Governance Questions, meeting prep checklist) and SAMCO_LOQ for a focused line-of-questioning document on a single governance issue. Applies the voice patterns from principles.md §IV. Renders markdown by default; DOCX via docx_renderer.py (Day 3+).
---

# Output Formatter Skill

**Owner.** Agent F (see `agents/AGENT_F.md`).

**Acceptance test.** `examples/brock_april_13_2026_prereadhand.md`. When the agent runs on the Brock April 13 PDF, the rendered output must be structurally and tonally indistinguishable from that hand-authored document. The hand version is the target, not the spec.

---

## Modes

Select based on `AnalysisResult.output_mode`:

| Mode | Template | Use when |
| :---- | :---- | :---- |
| `BROCK_FULL` | `templates/brock_full.md` | Rendering a full board-book pre-read across every agenda item. |
| `SAMCO_LOQ` | `templates/samco_loq.md` | Rendering a focused line-of-questioning on a single governance issue (one item, one pattern, one read-aloud). |

Default is `BROCK_FULL`.

---

## Inputs

Both templates consume the `AnalysisResult` pydantic model defined in `agents/AGENT_A.md`. The field-name contract is authoritative — do not rename fields in the template without coordinating with Agent A.

**Required fields (BROCK_FULL):**

- `meeting_metadata` — dict with `district_name_upper`, `meeting_type`, `meeting_date`, `meeting_time`, `location`, `trustee_name`, `page_count`.
- `executive_summary_table` — list of `{item_title, key_finding, risk_level}`. Order is governance-significance, not agenda order. Trust the analyst's ranking.
- `items` — list of `ItemAnalysis`. Each has `item`, `summary`, `key_data`, `legal_framework`, `flags`, `questions`.
- `prep_checklist` — list of strings, each pre-formatted with its bold priority lead-in (e.g., `"**1. Bond Refunding (HIGH priority):** …"`).

**Required fields (SAMCO_LOQ):**

- `meeting_metadata` — same as above.
- `loq_target` — string naming the subject/advisor/action being questioned (e.g., `"Samco Capital Markets – Bond Parameter Order"`).
- `executive_concern` — prose paragraph establishing the governance concern.
- `historical_precedent` — optional prose block; omit cleanly if not applicable.
- `timeline` — list of `{date, event}` in chronological order.
- `legal_framework` — list of `{authority, quote, application}` for every cited section.
- `questions` — list of `{n, question, purpose}` — `purpose` is an internal strategy note, rendered in a third column.
- `closing_statement` — prose paragraph for the trustee to read aloud.
- `evidence_references` — list of strings (documents to bring).
- `citation_verification` — list of `{authority, verified, note}`.
- `short_read_aloud` — prose paragraph condensed version.

---

## Template syntax

Jinja2. `{{ field }}` for substitution, `{% for … %}` for loops, `{% if … %}` for conditionals. Do not hand-roll string interpolation. Do not introduce a second templating dialect.

`trim_blocks=True, lstrip_blocks=True` when constructing the Jinja environment so the loops don't leave stray blank lines.

---

## Voice rules (always enforced)

Read `skills/governance-principles/principles.md` §IV. Apply on every render:

- **Quote adopted text verbatim.** Block-quote when the quote is more than a few words. Never paraphrase mandatory language ("shall", "must", "may not").
- **Number arguments. One point per section.** The hand version uses numbered lists and discrete sub-headings — match that rhythm.
- **No corporate filler.** No em-dashes as stacked qualifiers. No "I want to be respectful of everyone's time" prefaces. No summary of the summary.
- **Warm only on students, and sparingly.** If you find the template reaching for "every single child" framing outside a student-outcomes item, the content is drifting.
- **Sign as "Trustee [name]"** for governance points and `"[first name]"` for community points. For BROCK_FULL there is no signature at the bottom — the "Prepared for: Trustee [name]" line in the header carries the attribution. SAMCO_LOQ ends with a signature block using `meeting_metadata.trustee_name`.
- **Verify every authority** via the statute-mapper Skill before rendering. The template MUST NOT render an unverified citation without softening language. If `citation.verified == False`, wrap the authority in "reportedly" or drop it.

---

## Flag rendering (markdown)

Match the hand version. Flags render as inline paragraphs with a bold prefix — **not** as blockquotes — because that is how the hand artifact renders and how it reads in Agent D's web view.

```markdown
**WATCH:** One-line lede, then the explanatory body in the same paragraph. Keep it in body voice. End with a period.

**RED FLAG:** Lede, then body. Use sparingly — a doc full of red flags trains readers to ignore them.

**POSITIVE:** Lede, then body. Positives should name the specific thing working so it can be studied and replicated.
```

Severity mapping from `Flag.severity`:

| `Flag.severity` | Rendered prefix |
| :---- | :---- |
| `RED_FLAG` | `**RED FLAG:**` |
| `WATCH` | `**WATCH:**` |
| `POSITIVE` | `**POSITIVE:**` |

Order within an item: render flags in the order Agent C emits them. Do not re-sort. Do not re-prioritize. The analyst has already decided the flow.

Citations attached to a flag (the `citations: list[str]` field) do not render inline — they belong in the Legal Framework block for the item. If the flag body calls out an authority, quote it in prose. If it doesn't, omit.

---

## Governance question rendering

Questions are numbered list items, italicized for emphasis. **Numbering runs continuously across the entire document**, not per-item. The hand version starts at 1 in Item K, continues 5 in Item 4A, 7 in 4B, and so on through the whole pre-read.

```markdown
1. *Will the board president state the specific TGC sections — not just the blanket range — before entering closed session, as TGC §551.101 requires?*

2. *Is the certified agenda and audio recording being maintained as required by TGC §551.103?*
```

The template maintains a running counter across items. See `brock_full.md`.

---

## Table rendering

Standard markdown tables with left-aligned columns (`:----`). No ASCII-art tables. No HTML tables unless multi-row cells are unavoidable. Bold the first column when it carries the label (e.g., fund name, item name, category).

The `key_data` field on each `ItemAnalysis` is already-formatted markdown from Agent A — the template emits it as-is. Do not second-guess the analyst's column choices.

---

## Heading hierarchy

| Level | Used for |
| :---- | :---- |
| `#` | Executive Summary, each Item, Meeting Preparation Checklist |
| `##` | Sub-sections within an item (What Is Happening, Key Data from Attachment, Legal Framework, Governance Questions, plus any freeform analysis sub-sections Agent A emits inside `summary` or `key_data`) |
| `###` | Sub-sub sections (e.g., a specific scenario table inside a legal framework) |

Bold the heading text to match the hand version (`# **Executive Summary: Top Issues Tonight**`). The bold is cosmetic in most renderers but matches the hand-version Markdown source.

---

## Deduplication and ordering

- When `governance-principles` and `risk-flagger` both fire on the same item, Agent C deduplicates upstream. If duplicates slip through, keep the more specific one (usually the principle) and preserve its severity and citations. Never render the same concern twice in one item.
- Do not reorder items. `AnalysisResult.items` arrives in rendering order, which Agent A sets from agenda order. The exception is the executive summary table, which Agent A pre-sorts by governance significance.
- Do not reorder flags within an item. Trust the analyst.

---

## Softening unverified citations

Every authority in `legal_framework` is expected to come from the statute-mapper corpus. If `Citation.verified == False` for a cited section:

1. **Prefer dropping the citation.** A missing citation is better than a wrong one.
2. **If dropping leaves a gap**, soften the language: "The district's counsel should confirm which section of TEC Chapter 45 governs this scenario." Do not render a bare, unverified `TEC §XX.XXX`.

A wrong TEC citation destroys trust permanently. This is the single rule that cannot be waived.

---

## Do not

- **Do not render content that doesn't come from the structured input.** No invented summaries, no rhetorical filler, no "executive summary of the executive summary."
- **Do not modify authority text.** Quote as-is from the statute-mapper corpus. If the corpus quote is wrong, fix the corpus, not the render.
- **Do not reorder flags or items from the agent.** Trust the analyst.
- **Do not beautify beyond the hand reference.** The hand doc is stern, structured, direct. Match it. Do not add emoji, horizontal rules between items, or decorative framing.
- **Do not hardcode doctrine.** Anything that looks like a governance maxim belongs in `principles.md`, not in the template.
- **Do not render partial output as if it were complete.** If `items` is empty or `executive_summary_table` is empty, surface an error; do not ship a truncated doc.

---

## DOCX rendering (Day 3+)

`docx_renderer.py` converts the rendered markdown to `.docx` using `python-docx`:

- `#`, `##`, `###` → Heading 1 / 2 / 3
- Bold prefixes on flags preserved as bold run-level formatting
- Tables preserved as native Word tables
- Block quotes rendered with left-margin indent and italic
- Page numbers in footer, document title in header

Keep the DOCX faithful to the markdown. Fancy formatting can wait until after the markdown quality is dialed.

---

## Rendering entrypoint

```python
from skills.output_formatter.render import render

markdown = render(analysis_result)  # dispatches on analysis_result.output_mode
```

`render()` accepts an `AnalysisResult` pydantic instance or a plain dict with the same shape. It returns a string of markdown. It does not write to disk — the caller decides where the output goes.

---

## When the output looks wrong

Open the hand version side-by-side. Read the same section in both. The delta is your punchlist.

- **Structure drift?** The template is missing a sub-section or has an extra one. Fix the template.
- **Voice drift?** Read `principles.md` §IV aloud, then read your output aloud. Where the mouth-feel changes, the voice is wrong.
- **Citation mismatch?** The statute-mapper corpus is missing a section or the verifier is returning false negatives. Fix Agent B, not the template.
- **Flag tone wrong?** The pattern definition in `risk-flagger/SKILL.md` is producing the wrong severity. Fix Agent C, not the template.

The template is the last mile. It should be small, stable, and opinionated. If you're adding logic to the template to paper over upstream problems, stop and fix upstream.

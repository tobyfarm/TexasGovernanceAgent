---
name: governance-principles
description: Use this skill whenever analyzing a Texas public school board agenda item, strategic plan, monitoring report, policy proposal, or any document where governance judgment applies. The skill enforces a codified operator doctrine — sixteen core principles covering rule-of-law textualism, role clarity between board and administration, measurable goals, transparent deliberation under TOMA, fiduciary urgency, and specificity on the public record. The doctrine was extracted from two years of sitting-trustee work at Brock ISD. Trigger on any item asking for board action, board discussion, board review, board oversight, or any governance analysis task.
---

# Governance Principles Skill

**Owned by Agent C.** This file is a stub. Agent C fills in the full behavior on Day 1. See `agents/AGENT_C.md` for scope.

---

## The doctrine lives in `principles.md`

Read `skills/governance-principles/principles.md` at the start of every analysis pass. That file is the source of truth. This file tells you how to apply it; it does not duplicate the content.

## When applied to an agenda item

For each item:

1. Read the item text and any attached materials.
2. Walk through `principles.md` §I — the sixteen core principles. For each, ask:
   - Does this item trigger this principle?
   - If yes, in what direction — confirming or violating?
3. For each triggered principle, note which signal fired (from the principle's Detection Signals block), the severity (WATCH / RED_FLAG / POSITIVE), and the evidence quote from the item.
4. For each substantive flag, generate a governance question in the trustee voice patterns from §IV. Questions should be specific enough to be read aloud at the meeting.

## Output shape

Emit a structured block per triggered principle:

```json
{
  "principle_id": "P03",
  "principle_name": "Measurable goals or no goal",
  "direction": "VIOLATION",
  "signal": "Strategic objectives presented for Board adoption with measurable outcomes deferred to later reporting",
  "severity": "RED_FLAG",
  "evidence_quote": "...",
  "statute_anchor": "TEC §11.1511(b)(2)-(3)",
  "generated_question": "Will we adopt tonight any objective that does not include a baseline, a target, a date, and a named owner?"
}
```

## Voice enforcement

Every rendered output passes through the voice rules in `principles.md` §IV:

- Quote adopted text verbatim — never paraphrase mandatory language like "shall."
- Number arguments. One point per section.
- No corporate filler. No em-dashes as stacked qualifiers.
- Warm only on students, sparingly.
- Sign as "Trustee [name]" on governance points; "[first name]" on community points.

## Statute verification

Every `statute_anchor` passes through the statute-mapper Skill. If the citation cannot be verified against the bundled corpus, drop the anchor and rephrase the question to not depend on it.

## Do not

- Do not edit `principles.md` — that file is Toby's doctrine. Reference it; do not rewrite it.
- Do not invent principles. Sixteen exist; new principles go into principles.md v2, not into this Skill.
- Do not duplicate risk-flagger patterns. When a principle and a pattern both fire, both are emitted; the output-formatter deduplicates at render time.

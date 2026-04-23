---
name: governance-principles
description: Use this skill whenever analyzing a Texas public school board agenda item, strategic plan, monitoring report, policy proposal, budget amendment, bond action, closed-session posting, or any document where governance judgment applies. The skill enforces a codified operator doctrine — sixteen core principles covering rule-of-law textualism, role clarity between board and administration, measurable goals under TEC §11.1511, transparent deliberation under TOMA, fiduciary urgency, and specificity on the public record. The doctrine was extracted from two years of sitting-trustee work at Brock ISD. Trigger on any item asking for board action, board discussion, board review, board oversight, a performance-goal adoption, a scorecard update, or any governance analysis task.
---

# Governance Principles Skill

**Owned by Agent C.** The doctrine lives in `principles.md`. This file is the behavior layer — how to apply the doctrine to an agenda item and emit structured flags that Agent F renders.

---

## Load order for every analysis pass

1. Read `skills/governance-principles/principles.md` in full. It is authoritative and versioned; re-read it on each invocation so any update to the doctrine takes effect immediately.
2. Read the agenda item text, its attached materials, and any prior minutes or policy references cited in the packet.
3. If the item cites a statute, policy, or TAC rule, route that anchor through the statute-mapper Skill before emitting any flag that depends on it.

---

## Per-principle detection index

For each item, walk the sixteen principles below in order. The signals listed are the canonical trigger patterns. When a signal fires, emit a flag in the output shape defined later in this file. A single item can trigger multiple principles; do not suppress duplicates — Agent F deduplicates at render.

The canonical text of each principle, its "why it matters," and its full canonical quote block all live in `principles.md` §I. Do not paraphrase them into output; cite the principle ID and let the formatter pull the quote.

### P01 — Policy controls over procedure
**Triggers when any of:**
- Administrative interpretation introduces a restriction not present in policy text
- An appeal to TASB guidance is made as if controlling authority
- A deadline, cutoff, or condition appears in BOP or regulations but not in the underlying Board-adopted policy
- Language surfaces like "we've always done it this way," "that's just how TASB recommends," or "our operating procedure says"
**Default direction:** VIOLATION when triggered by restriction; CONFIRMING when the item explicitly subordinates BOP to policy.
**Default severity:** RED_FLAG on TASB-guidance-as-authority; WATCH otherwise.
**Statute anchor candidates:** local BE(LOCAL), BOP subordination clause.

### P02 — Plain-text textualism
**Triggers when any of:**
- Item summarizes a policy in a way that softens or expands the adopted mandatory language
- Administration describes what a policy "means" without citing the specific text
- TASB model, local policy, and BOP are invoked interchangeably as if equal in authority
- Mandatory verbs ("shall," "does not have the authority to") are treated as discretionary
**Hedging rule.** If the underlying text is not included in the packet, the Skill cannot confirm softening. In that case emit a WATCH asking for the verbatim adopted text, not a RED_FLAG.
**Default severity:** RED_FLAG when softening is confirmable against a cited document; WATCH when softening is suspected but the source text isn't in the packet.
**Statute anchor candidates:** the specific policy section at issue (pass to statute-mapper for verification).

### P03 — Equal trustee participation
**Triggers when any of:**
- A trustee-submitted agenda item is deferred, re-routed, or deflected without the submitting member's explicit consent
- Language suggests pre-clearance is required before a trustee can ask a question or submit an item
- President or Superintendent makes a unilateral call that belongs to the Board as a whole
- Procedure is being used to block substance
**Default severity:** RED_FLAG on unilateral deferral; WATCH on pre-clearance language.
**Statute anchor candidates:** BE(LOCAL), TGC §551.043 (posting), the board's own operating procedures.

### P04 — Transparent deliberation (TOMA)
**Triggers when any of:**
- Any suggestion that questions should be asked "offline," "beforehand," or "in private"
- Appeals to "Team of 8" used to suppress dissent or questions before a vote
- Closed-session citations that are vague, blanket, or don't match the actual topic (cross-fires with RF_01 and P11)
- Pressure to handle substantive topics via email rather than on the agenda
**Hedging rule.** Posting the blanket citation alone triggers P11/RF_01 but not P04 by itself. P04 fires when open-session conduct suggests substantive deliberation is being routed away from public view.
**Default severity:** RED_FLAG on suppression language; WATCH on vague-posting alone.
**Statute anchor candidates:** TGC Ch. 551 generally, TGC §551.101, §551.102.

### P05 — Discussion is not action
**Triggers when any of:**
- A discussion-only item is deferred "to a later meeting" with no concrete return date
- Administration frames a discussion request as requiring formal action or approval
- Procedural objections are raised primarily to delay a substantive discussion item
**Default severity:** WATCH on vague deferral; RED_FLAG if the deferral blocks an emerging-issue item (cross-fires with P07 and RF_12).
**Statute anchor candidates:** BE(LOCAL) trustee-submission clause; TEC §11.151(b).

### P06 — Substance over process
**Triggers when both:**
- A procedural argument is raised (authority, prior practice, timing), AND
- The substantive topic underneath is student-outcome bearing (AI, pathways, safety, audit findings, academic performance)
**Hedging rule.** Do not fire P06 on any procedural objection — only when the substantive payload is student-facing. When in doubt, emit a WATCH and name the tension, don't escalate.
**Default severity:** RED_FLAG when the procedural move demonstrably blocks student-outcome work; WATCH otherwise.
**Statute anchor candidates:** TEC §11.151(b), TEC §11.1515.

### P07 — Fiduciary urgency
**Triggers when any of:**
- An item is deferred without a concrete date or decision criterion
- Administration signals "we need more time" without specifying what they'd do with it
- Emerging issues — AI, new statute, safety, audit findings — are routed to "later"
**Default severity:** RED_FLAG on emerging-issue deferrals; WATCH on routine deferrals without criteria.
**Statute anchor candidates:** TEC §11.151(b), TEC §11.1515 (oversight duty runs in real time).

### P08 — Measurable goals or no goal
**The structured absence test.** For every objective, key result, or performance goal in the item, check for all six of: **baseline, target, date, cadence, guardrail, named owner.** Missing any one is a trigger.
**Triggers when any of:**
- An objective is presented without a measure, baseline, target, cadence, or owner
- "Key strategic actions" are presented for Board approval (actions are administration's lane; cross-fires with P16 and RF_10)
- Metrics are deferred to "later reporting cycles"
- An outcome commitment does not identify who owns the number
**Default severity:** RED_FLAG. This is statutory.
**Statute anchor candidates:** TEC §11.1511(b)(2)–(3), TEC §11.251.

### P09 — The floor is not the goal
**Triggers when any of:**
- A goal is pegged to a state-defined minimum (e.g., STAAR "Meets" threshold used as the target, not the floor)
- A scorecard presentation celebrates meeting a floor rather than exceeding it
- No guardrail is articulated beneath which performance triggers intervention
**Default severity:** WATCH. Escalate to RED_FLAG only when the state-minimum target is explicitly adopted as the goal.
**Statute anchor candidates:** TEC §11.1515; reference Principle 9 text.

### P10 — Transparent data, full population
**Triggers when any of:**
- A scorecard or data presentation has coverage under 100% without an explanation
- Aggregation across groups hides subgroup gaps
- Qualitative indicators are presented where quantitative ones exist (e.g., "culture survey" in place of outcome data)
- Outcome data is presented without subgroup breakdowns
**Default severity:** WATCH on partial coverage; RED_FLAG when the item is the TEC §39.306 annual performance report and coverage is partial or the data is qualitative-only.
**Statute anchor candidates:** TEC §39.306, TEC §11.1515.

### P11 — Specificity on the record
**Triggers when any of:**
- Agenda item has a generic header that hides substantive change (e.g., "amendment to Board Policy X" with no summary)
- Closed session is posted under the full range of TGC §§551.071–551.087 without specifying which sections actually apply tonight (cross-fires with RF_01)
- A budget amendment is described as "housekeeping" when it materially changes a fund
- A policy amendment is described by number only with no summary of what's changing
- The item references documents or attachments not included in the board book (cross-fires with RF_14)
**Hedging rule.** Apply a materiality test: would a reasonable community member be able to tell from the agenda header alone what decision is on the table? If not, fire. On routine ministerial items (minutes approval, gift acceptance under $500), do not fire unless the item touches a restricted-fund or public-comment policy.
**Default severity:** WATCH; escalate to RED_FLAG when the vague item is also substantively material (public-comment policy, bond, 4-day week, attendance zones, closure, calendar).
**Statute anchor candidates:** TGC §551.041, §551.043, §551.101.

### P12 — Authority cascades — look up
**Triggers when any of:**
- "We can't do that" framing appears where in fact discretion exists (Superintendent inclusion authority, Board President calendar authority, Board-as-a-whole override)
- Delay is attributed to external actors (counsel, TASB, TEA) where the substantive choice is actually the district's
- A procedural standoff would be resolved by a decision at a named level of authority
**Hedging rule.** Do not fire without identifying the specific level that holds the discretion being disclaimed. If the Skill cannot name the level, emit a WATCH asking "who has the authority to act here?" rather than a RED_FLAG.
**Default severity:** WATCH; RED_FLAG when the disclaimed authority is explicitly granted by statute or local policy cited elsewhere in the packet.
**Statute anchor candidates:** TEC §11.1512 (Superintendent day-to-day), TEC §11.151(b) (Board governance duty), BE(LOCAL) calendar clauses.

### P13 — When in doubt, cite the statute
**Operates as a postprocessing rule, not a detector.** Every flag that makes a governance claim must carry a `statute_anchor`. If the statute-mapper Skill cannot verify the anchor against the bundled corpus, the flag is softened (severity drops one level) or the anchor is removed and the question reworded to not depend on it. Never emit an unverified citation.
**Severity:** N/A — this principle governs all other outputs.

### P14 — Open records as a transparency tool
**Operates as a prescriptive reminder, not a detector.** When P11/RF_14 fires on missing materials, the generated question should mention the Texas Public Information Act (Gov't Code Ch. 552) as a legitimate next step. Do not emit P14 as a standalone flag.

### P15 — Tell the community
**Triggers when all:**
- P11 has fired on a vague title, AND
- The underlying topic keyword is in the community-interest list: public comment, attendance zones, bond, calendar, 4-day week, closure, public participation (BED), RFP for major vendor, closed-session on personnel at superintendent level
**Default severity:** RED_FLAG when the vague title is on a community-interest topic; otherwise P11 alone is sufficient.
**Statute anchor candidates:** TGC §551.041, BE(LOCAL), BED(LOCAL).

### P16 — Role clarity (board governs, admin executes)
**Triggers when any of:**
- Strategic plan item asks the Board to approve implementation tactics or "key strategic actions" (cross-fires with P08 and RF_10)
- Administration presents measures as already-decided with no Board adoption history on record
- Board member-directed items venture into HR, scheduling, or specific curriculum selections (reverse-direction drift)
- Scorecard presentation includes targets with no visible Board adoption date or resolution
**Hedging rule on the reverse direction.** When measures appear without adoption history, default to WATCH framed as "when did the Board adopt this target?" rather than asserting role drift.
**Default severity:** RED_FLAG on "actions for Board approval"; WATCH on absent adoption history.
**Statute anchor candidates:** TEC §11.1511(b)(2)–(3), TEC §11.1512, TEC §11.201(d).

---

## Question generation

For every flag at severity RED_FLAG or a substantive WATCH, generate at least one governance question in the voice patterns of `principles.md` §IV.

**Per-item question caps.**
- **Default items** (consent items, routine contracts, single-topic action items): up to **5** questions.
- **Multi-topic major items** (Priority-1 Balanced Scorecard, Budget Workshop, Bond parameter orders, major policy revisions): up to **12** questions. Each question must target a distinct metric, decision, or decision-relevant unknown. The hand version of a 166-page April 13 board book carries 10–12 questions on each of these items; compressing to 5 loses per-metric accountability hooks.

**Rules.**
1. Numbered, specific, and grounded in the quoted text of the item or the cited authority.
2. Sharp but not hostile. "I understand that reasoning. The issue is that…" is a model opener for a disagreement question.
3. Each question must be answerable by a named role in the room (Superintendent, Board President, CFO, financial advisor, legal counsel). Do not generate rhetorical questions.
4. When the question turns on a statute or policy, quote the controlling text.
5. End with a specific ask. "Will the presiding officer state, before entering closed session tonight, which specific subsections of §551.071–551.087 the Board intends to invoke?" is the shape.

**Closed-session question template.** When P11 or RF_01 fires on a closed-session posting, always emit the standing four-question set, adapted to the posted range:

1. Which specific subsections of TGC Chapter 551 does the Board intend to invoke tonight, and for which topic under each?
2. Is the certified agenda and audio recording being maintained per TGC §551.103, and preserved for at least two years?
3. Which exceptions are anticipated tonight — personnel (§551.074) on specific individuals? real property (§551.072)? attorney consultation (§551.071)? — so the public can track what is being deliberated?
4. *(Only when §551.074 is in scope.)* Have the affected employees been notified of their statutory right to request a public hearing under §551.074(b)?

---

## Output shape

Emit one structured block per triggered principle. Multiple blocks per item are expected. Agent F deduplicates at render. Field names are aligned with Agent A's `Flag` pydantic model (`agent/types.py`) where they map cleanly, with a few principle-specific extras.

```json
{
  "pattern_id": "P08",
  "principle_name": "Measurable goals or no goal",
  "direction": "VIOLATION",
  "signal": "Strategic objective presented for Board adoption with baseline, target, and cadence deferred to a later reporting cycle",
  "severity": "RED_FLAG",
  "summary": "Objectives being adopted tonight lack baseline, target, cadence, guardrail, or owner — violates TEC §11.1511(b)(2)-(3).",
  "detail": "TEC §11.1511(b)(2)-(3) requires the Board to adopt performance goals and monitor progress. An objective stated as 'every student will grow' without a baseline number, a target number, a date, a review cadence, a guardrail below which intervention triggers, and a named owner is aspiration — not governance. The Board cannot monitor what is not measurable.",
  "evidence_quote": "Objective 2: Every student will demonstrate growth.",
  "citations": ["TEC §11.1511(b)(2)-(3)"],
  "generated_question": "Will we adopt tonight any objective that does not include a baseline, a target, a date, a review cadence, a guardrail, and a named owner? If so, which specific number is the Board committing to monitor?",
  "cross_fires_with": ["RF_05", "RF_10", "P16"]
}
```

Fields:
- `pattern_id` — one of P01 through P16. Maps to `Flag.pattern_id`.
- `principle_name` — verbatim from `principles.md` §I section heading. Metadata for Agent F's rendering.
- `direction` — `VIOLATION`, `CONFIRMING`, or `MIXED`. Metadata.
- `signal` — which detection signal from the principle fired. Quote the signal verbatim from the index above. Metadata.
- `severity` — `RED_FLAG`, `WATCH`, or `POSITIVE`. Maps to `Flag.severity`.
- `summary` — one-line summary for the executive table. Maps to `Flag.summary`.
- `detail` — prose explanation in §IV voice. Maps to `Flag.detail`.
- `evidence_quote` — the exact sentence or phrase from the agenda item that triggered the principle. No paraphrase. Metadata.
- `citations` — the verified citations. Empty list if no citation survives statute-mapper verification. Maps to `Flag.citations`.
- `generated_question` — one question in §IV voice. Flows into `ItemAnalysis.questions`. Null for POSITIVE flags.
- `cross_fires_with` — other principle or pattern IDs that also fire. Agent F uses this for deduplication at render.

---

## Severity override rules

Adjust severity by at most one level, and only when one of these contextual signals is present:

- **Downgrade RED_FLAG → WATCH** when the underlying text is not in the packet and the violation is inferred from the summary only (applies especially to P02).
- **Downgrade RED_FLAG → WATCH** when the item is discussion-only with no vote tonight AND the flag would be cured by a question on the record.
- **Upgrade WATCH → RED_FLAG** when the same signal has fired on this item in prior meetings without remediation (requires packet to include minutes showing prior incidence).
- **Upgrade WATCH → RED_FLAG** when a P11 vague-title flag also hits the P15 community-interest keyword list.

Document every override in the `detail` text of the downstream risk-flagger output (the Skills share a render pass).

---

## Voice enforcement

Every rendered output passes through the voice rules in `principles.md` §IV:

- Quote adopted text verbatim — never paraphrase mandatory language like "shall" or "does not have the authority to."
- Number arguments. One point per section.
- No corporate filler. No em-dashes as stacked qualifiers. No "I want to be respectful of everyone's time" prefaces.
- Warm only on students, sparingly. "Every single child who walks through our doors" is a finishing move, not a header.
- Sign as "Trustee [name]" on governance points; "[first name]" on community points.
- Direct on disagreement: "I understand that reasoning. The issue is that…"

---

## Statute verification protocol

Every `statute_anchor` emitted by this Skill routes through the statute-mapper Skill before the item is finalized. If the citation does not verify against the bundled corpus:

1. First try to find a correct adjacent citation (e.g., §11.1511(b)(3) when (b)(2) was claimed).
2. If no correct citation is found, drop the anchor entirely.
3. Reword the `generated_question` to not depend on the dropped anchor.
4. Log the verification failure to `skills/risk-flagger/eval_notes.md` so Agent B can audit the corpus gap.

An unverified citation is a poison pill. Soften rather than invent.

---

## Do not

- **Do not edit `principles.md`.** That file is Toby's doctrine. Reference it; do not rewrite it. Proposed changes go to Toby for a version bump.
- **Do not invent principles.** Sixteen exist; new principles go into principles.md v2, not into this Skill.
- **Do not inline principle content into this file or into prompts.** Load `principles.md` at runtime. The doctrine versions.
- **Do not duplicate risk-flagger patterns.** When a principle and a pattern both fire, both are emitted; the output-formatter deduplicates at render time.
- **Do not emit prose.** This Skill emits structured flags. Prose is Agent F's responsibility.

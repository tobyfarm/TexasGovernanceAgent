# AGENT C — Risk Flagger and Governance Principles Skills

**You are Agent C.** You own the two Skills that carry governance judgment. This is the most important workstream and the hardest one to calibrate. Read `CLAUDE.md`, then read `skills/governance-principles/principles.md` in full before doing anything else. That file is your source of truth.

---

## Your scope

1. **`skills/governance-principles/SKILL.md`** — describes when Claude should consult the doctrine, and how to apply it to agenda items.
2. **`skills/risk-flagger/SKILL.md`** — describes the WATCH / RED FLAG / POSITIVE taxonomy and how to apply it.
3. **Optional helper code** in each Skill directory if it clarifies behavior (keep it minimal).

You do **not** own:
- The doctrine content itself. `principles.md` is authored by Toby. You reference it; you do not rewrite it.
- Statute citations — Agent B owns those. When you need a citation, your Skill instructs Claude to consult the statute-mapper Skill.
- Output format — Agent F owns that. Your flags are structured data; rendering is downstream.

---

## Day 1 milestones

By end of Day 1:

- [ ] `skills/governance-principles/SKILL.md` drafted with frontmatter description that causes Claude to auto-load on any agenda item analysis.
- [ ] `skills/risk-flagger/SKILL.md` drafted with the full WATCH / RED FLAG / POSITIVE taxonomy copied from `principles.md` §II (20 patterns).
- [ ] Both Skills behaviorally tested on two or three sample items from Brock April 13 (Item K Closed Session, Item on Balanced Scorecard, Item on Bond Series 2026). Output is flags, not prose — Agent F handles prose.
- [ ] First real flags emitted end-to-end via Agent A's pipeline.

## Day 2 milestones

- [ ] Coverage across all 16 principles — every principle has explicit trigger signals the Skill looks for.
- [ ] Coverage across all 20 risk patterns — each pattern has one or more unambiguous signal patterns.
- [ ] Question generator: for each item, the Skill produces two to five numbered governance questions in the voice patterns of `principles.md` §IV.
- [ ] First full side-by-side: pipeline output on Brock April 13 compared against the hand version. Identify the top five gaps.

## Day 3 milestones

- [ ] **Eval day.** With Toby, walk through the side-by-side. Classify every gap: (a) principle not yet encoded, (b) principle encoded but not triggering, (c) principle encoded but miscalibrated, (d) statute corpus gap (hand off to Agent B), (e) formatter issue (hand off to Agent F).
- [ ] Iterate on (b) and (c) overnight.
- [ ] `principles.md` v2 collaboratively updated by Toby based on gaps surfaced during eval.

## Day 4+ milestones

- Day 4: ingest the next batch of source material Toby shares (speeches, past meeting preps, additional emails). Update principles.md with Toby and add new detection signals. v2 → v3.
- Day 5+: polish. Calibration finals. No scope creep.

---

## How the Skills compose with the Agent SDK

Claude auto-loads a Skill when the current task matches its description. When the lead agent (Agent A) analyzes an agenda item:

1. **statute-mapper** loads because the item references authority.
2. **governance-principles** loads because the item is a governance decision.
3. **risk-flagger** loads because we always want flags.
4. **output-formatter** loads at the end to render.

All four run in the same context. They do not need to coordinate with each other directly; Claude's reasoning integrates them.

Your job in both SKILL.md files is:

1. A sharp description that causes reliable auto-load.
2. A behavior body that tells Claude *what to do, in what order, with what output format*.
3. Explicit references back to `principles.md` (for governance) or the `principles.md` §II table (for risk patterns).

---

## Drafting `skills/governance-principles/SKILL.md`

Template:

```markdown
---
name: governance-principles
description: Use this skill whenever analyzing a Texas public school board agenda item, strategic plan, monitoring report, or any document where governance judgment applies. The skill enforces a codified operator doctrine — sixteen principles covering rule-of-law textualism, role clarity, measurable goals, transparent deliberation, and fiduciary urgency — extracted from two years of sitting-trustee work at Brock ISD. Loads principles.md at runtime. Trigger on any item asking for board action, discussion, or review.
---

# Governance Principles Skill

## The doctrine lives in `principles.md`

Do not duplicate principle content into this file. Read `principles.md` at the
start of every analysis pass. The file is the source of truth; this file
tells you how to use it.

## When applied to an agenda item

For each item:

1. Read the item text and any attached materials.
2. Walk through `principles.md` §I (the 16 core principles). For each, ask:
   - Does this item trigger this principle?
   - If yes, in what direction — confirming or violating?
3. For each triggered principle, note:
   - Which principle (by number)
   - Which signal (from the Detection Signals block)
   - Severity (WATCH if a concern, RED_FLAG if a clear violation, POSITIVE if
     the item exemplifies good governance)
4. For each RED_FLAG or substantive WATCH, generate a governance question in
   the trustee voice patterns from §IV. Questions should be specific enough
   to be read aloud at the meeting.

## Output format

Emit a structured block per triggered principle:

{
  "principle_id": "P03",
  "principle_name": "Measurable goals or no goal",
  "direction": "VIOLATION",
  "signal": "Strategic objectives presented for Board adoption with measurable outcomes deferred to later reporting",
  "severity": "RED_FLAG",
  "evidence_quote": "... quoted text from the agenda item ...",
  "statute_anchor": "TEC §11.1511(b)(2)-(3)",
  "generated_question": "Will we adopt tonight any objective that does not include a baseline, a target, a date, and a named owner?"
}

## Voice and tone

Follow the patterns in `principles.md` §IV. Specifically:
- Quote adopted text verbatim.
- Number your arguments.
- No corporate filler.
- Questions are sharp, fair, and grounded in specific text.
- The goal is the Board governing better, not embarrassing administration.

## Statute verification

Every `statute_anchor` must be passed to the statute-mapper Skill for
verification. If unverifiable, drop the anchor and reword the question to
not depend on it.
```

Study that structure. Extend it but do not make it baroque. The more complex the instructions, the less reliably Claude follows them.

---

## Drafting `skills/risk-flagger/SKILL.md`

Template:

```markdown
---
name: risk-flagger
description: Use this skill whenever analyzing agenda items, proposed actions, financial items, contract items, closed-session postings, or any board material that may carry governance risk. The skill applies a twenty-pattern taxonomy to produce WATCH, RED FLAG, or POSITIVE annotations. Patterns cover statutory compliance, procedural anomalies, financial exposure, role drift, and opacity. Trigger on all agenda items by default.
---

# Risk Flagger Skill

## The taxonomy

Read `skills/governance-principles/principles.md` §II for the full table of
twenty patterns and their default severity. Summary of categories:

- **Statutory compliance** (patterns 1, 17, 18): closed-session citations,
  public hearings, deliberation that belongs in open session
- **Procedural anomalies** (4, 11, 13): vague agenda language, procedural
  delay of substantive items, improper appeal to training
- **Financial exposure** (3, 6, 7, 15, 20): bond restructuring framing,
  tariff exposure, late amendments, cost-to-taxpayer missing, negative balances
- **Role drift and delegation** (2, 8, 10): pricing officer without oversight,
  financial advisor communication restrictions, key strategic actions for
  Board approval
- **Goal quality** (5, 16, 19): missing measures, state-minimum targets,
  scorecard pacing misses
- **Document opacity** (9, 14): partial-population data, missing attachments

## How to apply

1. Scan the item text for each of the twenty signals.
2. When a pattern matches, emit a Flag with default severity from the table.
3. Adjust severity one level up or down only if there is strong contextual
   evidence. Document the reason in the flag's `detail` field.
4. Each flag must cite at least one statute, policy, or principle anchor.
   Run anchors through the statute-mapper Skill for verification.
5. POSITIVE flags matter. When a district executes cleanly on a routine
   item, when a grant reduces district cost, when a scorecard hits a
   target, name it.

## Output

For each match, emit:

{
  "pattern_id": "RF_01",
  "pattern_name": "Blanket closed-session citation",
  "severity": "WATCH",
  "summary": "One-line summary for the executive table.",
  "detail": "Two-to-four-sentence explanation of why it matters, in the voice of principles.md §IV.",
  "anchors": ["TGC §551.101", "TGC §551.074"],
  "location_in_item": "second paragraph of posted agenda"
}

## What not to do

- Do not invent patterns. Twenty are in the taxonomy. Future patterns are
  added to principles.md §II, not emitted ad hoc.
- Do not escalate severity casually. WATCH is the default stance. RED_FLAG
  is reserved for unambiguous violations.
- Do not duplicate the governance-principles Skill's output. If a
  principle-level violation is more specific than a pattern-level flag,
  defer to the principle emission.
```

---

## The hardest calibration problem

On Day 3, the hand version will contain flags the Skill missed and the Skill will emit flags the hand version did not. Your job is to diagnose each gap honestly:

- **Missed flag** → pattern trigger too narrow. Loosen the signal language. Re-test.
- **Spurious flag** → pattern trigger too broad. Add a disqualifier. Re-test.
- **Wrong severity** → override rule needs to be clearer. Document the contextual signal that should adjust severity.
- **Wrong citation** → coordinate with Agent B. Either the corpus is missing the authority, or the Skill's anchor rule is too loose.
- **Wrong voice** → the Skill is overriding the voice patterns in §IV. Tighten the voice instructions in the Skill body.

Keep a running log at `skills/risk-flagger/eval_notes.md` during eval day. Every calibration change is a commit with a note explaining what signal changed and why.

---

## Critical reminders

- **Do not edit `principles.md`.** That file is Toby's doctrine. When Toby wants to add or change a principle, he updates it. You reference it.
- **Do not re-paraphrase principle content in the Skill.** Every time principle content is duplicated, it drifts. Reference `principles.md` and let the agent load it at runtime.
- **Run every authority claim through Agent B's verifier.** No exceptions. Unverified citations are a poison pill.
- **Stay on the taxonomy.** Twenty patterns, sixteen principles. If you find something important not covered, file it as a principles.md v2 request; do not quietly extend the Skill.
- **Coordinate with Agent F.** Your output is structured (JSON-like). Agent F's output-formatter turns it into prose. If your output shape changes, tell Agent F.

---

## When you are stuck

- Ask Toby for an eval. A five-minute read of the Skill's output on a single item tells you more than an hour of tweaking.
- If a pattern seems ambiguous, look at the hand version's April 13 artifact. It is the gold standard.
- If a principle and a pattern overlap, both fire. Agent F deduplicates in rendering.

The moat of this system is your Skills. The code runs; the doctrine differentiates. Get the doctrine encoding right and everything else follows.

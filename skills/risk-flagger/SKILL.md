---
name: risk-flagger
description: Use this skill on every agenda item, proposed action, financial transaction, contract, closed-session posting, scorecard presentation, bond resolution, budget amendment, or board decision to produce WATCH, RED FLAG, or POSITIVE annotations. The skill applies a twenty-pattern taxonomy covering statutory compliance failures (closed-session citations, open-meetings compliance, public hearings), procedural anomalies (vague agendas, procedural delay, TASB-as-authority), financial exposure (bond restructuring, tariff exposure, late budget amendments, missing cost-to-taxpayer, negative balances), role drift and delegation (pricing officers without oversight, financial advisor communication, key-strategic-actions approval), goal quality (missing measures, state-minimum targets, scorecard pacing misses), and document opacity (partial-population data, missing attachments). Trigger on all agenda items by default.
---

# Risk Flagger Skill

**Owned by Agent C.** The taxonomy lives in `principles.md` §II. This file is the detection layer — how to match the twenty patterns against the board-book text, what severity to emit, and how to disqualify false positives.

---

## Load order for every scan

1. Read `skills/governance-principles/principles.md` §II for the canonical taxonomy. Re-read on each invocation; patterns version.
2. Read the agenda item text and any attached documents referenced in the packet.
3. Scan the item for each of the twenty signal patterns below. Multiple matches per item are expected.
4. Route every `anchors` list through the statute-mapper Skill before the flag is finalized. If the anchor does not verify, drop it and either reword or downgrade the flag.

---

## Detection table (RF_01 through RF_20)

Each row below maps to one pattern in `principles.md` §II. The "Fires on" column is the surface signal the Skill scans for. The "Disqualifier" column is the contextual signal that should suppress a match. The "Anchors" column lists default statute or policy citations to verify through statute-mapper. The "Cross-fires with" column names principles that will typically also trigger.

### RF_01 — Blanket closed-session citation
- **Fires on:** agenda posting lists the range §551.071–551.087 (or a superset of three or more consecutive subsections) without naming the specific topic being closed, or cites the whole of §551 as the authority.
- **Default severity:** WATCH.
- **Disqualifier:** posting names the single specific subsection that applies (e.g., "§551.074 — evaluation of the Superintendent").
- **Anchors:** TGC §551.101 (presiding officer must announce specific section before entering), TGC §551.102 (no action in closed session).
- **Cross-fires with:** P04, P11.
- **Summary line:** "Closed-session posted under blanket §§551.071–551.087 range — presiding officer should state specifics on the record before entering."

### RF_02 — Delegation of execution authority without Board oversight
- **Fires on:** item authorizes a Pricing Officer, delegate, or agent to act on behalf of the Board on a bond sale, contract award, or major purchase without stipulating a Board-facing oversight mechanism. The three oversight elements are (i) a dollar ceiling or maximum loss cap, (ii) a time window or expiration, and (iii) a requirement to report final terms back to the Board at the next regular meeting.
- **Default severity:** RED_FLAG when all three elements are absent. WATCH when one or two elements are present but not all three. Suppress the flag only when all three elements are explicitly in the item.
- **Disqualifier:** all three oversight elements present AND the delegation is bounded by a written parameter order referencing them.
- **Anchors:** TGC §1207.007, §1371.053 (Pricing Officer for bonds), TEC §11.1512 (Superintendent day-to-day).
- **Cross-fires with:** P16.
- **Summary line (RED_FLAG):** "Execution authority delegated with no Board-facing oversight mechanism."
- **Summary line (WATCH):** "Execution authority delegated with partial oversight — [element missing]; ask for report-back on final terms at the next meeting."

### RF_03 — Bond restructuring framed as "savings"
- **Fires on:** item describes a bond action as producing "savings" when the underlying structure is an extension of term, a deferral of principal, or a net cash outflow over the life of the debt.
- **Default severity:** RED_FLAG.
- **Disqualifier:** the item quantifies both (a) present-value savings using a stated discount rate AND (b) total cash paid over the life of the bond, and the total is lower than the pre-refunding total.
- **Anchors:** TEC §45.001 (bond issuance), MSRB G-17 (fair dealing), MSRB G-42 (fiduciary duty).
- **Cross-fires with:** P13.
- **Summary line:** "Refunding characterized as 'savings' — confirm whether it is present-value savings or term extension, and state total cash cost to taxpayers."

### RF_04 — Vague agenda title on substantive item
- **Fires on:** agenda header is generic ("discuss/approve amendment to Board Policy X," "housekeeping budget amendment," "approve contract") on an item whose attached materials reveal a material change.
- **Default severity:** WATCH; escalate to RED_FLAG when the topic is on the community-interest keyword list (public comment, attendance zones, bond, calendar, 4-day week, closure, BED, RFP for major vendor).
- **Disqualifier:** header specifies the section, dollar amount, or subject matter sufficient for a community member to know what is on the table.
- **Anchors:** TGC §551.041, §551.043.
- **Cross-fires with:** P11, P15.
- **Summary line:** "Agenda title does not disclose substantive change — public cannot tell from posting what decision is on the table."

### RF_05 — Goals without measures, baselines, targets, dates, or owners
- **Fires on:** any objective, performance goal, or key result presented for Board adoption that lacks any one of: baseline, target, date, cadence, guardrail, named owner.
- **Default severity:** RED_FLAG.
- **Disqualifier:** none for goal-adoption items. On informational scorecards, downgrade to WATCH.
- **Anchors:** TEC §11.1511(b)(2)–(3), TEC §11.251.
- **Cross-fires with:** P08, P16.
- **Summary line:** "Objective presented for Board adoption without [missing element] — violates TEC §11.1511."

### RF_06 — Tariff, supply chain, or price-adjustment exposure on vendor quotes
- **Fires on:** vendor quote, purchase order, or RFP award includes a tariff pass-through clause, a price-adjustment clause tied to commodity indices, or a quote-expiration pressure used to compress deliberation.
- **Default severity:** WATCH.
- **Disqualifier:** quote carries a stated ceiling, a fixed-price term, and no commodity-index clause.
- **Anchors:** TEC §44.031 (competitive bidding, best-value).
- **Cross-fires with:** —.
- **Summary line:** "Vendor quote exposes district to price escalation; confirm ceiling and whether quote-expiration timing is driving the vote."

### RF_07 — Late-cycle budget amendments
- **Fires on:** budget amendment brought late in the fiscal year (Q4 of the district's fiscal calendar) after accounts have been depleted, without an earlier forecast that flagged the drawdown.
- **Default severity:** WATCH.
- **Disqualifier:** prior board packet includes a mid-year forecast that projected the overrun.
- **Anchors:** TEC §44.002, §44.006.
- **Cross-fires with:** P07.
- **Summary line:** "Budget amendment brought after accounts drawn down — why was this not forecast sooner?"

### RF_08 — Financial advisor communication restrictions
- **Fires on:** materials, operating procedure, or administrative statement limits trustees from communicating directly with the district's municipal advisor, or channels all trustee questions through administration.
- **Default severity:** RED_FLAG.
- **Disqualifier:** none. MSRB G-42 fiduciary duty runs to the governing body.
- **Anchors:** MSRB G-42, MSRB G-17.
- **Cross-fires with:** P03, P16.
- **Summary line:** "Municipal advisor's fiduciary duty under MSRB G-42 runs to the governing body; direct trustee access is not administration's to grant or withhold."

### RF_09 — Partial-population data presented without a label
- **Fires on:** scorecard, survey, or data presentation where the reported coverage is below 100% (or is unstated) and no explanation of the subset is provided.
- **Default severity:** WATCH; escalate to RED_FLAG when the item is the TEC §39.306 annual public-performance presentation.
- **Disqualifier:** coverage rate is stated and the subset selection is explained.
- **Anchors:** TEC §39.306.
- **Cross-fires with:** P10.
- **Summary line:** "Data represents [X]% of the population with no explanation — presentation should state coverage and reason on the record."

### RF_10 — "Key strategic actions" presented for Board approval
- **Fires on:** strategic plan or scorecard item asks the Board to approve implementation actions or tactics, rather than objectives, measures, guardrails, and cadence.
- **Default severity:** WATCH.
- **Disqualifier:** the item separates Board-adopted objectives from administration-owned actions explicitly.
- **Anchors:** TEC §11.1511(b)(2)–(3), TEC §11.1512, TEC §11.201(d).
- **Cross-fires with:** P08, P16.
- **Summary line:** "Item asks the Board to approve actions — actions are administration's lane. Board adopts objectives, measures, guardrails, and cadence."

### RF_11 — Procedural objection used to delay substantive student-outcome item
- **Fires on:** item text or minutes reflect a procedural objection (authority, prior practice, timing, TASB guidance) raised against a student-outcome-bearing topic (AI, pathways, safety, audit findings, academic performance) that would otherwise proceed.
- **Default severity:** RED_FLAG.
- **Disqualifier:** the procedural objection identifies a statutory conflict AND the substantive topic is already on a firm return date.
- **Anchors:** TEC §11.151(b), TEC §11.1515, BE(LOCAL).
- **Cross-fires with:** P03, P05, P06.
- **Summary line:** "Procedural objection delays a substantive student-outcome item — principle 6 applies."

### RF_12 — Emerging-issue items routed to "later" without a date
- **Fires on:** item defers AI, new statute compliance, safety finding, audit finding, or regulatory change without a concrete return date or decision criterion.
- **Default severity:** RED_FLAG.
- **Disqualifier:** the deferral states a specific return meeting date and names what evidence or briefing will be produced between now and then.
- **Anchors:** TEC §11.151(b), TEC §11.1515.
- **Cross-fires with:** P05, P07.
- **Summary line:** "Emerging-issue item deferred without a date — delay is not neutral."

### RF_13 — Governance training cited to override adopted policy
- **Fires on:** Lone Star Governance (LSG), TASB, Team of 8, or similar training framework is cited as controlling authority when Board-adopted policy or statute says otherwise.
- **Default severity:** RED_FLAG.
- **Disqualifier:** training is cited as supplementary context alongside the controlling policy or statute.
- **Anchors:** BE(LOCAL), and whatever policy the training is being invoked against.
- **Cross-fires with:** P01.
- **Summary line:** "Governance training framework invoked to override Board-adopted policy — the policy controls."

### RF_14 — Referenced materials not included in the board book
- **Fires on:** item references a contract, policy, report, or attachment that is not included in the board book shared with trustees and the public.
- **Default severity:** RED_FLAG.
- **Disqualifier:** the referenced material is linked in the packet and accessible before the meeting.
- **Anchors:** TGC §551.043 (72-hour posting), Gov't Code Ch. 552 (PIA).
- **Cross-fires with:** P11, P14.
- **Summary line:** "Item references materials not included in the packet — the public should be able to read what the Board is reading."

### RF_15 — Action item with cost to taxpayers not on the record
- **Fires on:** item requiring a vote where the total cost to taxpayers is not stated in the posted materials or discussion, including multi-year total and any contingency exposure.
- **Default severity:** RED_FLAG.
- **Disqualifier:** the total cost and any contingency are stated on the record.
- **Anchors:** TEC §44.002 (budget framework), TEC §45.001 (bonds), MSRB G-17 (fair dealing).
- **Cross-fires with:** P13.
- **Summary line:** "Action item requires a vote without the cost to taxpayers on the record."

### RF_16 — Scorecard targets at or near the state minimum
- **Fires on:** scorecard or strategic plan target is pegged at the state-defined minimum (e.g., STAAR "Meets" bar, FIRST pass score) as the goal, not as the floor.
- **Default severity:** WATCH.
- **Disqualifier:** the target exceeds the state minimum and a separate guardrail is named below which intervention triggers.
- **Anchors:** TEC §11.1515; reference Principle 9.
- **Cross-fires with:** P09.
- **Summary line:** "Target pegged to the state minimum — the floor is not the goal."

### RF_17 — Statutorily-required public hearing not clearly held or recorded
- **Fires on:** a budget hearing, tax-rate hearing, or other statutorily-required public hearing is scheduled but the materials do not confirm posting, notice, or a record of the hearing.
- **Default severity:** RED_FLAG.
- **Disqualifier:** the materials show the notice, posting, and a record of the hearing with opportunity for public comment.
- **Anchors:** TEC §44.004 (budget adoption/hearing), Tax Code §26.06 (tax-rate hearing), TGC Ch. 551.
- **Cross-fires with:** P11.
- **Summary line:** "Statutorily-required public hearing — confirm notice, posting, and record on the public record."

### RF_18 — Deliberation that belongs in open session routed to closed session
- **Fires on:** closed session is posted on a subject that is not personnel-specific under §551.074, not attorney consultation on litigation or negotiation under §551.071, not real property under §551.072, not security under §551.076, and not one of the other enumerated exceptions. General policy deliberation routed to closed session.
- **Default severity:** RED_FLAG when the posted or convened subject clearly exceeds the cited exception.
- **Prospective-reminder mode.** When §551.074 is in a posted closed-session range (including blanket ranges that include it), emit a WATCH-severity reminder that §551.074 covers specific individuals by name or position only — general employment policy, salary schedules, and working conditions must be deliberated in open session per TOMA. This fires even before the session convenes; it is the standing prospective warning the hand version applies on closed-session items.
- **Disqualifier (RED_FLAG):** the closed-session subject matches the cited subsection (e.g., §551.074 used only on specific named individuals).
- **Anchors:** TGC §551.071, §551.072, §551.074, §551.076, §551.101.
- **Cross-fires with:** P04, P11.
- **Summary line (RED_FLAG):** "Subject routed to closed session appears to exceed the cited exception — Chapter 551 exceptions are read narrowly."
- **Summary line (WATCH, prospective):** "§551.074 covers specific individuals by name/position only. If the discussion tonight veers into general employment policy, working conditions, or salary schedules, it must return to open session."

### RF_19 — Scorecard pacing miss near an assessment window
- **Fires on:** scorecard update shows off-pace on a goal with fewer than 90 days to the next assessment window (STAAR, EOC, TELPAS) and no intervention plan is named.
- **Default severity:** WATCH.
- **Wrong-direction override:** escalate WATCH → RED_FLAG when the pacing miss is also a wrong-direction trajectory (MOY worse than BOY on Meets %, Predicted Growth, or equivalent leading indicator) AND the gap to annual goal is ≥15 points. A flat-but-off-pace indicator stays at WATCH; a rising-but-still-off-pace indicator stays at WATCH with a positive framing.
- **Disqualifier:** the item includes a dated intervention plan with named owner and measurable check-in before the assessment window.
- **Anchors:** TEC §11.1515, TEC §11.251.
- **Cross-fires with:** P08, P09.
- **Summary line (WATCH):** "Pacing miss with an assessment window approaching — demand a specific, dated intervention plan before the test."
- **Summary line (RED_FLAG, wrong-direction):** "Metric is moving the wrong way with an assessment window approaching — the interim system is surfacing the miss while intervention is still possible. A specific, dated intervention plan is required tonight."

### RF_20 — Account balance at or near zero or negative without prior warning
- **Fires on:** a fund balance, activity account, grant account, or auxiliary account is reported at zero, negative, or within a threshold of depletion without prior forecast or warning to the Board.
- **Default severity:** WATCH; escalate to RED_FLAG when the shortfall affects a statutory-reserve fund.
- **Disqualifier:** a prior monthly financial report flagged the drawdown with a forecast date.
- **Anchors:** TEC §44.002, §44.006.
- **Cross-fires with:** P07.
- **Summary line:** "Account balance near zero without prior warning — why did the district not see this coming?"

---

## POSITIVE flag catalog

The risk-flagger also names governance wins. Do not treat these as filler; POSITIVE flags are part of how Toby distinguishes real governance from reflexive opposition.

- **PF_A — Grant-backed purchases that reduce district cost** while still meeting a stated need. Name the grant, the cost offset, and the need.
- **PF_B — Clean execution on a routine item** with no embedded surprises (minutes, gift acceptance, routine reports). Name it when the cleanliness matters; do not name it on every filler item.
- **PF_C — Scorecard bright spots** where a target was hit or exceeded with a replicable intervention. Name the intervention and ask how it replicates.
- **PF_D — Proactive compliance** before a statute or deadline forces the action (early SB coverage, voluntary TEA framework adoption, early audit remediation).
- **PF_E — Specificity added to a previously vague item** (e.g., a closed-session citation narrowed from blanket to §551.074 explicitly after prior feedback).

POSITIVE flags emit the same JSON shape as WATCH/RED_FLAG with severity `POSITIVE`, `generated_question` null, and `summary` stating what was done well.

---

## Output shape

Emit one structured Flag per match. Multiple flags per item are expected. Field names align with Agent A's `Flag` pydantic model (`agent/types.py`); extra metadata travels alongside.

```json
{
  "pattern_id": "RF_01",
  "pattern_name": "Blanket closed-session citation",
  "severity": "WATCH",
  "summary": "Closed-session posted under blanket §§551.071–551.087 range — presiding officer should state specifics on the record before entering.",
  "detail": "The agenda lists the full §551.071–§551.087 range. Valid for posting, but TGC §551.101 requires the presiding officer to announce the specific subsection before entering closed session. Ask the presiding officer, before the Board recesses, which subsections actually apply tonight. Blanket citations give maximum flexibility; they also mean almost any topic could be discussed in closed session.",
  "citations": ["TGC §551.101", "TGC §551.102"],
  "location_in_item": "closed-session header of posted agenda",
  "cross_fires_with": ["P04", "P11"]
}
```

Fields:
- `pattern_id` — RF_01 through RF_20, or PF_A through PF_E for POSITIVE. Maps to `Flag.pattern_id`.
- `pattern_name` — verbatim from `principles.md` §II. Not on `Flag` directly; Agent A may prepend to `summary` or carry as metadata.
- `severity` — `RED_FLAG`, `WATCH`, or `POSITIVE`. Maps to `Flag.severity`.
- `summary` — one-line summary for the executive table. One sentence. Maps to `Flag.summary`.
- `detail` — two to four sentences in the voice of `principles.md` §IV. Quotes the controlling text when relevant. Names the specific ask. Maps to `Flag.detail`.
- `citations` — verified citations only. Pass through statute-mapper; drop any that do not verify. Maps to `Flag.citations`.
- `location_in_item` — where in the packet the signal was detected. Not on `Flag`; Agent A carries as auxiliary metadata if needed for debugging.
- `cross_fires_with` — principle IDs from the governance-principles Skill that also fire. Agent F uses this for deduplication at render.

---

## Severity override rules

Adjust severity by at most one level. Only these contextual signals warrant an override; document the reason in `detail`:

- **Downgrade RED_FLAG → WATCH** on RF_05 when the item is an informational scorecard, not a goal-adoption vote.
- **Downgrade RED_FLAG → WATCH** on RF_14 when the missing materials are routinely omitted (e.g., confidential personnel backup) and a public version is promised on request.
- **Upgrade WATCH → RED_FLAG** on RF_04 when the vague title is on a community-interest topic (public comment, attendance zones, bond, calendar, 4-day week, closure, BED, major RFP).
- **Upgrade WATCH → RED_FLAG** on RF_20 when the affected fund is a statutory-reserve fund.
- **Upgrade WATCH → RED_FLAG** on RF_09 when the item is the TEC §39.306 annual public-performance presentation.

---

## Statute verification protocol

Every anchor in an emitted flag passes through the statute-mapper Skill. If the citation does not verify against the bundled corpus:

1. Try to find the correct adjacent subsection.
2. If none, drop the anchor and downgrade severity one level (RED_FLAG → WATCH, WATCH remains WATCH).
3. Log the miss to `skills/risk-flagger/eval_notes.md` for Agent B audit.

A wrong citation destroys trust permanently. Soften rather than invent.

---

## Eval-day log

During Day 3 side-by-side calibration, record every pattern adjustment in `skills/risk-flagger/eval_notes.md`:

- Date and commit hash of the change
- Pattern ID affected
- Signal language before / after
- Which item surfaced the miss or false positive
- Why the change reflects the hand version's calibration

Every calibration change is a commit. Do not batch.

---

## Do not

- **Do not invent patterns.** Twenty patterns + five POSITIVE categories. New patterns go through Toby into `principles.md` §II.
- **Do not escalate severity casually.** WATCH is the default stance. RED_FLAG is reserved for unambiguous violations or strong override signals.
- **Do not duplicate governance-principles output.** When a principle and a pattern both fire, both are emitted; the formatter deduplicates at render.
- **Do not emit prose.** This Skill emits structured flags. Agent F's output-formatter renders them.
- **Do not emit POSITIVE flags on every routine item.** Reserve PF_B for cases where clean execution is the point.

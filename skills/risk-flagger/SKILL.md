---
name: risk-flagger
description: Use this skill on every agenda item, proposed action, financial transaction, contract, closed-session posting, scorecard presentation, bond resolution, budget amendment, or board decision to produce WATCH, RED FLAG, or POSITIVE annotations. The skill applies a twenty-pattern taxonomy with a high bar for emission — the hand-written reference on a 166-page board book produces roughly 3-4 flags per item, not 15-20. Patterns cover statutory compliance failures (closed-session citations, open-meetings compliance, public hearings), procedural anomalies (vague agendas, procedural delay, TASB-as-authority), financial exposure (bond restructuring, tariff exposure, late budget amendments, missing cost-to-taxpayer, negative balances), role drift and delegation (pricing officers without oversight, financial advisor communication, key-strategic-actions approval), goal quality (missing measures, state-minimum targets, scorecard pacing misses), and document opacity (partial-population data, missing attachments). Trigger on all agenda items by default, then filter aggressively.
---

# Risk Flagger Skill

**Owned by Agent C.** The taxonomy lives in `principles.md` §II. This file is the detection layer — how to match the twenty patterns against the board-book text, what severity to emit, and above all what NOT to emit.

---

## Calibration discipline — read this first

A sitting-trustee pre-read of the April 13, 2026 Brock ISD board book (166 pages, 11 agenda items) produces **41 flags total: 14 RED / 20 WATCH / 7 POSITIVE.** That is the calibration target — roughly 3–4 flags per item on average, with most routine items producing zero flags.

**When uncertain, do not emit.** The cost of a missed flag is a single question the trustee can ask anyway. The cost of a spurious flag is that every flag starts to feel like noise and the genuinely important ones lose weight. A 200-flag pre-read is unusable; a 40-flag pre-read is read carefully.

**Every flag must clear three bars before emission:**

1. **Required evidence.** Every "Required evidence" bullet under the pattern must be directly supported by specific text in the packet. If you cannot quote the triggering sentence, do not fire.
2. **No suppressor applies.** Every pattern has a list of suppressors (conditions under which the flag does NOT fire). Walk them before emitting.
3. **Materiality.** If the emission would be boilerplate, reflexive, or about a ministerial detail that does not affect a governance decision, do not fire.

**Patterns of over-firing to avoid:**

- Firing RF_02 on every administrative delegation rather than on material delegations with absent oversight.
- Firing RF_04 on any terse agenda title rather than on generic titles that obscure material change.
- Firing RF_05 on every scorecard rather than on goal-adoption votes.
- Firing RF_06 on every vendor quote that mentions "tariff" rather than on quotes with material exposure.
- Firing RF_09 on every dataset below 100% coverage rather than on decision-critical data with unexplained gaps.
- Firing RF_10 on discussion-only scorecards that show an "actions" column rather than on items where the Board is actually asked to approve actions.
- Firing RF_14 on every item referencing an external document rather than on items where the missing document is decision-critical.
- Firing RF_15 on every action item where the cover sheet lacks a cost line rather than on items where no total cost is anywhere in the posted materials.
- Firing RF_19 on every off-pace metric rather than on material pacing misses near an assessment window.
- Firing POSITIVE flags on every routine consent item rather than on genuine governance wins.

**Silence is the default.** Emit a flag only when the pattern clearly applies and the emission will help the Board govern. Do not pad the output.

---

## Load order for every scan

1. Read `skills/governance-principles/principles.md` §II for the canonical taxonomy. Re-read on each invocation; patterns version.
2. Read the agenda item text and any attached documents referenced in the packet.
3. Walk each of the twenty patterns. For each, check Required evidence (all must be present) and Suppressors (any present → do not fire).
4. Route every `citations` list through the statute-mapper Skill before the flag is finalized. If the anchor does not verify, drop it and either reword or downgrade the flag.

---

## Detection table (RF_01 through RF_20)

Each row below maps to one pattern in `principles.md` §II. **Required evidence** lists concrete text signals the item must contain for the flag to fire — all bullets must be supported. **Suppressors** lists conditions under which the flag does NOT fire, even if one or two Required evidence bullets match.

### RF_01 — Blanket closed-session citation
- **Required evidence (all must be present):**
  - The posted agenda lists TGC §§551.071–551.087 as a range, OR three or more non-adjacent subsections, OR "TGC Chapter 551" with no subsection specified.
  - The posting does not narrow the scope to the subsection(s) actually anticipated.
- **Suppressors:**
  - The posting names a single specific subsection with its subject (e.g., "§551.074 — evaluation of the Superintendent").
  - The posting lists at most two adjacent subsections with topics named for each.
- **Default severity:** WATCH.
- **Citations:** TGC §551.101, §551.102.
- **Cross-fires with:** P04, P11.
- **Summary line:** "Closed-session posted under blanket §§551.071–551.087 range — presiding officer should state specifics on the record before entering."

### RF_02 — Delegation of execution authority without Board oversight
- **Required evidence (all must be present):**
  - The item delegates decision authority to a Pricing Officer, Superintendent-as-delegate, or named officer on a specific transaction.
  - The delegated transaction is material: a bond issuance/refunding, a capital purchase ≥$100K, a multi-year contract ≥$50K/year, or a new authority (not a renewal of a standing authority).
  - At least one of three oversight elements is absent: (i) dollar ceiling or maximum loss cap, (ii) time window or expiration, (iii) mandatory report-back to the Board at the next regular meeting.
- **Suppressors:**
  - The delegation is a routine day-to-day authority granted to the Superintendent under TEC §11.1512 (hiring substitutes, routine procurement under board-approved thresholds).
  - The item renews a standing authority the Board has already approved and the renewal is not expanding scope.
  - All three oversight elements (ceiling, window, report-back) are in the item.
- **Default severity:** WATCH when one or two oversight elements are missing. RED_FLAG when all three are missing AND the transaction is a bond issuance.
- **Citations:** TGC §1207.007, §1371.053, TEC §11.1512.
- **Cross-fires with:** P16.
- **Summary line (WATCH):** "Execution authority delegated with partial oversight — ask for report-back on final terms at the next meeting."
- **Summary line (RED_FLAG):** "Execution authority delegated with no Board-facing oversight mechanism."

### RF_03 — Bond restructuring framed as "savings"
- **Required evidence (all must be present):**
  - The item or its cover sheet uses the word "savings," "refunding savings," or equivalent language.
  - The underlying analysis shows zero debt service savings, a term extension beyond the original maturity, or a net cash outflow over the life of the debt.
  - The structure is specifically a restructuring/refunding (not a new money issuance).
- **Suppressors:**
  - The item quantifies present-value savings using a stated discount rate AND total cash paid over the life of the bond is LOWER than pre-refunding total.
  - The item does not use "savings" framing at all (e.g., explicitly labels itself a "restructuring").
- **Default severity:** RED_FLAG.
- **Citations:** TEC §45.004 (refunding bonds specifically), TEC §45.001, MSRB G-17, MSRB G-42.
- **Cross-fires with:** P13.
- **Summary line:** "Refunding characterized as 'savings' — confirm whether it is present-value savings or term extension, and state total cash cost to taxpayers."

### RF_04 — Vague agenda title on substantive item
- **Required evidence (all must be present):**
  - The agenda title is generic ("amendment to Board Policy X," "housekeeping budget amendment," "approve contract," "update on Y") with no section, dollar amount, or substantive detail.
  - The attached materials or item body reveal a material substantive change (policy language change, dollar amount above $50K, program adoption, rights/access change).
  - At least one of: the topic is on the community-interest keyword list (public comment, attendance zones, bond, calendar, 4-day week, closure, BED, major RFP), OR the dollar amount is ≥$50K, OR rights/access are affected.
- **Suppressors:**
  - The title names the section, dollar amount, or subject matter (even briefly).
  - The item is consent-ministerial: minutes, gift acceptance under $500, routine renewal under an already-approved framework.
  - The item is clearly informational (presentation, update) with no decision.
- **Default severity:** WATCH. Escalate to RED_FLAG only when the vague title is on a community-interest topic AND the underlying change materially affects public rights or a fund above $100K.
- **Citations:** TGC §551.041, §551.043.
- **Cross-fires with:** P11, P15.
- **Summary line:** "Agenda title does not disclose substantive change — public cannot tell from posting what decision is on the table."

### RF_05 — Goals without measures, baselines, targets, dates, or owners
- **Required evidence (all must be present):**
  - The item is an ACTION/ADOPTION vote on objectives, performance goals, or a strategic plan (category is Action Item, and the action is to adopt or approve goal language).
  - An objective is presented without at least one of: baseline number, target number, date, review cadence, guardrail, named owner.
- **Suppressors:**
  - The item reports on previously-adopted goals (scorecard update, monitoring report, discussion-only). Do not fire even as WATCH; RF_19 covers pacing, not structure.
  - All six goal elements are present in the proposed language.
- **Default severity:** RED_FLAG.
- **Citations:** TEC §11.1511(b)(2)–(3), TEC §11.251.
- **Cross-fires with:** P08, P16.
- **Summary line:** "Objective presented for Board adoption without [missing element] — violates TEC §11.1511."

### RF_06 — Tariff, supply chain, or price-adjustment exposure on vendor quotes
- **Required evidence (all must be present):**
  - The vendor quote, PO, or RFP contains a tariff pass-through clause, a commodity-index price-adjustment clause, or a unilateral "subject to adjustment" clause.
  - The exposure is material: the potential price variation exceeds $25K OR 10% of the item cost (whichever is lower).
  - The quote also carries time pressure: explicit expiration date within 30 days, OR the item cites expiration as a reason to act tonight.
- **Suppressors:**
  - The quote has a firm ceiling AND a fixed-price term AND no commodity-index linkage.
  - The price-adjustment clause is boilerplate in a fixed-price award where the adjustment cannot exceed a stated small percentage.
  - The purchase is routine with multiple vendors competing on published Buy Board pricing and the exposure is below the materiality floor.
- **Default severity:** WATCH.
- **Citations:** TEC §44.031(a) (competitive bidding), TEC §44.031(a)(4) (interlocal coop), TEC §44.031(j) (best value).
- **Cross-fires with:** —.
- **Summary line:** "Vendor quote exposes district to price escalation; confirm ceiling and whether quote-expiration timing is driving the vote."

### RF_07 — Late-cycle budget amendments
- **Required evidence (all must be present):**
  - The amendment is brought in the final quarter of the district's fiscal year (for Brock ISD: May, June, July, August).
  - The affected account balance is at or below 10% of its original annual budget at the time of the amendment (account is substantially drawn down).
  - No prior board packet in the same fiscal year flagged the pending drawdown with a forecast date.
- **Suppressors:**
  - A mid-year financial report earlier in the same fiscal year projected the overrun.
  - The amendment responds to an event outside district control (unexpected grant receipt requiring matching expense, emergency repair, enrollment-driven bus addition).
  - The amendment is less than $10,000 AND involves reconciliation of a small auxiliary account.
- **Default severity:** WATCH.
- **Citations:** TEC §44.002, §44.006.
- **Cross-fires with:** P07.
- **Summary line:** "Budget amendment brought after accounts drawn down — why was this not forecast sooner?"

### RF_08 — Financial advisor communication restrictions
- **Required evidence (all must be present):**
  - Operating procedure, board policy, or administrative statement explicitly limits trustees from contacting the district's municipal advisor, OR channels all trustee questions through administration.
  - The municipal advisor in question is currently engaged by the district (not a prospective engagement).
- **Suppressors:**
  - Administration facilitates direct contact on request.
  - The restriction is a scheduling courtesy (e.g., "please copy the CFO so everyone has the same info"), not a gatekeeping rule.
- **Default severity:** RED_FLAG.
- **Citations:** MSRB G-42, MSRB G-17.
- **Cross-fires with:** P03, P16.
- **Summary line:** "Municipal advisor's fiduciary duty under MSRB G-42 runs to the governing body; direct trustee access is not administration's to grant or withhold."

### RF_09 — Partial-population data presented without a label
- **Required evidence (all must be present):**
  - The data in the item has reported coverage below 90% OR coverage rate is not stated at all.
  - The presentation does not explain the subset selection or the reason for partial coverage.
  - The data is being used for a Board decision, a goal-setting decision, or as the basis of a claim the Board may act on (not just informational context).
- **Suppressors:**
  - Coverage rate is stated AND the subset selection is explained.
  - The data is a pilot or early rollout explicitly labeled as such.
  - The data is clearly informational context (e.g., anecdotal examples in a narrative) not driving a Board decision.
- **Default severity:** WATCH. Escalate to RED_FLAG only when the item is the TEC §39.306 annual public-performance presentation AND coverage is below 90%.
- **Citations:** TEC §39.306.
- **Cross-fires with:** P10.
- **Summary line:** "Data represents a subset of the population with no explanation — presentation should state coverage and reason on the record."

### RF_10 — "Key strategic actions" presented for Board approval
- **Required evidence (all must be present):**
  - The item's category on the cover sheet is ACTION (Action Item, Consent Action), not Discussion or Presentation.
  - The Board is asked to approve, adopt, or ratify a set of implementation actions, tactics, or "key strategic actions" — language like "approve the strategic actions," "adopt these key strategic actions for implementation."
  - The actions are distinct from the objectives, measures, guardrails, and cadence (if present, those are separate).
- **Suppressors:**
  - The item is a DISCUSSION or PRESENTATION of a scorecard that shows a "Key Strategic Actions" column labeled as administration's "How?" — role labeling is clear, no Board approval of actions is being requested.
  - The item explicitly separates Board-adopted objectives from administration-owned actions, with the vote only on objectives/measures/cadence.
  - The "actions" are Board-level standards (e.g., setting a policy floor), not implementation tactics.
- **Default severity:** WATCH.
- **Citations:** TEC §11.1511(b)(2)–(3), TEC §11.1512, TEC §11.201(d).
- **Cross-fires with:** P08, P16.
- **Summary line:** "Item asks the Board to approve actions — actions are administration's lane. Board adopts objectives, measures, guardrails, and cadence."

### RF_11 — Procedural objection used to delay substantive student-outcome item
- **Required evidence (all must be present):**
  - The item text or minutes record a procedural objection (authority, prior practice, timing, TASB guidance) raised against a specific substantive item.
  - The substantive item is student-outcome bearing: AI in education, pathways, safety, audit findings, academic performance, student discipline policy.
  - The procedural objection, if accepted, would delay or block the substantive item.
- **Suppressors:**
  - The procedural objection identifies a clear statutory conflict that genuinely prevents action tonight AND the substantive topic has a named firm return date.
  - No substantive delay results from the objection (e.g., the item proceeds anyway with a minor schedule change).
- **Default severity:** RED_FLAG.
- **Citations:** TEC §11.151(b), TEC §11.1515, BE(LOCAL).
- **Cross-fires with:** P03, P05, P06.
- **Summary line:** "Procedural objection delays a substantive student-outcome item — principle 6 applies."

### RF_12 — Emerging-issue items routed to "later" without a date
- **Required evidence (all must be present):**
  - The item defers a topic that is emerging in nature: AI adoption, new statutory compliance (HB2, HB3 updates, new TEA rule), safety finding, audit finding, regulatory change.
  - The deferral does not name a concrete return meeting date or a decision criterion for when it will return.
- **Suppressors:**
  - The deferral states a specific return meeting date AND names what evidence or briefing will be produced between now and then.
  - The topic has been on the agenda previously and the deferral is to a known recurring workshop (e.g., deferred to "Budget Workshop #2" which is on the calendar).
- **Default severity:** RED_FLAG.
- **Citations:** TEC §11.151(b), TEC §11.1515.
- **Cross-fires with:** P05, P07.
- **Summary line:** "Emerging-issue item deferred without a date — delay is not neutral."

### RF_13 — Governance training cited to override adopted policy
- **Required evidence (all must be present):**
  - The item invokes Lone Star Governance (LSG), TASB guidance, Team of 8 training, or similar framework.
  - The invocation is as controlling authority for a decision or restriction.
  - The invocation contradicts or narrows Board-adopted policy, statute, or a trustee's statutory rights.
- **Suppressors:**
  - The training is cited as supplementary context, best practice, or alongside the controlling policy/statute.
  - The invocation is descriptive (e.g., "LSG recommends X") without the item being bound by it.
- **Default severity:** RED_FLAG.
- **Citations:** BE(LOCAL), and the policy the training is being invoked against.
- **Cross-fires with:** P01.
- **Summary line:** "Governance training framework invoked to override Board-adopted policy — the policy controls."

### RF_14 — Referenced materials not included in the board book
- **Required evidence (all must be present):**
  - The item references a specific contract, policy, report, or attachment by name.
  - The referenced document is decision-critical: it is the text being approved, the policy being amended, the contract being signed, or the basis for a material expenditure.
  - The document is not in the board book AND is not accessible via a working link in the packet.
- **Suppressors:**
  - The referenced material is supporting context (not the thing being approved) AND the packet includes sufficient summary for the Board to decide.
  - The item is informational, not an action/decision.
  - The reference is to a historical document (prior minutes, superseded policy) cited for context.
- **Default severity:** RED_FLAG when the missing document is the text of the action being voted on. WATCH when it is supporting but material.
- **Citations:** TGC §551.043 (72-hour posting), Gov't Code Ch. 552 (PIA).
- **Cross-fires with:** P11, P14.
- **Summary line:** "Item references materials not included in the packet — the public should be able to read what the Board is reading."

### RF_15 — Action item with cost to taxpayers not on the record
- **Required evidence (all must be present):**
  - The item requires a Board vote (Action Item category).
  - The total cost to taxpayers is not stated anywhere in the posted materials — not on the cover sheet, not in the BLUF, not in attached tables, not in the item body.
  - The item commits district funds or incurs a financial obligation.
- **Suppressors:**
  - Total cost is stated anywhere in the packet, even as "up to $X" or "estimated $X."
  - The item is a grant/revenue receipt (no cost to taxpayers; may offset cost).
  - The item is budget-neutral (e.g., intra-fund transfer with no net expense increase).
- **Default severity:** RED_FLAG.
- **Citations:** TEC §44.002, TEC §45.001, MSRB G-17.
- **Cross-fires with:** P13.
- **Summary line:** "Action item requires a vote without the cost to taxpayers on the record."

### RF_16 — Scorecard targets at or near the state minimum
- **Required evidence (all must be present):**
  - A scorecard or strategic plan target is pegged at the state-defined minimum as the goal (e.g., STAAR "Meets" threshold as the goal, FIRST pass score as the goal).
  - The target is being adopted or ratified (not just reported from prior adoption).
- **Suppressors:**
  - The target exceeds the state minimum AND a separate guardrail is named below which intervention triggers.
  - The target is a guardrail or floor explicitly labeled as such (not the goal).
- **Default severity:** WATCH. Escalate to RED_FLAG only when the item is a goal-adoption vote AND the target explicitly equals the state minimum.
- **Citations:** TEC §11.1515.
- **Cross-fires with:** P09.
- **Summary line:** "Target pegged to the state minimum — the floor is not the goal."

### RF_17 — Statutorily-required public hearing not clearly held or recorded
- **Required evidence (all must be present):**
  - The item is a budget hearing, tax-rate hearing, or other statutorily-required public hearing.
  - The posted materials do not confirm posting, notice, or a record of public comment opportunity.
- **Suppressors:**
  - Materials show the notice, posting, and a record of the hearing with opportunity for public comment.
  - The item is not statutorily required to have a public hearing.
- **Default severity:** RED_FLAG.
- **Citations:** TEC §44.004 (budget hearing), Tax Code §26.06 (tax-rate hearing), TGC Ch. 551.
- **Cross-fires with:** P11.
- **Summary line:** "Statutorily-required public hearing — confirm notice, posting, and record on the public record."

### RF_18 — Deliberation that belongs in open session routed to closed session
- **Required evidence, posted-subject mode (all must be present):**
  - Closed session is posted on a subject that does not fit any of the enumerated TGC Ch. 551 exceptions (§551.071 attorney; §551.072 real property; §551.074 personnel specific individuals; §551.076 security; §551.082 discipline; §551.083 gifts; §551.087 economic development).
  - The posted subject involves general policy, salary schedules, working conditions, or matters not individual-specific.
- **Required evidence, prospective-reminder mode (all must be present):**
  - A closed-session posting includes §551.074 (directly or in a blanket range).
  - This is the only prospective-reminder emission per closed-session item — do not duplicate for every subsection in the range.
- **Suppressors:**
  - Closed-session subject is named and matches the cited subsection narrowly (e.g., §551.074 used only for a specific named individual's evaluation).
  - A prospective reminder has already been emitted for this closed-session item.
- **Default severity:** RED_FLAG in both modes.
- **Citations:** TGC §551.071, §551.072, §551.074, §551.076, §551.101, §551.102.
- **Cross-fires with:** P04, P11.
- **Summary line (posted-subject mode):** "Subject routed to closed session appears to exceed the cited exception — Chapter 551 exceptions are read narrowly."
- **Summary line (prospective-reminder mode):** "§551.074 (personnel) covers specific individuals by name or position only. If the discussion tonight veers into general employment policy, working conditions, or salary schedules, it must return to open session."

### RF_19 — Scorecard pacing miss near an assessment window
- **Required evidence (all must be present):**
  - Scorecard update reports a MOY or later interim measurement on a goal.
  - The gap between the current interim and the annual goal is ≥5 points on Meets %, Predicted Growth Score, or equivalent leading indicator.
  - The next assessment window (STAAR, EOC, TELPAS) is within 90 days.
  - The item does not include a dated intervention plan with named owner and measurable check-in.
- **Wrong-direction override:** Escalate WATCH → RED_FLAG when the MOY indicator is worse than the BOY indicator on the same metric AND the gap to annual goal is ≥15 points. A flat or rising-but-still-off-pace indicator stays at WATCH (or is suppressed if the gap is small).
- **Suppressors:**
  - The gap to annual goal is <5 points.
  - The item includes a dated intervention plan with named owner and a measurable check-in before the assessment window.
  - The indicator is above the annual goal (not a pacing miss; consider PF_C if notable).
- **Default severity:** WATCH.
- **Citations:** TEC §11.1515, TEC §11.251.
- **Cross-fires with:** P08, P09.
- **Summary line (WATCH):** "Pacing miss with an assessment window approaching — demand a specific, dated intervention plan before the test."
- **Summary line (RED_FLAG, wrong-direction):** "Metric is moving the wrong way with an assessment window approaching — the interim system is surfacing the miss while intervention is still possible. A specific, dated intervention plan is required tonight."

### RF_20 — Account balance at or near zero or negative without prior warning
- **Required evidence (all must be present):**
  - A fund balance, activity account, grant account, or auxiliary account is reported at zero, negative, or within 10% of depletion relative to its original annual budget.
  - No prior monthly financial report in the same fiscal year flagged the drawdown with a forecast date.
- **Suppressors:**
  - A prior monthly report projected the drawdown with a date.
  - The account is seasonal by design (e.g., activity account drawn down at year-end as expected).
- **Default severity:** WATCH. Escalate to RED_FLAG only when the affected fund is a statutory reserve (Debt Service I&S Fund, required-reserve fund) AND the coverage ratio is below 30 days of obligations.
- **Citations:** TEC §44.002, TEC §44.006.
- **Cross-fires with:** P07.
- **Summary line:** "Account balance near zero without prior warning — why did the district not see this coming?"

---

## POSITIVE flag catalog

The risk-flagger also names governance wins. POSITIVE is the easiest severity to over-emit — reserve it for genuine, nameable wins. Target: **no more than 1 POSITIVE per 2 agenda items on average.** The hand version emits 7 POSITIVEs across 11 items.

### PF_A — Grant-backed cost reduction
- **Required evidence (all must be present):**
  - The item is funded in part by a grant (TERP, TCSB, TEA, federal, philanthropic).
  - The grant covers at least 25% of the item's total cost.
  - The item cites the grant source and the dollar amount.
- **Suppressors:**
  - Grant covers less than 25% of cost (not material offset).
  - The "grant" is routine state allotment funding, not a competitive or discretionary grant.
- **Summary line:** "Grant covers [X]% of cost, meeting a district need with reduced local burden."

### PF_B — Clean execution on a routine item
- **Required evidence (all must be present):**
  - The item is a routine, procedurally-simple decision (interlocal renewal, minutes approval is not enough on its own, compliance attestation).
  - The item has NO other flags from RF_01–RF_20.
  - The cleanliness is notable given surrounding context (e.g., after prior meetings flagged vagueness on a related topic, this item is now specific).
- **Suppressors:**
  - Any other flag fires on the same item (PF_B does not co-emit with WATCH/RED_FLAG on the same item).
  - The item is a purely ministerial approval (minutes, check register) where cleanliness is the baseline expectation.
- **Emission cap:** at most 2 PF_B per agenda. If more candidates qualify, pick the two most notable and drop the rest.
- **Summary line:** "Routine execution; no embedded surprises."

### PF_C — Scorecard bright spot
- **Required evidence (all must be present):**
  - The scorecard reports an annual goal hit or exceeded at MOY or earlier, OR a leading indicator improved by at least 10 points on Meets % / Predicted Growth Score.
  - A replicable intervention or identifiable cohort is associated with the gain (the item can be asked "what's working").
- **Suppressors:**
  - Improvement is smaller than 10 points.
  - The improvement is on a content-coverage-driven metric where the BOY baseline was not meaningful (e.g., US History early-year content gaps).
- **Summary line:** "[Campus/cohort] hit/exceeded the goal; ask what's working and how to replicate."

### PF_D — Proactive compliance
- **Required evidence (all must be present):**
  - The item addresses a statutory, regulatory, or compliance requirement.
  - The action is taken at least 30 days ahead of the statutory deadline, OR is voluntarily adopting a standard not required by statute.
- **Suppressors:**
  - The action is on the ordinary statutory timeline (not proactive).
  - The action is a routine renewal triggered by a normal review cycle.
- **Summary line:** "Proactive compliance move ahead of [deadline/requirement]."

### PF_E — Specificity added after prior vagueness
- **Required evidence (all must be present):**
  - A prior meeting's version of the same item was flagged vague (WATCH/RED_FLAG on RF_04 or P11).
  - The current version names the section, dollar amount, or subject matter that was missing before.
- **Suppressors:**
  - No prior vagueness flag on the same topic.
  - The specificity was always present; PF_E requires a before/after improvement.
- **Summary line:** "Specificity added to a previously vague item — governance improvement on the record."

POSITIVE flags emit the same JSON shape as WATCH/RED_FLAG with severity `POSITIVE`, `generated_question` null, and `summary` stating what was done well.

---

## Output shape

Emit one structured Flag per match. Field names align with Agent A's `Flag` pydantic model (`agent/types.py`); extra metadata travels alongside.

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
- **Upgrade WATCH → RED_FLAG** on RF_04 when the vague title is on a community-interest topic AND rights/access or fund ≥$100K are affected.
- **Upgrade WATCH → RED_FLAG** on RF_20 when the affected fund is a statutory reserve AND the coverage ratio is below 30 days of obligations.
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
- **Do not emit POSITIVE flags on every routine item.** PF_B caps at 2 per agenda. PF_A requires material offset. PF_C requires a 10-point improvement or goal hit.
- **Do not emit a flag when uncertain.** The default stance is silence. If Required evidence is not clearly supported by specific item text, do not fire. The hand version's restraint is deliberate; match it.
- **Do not re-emit RF_18 prospective mode** for every §551 subsection in a range — one emission per closed-session item covers it.

# Risk Flagger · Eval Notes

Running log of calibration changes and dry-run traces. Every pattern adjustment is a separate commit with a note explaining what signal changed and why. Shared log for both the `risk-flagger` and `governance-principles` Skills.

---

## 2026-04-22 · Day 1 calibration · Brock April 13 Item K (Closed Session)

**Item under test.** Agenda Item K — Closed Session, posted under the blanket range "TGC §§551.071–551.087."

**PDF status.** `examples/brock_april_13_2026.pdf` not yet in the worktree at time of this dry run. Calibration check uses the Item K description in `agents/AGENT_C.md` and the principle and pattern definitions in `skills/governance-principles/principles.md`. When the PDF lands, re-run and confirm.

**Expected flag set.**

1. **RF_01 · Blanket closed-session citation · WATCH**
   - `summary` — "Closed-session posted under blanket §§551.071–551.087 range — presiding officer should state specifics on the record before entering."
   - `detail` — "The agenda lists the full §551.071–§551.087 range without naming which subsection applies tonight. Valid for posting, but TGC §551.101 requires the presiding officer to announce the specific section before the Board enters closed session. Ask on the record which subsections actually apply. A blanket citation gives the Board maximum flexibility; it also means almost any topic could be discussed in closed session."
   - `anchors` — `["TGC §551.101", "TGC §551.102"]`
   - `location_in_item` — "closed-session header of posted agenda"
   - `cross_fires_with` — `["P04", "P11"]`

2. **P11 · Specificity on the record · WATCH**
   - `direction` — `VIOLATION`
   - `signal` — "Closed session posted under the full range of TGC §§551.071–551.087 without specifying which sections actually apply tonight"
   - `evidence_quote` — the closed-session header text (populate from PDF)
   - `statute_anchor` — `TGC §551.101`
   - `generated_question` — "Will the presiding officer state, before the Board recesses into closed session tonight, which specific subsections of TGC §§551.071–551.087 the Board intends to invoke, and the corresponding topic for each?"
   - `severity` — WATCH by default. Does not escalate to RED_FLAG without a community-interest topic signal (public comment, attendance zones, bond, calendar, 4-day week, closure, BED, major RFP). If the stated closed-session subject, once announced, touches general policy rather than personnel under §551.074 or attorney consultation under §551.071, then RF_18 also fires and P11 escalates.

**Flags that should NOT fire on the posting alone.**

- **P04 · Transparent deliberation (TOMA)** — does not fire on vague posting in isolation. Per the hedging rule in `skills/governance-principles/SKILL.md`, P04 requires open-session conduct suggesting deliberation is being routed away from public view (e.g., "let's discuss this offline," pre-clearance language). The blanket posting alone is covered by P11 and RF_01.
- **RF_18 · Deliberation belongs in open session** — cannot fire without knowing what is actually being discussed in closed session. Would fire if, once the presiding officer names the subsection, the subject exceeds the cited exception (e.g., §551.074 invoked for general workforce policy rather than specific named individuals).
- **P15 · Tell the community** — fires only if the underlying closed-session topic is on the community-interest keyword list. Cannot determine from the posting alone.

**Calibration call.** The SKILL.md wording is consistent with Principle 11's canonical quote: *"The blanket citation gives the board maximum flexibility but also means almost any topic could potentially be discussed in closed session. As a governance practice, the board president should specify which exceptions actually apply before entering."* The expected output for Item K is a single executive-row WATCH with two sourcing anchors and one governance question. Agent F will deduplicate the RF_01 + P11 overlap at render.

**Open calibration questions for Day 3 eval.**

- Does the hand version treat Item K as a WATCH or does it escalate to RED_FLAG? The SKILL.md defaults to WATCH; if the hand version escalates based on the pattern recurring across prior meetings, the override rule "Upgrade WATCH → RED_FLAG when the same signal has fired on this item in prior meetings without remediation" covers it. Need the prior minutes to confirm.
- Does the hand version generate one question or two? Current Skill generates one. If the hand version asks both (a) which subsections apply and (b) how long the Board expects to be in closed session, add a standard second question to the P11 generator.
- Does the hand version cite TGC §551.101 only, or §551.101 + §551.102 together? Current Skill emits both. Adjust based on hand calibration.

---

## 2026-04-22 · Day 2 first-pass side-by-side · Brock April 13 full board book

**Reference artifact.** `examples/brock_april_13_2026_prereadhand.md` (imported from main repo). Hand version produced in ~4 hours of trustee work on the 166-page board book. All eleven agenda items walked below. Skills' expected emission is simulated (no pipeline yet; Agent A not built).

Legend: ✅ match, ⚠ partial match (severity or wording differs), ✗ gap (hand version emits; Skill cannot), + (Skill would emit; hand version does not).

---

### Item 4A · March 9 Minutes
- Hand version: no flags; two procedural questions.
- Skills expected: no flags.
- ✅ Clean.

### Item 4B · Check Register (pp. 8–29)
- Hand version: no flags; two questions (large single-vendor review, Reeder Construction draw).
- Skills expected: no flags.
- ✅ Clean.

### Item 4C · Revenue & Expenditure Reports (pp. 30–31)
- Hand WATCH on General Fund revenue realization (observational, not a pattern violation).
- Hand POSITIVE on Debt Service over-collected ($8.68M vs $7.25M budget).
- Hand RED FLAG on Debt Service 99.92% expended + estimated I&S Fund Balance $389,750 = ~15 days of debt service coverage.
- Skills expected: RF_20 WATCH (account balance near zero — I&S Fund at $389K vs $9.2M annual debt service). ⚠ Hand escalates to RED FLAG based on trajectory (80% decline in 3 years). Current RF_20 signal language doesn't capture trajectory; see gaps_for_v2.md item 2.
- ⚠ Severity gap. Propose broadening RF_20 signal to include multi-year decline trajectory.
- ✗ POSITIVE on revenue over-performance not covered by PF_A–PF_E. Propose extending PF_C to revenue bright spots.

### Item 4D · Region 11 Interlocal (pp. 32–34)
- Hand POSITIVE on routine renewal.
- Skills expected: PF_B (clean execution on a routine item).
- ✅ Match.

### Item 4E · Multipurpose Student Center Update (pp. 35–46)
- Hand version: no flags; three questions.
- Skills expected: no flags.
- ✅ Clean.

### Item 5 · Budget Workshop #1 (pp. 47–68)
- Hand RED FLAG on RADA declining two consecutive years, direct M&O revenue loss.
  - Skills expected: no match. ✗ No pattern for enrollment decline vs ADA-based funding. See gaps_for_v2.md item 3.
- Hand WATCH on attendance rate nuance (RADA −13 while enrollment +13). Observational; no pattern fires. Not a gap.
- Hand WATCH on PCAD preliminary values (budget built on estimates).
  - Skills expected: weak match to RF_09 (partial data) or RF_07 (late in cycle). ⚠ Neither is a tight fit — this is a "decision made on incomplete information" pattern. Candidate for v2.
- Hand RED FLAG on $72K Fast Growth Allotment loss (state no longer classifies Brock as fast growth).
  - Skills expected: no match. ✗ Same enrollment-revenue pattern as above.
- Hand RED FLAG on $1.18M restricted HB2 salary already committed; structural salary obligation on potentially temporary funding.
  - Skills expected: no match. ✗ Critical gap: state legislative funding dependency. See gaps_for_v2.md item 1.
- Hand WATCH on multiple "amount TBD" line items. Hand RED FLAG on missing recapture estimate.
  - Skills expected: RF_15 (cost to taxpayers missing). ✅ Match.
- Hand POSITIVE on CTE revenue growth ($963K → $2.94M over 10 years).
  - Skills expected: PF_C is scorecard-focused; doesn't clearly cover revenue bright spots. ⚠ Partial. Extend PF_C.
- Hand WATCH on CTE FTE deceleration. Observational.
- Hand RED FLAG on revenue/expenditure trend (expenditures tracking close to revenue; I&S reserves thin).
  - Skills expected: RF_20 WATCH. ⚠ Severity and signal breadth gap. See gaps_for_v2.md item 2.
- Hand RED FLAG on CFO identifying risks without presenting mitigation plan.
  - Skills expected: no match. ✗ No pattern for "risks identified without mitigation plan." Candidate for v2.
- Hand WATCH cross-reference to bond issue (legislative dependency pairing with HB2). Captured by gaps_for_v2.md item 1.
- 12 governance questions (15–26). My SKILL.md caps questions at 5 per item. ⚠ Calibration: cap is too low for multi-subject budget items. Adjust to "up to 5 per topic, up to 12 per major multi-topic item."

### Item 6 · Balanced Scorecard — Priority 1 Secondary (pp. 69–86)
- Hand RED FLAG on BHS Algebra I Predicted Growth 81 → 62 (19-point drop), 23 points below 85 goal.
  - Skills expected: RF_19 (pacing miss near assessment window) RED_FLAG. ✅ Match. Note: my RF_19 default is WATCH; escalate to RED_FLAG when the miss is ≥15 points below goal. Add override rule.
- Hand POSITIVE on BHS English I 57 → 82 Predicted Growth.
  - Skills expected: PF_C (scorecard bright spot). ✅ Match.
- Hand WATCH on BHS English II flat at 72 vs 85 goal (13 below).
  - Skills expected: RF_19 WATCH. ✅ Match.
- Hand POSITIVE on BJH 8th grade hitting 90 Reading growth goal at MOY.
  - Skills expected: PF_C. ✅ Match.
- Hand RED FLAG on BJH 6th Math dropped from 68.4% to 58.8% (below 63% goal).
  - Skills expected: RF_19 WATCH → RED_FLAG when the trend is downward inside the assessment window. ⚠ Need override rule for "pacing miss in wrong-direction trajectory" = RED_FLAG.
- Hand WATCH on BJH 8th Science/Social Studies interim clarification.
  - Skills expected: RF_09 (partial-population data without label — missing #1 vs #2 designation). ⚠ Partial match.
- 10 governance questions (27–36). Multi-metric scorecard item supports more than 5 questions.

### Item 7 · Bond Series 2026 Parameter Order (pp. 87–127)
- Hand RED FLAG on "THIS IS NOT A SAVINGS REFUNDING."
  - Skills expected: RF_03 RED_FLAG. ✅ Match. Confirmed by Samco "savings column blank."
- Hand describes delegation to Pricing Officer with parameter guardrails but no explicit report-back to Board.
  - Skills expected: RF_02 RED_FLAG (default). ⚠ Hand version treats this as WATCH-level, not RED_FLAG, because the parameter order carries a $5M loss cap, 6% interest cap, 2048 maturity cap, and one-year expiration. My RF_02 disqualifier requires ALL three (dollar ceiling AND time window AND report-back); report-back is absent, so RF_02 remains RED_FLAG. Calibration: soften disqualifier. Downgrade RED_FLAG → WATCH when 2 of 3 elements present; keep RED_FLAG only when all three are absent.
- Hand RED FLAG on I&S Fund Balance 80% decline in 3 years, refunding draws additional $2M.
  - Skills expected: RF_20 WATCH. ⚠ Severity/signal gap (trajectory). See gaps_for_v2.md item 2.
- Hand RED FLAG on Hold Harmless $32.2M legislative dependency.
  - Skills expected: no match. ✗ State-legislative-dependency gap. See gaps_for_v2.md item 1.
- Hand WATCH on Samco $50M/yr taxable value growth assumption vs 3.96% current growth. Observational.
- Hand WATCH on annual refunding cycle.
  - Skills expected: no match. ✗ See gaps_for_v2.md item 4 (repeated delegation without multi-year strategy).
- Hand WATCH on Capital Appreciation Bond authorization in Section 3(c).
  - Skills expected: no match. ✗ CAB-specific risk not in taxonomy. Minor gap; could subsume under RF_03 ("framed as savings") if CABs are used to mask cost, but the pattern is more precisely "compounding debt structure authorized without total cost disclosure."
- Hand WATCH on agenda title mentions 2016/2017 only, parameter order includes 2015.
  - Skills expected: RF_04 + P11. ✅ Match.
- Hand RED FLAG on dual legislative dependency (HB2 + Hold Harmless).
  - Covered by gaps_for_v2.md item 1.
- 10 governance questions (37–46).

### Item 8 · Teacher Contracts 2026–2027 (pp. 128–130)
- Hand WATCH on TEC §21.206 deadline timeline. Observational confirmation, not a pattern violation.
- 5 questions.
- Skills expected: no flags.
- ✅ Clean — no missed flags.

### Item 9 · TIA Payouts (p. 131)
- Hand note: "Prior Discussion: None" — suggests pulling from consent for fuller discussion.
  - Skills expected: no match. ✗ No pattern for "new program commitment voted without prior discussion." Candidate for v2 (gaps_for_v2.md item 5).
- Hand note: agenda placement mismatch (cover sheet says Consent Agenda, agenda places under Business Action J.3).
  - Skills expected: P11 WATCH (specificity — the same item is posted two different ways). ✅ Weak match.
- 5 questions.

### Item 10 · Fund 491 Student Nutrition Budget Amendment (pp. 132–136)
- Hand implicit WATCH on food account balance at −$36.96 (essentially depleted).
  - Skills expected: RF_20 WATCH. ✅ Match.
- Hand implicit WATCH on late-cycle amendment after account drawn down.
  - Skills expected: RF_07 WATCH. ✅ Match.
- 4 questions.

### Item 11 · School Bus Purchase — TERP Grant (pp. 137–166)
- Hand WATCH on tariff surcharge language (Blue Bird, Rush Truck).
  - Skills expected: RF_06 WATCH. ✅ Match.
- Hand WATCH on quote expiration May 1.
  - Skills expected: RF_06 (quote-expiration pressure). ✅ Match.
- Hand POSITIVE on 63% grant coverage reducing district cost.
  - Skills expected: PF_A. ✅ Match.
- Hand question 66: "Was the 2/2/26 grant contract signing within Troy Roberts' delegated authority or did it need prior board approval?"
  - Skills expected: P16 WATCH (role clarity — "when did the Board authorize entering this grant contract?"). ✅ Weak match.
- 6 questions.

---

### Item K revisit (now with hand version loaded)

Hand version's actual flags on Item K:
- WATCH on blanket citation (maximum flexibility vs narrow scope) → ✅ matches RF_01 WATCH and P11 WATCH.
- RED FLAG on "§551.074 does NOT authorize general employment policy" (prospective warning) → matches RF_18 RED_FLAG as a conditional — fires only if closed session veers into general policy. Hand version emits it prospectively as a reminder. Skill should also emit it prospectively when a closed session posting includes §551.074; add an override in RF_18 for "prospective reminder" mode at WATCH severity.
- 4 questions vs my SKILL.md's max 5 (fine). But the 4 questions cover: (a) specific sections, (b) certified agenda/recording maintained, (c) which exceptions anticipated, (d) §551.074 notification of employees' right to open hearing. My Skill as written would generate (a) and possibly (c); (b) and (d) are boilerplate I should add to the P11/RF_01 question generator's standard set for closed-session items.

**Calibration actions captured in this pass:**
1. RF_02 disqualifier — soften to "2 of 3 elements downgrades to WATCH."
2. RF_19 — add override rule: "wrong-direction trajectory within 90 days of assessment window escalates WATCH → RED_FLAG."
3. RF_18 — add prospective-reminder mode: when §551.074 is in the posted range, emit WATCH noting the narrow scope of personnel exception even before the session convenes.
4. RF_20 — broaden signal to include multi-year decline trajectory, not just "at or near zero."
5. PF_C — extend to cover revenue bright spots, not only scorecard bright spots. Rename "PF_C — Bright spots" with sub-types: scorecard, revenue, operational.
6. Question-generation cap — raise from 5 to 12 for multi-topic items (budget workshop, priority-1 scorecard, bond refunding); keep 5 as default for single-topic items.
7. Closed-session question template — add standing questions on (a) certified agenda/recording under §551.103 and (b) employee notification of open-hearing right under §551.074(b) when §551.074 is in scope.

Calibration actions 1–3 and 6–7 are in-Skill edits I can apply directly. Items 4 and 5 touch the taxonomy boundary and are proposed as v2 additions in `skills/governance-principles/gaps_for_v2.md`.

---

## Template for future entries

```
## YYYY-MM-DD · [item name]

**Item under test.** [agenda item and context]
**Observed flags.** [what the Skill emitted]
**Hand-version flags.** [what the hand version emits on the same item]
**Gap.** [missed / spurious / wrong severity / wrong citation / wrong voice]
**Change.** [signal language before → after, or override rule added]
**Commit.** [hash]
```

---
name: risk-flagger
description: Use this skill on every agenda item, proposed action, financial transaction, contract, closed-session posting, or board decision to produce WATCH, RED FLAG, or POSITIVE annotations. The skill applies a twenty-pattern taxonomy covering statutory compliance failures, procedural anomalies, financial exposure, role drift, opacity, and goal quality. Trigger on all agenda items by default.
---

# Risk Flagger Skill

**Owned by Agent C.** This file is a stub. Agent C fills in the full behavior on Day 1. See `agents/AGENT_C.md` for scope.

---

## The taxonomy

Read `skills/governance-principles/principles.md` §II for the full table of twenty patterns and their default severity. High-level categories:

- **Statutory compliance** — closed-session citations, public hearings, deliberation that belongs in open session
- **Procedural anomalies** — vague agenda language, procedural delay of substantive items, improper appeals to TASB "guidance"
- **Financial exposure** — bond restructuring framing, tariff exposure, late amendments, cost-to-taxpayer missing, negative balances
- **Role drift and delegation** — pricing officer without oversight, financial advisor communication restrictions, key strategic actions for Board approval
- **Goal quality** — missing measures, state-minimum targets, scorecard pacing misses
- **Document opacity** — partial-population data, missing attachments

## How to apply

1. Scan the item text for each of the twenty signal patterns.
2. When a pattern matches, emit a `Flag` with default severity from the taxonomy table.
3. Adjust severity one level only with strong contextual evidence; document the reason in the `detail` field.
4. Each flag must cite at least one statute, policy, or principle anchor. Run anchors through the statute-mapper Skill before emitting.
5. POSITIVE flags matter. Clean execution, grant-reduced costs, hit targets — name them.

## Output shape

Emit one structured Flag per match:

```json
{
  "pattern_id": "RF_01",
  "pattern_name": "Blanket closed-session citation",
  "severity": "WATCH",
  "summary": "One-line summary for the executive table.",
  "detail": "Two-to-four-sentence explanation in the voice of principles.md §IV.",
  "anchors": ["TGC §551.101", "TGC §551.074"],
  "location_in_item": "second paragraph of posted agenda"
}
```

## Severity defaults (WATCH unless specified)

RED_FLAG defaults:
- Pattern 2 (delegation without Board oversight)
- Pattern 3 (restructuring framed as savings)
- Pattern 5 (unmeasurable goals)
- Pattern 8 (financial advisor communication restrictions)
- Pattern 11 (procedural delay of substantive items)
- Pattern 12 (emerging-issue items deferred without a date)
- Pattern 13 (governance training cited to override policy)
- Pattern 14 (materials not in board book)
- Pattern 15 (cost to taxpayers missing)
- Pattern 17 (public hearings missing)
- Pattern 18 (open-session content routed to closed)

All others default to WATCH unless context warrants RED_FLAG.

## Do not

- Do not invent patterns. Twenty are in the taxonomy. New patterns go through Toby into principles.md §II.
- Do not escalate severity casually. WATCH is the default.
- Do not duplicate governance-principles output. When both fire, both are emitted; the formatter deduplicates at render.

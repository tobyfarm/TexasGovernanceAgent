---
name: statute-mapper
description: Use this skill when any agenda item, board communication, strategic plan, or proposed action references Texas statute, local board policy, Texas Administrative Code, TEA framework (LSG, ESF, FIRST, TAPR), MSRB rule, or any legal or procedural authority. The skill maps every authority claim to a specific controlling citation and verifies the citation against the bundled corpus before emitting it. Trigger on any mention of TEC, TGC, TOMA, TAC, TASB, MSRB, policy codes like BE(LOCAL) or BED(LOCAL), Board Operating Procedures, Pricing Officer delegation, bond authority, budget amendments, closed-session postings, or any legal or procedural argument.
---

# Statute Mapper Skill

**Owned by Agent B.** This file is a stub. Agent B fills in the full behavior on Day 1. See `agents/AGENT_B.md` for scope.

---

## Purpose

Every governance claim deserves a verified authority. This Skill maps claims to controlling text and verifies each citation against the bundled corpus at `skills/statute-mapper/statutes/`. No hallucinated citations.

## When to use

When the task involves any of:
- Analyzing a board agenda item
- Reviewing proposed policy language
- Interpreting a procedural decision (agenda placement, closed session, delegation, posting)
- Evaluating a financial transaction (bond issuance, budget amendment, procurement)
- Assessing compliance with TOMA, PIA, or sunshine requirements

## How to use

1. Identify every authority claim in the target text — explicit citations, implicit claims, and references to adopted policy.
2. For each claim, look up the controlling authority in the bundled corpus at `statutes/`.
3. Return a `Citation` object with `verified=True` only if the authority text was found in the corpus.
4. Prefer verbatim quotation over paraphrase. Downstream renderers use the quoted text.
5. **Never fabricate.** If a policy or statute is not in the corpus, return `verified=False`.

## Bundled corpus

Location: `skills/statute-mapper/statutes/`

- `tec-ch-11.md` — Board governance authority and duties
- `tec-ch-44.md` — Budget framework and amendments
- `tec-ch-45.md` — Bond issuance authority
- `tgc-ch-551.md` — Open Meetings Act (TOMA)
- `msrb.md` — Municipal advisor fair dealing and fiduciary duty
- `tea-frameworks.md` — Descriptive notes on LSG, ESF, FIRST, TAPR
- `brock-isd/` — District-specific local policy when Toby adds it

Each file uses a consistent format — see Agent B's detailed instructions.

## Verifier

`skills/statute-mapper/verifier.py` exposes:

```python
def verify(citation: str) -> VerificationResult
```

Call it on every authority before emitting.

## Do not

- Do not match partial citations to full authorities (e.g., do not silently expand `TEC §11` to `TEC §11.151`). Return unverified.
- Do not paraphrase statute text. Quote.
- Do not do live web lookup of statute. The corpus is the source of truth.
- Do not modify `principles.md` — that file belongs to Agent C.

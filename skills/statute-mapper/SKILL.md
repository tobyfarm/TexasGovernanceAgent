---
name: statute-mapper
description: Use this skill when any agenda item, board communication, strategic plan, or proposed action references Texas statute, local board policy, Texas Administrative Code, TEA framework (LSG, ESF, FIRST, TAPR), MSRB rule, or any legal or procedural authority. The skill maps every authority claim to a specific controlling citation and verifies the citation against the bundled corpus before emitting it. Trigger on any mention of TEC, TGC, TOMA, TAC, TASB, MSRB, policy codes like BE(LOCAL) or BED(LOCAL), Board Operating Procedures, Pricing Officer delegation, bond authority, budget amendments, closed-session postings, or any legal or procedural argument.
---

# Statute Mapper Skill

**Owned by Agent B.** This Skill is the legal grounding layer. Every citation the system emits passes through `verify()`. No hallucinated authorities, ever.

The governance-principles Skill (Agent C) owns *interpretation*. This Skill owns *availability and accuracy*.

---

## Purpose

The governance doctrine at `skills/governance-principles/principles.md` §III lists the statutes, TOMA sections, MSRB rules, and local policies Toby cites most often. This Skill is how the agent:

1. **Recognizes** authority claims in the target text — explicit citations, implicit claims ("the board has discretion here"), and references to adopted policy.
2. **Resolves** each claim to a specific controlling citation in the bundled corpus.
3. **Verifies** the citation matches real authority text bundled with the repo.
4. **Quotes** the authority verbatim so downstream renderers can reproduce it exactly.

A wrong TEC citation destroys trust permanently. Err on the side of softening or dropping a claim before emitting an unverified citation.

---

## When to use

Load this Skill whenever the task involves any of:

- Analyzing a board agenda item
- Reviewing proposed or adopted policy language
- Interpreting a procedural decision (agenda placement, closed session entry, delegation, posting adequacy)
- Evaluating a financial transaction (bond issuance, budget amendment, procurement, RFP, delegation of pricing authority)
- Assessing compliance with TOMA, PIA, or sunshine requirements
- Evaluating trustee submission rights, equal participation, or board-president authority questions
- Drafting a pre-read, line of questioning, or trustee correspondence that will cite authority

If the task mentions any of: TEC, TGC, TOMA, TAC, TASB, MSRB, policy codes like BE(LOCAL), BED(LOCAL), CQD, Board Operating Procedures, "Team of 8," LSG, ESF, FIRST, or any section number in the form `§XXX.XXX` — treat it as in scope.

---

## How to use

### 1. Identify every authority claim

Walk the target text and list:

- **Explicit citations.** Section numbers, policy codes, rule numbers. Examples: "TEC §11.151(b)", "BE(LOCAL)", "MSRB Rule G-42", "TGC §551.074".
- **Implicit authority claims.** Unquoted claims about power, duty, or discretion. Examples: "the Board must adopt goals," "the Superintendent has authority to," "the President may defer." These need a citation attached or softened.
- **Policy references.** Mentions of adopted policy, board operating procedures, or TASB-sourced language. BOP and TASB guidance are **subordinate** to board-adopted policy (see principles.md §I Principle 1).
- **Framework references.** LSG, ESF, FIRST, TAPR, Team of 8. These are frameworks, not statute — treat accordingly.

### 2. Normalize the citation string

Pass the raw citation to the normalizer. Accepted variants:

| Raw | Normalized |
|---|---|
| `TEC §11.151(b)` | `TEC §11.151(b)` |
| `Texas Education Code §11.151(b)` | `TEC §11.151(b)` |
| `Texas Education Code 11.151(b)` | `TEC §11.151(b)` |
| `Tex. Educ. Code §11.151(b)` | `TEC §11.151(b)` |
| `Ed. Code §11.151(b)` | `TEC §11.151(b)` |
| `TGC §551.074` | `TGC §551.074` |
| `Texas Government Code §551.074` | `TGC §551.074` |
| `Gov't Code §551.074` | `TGC §551.074` |
| `MSRB Rule G-42` | `MSRB G-42` |
| `MSRB G-42` | `MSRB G-42` |
| `BE(LOCAL)` | `BE(LOCAL)` |
| `§11.151(b)` | **unverified** — code prefix missing, ambiguous |
| `11.151(b)` | **unverified** — code prefix missing, ambiguous |
| `TEC §11` | **unverified** — subsection-less, too broad |

The normalizer is strict on purpose. Silent expansion of a bare section number is how citations drift.

### 3. Call `verify()`

The directory name `statute-mapper` contains a hyphen, so it is not a
valid Python package name. Load the verifier module by path:

```python
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "statute_mapper_verifier",
    Path("skills/statute-mapper/verifier.py"),
)
_verifier = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_verifier)
verify = _verifier.verify

result = verify("TEC §11.151(b)")
if result.verified:
    render_with_quote(result.quoted_text)
elif result.status == "corpus_gap":
    render_cited_but_not_quoted(result.authority, note=result.diagnostic)
else:
    soften_or_drop(result.authority, note=result.diagnostic)
```

`verify_all(citations)` returns a list of `VerificationResult`s for batch
lookups. `list_corpus_entries()` enumerates every heading in the corpus
with a `has_text` flag — used by the eval harness to surface scaffold gaps.

CLI coverage snapshot:

```bash
python3 skills/statute-mapper/verifier.py --list
```

The `VerificationResult` contract:

```python
@dataclass
class VerificationResult:
    verified: bool              # True iff heading matched AND blockquote text populated
    authority: str              # canonical normalized citation
    quoted_text: str | None     # verbatim text from corpus (None if not verified)
    source_file: str | None     # e.g., "tec-ch-11.md"
    status: str                 # "verified" | "corpus_gap" | "partial_match" | "unknown"
    diagnostic: str | None      # human-readable note for logs / downstream context
```

**Three distinct unverified states** — do not collapse them. Downstream agents log and render each differently:

- **`corpus_gap`** — the heading exists in the corpus but the blockquote text has not yet been bundled. The citation is recognized as real; the agent may name the authority but must not invent text to quote. Log to `logs/corpus_gaps.log` so the corpus can be filled in.
- **`partial_match`** — the incoming citation is broader or narrower than what the corpus indexes (e.g., incoming `TEC §11.151` when the corpus has `TEC §11.151(b)`). Return `verified=False` and include the candidate specific headings in the diagnostic. **Do not silently expand.** The agent should either pick a specific subsection or soften the claim.
- **`unknown`** — no heading matched and no near-miss. Likely a hallucination or a real authority not yet bundled. Log to `logs/unverified_citations.log`.

### 4. Quote verbatim; never paraphrase

When `verified=True`, emit the quoted text inside a blockquote. Preserve mandatory language ("shall," "does not have the authority") exactly. Do not trim for length — if a subsection is too long to inline, call out the specific clause and link to the corpus file.

### 5. Annotate the rendered output

Each verified citation in the output carries: canonical citation, verbatim quote, and `source_file`. The output-formatter Skill (Agent F) uses these to build the Legal Framework section of the pre-read.

---

## Bundled corpus

Location: `skills/statute-mapper/statutes/`

| File | Contents |
|---|---|
| `tec-ch-11.md` | TEC Chapter 11 — governance authority. §§11.151, 11.1511, 11.1512, 11.1515, 11.201, 11.251 |
| `tec-ch-44.md` | TEC Chapter 44 — budget and procurement. §§44.002, 44.004, 44.006, 44.031 |
| `tec-ch-45.md` | **(Day 2)** TEC Chapter 45 — bond issuance. §45.001 |
| `tgc-ch-551.md` | TGC Chapter 551 — Open Meetings Act. §§551.001, 551.041, 551.043, 551.071, 551.072, 551.074, 551.076, 551.082, 551.0821, 551.083, 551.087, 551.101, 551.102, 551.103 |
| `msrb.md` | **(Day 2)** MSRB Rules G-17 (fair dealing) and G-42 (fiduciary duty) |
| `tea-frameworks.md` | **(Day 2)** Descriptive notes on LSG, ESF, FIRST, TAPR |
| `brock-isd/` | District-specific local policy (BE(LOCAL), BED(LOCAL), CQD, BOP). Populated as Toby adds documents. |

### Corpus file format

Every corpus file starts with a retrieval-date comment:

```markdown
<!-- Retrieved from statutes.capitol.texas.gov on YYYY-MM-DD -->
```

Each cited authority is a level-3 heading followed by a blockquote of the verbatim text. Example:

````markdown
### TEC §11.151(b)

**Title.** Powers and Duties of Board of Trustees of Independent School District.

> The trustees as a body corporate have the exclusive power and duty to govern
> and oversee the management of the public schools of the district. All powers
> and duties not specifically delegated by statute to the agency or to the
> State Board of Education are reserved for the trustees, and the agency may
> not substitute its judgment for the lawful exercise of those powers and
> duties by the trustees.

**Cross-references:** §11.1511 (specific powers and duties of board).
**Common usage:** Cited to establish that governance authority rests with the
Board, not administration or advisors. See SAMCO Q&A, January 2026 agenda dispute.
````

The verifier parses the heading and extracts the `>` blockquote that follows it.

### Granularity rule

The heading is at the granularity Toby cites. If the doctrine cites `§11.151(b)`, the heading is `### TEC §11.151(b)` and the blockquote is just subsection (b). If the doctrine cites the whole section (`§11.251`), the heading is `### TEC §11.251` and the blockquote is the whole section. This mirrors how a trustee pulls quotes: precisely, at the clause in question.

---

## Do not

- **Do not fabricate a citation.** If a policy or statute isn't in the corpus, return `verified=False`. Log the gap. Do not guess.
- **Do not silently expand a citation.** `TEC §11` never becomes `TEC §11.151(b)` without the agent choosing. Return `partial_match` with candidate headings.
- **Do not paraphrase statute text.** Paraphrased statute is worse than missing statute.
- **Do not do live web lookup at inference time.** The corpus is the source of truth. The agent runs offline once loaded.
- **Do not modify `principles.md`.** That file belongs to Agent C.
- **Do not rename this Skill or its corpus files.** Agents A, C, and F depend on the filenames.

---

## Coordination

**With Agent A (lead loop).** Agent A emits `Citation` objects and passes them here. `verified` is a binary contract for downstream renderers; `status` and `diagnostic` are the diagnostic channel. Agent A logs every unverified citation — the two log files (`logs/unverified_citations.log` and `logs/corpus_gaps.log`) are the Day 3 eval input for expanding the corpus.

**With Agent C (governance-principles, risk-flagger).** Agent C consumes verified citations to ground every principle check and risk flag. When Agent C flags a pattern that requires an authority not in the corpus, they file a request; this Skill adds it.

**With Agent F (output-formatter).** The output-formatter pulls `quoted_text` from `VerificationResult` into the Legal Framework section of the pre-read. Verbatim quote, no paraphrase.

---

## Critical reminders

- **Corpus is bundled, not fetched.** Offline after load.
- **Quote verbatim.** Copy from the statutes site; preserve "shall."
- **Update retrieval dates.** The Texas Legislature does meet; the retrieval-date comment is how we detect staleness.
- **Local policy lives in `statutes/brock-isd/`.** Same format; the `source_file` field distinguishes.
- **You are the last line of defense against hallucinated authority.** Nothing matters more.

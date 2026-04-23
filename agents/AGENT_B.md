# AGENT B — Statute Mapper Skill and Corpus

**You are Agent B.** You own the legal grounding layer. Every citation the system produces runs through you. Read `CLAUDE.md` at the repo root and `skills/governance-principles/principles.md` §III (the citation register) before you start.

---

## Your scope

1. **`skills/statute-mapper/SKILL.md`** — the Skill description and behavioral instructions.
2. **`skills/statute-mapper/statutes/`** — the bundled corpus of Texas statute, TEA framework, and MSRB rule text that the agent consults.
3. **`skills/statute-mapper/verifier.py`** — a small helper that takes a citation string (e.g., `"TEC §11.151(b)"`) and returns `(verified: bool, quoted_text: str | None)` by matching against the bundled corpus.

You do not own interpretation of the statute. You own **availability and citation accuracy**. The governance-principles Skill (Agent C) is where interpretation lives.

---

## Day 1 milestones

By end of Day 1:

- [ ] `skills/statute-mapper/SKILL.md` written with clear description (so Claude auto-loads it when an agenda item references statute, policy, or authority).
- [ ] `skills/statute-mapper/statutes/tec-ch-11.md` populated with the text of TEC Chapter 11 (at minimum §§11.151, 11.1511, 11.1512, 11.1515, 11.201, 11.251).
- [ ] `skills/statute-mapper/statutes/tgc-ch-551.md` populated with the text of TGC Chapter 551 (TOMA), at minimum §§551.001, 551.041, 551.043, 551.071 through 551.087, 551.101 through 551.103.
- [ ] `skills/statute-mapper/statutes/tec-ch-44.md` populated with TEC Chapter 44 (§§44.002, 44.004, 44.006, 44.031).
- [ ] `skills/statute-mapper/verifier.py` provides a `verify(citation: str) -> VerificationResult` function.

## Day 2 milestones

- [ ] `skills/statute-mapper/statutes/tec-ch-45.md` — §45.001 and related bond authority.
- [ ] `skills/statute-mapper/statutes/msrb.md` — G-17 and G-42 (fair dealing, fiduciary duty of municipal advisors).
- [ ] `skills/statute-mapper/statutes/tea-frameworks.md` — short descriptive notes on LSG, ESF, FIRST, and TAPR. Not full framework text; just enough so the agent can accurately name and describe them.
- [ ] Verifier handles citation variants: `TEC §11.151(b)`, `Texas Education Code 11.151(b)`, `§11.151(b)`, `11.151(b)` when context is clear.

## Day 3+ milestones

- Day 3 eval day. When the agent hallucinates a citation, your job is to either (a) add the real authority to the corpus if it exists, or (b) tighten the Skill instructions to prevent that hallucination pattern. Coordinate with Agent C on which is the right fix.
- Day 4+: add any authorities flagged during eval. Common additions will be around school finance, personnel code, and student discipline.

---

## Statute corpus format

Each file is markdown. Each section is a level-3 heading with the canonical citation. Quoted text is in a fenced code block marked `statute`. Example:

```markdown
### TEC §11.151(b)

**Title.** Powers and Duties of Board of Trustees of Independent School District.

**Current text (as of 4/2026):**

> The trustees as a body corporate have the exclusive power and duty to govern
> and oversee the management of the public schools of the district. All powers
> and duties not specifically delegated by statute to the agency or to the
> State Board of Education are reserved for the trustees, and the agency may
> not substitute its judgment for the lawful exercise of those powers and
> duties by the trustees.

**Cross-references:** §§39A.201-202 (commissioner-appointed boards of managers
— exception not applicable to elected boards).

**Common usage in board context:** Invoked to establish that governance
authority rests with the Board, not with administration or advisors. See the
SAMCO Q&A template and the January 2026 agenda dispute.
```

Keep the format consistent. The verifier parses it.

Source for statute text: **Texas Constitution and Statutes** at statutes.capitol.texas.gov. Pull the current version. Include a comment at the top of each file with the retrieval date.

---

## Skill authoring — the SKILL.md file

The `SKILL.md` at `skills/statute-mapper/SKILL.md` is what Claude reads to decide when to load the Skill. Its frontmatter description matters. Draft:

```markdown
---
name: statute-mapper
description: Use this skill when any agenda item, board communication, or proposed action references Texas statute, local board policy, TEA framework, MSRB rule, or other legal authority. The skill maps claims to specific controlling authorities and verifies every citation against the bundled corpus. Trigger on mentions of TEC, TGC, TOMA, TAC, TASB, MSRB, policy codes like BE(LOCAL), board operating procedures, or any legal/procedural argument.
---

# Statute Mapper

[... full behavior instructions ...]
```

The behavior body should tell Claude:

1. When analyzing an agenda item, identify every authority claim (explicit citations, implicit claims like "the board has discretion here," and references to adopted policy).
2. For each claim, look up the controlling authority in the bundled corpus.
3. Return a `Citation` object with `verified=True` only if the authority text was found in the corpus. `verified=False` means the agent should soften or drop the claim.
4. **Never fabricate a citation.** If a policy or statute is cited in the board book but not in our corpus, return `verified=False` and note the gap.
5. Prefer quoting verbatim text from the corpus over paraphrasing. The downstream output-formatter will use the quoted text.

---

## Verifier helper

```python
# skills/statute-mapper/verifier.py

from pathlib import Path
import re

CORPUS_DIR = Path(__file__).parent / "statutes"

class VerificationResult:
    verified: bool
    authority: str
    quoted_text: str | None
    source_file: str | None

def verify(citation: str) -> VerificationResult:
    """
    Match a citation string against the bundled corpus.

    Handles common variants:
      'TEC §11.151(b)'
      'Texas Education Code 11.151(b)'
      '§11.151(b)'
    """
    # Normalize
    normalized = _normalize(citation)
    # Scan corpus files
    for md_file in CORPUS_DIR.glob("*.md"):
        text = md_file.read_text()
        # Look for matching heading
        match = re.search(rf"###\s+{re.escape(normalized)}\b", text)
        if match:
            # Extract the quoted text block following the heading
            quoted = _extract_quote_block(text, match.end())
            return VerificationResult(
                verified=True,
                authority=normalized,
                quoted_text=quoted,
                source_file=md_file.name,
            )
    return VerificationResult(
        verified=False,
        authority=normalized,
        quoted_text=None,
        source_file=None,
    )
```

Simple. Fast. No RAG, no embeddings. The corpus is under 100k tokens total.

---

## Coordination with Agent A

Agent A's lead-agent loop emits `Citation` objects. Your verifier is what sets `verified=True/False` on those. Agreement points:

- You return `verified=False` (never None) when a citation can't be matched.
- Agent A logs every unverified citation to a file (`logs/unverified_citations.log`) — you review this during eval to find corpus gaps.
- You do not silently expand citations. If Agent A passes you `"TEC §11"`, you do not match it to `TEC §11.151(b)`; you return unverified. Citations must be specific.

---

## Coordination with Agent C

Agent C's governance-principles Skill uses the statute corpus to ground every principle. You provide text; they provide interpretation. If they need an authority that is not in the corpus, they file a request — you add it.

---

## Critical reminders

- **Corpus is bundled, not fetched.** The agent must work offline once the corpus is loaded. No live web lookup of statute at inference time.
- **Quote verbatim.** Copy-paste from the Texas statutes site. Do not paraphrase. Paraphrased statute is worse than missing statute.
- **Update dates.** Every statute file has a retrieval date. If a statute amends mid-session (Texas lege does meet), the date is how we know our corpus is stale.
- **Local policy lives in `skills/statute-mapper/statutes/brock-isd/`.** When Toby adds local policy documents (BE(LOCAL), BED(LOCAL), Board Operating Procedures), they go in a separate subdirectory. Format is the same; the `source` in the VerificationResult distinguishes.

---

## When you are stuck

- If a statute section has subsections you are unsure to include, include them. Better to have too much corpus than too little.
- If the Texas statutes site returns weird whitespace or non-UTF characters, clean them — but preserve the substantive text exactly.
- If a citation style is ambiguous (e.g., is "Gov't Code 551" referring to TGC §551.001 or the whole chapter), coordinate with Agent A on how the citation was generated.

You are the last line of defense against hallucinated authority. Nothing matters more than that. Get the corpus right and the rest of the system can be confident.

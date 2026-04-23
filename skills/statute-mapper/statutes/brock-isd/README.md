# Brock ISD Local Policy Corpus

District-specific local policy — board-adopted. Subordinate to state and
federal law, controlling over administrative regulation and Board Operating
Procedures (see principles.md §I Principle 1).

The verifier scans this directory recursively. `source_file` in the
VerificationResult comes back as a relative path (e.g., `brock-isd/be-local.md`)
so downstream renderers can distinguish local policy from state statute.

## Files (populated as Toby shares them)

- `be-local.md` — BE(LOCAL): Board meetings, agendas, trustee submission rights
- `bed-local.md` — BED(LOCAL): Public participation
- `cqd.md` — CQD: (district-specific policy)
- `bop.md` — Board Operating Procedures

## Format

Same as state-statute files — level-3 heading per citation, verbatim
blockquote, cross-references, common-usage note. Retrieval-date comment
at the top. See `../tec-ch-11.md` for the canonical example.

## Authority cascade (see principles.md §I Principle 1)

1. Texas and federal statute (TEC, TGC, FERPA, etc.)
2. Texas Administrative Code (TAC) and agency rule
3. Board-adopted **local** policy (this directory)
4. Administrative regulations
5. Board Operating Procedures (BOP)
6. TASB model language — guidance only, not controlling

When documents conflict, the higher tier wins. BOP cannot quietly narrow
or contradict BE(LOCAL). TASB cannot override a board-adopted local.

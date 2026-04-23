# Agent C → Agent B · Corpus coordination for Brock April 13

**From:** Agent C (governance-principles + risk-flagger)
**To:** Agent B (statute-mapper + corpus)
**Date:** 2026-04-23
**Re:** Statutes the Skills emit that need corpus coverage

---

## Additional sections needed beyond `principles.md` §III

Agent A's first live pipeline run on the Brock April 13 PDF surfaced a need to cite several statutes that are not yet enumerated in `principles.md` §III. These are real citations the hand-version pre-read uses and that the risk-flagger now emits. Please load the following into `skills/statute-mapper/statutes/` so the verifier returns `verified=True` on them.

### Bond refunding authority (Item 7 — Bond Series 2026)

The hand version's Item 7 legal framework relies on four specific statutory anchors beyond the `§45.001` reference already in §III:

- **TEC §45.004 — Refunding bonds.** Direct authority for school-district refunding bond issuances. Cited by RF_03 in the updated fixture. Load section text.
- **TEC §45.051 through §45.063 — Subchapter C, Permanent School Fund Bond Guarantee Program.** The parameter order's Section 19 invokes Article VII §5 of the Texas Constitution and the PSF Guarantee Program. Hand version quotes this. Please load the subchapter — §45.051 (definitions), §45.052 (authority and purpose), §45.053 (guaranteed bonds), §45.057 (limitation on amount), §45.058 (payment if bond not paid when due), §45.061 (Comptroller withholding on default), §45.063 (applicability to refunding). §45.061 is the key one for the fiduciary-duty / credit-rating discussion.
- **TGC Chapter 1207** — statewide refunding bond framework. §1207.007 is already in §III (Pricing Officer delegation). Please also load §1207.001 (definitions), §1207.002 (authority to issue), §1207.032 (delegation of pricing authority), §1207.061 (security).
- **TGC Chapter 1371** — public improvement obligations. §1371.053 is already in §III. Please also load §1371.051 (applicability) and §1371.056 (effect of noncompliance).

### Competitive bidding subsection detail (Item 11 — Bus Purchase and general RF_06)

The hand version cites `TEC §44.031` with specific subsection granularity. The corpus needs at minimum:

- **TEC §44.031(a) — Competitive methods required** for purchases valued at $50,000 or more.
- **TEC §44.031(a)(4) — Interlocal cooperative exemption.** Authorizes purchasing through Buy Board / TIPS-TAPS / other interlocal cooperatives in lieu of individual bidding.
- **TEC §44.031(a)(5) — School bus $20,000 threshold.** Most-favorable-bid rule for school bus purchases specifically.
- **TEC §44.031(j) — Best-value consideration.** Life-cycle cost, total cost of ownership, reliability.

### Items previously surfaced in `eval_notes.md` corpus-gap audit

For completeness, the earlier corpus-gap audit (commit `97c9682`) listed these additional authorities. Reposting here so Agent B has a single consolidated list:

| Citation | Used by | Items | Purpose |
|---|---|---|---|
| TGC §551.041 | P11, RF_04 | K, 7, 9 | Notice of meeting / agenda posting contents |
| TGC Ch. 1207 generally | RF_27 | 7 | Refunding framework (see above for subsections) |
| Tax Code §26.06 | RF_17 | 5, 7 | Tax-rate hearing notice |
| Texas Health & Safety Code Ch. 390 | RF_06, PF_A | 11 | TERP / Texas Clean School Bus Program |
| TGC §791.011, §791.025 | PF_B | 4D | Interlocal Cooperation Act |
| TEC §21.102, §21.103, §21.206 | Item 8 legal framework | 8 | Probationary contracts; §21.206 notice deadline |
| TEC §21.003 | Item 8 | 8 | Certification requirement |
| TEC §21.3521 | RF_25 (v2) | 9 | Teacher Incentive Allotment |
| TEC §42 (general) | RF_23 (v2) | 5 | School finance / ADA-driven M&O |

### Priority for Agent B

**High priority** (emitting now, unverified → softening flag severity):
1. TEC §45.004 (refunding authority)
2. TEC §45.051 and §45.061 (PSF guarantee + Comptroller withholding)
3. TEC §44.031(a)(4) and §44.031(a)(5) (interlocal coop + school bus threshold)
4. TGC §551.041 (notice contents)
5. Tax Code §26.06 (tax-rate hearing)

**Medium priority** (emitted on specific items but not load-bearing):
6. TEC §21.3521 (TIA)
7. TEC §21.206 (teacher-contract notice deadline)
8. Texas Health & Safety Code Ch. 390 (TERP)
9. TGC §791.011 (interlocal)

**Deferred to v2** (these cite-paths activate only when Toby approves new risk patterns):
10. TEC §42 (general school finance) — supports proposed RF_23
11. Remaining §45.05x PSF subsections — supports RF_03 depth

### Proposal to Toby at next `principles.md` version bump

Recommend promoting into §III:
- TEC §45.004
- TEC §44.031(a)(4) and (a)(5)
- TGC §551.041
- Tax Code §26.06
- TEC §21.206

These show up often enough across Brock-type board books to warrant being on the fast-lookup list rather than buried in the corpus.

---

**Signed,** Agent C

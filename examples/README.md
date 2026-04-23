# Examples

This directory holds the reference artifacts against which the agent is evaluated.

## Files

- **`brock_april_13_2026.pdf`** — the source board book (166 pages). Toby drops this in after the initial commit. Public record; no FERPA concerns.
- **`brock_april_13_2026_prereadhand.md`** — the hand-written trustee pre-read for the same meeting. Produced in roughly four hours of work. **This is the acceptance test.** Agent output on the same input must match this artifact in structure, citation discipline, flag calibration, and voice.
- **`brock_april_13_2026_output.md`** — the agent-generated pre-read (gitignored). Regenerated every run.
- **`samco_april_2026_loq.md`** — the SAMCO line-of-questioning artifact. Reference for the SAMCO_LOQ output mode.

## How to use

The Brock eval test in `tests/test_brock_april_13.py` runs the full pipeline on the source PDF and compares the generated output to the hand version. Expect initial delta; the calibration loop happens during Day 3 eval.

## Adding more references

When Toby shares additional reference prep docs or line-of-questioning artifacts from past meetings, they go here. Each reference artifact improves the agent's calibration and expands the test coverage.

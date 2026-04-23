# CLAUDE.md

**This file is automatically read by every Claude Code session working in this repository. Read it completely before taking any action.**

---

## What we are building

An open-source AI agent that turns dense Texas school-board packets (often 100–200 pages) into trustee-ready pre-reads, grounded in Texas statute and in an operator-level governance doctrine authored by a sitting trustee. A Gemini Live voice layer sits on top of the generated document so any board member can interrogate it conversationally.

The architecture has two stages.

**Stage 1 (Claude).** Ingest a PDF board book, walk each agenda item through a Claude Agent SDK loop that applies four custom Skills (statute-mapper, governance-principles, risk-flagger, output-formatter), produce a structured markdown pre-read.

**Stage 2 (Gemini).** Open a Gemini 3.1 Flash Live WebSocket session with the board book + generated pre-read + principles excerpt pre-loaded into the 128k context window. The board member speaks; the model answers in real time, constrained to that one document.

---

## The acceptance test (read this first)

We are not building a generic board-book analyzer. We are reproducing, in under sixty seconds, the quality of a hand-written trustee pre-read that currently takes four hours per meeting.

The canonical reference is `examples/brock_april_13_2026_prereadhand.md` — an artifact produced by hand. The agent is "done" when its output on the same input PDF is indistinguishable in:

1. **Structure** — executive summary table → per-item deep dive (What Is Happening → Key Data → Legal Framework with verified citations → Governance Questions → WATCH/RED FLAG/POSITIVE flags) → meeting prep checklist
2. **Citation discipline** — every TEC/TGC/TAC reference verified against the bundled corpus; no hallucinated authorities
3. **Risk flags** — the WATCH/RED FLAG/POSITIVE taxonomy applied with the same calibration as the hand version
4. **Voice** — preserves the tone patterns captured in `skills/governance-principles/principles.md` §IV

Every agent session in this repo should pause before calling something "done" and run the side-by-side eval. If you cannot defend the output as indistinguishable from the hand version, the work is not done.

---

## Repo structure

```
brock-governance-agent/
├── README.md                  # public face of the project
├── CLAUDE.md                  # this file — instructions for Claude Code
├── ORCHESTRATION.md           # how to run parallel agents (for Toby)
├── LICENSE                    # MIT
├── .gitignore
├── agents/
│   ├── AGENT_A.md             # ingestion + Claude Agent SDK loop
│   ├── AGENT_B.md             # statute-mapper Skill + corpus
│   ├── AGENT_C.md             # risk-flagger + governance-principles Skills
│   ├── AGENT_D.md             # hosted web site (Next.js on Vercel)
│   ├── AGENT_E.md             # voice layer (Gemini 3.1 Flash Live)
│   └── AGENT_F.md             # output-formatter Skill + Plan Architect
├── skills/
│   ├── statute-mapper/
│   │   ├── SKILL.md
│   │   └── statutes/          # bundled TEC / TGC / TAC / MSRB text
│   ├── governance-principles/
│   │   ├── SKILL.md
│   │   └── principles.md      # THE DOCTRINE — source of truth
│   ├── risk-flagger/
│   │   └── SKILL.md
│   └── output-formatter/
│       ├── SKILL.md
│       └── templates/         # Brock-format + SAMCO-format templates
├── agent/                     # Agent SDK loop implementation
├── api/                       # FastAPI HTTP wrapper
├── web/                       # Next.js site
├── voice/                     # Gemini Live bridge
├── examples/                  # canonical test cases — Brock April 13
└── tests/                     # eval harness
```

Each agent workstream lives in one top-level directory plus its owned Skill(s). See the relevant `agents/AGENT_X.md` for full scope.

---

## Tech stack (do not deviate without explicit approval)

**Python 3.11+** for the agent runtime, API, and voice bridge.
- Package manager: **uv** (`uv init`, `uv add`, `uv run`). Fast. Do not use pip/poetry.
- HTTP: **FastAPI** + **uvicorn**.
- PDF ingestion: **pypdf** for text extraction, **pdfplumber** for tables when needed.
- Claude Agent SDK: installed per [docs.claude.com](https://docs.claude.com). Use the Python SDK.

**TypeScript / Next.js 15** for the hosted site.
- Package manager: **pnpm**.
- UI: **Tailwind CSS** + **shadcn/ui**.
- Deploy target: **Vercel**.

**Gemini 3.1 Flash Live** for voice.
- WebSocket, 16kHz PCM audio in / 24kHz out.
- Google Gen AI SDK (Python) for the bridge.

**Formatting.** ruff (Python), prettier (TS). Run on commit.

**Testing.** pytest. The critical test is the Brock eval, not unit coverage.

---

## The four Skills — where the IP lives

These are the governance domain knowledge of the system. Each Skill is a `SKILL.md` file Claude auto-loads when relevant. Agents B, C, and F own these.

1. **`skills/statute-mapper/SKILL.md`** — maps any agenda item to TEC, TGC (TOMA), TAC, TEA frameworks, MSRB rules, and local board policy. Bundled statute corpus lives alongside. Owned by Agent B.
2. **`skills/governance-principles/SKILL.md`** — the doctrine layer. Loads `principles.md` at runtime. Checks every objective for baseline/target/date/cadence/guardrail/owner. Scores items for role fit (govern vs. execute). Owned by Agent C.
3. **`skills/risk-flagger/SKILL.md`** — the WATCH / RED FLAG / POSITIVE taxonomy. Pattern-matches on known failure modes (blanket citations, delegation without oversight, tariff exposure, etc.). Owned by Agent C.
4. **`skills/output-formatter/SKILL.md`** — assembles the final artifact in one of two modes: full Brock-format pre-read, or focused SAMCO-style line-of-questioning. Owned by Agent F.

**The doctrine is the IP.** `skills/governance-principles/principles.md` is the single source of truth for the operator doctrine. Do not inline principle content into code or other Skills; always reference the file. The doctrine will version over time.

---

## Voice and tone for agent output

Any output that faces a trustee or a district reader must follow the voice patterns in `skills/governance-principles/principles.md` §IV. Key rules:

- **Quote adopted text verbatim.** Never paraphrase mandatory language like "shall."
- **Cite the controlling authority** on every governance claim. Statute section + quoted text.
- **Numbered points** for arguments. One point per section.
- **No corporate filler.** No em-dashes as stacked qualifiers. No paragraph-length throat-clearing before the point.
- **Warm only on students.** "Every single child who walks through our doors…" — use sparingly.
- **Respectful on disagreement.** "I understand that reasoning. The issue is that…"
- **Sign as Trustee** when making a governance point; sign as Toby when making a community or personal point.

The one-line heuristic: write as if the document will be read into the public record at the next board meeting. Because it might be.

---

## Common commands

```bash
# Python environment setup (run once in repo root)
uv sync

# Run the agent against a board book PDF
uv run python -m agent.run examples/brock_april_13_2026.pdf

# Run the API locally
uv run uvicorn api.server:app --reload --port 8000

# Run the web site locally (from web/)
pnpm dev

# Run the voice bridge (from voice/)
uv run python bridge.py

# Run the Brock eval
uv run pytest tests/test_brock_april_13.py -v

# Lint + format
uv run ruff check --fix && uv run ruff format
```

---

## What NOT to do

1. **Do not invent statute citations.** If the statute-mapper Skill cannot verify a citation against the bundled corpus, soften or drop the flag. A wrong TEC citation destroys trust permanently.
2. **Do not inline principles into hardcoded prompts.** Always load from `principles.md`. The doctrine versions.
3. **Do not paraphrase board-policy text.** Quote it.
4. **Do not reproduce song lyrics, poems, or copyrighted news article text in output.** The board packet is the user's own material; that's fine. External sources are not.
5. **Do not build a RAG system on the statute corpus** for the MVP. The corpus is small enough (≤50k tokens) to load directly. RAG is a Day-30 optimization, not a Day-2 one.
6. **Do not block the eval loop.** Day 3 is an eval day; every agent should be in a state where side-by-side comparison against the Brock hand version is possible by end of Day 2.
7. **Do not commit API keys.** `.env.example` is tracked; `.env` is gitignored.
8. **Do not rename the Skills.** Their filenames and descriptions are what Claude uses to auto-load them. Changes cascade.

---

## The six-day timeline

| Day | Target state |
|---|---|
| **Day 1 (Wed 4/23)** | All six agent workstreams scaffolded. Agent A produces a rough end-to-end run on the Brock April 13 PDF. |
| **Day 2 (Thu 4/24)** | Statute-mapper and risk-flagger Skills populated. Output-formatter emits recognizable Brock format. First real pre-read. |
| **Day 3 (Fri 4/25)** | **Eval day.** Side-by-side vs. hand version. Iterate Skills overnight. |
| **Day 4 (Sat 4/26)** | SAMCO line-of-questioning mode. Second eval on a different board book. Voice integration end-to-end. |
| **Day 5 (Sun 4/27)** | Hosted site live on Vercel. README polished. Repo review. Third eval from a cold reader. |
| **Day 6 (Mon 4/28)** | Demo script. Dry runs. Buffer. |
| **Demo** | **Tue 4/29, 8 AM CT.** |

If Day 3 eval is not going well, the cut order is: Agent F's Plan Architect first, then Agent E's voice layer. The Board Book Red Team in Brock format is the non-negotiable core.

---

## For more detail

- Project background and thesis → `README.md`
- How to run parallel agents on this repo → `ORCHESTRATION.md`
- Individual agent workstreams → `agents/AGENT_A.md` through `agents/AGENT_F.md`
- The governance doctrine → `skills/governance-principles/principles.md`
- The hand-written reference artifact → `examples/brock_april_13_2026_prereadhand.md`

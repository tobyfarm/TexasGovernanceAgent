# Brock Governance Agent

**An open-source AI agent that turns Texas school-board packets into trustee-ready pre-reads.**

Built by [Toby Farmer](https://linkedin.com) — elected Trustee, Brock ISD — during the Anthropic hackathon, April 2026. Grounded in Texas statute and in an operator-level governance doctrine authored over four years on the board. MIT licensed. Self-hostable.

---

## What it does

Upload a board-meeting packet (typically 100 to 200 pages) and get back, in under a minute:

- An **executive summary** ranking every agenda item by governance risk
- A **per-item deep dive** — What's Happening / Key Data / Legal Framework with verified citations / Governance Questions / **WATCH** / **RED FLAG** / **POSITIVE** flags
- A **meeting-prep checklist** for the trustee
- A **voice companion** powered by Gemini Live that lets you interrogate the document conversationally on the way to the meeting

The agent reproduces the quality of a hand-written trustee pre-read that normally takes four hours per meeting. The reference deployment is Brock ISD in Parker County, Texas.

---

## Why it exists

Texas law gives school boards an exclusive duty to govern student outcomes (TEC §11.151(b)). In practice, governance breaks down in three predictable ways: boards adopt goals without measurable outcomes, boards drift into execution details that belong to administration, and the feedback loop between strategic plan and monthly agenda dies by October.

This agent encodes — in the form of four auto-loaded Agent Skills — the operator doctrine that separates real governance from theater. It enforces the textualism discipline of quoting adopted policy, the risk-flagging taxonomy of an experienced trustee, and the question-generation style that surfaces what actually matters in the meeting.

---

## Architecture (two stages)

**Stage 1 — Analysis (Claude).** A single Claude Agent SDK loop ingests the PDF, walks each agenda item through four custom Skills, verifies every citation against a bundled Texas-statute corpus, and assembles the pre-read.

**Stage 2 — Conversation (Gemini).** The generated document opens a Gemini 3.1 Flash Live session with the board book, pre-read, and a principles excerpt pre-loaded into the 128k context window. The board member speaks; the model answers in real time.

Each model plays to its strength: Claude for multi-step reasoning, citation verification, and document assembly; Gemini Live for low-latency native-audio conversation with a tight contextual guardrail.

See [governance_agent.html](https://github.com/tobyfarm/brock-governance-agent) or the full architecture diagrams in the landing page.

---

## Quick start

**Prerequisites.** Python 3.11+, [uv](https://github.com/astral-sh/uv), Node 20+ with pnpm, an Anthropic API key, and a Google AI API key (for voice).

```bash
# Clone
git clone https://github.com/tobyfarm/brock-governance-agent.git
cd brock-governance-agent

# Environment setup
uv sync
cp .env.example .env  # then add your ANTHROPIC_API_KEY and GOOGLE_API_KEY

# Run the agent against the reference board book
uv run python -m agent.run examples/brock_april_13_2026.pdf

# Run the local HTTP API
uv run uvicorn api.server:app --reload --port 8000

# Run the web UI (separate terminal, from web/)
cd web && pnpm install && pnpm dev
```

The pre-read writes to `examples/brock_april_13_2026_output.md`. Compare it side-by-side with `examples/brock_april_13_2026_prereadhand.md` — that's the acceptance test.

Every run also writes versioned artifacts to `logs/runs/{run_id}/` (`result.json`, `result.md`, `meta.json`) so successive calibration passes are diffable. A coarse comparator is available:

```bash
uv run python -m eval.compare examples/brock_april_13_2026_output.md \
                              examples/brock_april_13_2026_prereadhand.md
```

The CLI supports `--mode SAMCO_LOQ` for the SAMCO-style line of questioning, `--concurrency N` to tune parallel item analysis, and `--manual-split split.yaml` when auto-detected agenda boundaries miss. The API mirrors the same controls: `POST /analyze` accepts a `mode` form field and streams progress as Server-Sent Events; `GET /runs` and `GET /runs/{run_id}` surface persisted results. Set `BROCK_API_KEY` to require an `X-API-Key` header on write endpoints.

---

## The four Skills

All governance intelligence lives in four markdown files. Fork the repo, tune the Skills to your district's norms, ship.

- **`skills/statute-mapper/SKILL.md`** — Texas Education Code, TOMA, TAC, TEA frameworks, MSRB rules, local policy. Citation verification discipline.
- **`skills/governance-principles/SKILL.md`** — the doctrine layer. Every objective checked for baseline, target, date, cadence, guardrail, owner. Role-fit scoring for every agenda item.
- **`skills/risk-flagger/SKILL.md`** — the WATCH / RED FLAG / POSITIVE taxonomy. Twenty-plus pattern matches on known board-governance failure modes.
- **`skills/output-formatter/SKILL.md`** — assembles the final artifact in Brock-format full pre-read or SAMCO-format line-of-questioning mode.

The doctrine file itself — [`skills/governance-principles/principles.md`](skills/governance-principles/principles.md) — is the heart of the project. Sixteen governance principles extracted from two years of board-meeting emails, a 166-page board-book analysis, and the public record. Forkable.

---

## Deploying your own instance

The agent runs locally. The web UI deploys to Vercel with `vercel deploy` from the `web/` directory. The voice bridge requires Google AI credentials with Live API access. See [`ORCHESTRATION.md`](ORCHESTRATION.md) for the full walkthrough.

---

## Contributing

Pull requests welcome. The highest-leverage contributions are to the Skills — if you are a Texas trustee and want to add a governance pattern from your district, open an issue or a PR on `skills/risk-flagger/SKILL.md` or `skills/governance-principles/principles.md`.

---

## The roadmap

Board Book Red Team is the opening move. The same architecture powers six agents:

1. ◊ **Board Book Red Team** — shipped
2. Strategic Plan Architect — v1
3. Policy & Statute Mapper (standalone) — v1
4. Lone Star Governance Coach (meeting analytics) — v2
5. Outcome Monitor (live dashboards against board-adopted Key Results) — v2
6. Conservator Toolkit (BIP drafting, exit-criteria tracking) — v3

---

## License

MIT. Use it. Fork it. Ship better governance.

---

## Credits

Built with Claude (Anthropic) for the analysis layer. Voice powered by Gemini 3.1 Flash Live (Google). Grounded in the Texas Education Code, Texas Government Code, and the Texas Association of School Boards' governance framework. Reference deployment at Brock Independent School District, Parker County, Texas.

For Texas trustees, by a Texas trustee.

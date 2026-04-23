# ORCHESTRATION.md

**How to run parallel Claude Code agents against this repo on a single machine.**

This file is for Toby. It is not read by Claude Code. It is a runbook for a human orchestrating six workstreams against a six-day deadline.

---

## Prerequisites (one-time)

1. **Claude Code installed.** Follow [code.claude.com/docs](https://code.claude.com/docs). Verify with `claude --version`.
2. **GitHub CLI** (optional but useful): `gh auth login`.
3. **Python 3.11+, uv, Node 20+, pnpm.** Install via Homebrew or equivalent.
4. **API keys in `.env`**: `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`. See `.env.example` in the repo root once you create it.
5. **Terminal multiplexer.** iTerm2 tabs work fine. tmux if you like it.

---

## Day 0 — Prepare the repo (30 minutes)

```bash
# From github.com/tobyfarm in the web UI:
#   Create new private repo: brock-governance-agent
#   Initialize with: no files (we'll push what we have)

# Locally:
cd ~/code  # or wherever
git clone git@github.com:tobyfarm/brock-governance-agent.git
cd brock-governance-agent

# Drop the full orchestration package from Claude here
# (the contents of /mnt/user-data/outputs/repo/ from the chat)

# First commit
git add .
git commit -m "chore: initial scaffold from orchestration package"
git push origin main

# Create feature branches for each workstream
for agent in a b c d e f; do
  git branch feature/agent-$agent
done
git push origin --all

# Create worktrees — each agent gets its own working copy
mkdir -p ../worktrees
git worktree add ../worktrees/agent-a feature/agent-a
git worktree add ../worktrees/agent-b feature/agent-b
git worktree add ../worktrees/agent-c feature/agent-c
git worktree add ../worktrees/agent-d feature/agent-d
git worktree add ../worktrees/agent-e feature/agent-e
git worktree add ../worktrees/agent-f feature/agent-f
```

You now have six independent working copies. Each agent runs in its own. No file conflicts. Merge back through PRs or fast-forwards twice a day.

---

## Kicking off a Claude Code agent

For each worktree, open a terminal tab and run:

```bash
cd ~/code/worktrees/agent-a    # or agent-b, etc.
claude
```

At the Claude Code prompt, say:

> Read `CLAUDE.md` at the repo root. Then read `agents/AGENT_A.md`. You are Agent A. Execute the Day 1 milestones listed in that file. When you reach a decision point that requires input from me, pause and ask.

**Important:** start with the exact line above. Do not add extra context. The AGENT_X.md files are self-contained worker instructions.

---

## The six workstreams at a glance

| Tab | Agent | Directory | What it owns | Day 1 milestone |
|---|---|---|---|---|
| 1 | **A** | `worktrees/agent-a` | PDF ingestion + Claude Agent SDK loop + API wrapper | Rough end-to-end run on Brock April 13 |
| 2 | **B** | `worktrees/agent-b` | `skills/statute-mapper/` + statute corpus | TEC Ch 11 + Ch 44 + TGC Ch 551 loaded |
| 3 | **C** | `worktrees/agent-c` | `skills/risk-flagger/` + `skills/governance-principles/` | Skills consume `principles.md`; first flags emitted |
| 4 | **D** | `worktrees/agent-d` | `web/` Next.js site | Skeleton deployed to Vercel preview |
| 5 | **E** | `worktrees/agent-e` | `voice/` Gemini Live bridge | WebSocket echo test working |
| 6 | **F** | `worktrees/agent-f` | `skills/output-formatter/` + Plan Architect | Brock-format template stub rendering |

---

## Daily rhythm

**Morning (30 min).**
- Pull latest main into each worktree: `cd worktree && git pull --rebase origin main`
- Read each agent's overnight output. Answer any paused questions.
- Open all six tabs, kick off the day's milestones per each AGENT_X.md.

**Midday (15 min).**
- Merge checkpoint. Agents that have shipped Day-N milestones open PRs against main.
- Fast-forward merge clean PRs. Resolve any conflicts (should be rare with worktree isolation).
- Redistribute updated main to all worktrees.

**Evening (30 min).**
- Status check on each tab. Agents that are blocked need input. Unblock them.
- Kick off overnight work — for Claude Code this means giving an agent a clear next target and letting it run.
- Check in on the Brock April 13 eval (Day 2 onward). This is the quality bar.

---

## When an agent gets stuck

Three common failure modes and how to recover:

**1. Agent hallucinates a library or API.** Interrupt, paste the real doc snippet into the context, and say "use this version instead." Common for rapidly-moving tools (Claude Agent SDK, Gemini Live).

**2. Agent over-engineers.** Say "simplify. The MVP is [X]. Remove everything that is not on the critical path to [X]." Claude Code sometimes drifts into abstraction that does not ship.

**3. Agent thrashes on a decision.** You make the call. The AGENT_X.md files are prescriptive on tech stack to prevent this, but edge cases happen. Be decisive.

---

## Merge strategy

Protect `main` via branch protection settings or convention:

- **No direct commits to main.** Merge via PR.
- **Fast-forward merges only.** Rebase feature branches before merging.
- **Squash merges for tidy history** when a feature branch has many small commits.

Twice-daily merges are enough. More frequent and you spend all your time coordinating; less frequent and conflicts start accumulating.

---

## Cutting scope (when Day 3 eval goes sideways)

If by end of Day 3 the Brock eval is still materially off from the hand version, cut in this order to protect the core:

1. **Cut Plan Architect** (Agent F's secondary deliverable). The output-formatter Skill stays; the second agent does not ship.
2. **Cut voice layer end-to-end integration** (Agent E). The bridge may still work standalone; it just does not wire into the site.
3. **Cut Vercel deploy** (Agent D). Hosted site can be demoed locally via `pnpm dev` and a screen share.

Do not cut Agents A, B, or C. The Board Book Red Team producing Brock-format output with verified citations is the non-negotiable core. Everything else is upside.

---

## Demo day (Tuesday 4/29, 8 AM CT)

By 6 AM local time:

- Cold boot every tab. Kill everything. Start fresh from main.
- Run the Brock eval one last time. Save the output.
- Run one additional eval on a second board book (not Brock) as insurance against overfit.
- Charge laptop fully. Connect projector. Test the voice path end-to-end.
- Keep your hand-written April 13 pre-read printed nearby. It's the authority artifact.

The demo is 3 minutes. Lead with the upload-and-generate moment. Second beat is the voice moment. Close with the principles file — the moat.

---

## A note on agent autonomy

Claude Code agents are excellent at implementation. They are less good at judgment calls about product scope or governance nuance. Your job over six days is to:

- **Defend the acceptance test.** If the Brock eval is not passing, no feature matters.
- **Protect the doctrine.** `principles.md` is the IP. Changes to it go through you.
- **Unblock the agents.** Most thrashing dissolves with a decisive "do X, not Y."
- **Merge honestly.** If code is not working, don't merge it to main. Quality of `main` is the quality of the demo.

Everything else — the code, the deploys, the API wiring, the styling, the tests — the agents will handle if you keep them pointed at the right targets.

Six days. Go.

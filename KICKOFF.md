# KICKOFF.md

**The first 30 minutes. What you run, in what order, to go from an empty GitHub repo to six parallel Claude Code agents working the problem.**

This file is for Toby. Other agents should not read this file — they work from `CLAUDE.md` and their specific `AGENT_X.md`.

---

## Step 1 — Create the GitHub repo (2 minutes)

On `github.com/tobyfarm`:

1. Click **New repository**
2. Name: `brock-governance-agent`
3. Private ✓
4. **Do not** add README, .gitignore, or license — we're pushing our own
5. Create

Copy the SSH URL: `git@github.com:tobyfarm/brock-governance-agent.git`

---

## Step 2 — Clone, scaffold, push (5 minutes)

In terminal:

```bash
# Where you keep your code
cd ~/code

# Clone the empty repo
git clone git@github.com:tobyfarm/brock-governance-agent.git
cd brock-governance-agent

# Download the scaffold tarball from Claude's output
# (drag brock-governance-agent-scaffold.tar.gz from Finder to here)
tar xzf brock-governance-agent-scaffold.tar.gz
rm brock-governance-agent-scaffold.tar.gz

# Verify the structure
ls -la
# Should show: CLAUDE.md, README.md, ORCHESTRATION.md, KICKOFF.md,
#              LICENSE, .env.example, .gitignore, agents/, skills/, examples/

# Set up environment
cp .env.example .env
# Open .env and paste your ANTHROPIC_API_KEY and GOOGLE_API_KEY

# First commit
git add .
git commit -m "chore: initial scaffold from orchestration package"
git push origin main
```

---

## Step 3 — Drop in the reference artifacts (3 minutes)

The acceptance test is your hand-written Brock April 13 pre-read. The agents need both the source PDF and the reference output.

```bash
# Drop the Brock April 13 source board book
cp ~/Downloads/brock_april_13_2026.pdf examples/

# Drop your hand-written pre-read (the gold standard for evaluation)
cp ~/path/to/your/hand-written-preread.md examples/brock_april_13_2026_prereadhand.md

# Also drop your SAMCO line-of-questioning doc for the SAMCO_LOQ mode reference
cp ~/path/to/samco-loq.md examples/samco_april_2026_loq.md

git add examples/
git commit -m "feat: add reference artifacts for Brock April 13 eval"
git push
```

If you don't have these exact filenames, adjust and update `CLAUDE.md` reference paths accordingly.

---

## Step 4 — Run the setup script (2 minutes)

Create `setup.sh` in the repo root with the content below, then run it:

```bash
# Write the script
cat > setup.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

echo "==> Creating feature branches for each agent workstream"
for agent in a b c d e f; do
  git branch -f feature/agent-$agent main
done
git push origin --all

echo "==> Creating worktrees (each agent gets an isolated working copy)"
mkdir -p ../worktrees
for agent in a b c d e f; do
  if [ ! -d "../worktrees/agent-$agent" ]; then
    git worktree add "../worktrees/agent-$agent" "feature/agent-$agent"
  else
    echo "  (worktree for agent-$agent already exists, skipping)"
  fi
done

echo "==> Setting up Python environment in main worktree"
if command -v uv &> /dev/null; then
  uv init --quiet || true
  echo "  uv ready. Agents will add dependencies as needed."
else
  echo "  ⚠ uv not installed. Install with: brew install uv"
fi

echo ""
echo "==> DONE. Ready to kick off agents."
echo ""
echo "Open six terminal tabs. In each tab, cd to the matching worktree"
echo "and run 'claude'. Then paste the kickoff prompt from KICKOFF.md §5."
echo ""
echo "  Tab 1:  cd ../worktrees/agent-a && claude"
echo "  Tab 2:  cd ../worktrees/agent-b && claude"
echo "  Tab 3:  cd ../worktrees/agent-c && claude"
echo "  Tab 4:  cd ../worktrees/agent-d && claude"
echo "  Tab 5:  cd ../worktrees/agent-e && claude"
echo "  Tab 6:  cd ../worktrees/agent-f && claude"
EOF

chmod +x setup.sh
./setup.sh
```

You now have `../worktrees/agent-a/` through `../worktrees/agent-f/` — six isolated copies of the repo, each on its own feature branch.

---

## Step 5 — Kick off the six agents (15 minutes)

Open six terminal tabs. In each tab, change into the matching worktree and run `claude`:

```bash
# Tab 1
cd ~/code/worktrees/agent-a && claude

# Tab 2
cd ~/code/worktrees/agent-b && claude

# (repeat for c, d, e, f)
```

Then, in each tab, paste **exactly** the matching prompt below. Do not paraphrase. The prompts are tuned per agent.

---

### Tab 1 — Agent A (Ingestion + Agent SDK)

```
Read CLAUDE.md at the repository root. Then read agents/AGENT_A.md in full.

You are Agent A. Your scope is PDF ingestion, the Claude Agent SDK loop, and the FastAPI HTTP wrapper. You do not own the Skills — Agents B, C, and F do. You load and orchestrate them.

Your Day 1 targets:
1. uv init and set up the Python project with Agent SDK, FastAPI, pypdf, pdfplumber, pydantic, python-dotenv
2. Build agent/ingestion.py that parses examples/brock_april_13_2026.pdf into AgendaItem dicts
3. Build agent/run.py that instantiates the Agent SDK lead agent and loops through items
4. Stub api/server.py with /health and /analyze endpoints
5. Produce one rough end-to-end run on the Brock PDF. Quality will be low — that's expected on Day 1.

Stabilize the AnalysisResult pydantic contract from AGENT_A.md "Interface contract" by end of Day 2. Other agents depend on it.

Start by reading the files. Then tell me what you plan to do first before doing it.
```

---

### Tab 2 — Agent B (Statute Mapper + Corpus)

```
Read CLAUDE.md at the repository root. Then read agents/AGENT_B.md in full. Then read skills/governance-principles/principles.md §III (the Citation Register).

You are Agent B. You own the legal grounding layer. Every citation the system produces runs through you. No hallucinated authorities, ever.

Your Day 1 targets:
1. Populate skills/statute-mapper/SKILL.md with the full behavior instructions from AGENT_B.md
2. Populate skills/statute-mapper/statutes/tec-ch-11.md with TEC §§11.151, 11.1511, 11.1512, 11.1515, 11.201, 11.251 (verbatim text from statutes.capitol.texas.gov)
3. Populate skills/statute-mapper/statutes/tgc-ch-551.md with TGC §§551.001, 551.041, 551.043, 551.071, 551.072, 551.074, 551.076, 551.082, 551.0821, 551.083, 551.087, 551.101, 551.102, 551.103 (verbatim)
4. Populate skills/statute-mapper/statutes/tec-ch-44.md with §§44.002, 44.004, 44.006, 44.031
5. Build skills/statute-mapper/verifier.py with the verify(citation) function

IMPORTANT: statute text must be verbatim from the Texas statutes website. Do not paraphrase. Include a retrieval date comment at the top of each file. If you cannot access the site, fetch the PDFs from the Texas Legislature archive.

Start by reading the files. Then outline your plan before fetching any statute text.
```

---

### Tab 3 — Agent C (Risk Flagger + Governance Principles)

```
Read CLAUDE.md at the repository root. Then read agents/AGENT_C.md in full. Then read skills/governance-principles/principles.md in full — that file is your source of truth.

You are Agent C. You own the two Skills that carry governance judgment. This is the hardest calibration problem in the project. Your output is what separates this agent from a generic board-book summarizer.

Your Day 1 targets:
1. Populate skills/governance-principles/SKILL.md with the behavior instructions from AGENT_C.md "Drafting skills/governance-principles/SKILL.md"
2. Populate skills/risk-flagger/SKILL.md with the behavior instructions from AGENT_C.md "Drafting skills/risk-flagger/SKILL.md"
3. Walk through principles.md §I (16 principles) and §II (20 risk patterns). Make sure every principle and every pattern has explicit trigger signals the Skill can detect.
4. On Brock April 13 Item K (Closed Session with blanket TGC §§551.071-551.087 citation), verify your Skills emit the correct flags. This is a calibration check — do not skip it.

Do NOT edit principles.md itself. That file is Toby's doctrine. Reference it; do not rewrite it.

Start by reading the files. Then explain which principles you think will be hardest to encode and why.
```

---

### Tab 4 — Agent D (Hosted Web Site)

```
Read CLAUDE.md at the repository root. Then read agents/AGENT_D.md in full. Then open governance_agent.html in the repo root — that file is the brand reference for your visual language.

You are Agent D. You own the public-facing web site. This is the viral surface — every trustee who tries it becomes a distribution node.

Your Day 1 targets:
1. Scaffold web/ with Next.js 15 + Tailwind + TypeScript + shadcn/ui (pnpm)
2. Build the landing page at / — match the visual language of governance_agent.html (Fraunces display serif, Instrument Sans body, cream + ink palette, Claude orange accent)
3. Build /analyze with a drag-and-drop PDF upload zone (even if upload is stubbed for Day 1)
4. Deploy to Vercel preview. Get a public URL.

Tech is locked: Next.js 15 App Router, Tailwind CSS, shadcn/ui customized to match the serif-editorial aesthetic. Do NOT use Inter, Space Grotesk, Geist, or any other convergent AI-aesthetic font. Fraunces + Instrument Sans + JetBrains Mono from Google Fonts.

Start by reading the files and the reference HTML. Then show me the color palette and type scale you plan to use.
```

---

### Tab 5 — Agent E (Voice Layer)

```
Read CLAUDE.md at the repository root. Then read agents/AGENT_E.md in full.

You are Agent E. You own the voice companion — a Gemini 3.1 Flash Live WebSocket bridge that lets trustees interrogate the generated pre-read conversationally.

Your Day 1 targets:
1. Scaffold voice/ with uv and install google-genai, websockets, python-dotenv
2. Get WebSocket auth working with GOOGLE_API_KEY from .env
3. Echo test: browser client connects to your bridge, sends text, receives Gemini text response
4. Verify the model name and API surface against current docs at ai.google.dev/gemini-api/docs/live-api — API is moving

Tech is locked: Gemini 3.1 Flash Live, WebSocket, 16kHz PCM input, 24kHz output, Python google-genai SDK. System instruction strictly scopes the model to the loaded document.

Start by reading the files and checking the current Gemini Live API docs. Tell me the exact model name you plan to use and flag any API changes since AGENT_E.md was written.
```

---

### Tab 6 — Agent F (Output Formatter + Plan Architect)

```
Read CLAUDE.md at the repository root. Then read agents/AGENT_F.md in full. Then open examples/brock_april_13_2026_prereadhand.md — that artifact is the acceptance test for your output formatter.

You are Agent F. You own the last-mile rendering and the second (secondary) agent — Plan Architect. Rendering turns structured analysis into the trustee-ready document. Plan Architect is a Day-5 stretch goal; cut it if Day 3 eval is rocky.

Your Day 1 targets:
1. Populate skills/output-formatter/SKILL.md with the behavior instructions from AGENT_F.md
2. Build skills/output-formatter/templates/brock_full.md — a Jinja2 (or mustache) template whose structure exactly matches examples/brock_april_13_2026_prereadhand.md
3. Do a first rough render of Brock April 13 using dummy data. The structure should look right even if the content is placeholder.

The hand version at examples/brock_april_13_2026_prereadhand.md IS the acceptance test. Study it. Your template's structural fidelity to that document is the metric.

Voice rules come from principles.md §IV. Every render passes through those rules.

Start by reading the files and the hand-written reference. Then describe the section-by-section structure you see in the reference doc.
```

---

## Step 6 — Daily rhythm (from Day 1 onward)

See `ORCHESTRATION.md` for the full runbook. The short version:

- **Morning 8 AM.** Pull main into each worktree. Read each agent's overnight output. Answer paused questions. Kick off day's milestones.
- **Noon 12 PM.** Merge checkpoint. Shipping agents open PRs. Fast-forward clean merges. Redistribute to worktrees.
- **Evening 6 PM.** Status check. Unblock blockers. Kick off overnight work.
- **Eval check (Day 2 onward).** Run the Brock April 13 eval once per day. Compare against the hand version. Log the gaps.

---

## If something goes wrong in the first hour

**The setup script fails partway through.** Delete `../worktrees/` and rerun. The script is idempotent; existing worktrees are skipped.

**An agent says it can't find `CLAUDE.md`.** Verify you ran `claude` from inside a worktree, not from the main repo or from your home directory. Claude Code picks up `CLAUDE.md` from the directory it's launched in.

**An agent asks for a file that doesn't exist** (e.g., Agent F asks for the hand-written pre-read, but you haven't dropped it in yet). Drop it in to the main worktree, commit, push, and have each downstream worktree `git pull origin main`.

**Two agents edit the same file.** Use `git worktree` isolation — agents working in different worktrees cannot collide. If they do (because you manually invited conflict), use your judgment on which version to keep.

**You change your mind on a tech decision** (e.g., "actually, let's use poetry instead of uv"). Stop all agents. Update `CLAUDE.md` or the relevant `AGENT_X.md`. Restart agents with the new instruction. Be sure before you do this; thrashing on tech decisions burns Day-1 hours.

---

## The 48-hour checkpoint

By end of Day 2 (Thursday 4/24 evening), the repo state should be:

- [ ] Agent A: end-to-end run on Brock April 13 produces a valid `AnalysisResult` and writes a markdown pre-read (poor quality is OK; pipeline completeness is the bar)
- [ ] Agent B: statute corpus has TEC Ch 11, Ch 44, TGC Ch 551 loaded verbatim; verifier.py works on at least 20 sample citations
- [ ] Agent C: both Skills populated; Brock April 13 emits recognizable flags and questions (calibration is Day 3+)
- [ ] Agent D: landing page deployed to Vercel preview; upload UX works (may be stubbed)
- [ ] Agent E: Gemini Live echo test works; full audio bridge running locally
- [ ] Agent F: Brock-format template renders dummy data into correct structure

If any two of those are behind by end of Day 2, you are behind. Triage at that point. The non-cuttables are A, B, and C.

---

## The 72-hour eval (Friday 4/25 evening)

Sit down with the generated Brock April 13 pre-read and the hand-written reference. Side-by-side. Read both. Log every delta.

Classify each delta:
- **Principle gap** → add to principles.md v2
- **Skill miscalibration** → Agent C fix
- **Corpus gap** → Agent B fix
- **Formatter issue** → Agent F fix
- **Pipeline issue** → Agent A fix

Fix overnight. Re-run Saturday morning. If the delta is substantially closed by Saturday noon, you are on track. If not, execute the cut order in ORCHESTRATION.md (Plan Architect first, then voice end-to-end integration, then Vercel deploy).

---

## The demo (Tuesday 4/29, 8 AM CT)

Three minutes. Order:

1. **30 seconds** — Upload the Brock April 13 PDF. Output streams on screen. Live.
2. **90 seconds** — Scroll the generated pre-read. Land on one RED FLAG item. Open the voice session. Ask: *"What should I ask SAMCO about the 2026 bond series tonight?"* Gemini answers in your doctrine language.
3. **60 seconds** — Open `principles.md`. Explain that the doctrine is the moat. Anyone can fork this for their district. End with: *"For Texas trustees, by a Texas trustee."*

Close. Thank the judges. Done.

---

You have everything you need. Six days. Go.

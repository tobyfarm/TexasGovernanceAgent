#!/usr/bin/env bash
# setup.sh — bootstrap script for the Brock Governance Agent repo
# Run this from the repo root after the initial commit is pushed.
# Idempotent: safe to re-run if something fails partway through.

set -euo pipefail

REPO_ROOT="$(pwd)"
WORKTREE_PARENT="$(dirname "$REPO_ROOT")/worktrees"

echo "============================================================"
echo "  Brock Governance Agent — Bootstrap"
echo "============================================================"
echo ""
echo "Repo root:       $REPO_ROOT"
echo "Worktree parent: $WORKTREE_PARENT"
echo ""

# -----------------------------------------------------------------
# 1. Sanity checks
# -----------------------------------------------------------------

if [ ! -f "CLAUDE.md" ]; then
  echo "✗ CLAUDE.md not found. Run this script from the repo root."
  exit 1
fi

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  echo "✗ Not inside a git repository. Clone the repo first."
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "⚠ Working tree has uncommitted changes. Commit or stash before continuing."
  git status --short
  exit 1
fi

# -----------------------------------------------------------------
# 2. Create feature branches for each agent
# -----------------------------------------------------------------

echo "==> Creating feature branches for each agent workstream"
for agent in a b c d e f; do
  branch="feature/agent-$agent"
  if git show-ref --verify --quiet "refs/heads/$branch"; then
    echo "    (branch $branch already exists, skipping)"
  else
    git branch "$branch" main
    echo "    created $branch"
  fi
done

echo "==> Pushing all branches to origin"
git push origin --all --quiet

# -----------------------------------------------------------------
# 3. Create worktrees
# -----------------------------------------------------------------

echo ""
echo "==> Creating worktrees (one per agent, isolated from each other)"
mkdir -p "$WORKTREE_PARENT"
for agent in a b c d e f; do
  worktree_path="$WORKTREE_PARENT/agent-$agent"
  branch="feature/agent-$agent"
  if [ -d "$worktree_path" ]; then
    echo "    (worktree $worktree_path already exists, skipping)"
  else
    git worktree add "$worktree_path" "$branch" --quiet
    echo "    created $worktree_path on $branch"
  fi
done

# -----------------------------------------------------------------
# 4. Python environment
# -----------------------------------------------------------------

echo ""
echo "==> Python environment check"
if command -v uv &>/dev/null; then
  echo "    uv: $(uv --version)"
else
  echo "    ⚠ uv not installed. Install with: brew install uv (or see https://docs.astral.sh/uv/)"
fi

if command -v python3 &>/dev/null; then
  python_version="$(python3 --version 2>&1)"
  echo "    python3: $python_version"
else
  echo "    ⚠ python3 not found. Install Python 3.11 or later."
fi

# -----------------------------------------------------------------
# 5. Node environment
# -----------------------------------------------------------------

echo ""
echo "==> Node environment check"
if command -v node &>/dev/null; then
  echo "    node: $(node --version)"
else
  echo "    ⚠ node not installed. Install Node 20 or later."
fi

if command -v pnpm &>/dev/null; then
  echo "    pnpm: $(pnpm --version)"
else
  echo "    ⚠ pnpm not installed. Install with: npm install -g pnpm"
fi

# -----------------------------------------------------------------
# 6. .env check
# -----------------------------------------------------------------

echo ""
echo "==> Environment variables"
if [ -f ".env" ]; then
  echo "    .env exists"
  if grep -q "ANTHROPIC_API_KEY=sk-" ".env" 2>/dev/null; then
    echo "    ✓ ANTHROPIC_API_KEY appears to be set"
  else
    echo "    ⚠ ANTHROPIC_API_KEY not set in .env — add it before kicking off agents"
  fi
  if grep -q "GOOGLE_API_KEY=" ".env" && ! grep -q "GOOGLE_API_KEY=$" ".env" 2>/dev/null; then
    echo "    ✓ GOOGLE_API_KEY appears to be set"
  else
    echo "    ⚠ GOOGLE_API_KEY not set in .env — needed for Agent E (voice)"
  fi
else
  echo "    ⚠ .env not found. Run: cp .env.example .env && edit .env"
fi

# -----------------------------------------------------------------
# 7. Claude Code check
# -----------------------------------------------------------------

echo ""
echo "==> Claude Code check"
if command -v claude &>/dev/null; then
  echo "    claude: installed"
else
  echo "    ⚠ claude not found on PATH. Install from https://code.claude.com/docs"
fi

# -----------------------------------------------------------------
# 8. Print kickoff commands
# -----------------------------------------------------------------

echo ""
echo "============================================================"
echo "  READY"
echo "============================================================"
echo ""
echo "Open six terminal tabs. In each tab, run:"
echo ""
for agent in a b c d e f; do
  echo "  Tab $(echo "$agent" | tr 'a-f' '1-6'): cd $WORKTREE_PARENT/agent-$agent && claude"
done
echo ""
echo "Then, in each tab, paste the kickoff prompt from KICKOFF.md §5."
echo ""
echo "Daily rhythm and troubleshooting → ORCHESTRATION.md"
echo ""

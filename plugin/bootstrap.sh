#!/usr/bin/env bash
#
# bootstrap.sh — Create an isolated git worktree with the plan-review plugin
# loaded, then launch Claude Code with --plugin-dir.
#
# Usage: ./bootstrap.sh [base-branch]
#   base-branch: Branch to base the worktree on (default: main)
#
set -euo pipefail

BASE_BRANCH="${1:-main}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git -C "$PLUGIN_DIR" rev-parse --show-toplevel)"

# ── Prerequisite validation ──────────────────────────────────────────────

if ! command -v codex &>/dev/null; then
  echo "Error: codex CLI not found. Install it before running bootstrap." >&2
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  echo "Error: Python 3 not found. Install it before running bootstrap." >&2
  exit 1
fi

# ── Worktree creation ───────────────────────────────────────────────────

WT_DIR="$REPO_ROOT/.worktrees/plan-review-$TIMESTAMP"
BRANCH_NAME="plan-review/$TIMESTAMP"

echo "Creating worktree at $WT_DIR from $BASE_BRANCH..."
git -C "$REPO_ROOT" worktree add -b "$BRANCH_NAME" "$WT_DIR" "$BASE_BRANCH"

echo ""
echo "Worktree created!"
echo "  Worktree: $WT_DIR"
echo "  Branch:   $BRANCH_NAME"
echo ""
echo "Skills available:"
echo "  /codex-plan-review:plan-with-review         — Create a Codex-reviewed plan"
echo "  /codex-plan-review:implement-approved-plan  — Implement an approved plan"
echo ""

# ── Launch Claude Code ──────────────────────────────────────────────────

echo "Launching Claude Code..."
cd "$WT_DIR"
exec claude --plugin-dir "$PLUGIN_DIR"

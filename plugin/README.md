# Codex Plan Review Plugin for Claude Code

An automated plan review loop: Claude writes a plan, Codex evaluates it, and the loop repeats until Codex deems the plan optimal.

## Prerequisites

- **Claude Code** with plugin support
- **Codex CLI** on PATH (`codex` command available)
- **Python 3** on PATH (`python3` command available)
- **Codex MCP configuration** — user-managed `.codex/config.toml` (the plugin does NOT configure Codex's MCP servers)

## Installation

### Option A: Marketplace (recommended)

Add the marketplace and install:

```bash
/plugin marketplace add <repo-url>
/plugin install codex-plan-review@codex-plan-review
```

### Option B: Direct plugin loading

Load the plugin directly with `--plugin-dir`:

```bash
claude --plugin-dir ./plugin
```

### Option C: Bootstrap with worktree

Create an isolated worktree and launch with the plugin loaded:

```bash
./plugin/bootstrap.sh [base-branch]
```

This will:
1. Validate prerequisites
2. Create an isolated git worktree
3. Launch Claude Code with the plugin loaded via `--plugin-dir`

## Usage

Once Claude Code is running with the plugin:

1. **`/codex-plan-review:plan-with-review [strategy-path]`** — Create an implementation plan
   - Reads the strategy document
   - Researches the codebase
   - Writes `docs/plan.md` with required sections
   - Automatically triggers Codex review via PostToolUse hook
   - Handles the revision loop until Codex approves

2. **`/codex-plan-review:implement-approved-plan`** — Implement an approved plan
   - Validates `approval.json` against current `docs/plan.md`
   - Proceeds with implementation only if approval is valid

## Plugin Structure

```
plugin/
├── .claude-plugin/
│   └── plugin.json               # Plugin manifest
├── bootstrap.sh                   # Worktree + launch script
├── hooks/
│   ├── hooks.json                 # Hook configuration
│   ├── plan_review.py             # PostToolUse: Codex review on plan writes
│   ├── enforce_approval.py        # PreToolUse: gate writes until approved
│   ├── bash_drift_check.py        # PostToolUse: detect unexpected file changes
│   └── codex_review_schema.json   # Codex structured output schema
├── skills/
│   ├── plan-with-review/
│   │   └── SKILL.md               # Planning workflow skill
│   └── implement-approved-plan/
│       └── SKILL.md               # Implementation workflow skill
└── tests/
```

## How It Works

1. Claude writes `docs/plan.md` → PostToolUse hook triggers
2. Hook validates plan structure (6 required sections)
3. Hook snapshots plan and sends to Codex CLI for review
4. If Codex says "not optimal" → hook blocks with feedback → Claude revises
5. If Codex says "optimal" → hook writes `approval.json` → Claude asks user to confirm
6. PreToolUse hook prevents any file writes (except `docs/plan.md`) until approval exists

**Note:** Approval is hash-locked — `approval.json` stores a SHA-256 hash of the approved `docs/plan.md`. If the plan is modified after approval, the hash won't match and implementation will be blocked until the plan is re-reviewed.

## Runtime Artifacts

All review artifacts live in `.claude/review/` (created at runtime):

- `plan_v{N}.snapshot.md` — Plan snapshot before each review
- `plan_v{N}.codex.json` — Codex structured output
- `plan_v{N}.annotated.md` — Codex annotated plan
- `approval.json` — Approval record with plan hash
- `version_counter` — Current revision number
- `codex_thread_id` — Persistent Codex session ID

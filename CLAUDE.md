# CLAUDE.md — Codex Plan Review Plugin

## Project Overview

Claude Code plugin that enforces a **plan-then-implement** workflow using Codex CLI as an automated reviewer. Claude writes a plan at `docs/plan.md`, Codex evaluates it for accuracy and optimality, and the loop repeats until Codex approves. Implementation is then gated behind a SHA-256 hash of the approved plan.

## Commands

```bash
# Load plugin
claude --plugin-dir ./plugin

# Bootstrap with worktree (creates isolated branch)
./plugin/bootstrap.sh [base-branch]

# Run tests
cd plugin && python3 -m pytest tests/

# Validate plugin manifest
claude plugin validate .
```

### Skills (inside Claude Code)

```
/codex-plan-review:plan-with-review                    # Plan using docs/strategy.md
/codex-plan-review:plan-with-review path.md            # Plan using specific file
/codex-plan-review:plan-with-review add authentication # Plan from free-text
/codex-plan-review:implement-approved-plan             # Implement the approved plan
```

## Architecture

### Directory Layout

```
plugin/
├── .claude-plugin/plugin.json          # Plugin manifest
├── hooks/
│   ├── hooks.json                      # Hook registrations
│   ├── plan_review.py                  # PostToolUse: Codex review loop
│   ├── enforce_approval.py             # PreToolUse: gate writes on approval
│   ├── bash_drift_check.py             # PostToolUse: detect unexpected changes
│   ├── validate_approval.py            # Standalone approval validator CLI
│   └── codex_review_schema.json        # Structured output schema for Codex
├── skills/
│   ├── plan-with-review/SKILL.md       # Planning skill
│   └── implement-approved-plan/SKILL.md
├── bootstrap.sh                        # Worktree creation + launch
└── tests/                              # pytest tests per hook
```

### Hook System

All hooks read JSON from **stdin** and write JSON to **stdout**.

| Hook | Trigger | Purpose |
|------|---------|---------|
| `enforce_approval.py` | PreToolUse `Write\|Edit\|Bash` | Denies file writes and non-readonly Bash unless a valid approval exists. Always allows `docs/plan.md`. |
| `plan_review.py` | PostToolUse `Write\|Edit` | On `docs/plan.md` write: validates structure, calls Codex, blocks with feedback or writes `approval.json`. Timeout 600s. |
| `bash_drift_check.py` | PostToolUse `Bash` | Checks `git status` for unexpected file changes outside `docs/plan.md` and `.claude/review/`. Skips during implementation. |

**Hook output protocol:**
- Allow: `{}`
- Block: `{"decision": "block", "reason": "...", "hookSpecificOutput": {"additionalContext": "..."}}`
- Deny (PreToolUse): `{"hookSpecificOutput": {"permissionDecision": "deny", "reason": "..."}}`

### Approval Flow

1. Claude writes `docs/plan.md` with 6 required sections: `## Goal`, `## Context`, `## Approach`, `## Changes`, `## Risks`, `## Open Questions`
2. `plan_review.py` invalidates any prior approval, snapshots the plan, and calls `codex exec --json --output-schema`
3. Codex returns structured JSON (`is_optimal`, `blocking_issues`, `recommended_changes`, `annotated_plan_markdown`, `summary`)
4. If `is_optimal: false` → hook blocks with feedback, Claude revises (max 5 revisions)
5. If `is_optimal: true` → writes `approval.json` with `plan_hash` (SHA-256 of plan content)
6. Subsequent file writes/edits validated against that hash by `enforce_approval.py`

### Runtime Artifacts (`.claude/review/`)

| File | Purpose |
|------|---------|
| `version_counter` | Integer tracking current revision |
| `codex_thread_id` | Codex session UUID for multi-turn review |
| `plan_v{N}.snapshot.md` | Plan snapshot before each review |
| `plan_v{N}.codex.json` | Codex structured output |
| `plan_v{N}.annotated.md` | Codex annotated plan with inline comments |
| `approval.json` | Approval record: `is_optimal`, `plan_hash`, `review_version`, `approved_at`, `codex_thread_id` |

## Key Conventions

- **Python 3**, standard library only — no external dependencies
- **No build system** — hooks are invoked directly via `python3`
- Requires `codex` CLI on PATH
- `${CLAUDE_PLUGIN_ROOT}` is resolved by Claude Code to the plugin directory
- Hooks fail closed: malformed input → deny
- All runtime state is project-local under `.claude/review/` (gitignored)
- `enforce_approval.py` allowlists readonly commands (`rg`, `grep`, `ls`, `cat`, `git status`, `git diff`, etc.) and blocks execution commands (`python3`, `node`, `npm`, `rm`, etc.) plus shell operators (`|`, `;`, `&&`, etc.) before approval

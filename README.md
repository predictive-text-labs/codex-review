# Codex Plan Review

> A Claude Code plugin that enforces AI-reviewed implementation plans — Claude writes the plan, Codex validates it against the actual codebase, and file writes are physically blocked until the plan is approved.

## Why Use This?

LLM-generated implementation plans suffer from three recurring problems:

1. **Hallucinated APIs** — the plan references functions, modules, or patterns that don't exist in the codebase
2. **Missed edge cases** — the plan overlooks error handling, concurrency, or integration points that the real code requires
3. **Suboptimal approaches** — the plan proposes a reasonable solution but ignores a better pattern already established in the codebase

This plugin solves these by adding a second model (Codex CLI) as an automated reviewer that validates every claim against the actual code before implementation begins.

**The key innovation is hook-level enforcement.** This isn't a suggestion to "please review your plan" — Claude physically cannot write files other than the plan until Codex approves it. The Write, Edit, and Bash tools are all gated by a PreToolUse hook that checks for a valid, hash-locked approval.

## How It Works

```
                        ┌─────────────────────────────────┐
                        │      PLANNING PHASE             │
                        │   (Write/Edit/Bash restricted)  │
                        └────────────────┬────────────────┘
                                         │
                 User invokes /plan-with-review
                                         │
                                         ▼
                  Claude researches codebase (read-only)
                  Writes docs/plan.md
                                         │
                                         ▼
              ┌─── PostToolUse hook triggers ◄──────────┐
              │    Validates plan structure              │
              │    Snapshots plan (v1, v2, ...)          │
              │    Sends to Codex CLI for review         │
              │                                         │
              ▼                                         │
         Codex reviews                                  │
              │                                         │
         ┌────┴─────┐                                   │
         ▼          ▼                                   │
     Approved    Rejected                               │
         │          │                                   │
         │          └── Claude reads annotated feedback  │
         │              Revises docs/plan.md ────────────┘
         │
         ▼
    approval.json written
    (SHA-256 hash-locked to plan)
         │
         ▼
┌────────────────────────────────────┐
│      IMPLEMENTATION PHASE          │
│   (Write/Edit/Bash unrestricted)   │
└────────────────┬───────────────────┘
                 │
    User runs /implement-approved-plan
                 │
                 ▼
    PreToolUse hook validates approval hash
    Unlocks file writes
                 │
                 ▼
    Claude implements the approved plan
```

**The review loop in detail:**

1. Claude writes `docs/plan.md` with all 6 required sections
2. The PostToolUse hook validates plan structure, snapshots the plan, and sends it to Codex CLI
3. Codex evaluates every claim against the actual code via its MCP servers
4. If rejected — the hook blocks with feedback; Claude reads the annotated review, evaluates each issue against the code, and revises the plan (re-triggering review automatically)
5. If approved — the hook writes `approval.json` with the plan's SHA-256 hash; Claude presents the plan and asks the user to confirm
6. The user runs `/implement-approved-plan` (optionally after `/clear` to free context) and the PreToolUse hook now allows file writes

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | AI coding agent (host for the plugin) | `npm install -g @anthropic-ai/claude-code` |
| [Codex CLI](https://github.com/openai/codex) | Second model for plan review | `npm install -g @openai/codex` |
| Python 3 | Hook scripts runtime | Pre-installed on macOS/Linux |
| Git | Version control, drift detection | Pre-installed on macOS/Linux |

**Verify your setup:**

```bash
claude --version    # Claude Code CLI
codex --version     # Codex CLI
python3 --version   # Python 3
git --version       # Git
```

**Note:** Codex MCP configuration (`.codex/config.toml`) is user-managed. The plugin does not configure Codex's MCP servers — you must ensure Codex has the MCP access it needs to review your codebase effectively.

## Installation

### Option A: Marketplace (recommended)

```bash
/plugin marketplace add <repo-url>
/plugin install codex-plan-review@codex-plan-review
```

### Option B: Direct plugin loading

```bash
claude --plugin-dir ./plugin
```

### Option C: Bootstrap with worktree

Creates an isolated git worktree and launches Claude Code with the plugin loaded:

```bash
./plugin/bootstrap.sh [base-branch]
```

Example output:

```
Creating worktree at /repo/.worktrees/plan-review-20250222-143000 from main...
Worktree created!
  Worktree: /repo/.worktrees/plan-review-20250222-143000
  Branch:   plan-review/20250222-143000

Skills available:
  /codex-plan-review:plan-with-review         — Create a Codex-reviewed plan
  /codex-plan-review:implement-approved-plan  — Implement an approved plan

Launching Claude Code...
```

## Usage

Once Claude Code is running with the plugin, there are two skills:

### Plan with Review

Three ways to invoke:

```bash
# From a strategy document (default: docs/strategy.md)
/codex-plan-review:plan-with-review

# From a specific file
/codex-plan-review:plan-with-review path/to/strategy.md

# From a free-text description
/codex-plan-review:plan-with-review add authentication to the API
```

**What happens:**

1. Claude reads the input (file or text) and researches the codebase using read-only tools
2. Claude writes `docs/plan.md` with all required sections
3. The PostToolUse hook automatically sends the plan to Codex for review
4. If rejected, Claude reads Codex's annotated feedback, evaluates it against the code, and revises
5. The loop repeats (up to 5 revisions) until Codex approves
6. On approval, Claude presents the plan and asks: *"Ready to execute?"*

### Implement Approved Plan

```bash
/codex-plan-review:implement-approved-plan
```

**What happens:**

1. Runs `validate_approval.py` to confirm `approval.json` is valid and hash matches
2. Reads `docs/plan.md` for the approved approach and file-level changes
3. Implements the plan systematically, one file/component at a time

**Tip:** Use `/clear` between planning and implementation to free up context window. The implementation skill works entirely from artifacts (`docs/plan.md` and `approval.json`) — it does not depend on the planning session.

## Plan Structure

The plan at `docs/plan.md` must contain these 6 sections. The PostToolUse hook rejects the plan if any are missing.

| Section | Purpose |
|---------|---------|
| `## Goal` | What this plan achieves. One paragraph. |
| `## Context` | Relevant codebase context. Reference specific files and patterns. |
| `## Approach` | High-level architectural approach. Why this over alternatives. |
| `## Changes` | File-level detail: what changes, new files, affected dependencies. |
| `## Risks` | What could go wrong. Mitigation strategies. |
| `## Open Questions` | Unresolved questions needing user input. |

## Architecture

### Plugin Directory

```
plugin/
├── .claude-plugin/
│   └── plugin.json                 # Plugin manifest (name, version, description)
├── bootstrap.sh                    # Worktree creation + Claude Code launch
├── hooks/
│   ├── hooks.json                  # Hook configuration (matchers, timeouts)
│   ├── enforce_approval.py         # PreToolUse: gate writes until approved
│   ├── plan_review.py              # PostToolUse: Codex review on plan writes
│   ├── bash_drift_check.py         # PostToolUse: detect unexpected file changes
│   ├── validate_approval.py        # Standalone approval validation script
│   └── codex_review_schema.json    # Codex structured output schema
├── skills/
│   ├── plan-with-review/
│   │   └── SKILL.md                # Planning workflow skill definition
│   └── implement-approved-plan/
│       └── SKILL.md                # Implementation workflow skill definition
└── tests/
    ├── test_enforce_approval.py
    ├── test_plan_review.py
    ├── test_validate_approval.py
    └── test_bash_drift_check.py
```

### Hook System

| Hook | Type | Matcher | Timeout | Purpose |
|------|------|---------|---------|---------|
| `enforce_approval.py` | PreToolUse | `Write\|Edit\|Bash` | 10s | Gate all writes and dangerous commands until plan is approved |
| `plan_review.py` | PostToolUse | `Write\|Edit` | 600s | Trigger Codex review when `docs/plan.md` is written |
| `bash_drift_check.py` | PostToolUse | `Bash` | 30s | Detect unexpected file changes after Bash commands |

### Hook Details

**`enforce_approval.py` (PreToolUse)**

The enforcement gate. Runs before every Write, Edit, and Bash tool use.

- **Write/Edit to `docs/plan.md`**: Always allowed (Claude needs to write the plan)
- **Write/Edit to `.claude/review/`**: Always denied (hook-managed directory)
- **Write/Edit to any other file**: Denied unless `approval.json` exists with valid hash
- **Bash commands before approval**: Only read-only commands allowed. The hook maintains:
  - An allowlist of safe commands (`rg`, `grep`, `ls`, `cat`, `head`, `tail`, `wc`, `tree`, `echo`, `pwd`, etc.)
  - Read-only git subcommands (`status`, `diff`, `show`, `log`, `branch`, etc.)
  - A blocklist of dangerous commands (`python3`, `node`, `npm`, `sed`, `rm`, `mv`, `curl`, etc.)
  - Shell operator detection (`|`, `;`, `&&`, `>`, `>>`, `` ` ``, `$(`, etc.)
  - Special exception: `python3 validate_approval.py` is allowed (needed by the implementation skill)
- **After approval**: Everything is allowed

**`plan_review.py` (PostToolUse)**

The review engine. Triggers after any Write/Edit to `docs/plan.md`.

1. Invalidates any previous approval (deletes `approval.json`, thread ID, all versioned artifacts, resets counter)
2. Validates plan structure (checks for all 6 required section headings)
3. Increments version counter and snapshots the plan
4. Checks max revision threshold (default: 5); blocks if exceeded
5. Builds a review prompt and sends the plan to Codex CLI (`codex exec --json`)
6. Manages persistent Codex sessions (stores thread ID for resume across revisions)
7. On approval: writes `approval.json` with SHA-256 hash of the plan
8. On rejection: returns blocking issues and path to annotated feedback

**`bash_drift_check.py` (PostToolUse)**

Runs after every Bash command during the planning phase. Checks `git status --porcelain` for file changes outside `docs/plan.md` and `.claude/review/`. If unexpected changes are detected, it blocks with a list of affected files. Skips entirely if a valid approval exists (implementation phase).

## Runtime Artifacts

All review artifacts are stored in `.claude/review/` (created at runtime, gitignored):

| File | Description |
|------|-------------|
| `plan_v{N}.snapshot.md` | Frozen copy of the plan before review round N |
| `plan_v{N}.codex.json` | Codex's structured JSON output for round N |
| `plan_v{N}.annotated.md` | Codex's annotated plan with inline comments for round N |
| `approval.json` | Approval record (written when Codex approves) |
| `version_counter` | Current revision number (plain text integer) |
| `codex_thread_id` | Persistent Codex session ID for resume |

### `approval.json` Structure

```json
{
  "is_optimal": true,
  "plan_hash": "sha256-hex-digest-of-docs/plan.md",
  "review_version": 3,
  "approved_at": "2025-02-22T14:30:00+00:00",
  "codex_thread_id": "thread_abc123"
}
```

**Hash sensitivity:** The `plan_hash` is a SHA-256 of the raw bytes of `docs/plan.md`. Any modification to the plan after approval — even whitespace changes — will invalidate the hash and block implementation until the plan is re-reviewed.

## Codex Review Schema

Codex returns structured JSON conforming to `codex_review_schema.json`:

```json
{
  "is_optimal": false,
  "blocking_issues": [
    {
      "severity": "high",
      "claim": "Plan references a UserService.authenticate() method",
      "evidence": "UserService has no authenticate() method; auth is handled by AuthMiddleware",
      "fix": "Replace UserService.authenticate() references with AuthMiddleware.verify()"
    }
  ],
  "recommended_changes": [
    "Consider using the existing RateLimiter instead of implementing a new one"
  ],
  "annotated_plan_markdown": "## Goal\n...\n> [CODEX] This claim is inaccurate...",
  "summary": "Plan contains 1 high-severity inaccuracy in the auth approach"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `is_optimal` | `boolean` | `true` only if the plan is solid, accurate, and optimal |
| `blocking_issues` | `array` | Issues that must be fixed. Each has `severity` (high/medium/low), `claim`, `evidence`, and `fix` |
| `recommended_changes` | `array` of `string` | Non-blocking suggestions for improvement |
| `annotated_plan_markdown` | `string` | The full plan with Codex's inline comments as blockquotes |
| `summary` | `string` | One-line summary of the review result |

## Troubleshooting

### "Codex CLI not found"

The `codex` command is not on your PATH.

```bash
npm install -g @openai/codex
codex --version  # Verify installation
```

### "Missing required sections"

Your `docs/plan.md` is missing one or more of the 6 required section headings. The error message lists which ones. Ensure your plan contains exactly these headings:

```markdown
## Goal
## Context
## Approach
## Changes
## Risks
## Open Questions
```

### "Maximum revision threshold reached"

The plan has been revised 5 times without reaching Codex approval. The hook will not allow further revisions. You have two options:

1. **Review the impasse** — read the latest annotated feedback in `.claude/review/` and decide if the remaining issues matter
2. **Force-approve manually** — create `approval.json` with the correct hash:

```bash
# Generate the plan hash
python3 -c "
import hashlib, json
with open('docs/plan.md', 'rb') as f:
    h = hashlib.sha256(f.read()).hexdigest()
json.dump({'is_optimal': True, 'plan_hash': h, 'review_version': 0, 'approved_at': '', 'codex_thread_id': ''}, open('.claude/review/approval.json', 'w'), indent=2)
print('Force-approved with hash:', h)
"
```

### "Cannot write to files other than docs/plan.md"

The enforcement hook is blocking writes because no valid approval exists. Either:

- Complete the plan review process (`/plan-with-review`)
- Or force-approve as described above

### "Plan modified since approval"

`docs/plan.md` has been changed after Codex approved it (the SHA-256 hash no longer matches). You need to re-run the review:

```bash
/codex-plan-review:plan-with-review
```

### "Codex CLI timed out"

The Codex review exceeded the 540-second subprocess timeout. This can happen with very large plans or Codex server issues. Options:

- Re-trigger the review by writing the plan again
- Simplify the plan (split into smaller plans)
- Force-approve if you're confident in the plan

### "Unexpected file changes detected"

The bash drift check found files modified outside of `docs/plan.md` and `.claude/review/` during the planning phase. This usually means a Bash command had unintended side effects. Revert the unexpected changes or investigate what caused them.

## OpenSpec Integration

This project uses [OpenSpec](https://github.com/openspec) for specification management. The `openspec/` directory contains WHEN/THEN specifications that formally describe the plugin's behavior.

### Directory Structure

```
openspec/
└── specs/
    ├── plan-review-hook/         # Core hook behavior
    ├── codex-review-schema/      # Review output format
    ├── approval-validation-cli/  # Approval validation
    ├── artifact-snapshots/       # Plan snapshotting
    ├── codex-session-manager/    # Codex thread persistence
    ├── implement-skill/          # Implementation skill
    ├── plan-skill/               # Planning skill
    ├── plugin-bootstrap/         # Worktree bootstrap
    ├── plugin-manifest/          # Plugin manifest format
    ├── plugin-marketplace/       # Marketplace integration
    ├── plugin-skills-format/     # Skill file format
    └── worktree-bootstrap/       # Worktree creation
```

### Sample Spec (WHEN/THEN format)

From `plan-review-hook/spec.md`:

```markdown
#### Scenario: Missing headings block review
- **WHEN** `docs/plan.md` is missing `## Risks` and `## Open Questions`
- **THEN** the hook returns `decision: "block"` with reason
  "Missing required sections: ## Risks, ## Open Questions"

#### Scenario: User force-approves after impasse
- **WHEN** the user manually writes `approval.json` with correct
  `plan_hash` and `is_optimal: true`
- **THEN** the PreToolUse gate allows implementation to proceed
```

### OpenSpec Commands

The project includes OpenSpec slash commands for managing specifications and changes:

| Command | Description |
|---------|-------------|
| `/opsx:explore` | Enter explore mode — think through ideas, investigate problems, clarify requirements |
| `/opsx:new` | Start a new change using the artifact-driven workflow |
| `/opsx:ff` | Fast-forward — create a change and generate all artifacts in one go |
| `/opsx:apply` | Implement tasks from an OpenSpec change |
| `/opsx:continue` | Continue working on a change — create the next artifact |
| `/opsx:verify` | Verify implementation matches change artifacts before archiving |
| `/opsx:sync` | Sync delta specs from a change to main specs |
| `/opsx:archive` | Archive a completed change |
| `/opsx:bulk-archive` | Archive multiple completed changes at once |
| `/opsx:onboard` | Guided onboarding — walk through a complete OpenSpec workflow cycle |

## Contributing

### Dev Setup

```bash
git clone <repo-url>
cd codex-review
claude --plugin-dir ./plugin    # Load the plugin for development
```

### Making Changes

This project uses its own review workflow. To make changes:

1. Run `/codex-plan-review:plan-with-review` with your proposed change
2. Iterate through the review loop until Codex approves
3. Run `/codex-plan-review:implement-approved-plan` to implement

### Testing Hooks Manually

Each hook reads JSON from stdin. You can test them directly:

```bash
# Test enforce_approval.py — should deny (no approval exists)
echo '{"tool_name":"Write","tool_input":{"file_path":"src/main.py"},"cwd":"/your/repo"}' \
  | python3 plugin/hooks/enforce_approval.py

# Test enforce_approval.py — should allow (plan.md is always writable)
echo '{"tool_name":"Write","tool_input":{"file_path":"docs/plan.md"},"cwd":"/your/repo"}' \
  | python3 plugin/hooks/enforce_approval.py

# Test enforce_approval.py — should allow (read-only Bash command)
echo '{"tool_name":"Bash","tool_input":{"command":"git status"},"cwd":"/your/repo"}' \
  | python3 plugin/hooks/enforce_approval.py

# Test enforce_approval.py — should deny (write command before approval)
echo '{"tool_name":"Bash","tool_input":{"command":"npm install"},"cwd":"/your/repo"}' \
  | python3 plugin/hooks/enforce_approval.py

# Test bash_drift_check.py — checks git status for unexpected changes
echo '{"tool_name":"Bash","tool_input":{"command":"ls"},"cwd":"/your/repo"}' \
  | python3 plugin/hooks/bash_drift_check.py
```

### Running Tests

```bash
python3 -m pytest plugin/tests/ -v
```

### Code Style

- Hook scripts are standalone Python 3 with no external dependencies
- All hooks communicate via JSON on stdin/stdout
- Hooks exit 0 in all cases (errors are communicated via JSON output, not exit codes)

## Project Structure

```
codex-review/
├── README.md                       # This file
├── plugin/                         # Claude Code plugin
│   ├── .claude-plugin/
│   │   └── plugin.json             # Plugin manifest
│   ├── README.md                   # Plugin-specific documentation
│   ├── bootstrap.sh                # Worktree + launch script
│   ├── hooks/                      # Hook scripts
│   │   ├── hooks.json              # Hook configuration
│   │   ├── enforce_approval.py     # PreToolUse enforcement gate
│   │   ├── plan_review.py          # PostToolUse Codex review
│   │   ├── bash_drift_check.py     # PostToolUse drift detection
│   │   ├── validate_approval.py    # Standalone approval validator
│   │   └── codex_review_schema.json
│   ├── skills/                     # Skill definitions
│   │   ├── plan-with-review/
│   │   └── implement-approved-plan/
│   └── tests/                      # Hook unit tests
├── openspec/                       # Specifications (OpenSpec format)
│   └── specs/                      # WHEN/THEN behavioral specs
├── docs/                           # Runtime artifacts (gitignored)
│   └── plan.md                     # Generated plan (created at runtime)
└── .claude-plugin/
    └── marketplace.json            # Marketplace registration
```

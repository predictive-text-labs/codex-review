## Why

Claude Code produces implementation plans that go unreviewed before execution. There is no programmatic quality gate between "plan written" and "plan executed." This plugin wires Codex CLI as an automated reviewer through Claude Code hooks, so plans get maximally evaluated against the actual codebase before a human ever sees the "ready to execute?" prompt. It's a reusable Claude Code plugin that can be installed into any project — not a one-off configuration.

## What Changes

- Add a `PostToolUse` hook that triggers when Claude writes/edits `plan.md`, sending the plan to Codex CLI for structured review
- Add a persistent Codex session manager that tracks thread IDs per worktree (never uses `--last`/`--latest`)
- Add structured output schema for Codex reviews (`is_optimal`, `blocking_issues`, `annotated_plan_markdown`)
- Add artifact snapshotting: each review cycle produces versioned snapshots (`plan_vN.snapshot.md`, `plan_vN.annotated.md`, `plan_vN.codex.json`)
- Add a git worktree bootstrap script so Claude Code and Codex share the same isolated workspace
- Add hook feedback injection: when Codex says "not optimal", the hook returns `decision: "block"` with `additionalContext` containing Codex's feedback, driving Claude to revise
- Add a `PreToolUse` hook that denies Write|Edit to non-plan files until `approval.json` confirms a valid, hash-matched approval — the hard guarantee
- Add a Claude Code skill (`/plan-with-review`) that guides Claude through the planning workflow: read strategy, produce `docs/plan.md` in the correct format, and handle the Codex feedback revision loop
- Add a Claude Code skill (`/implement-approved-plan`) that guides Claude through implementation of an approved plan: validates `approval.json` against current `docs/plan.md` hash before proceeding, stops if mismatch or not approved

## Capabilities

### New Capabilities

- `plan-review-hook`: The PostToolUse hook that intercepts plan.md writes, runs Codex review, and gates completion. Core orchestration logic including hook configuration, plan file detection, and decision/feedback JSON responses.
- `codex-session-manager`: Persistent Codex CLI session management. Handles thread ID capture from `--json` event streams, storage per worktree, and `exec resume <SESSION_ID>` invocation. Ensures session integrity across concurrent worktrees.
- `codex-review-schema`: Structured output schema and parsing for Codex review results. Defines the JSON contract (`is_optimal`, `blocking_issues`, `recommended_changes`, `annotated_plan_markdown`) and validates Codex output.
- `artifact-snapshots`: Versioned plan snapshots and Codex annotations. Manages the `.claude/review/` directory with `plan_vN.snapshot.md`, `plan_vN.annotated.md`, and `plan_vN.codex.json` files for auditability.
- `worktree-bootstrap`: Git worktree creation and setup script. Creates an isolated branch and launches Claude Code in the worktree. Does not configure Codex MCP servers — that's the user's responsibility.
- `plan-skill`: A Claude Code skill (invoked via `/plan-with-review`) that guides Claude through the planning workflow. Reads strategy input, instructs Claude to write the plan to `docs/plan.md` in a structured format, and handles Codex feedback revisions. Skill = guidance for the planning phase.
- `implement-skill`: A Claude Code skill (invoked via `/implement-approved-plan`) that guides Claude through implementing an approved plan. First step: read `docs/plan.md` and `.claude/review/approval.json`, validate that `plan_hash` matches the current plan, and confirm `is_optimal` is true. If validation fails, stops and tells Claude to run `/plan-with-review`. Skill = guidance for the implementation phase.

### Modified Capabilities

_(none - this is a greenfield tool)_

## Impact

- **This is a reusable plugin**: The deliverable is a set of files (hooks, skills, schema, bootstrap script) that can be copied/installed into any project's `.claude/` directory. Not a configuration for one specific repo.
- **Plugin files**: `.claude/hooks/` (Python scripts), `.claude/skills/` (skill markdown files), `.claude/hooks/codex_review_schema.json`, `bootstrap.sh`
- **Runtime artifacts**: `.claude/review/` directory (created at runtime by hooks — snapshots, reviews, approval.json, counters)
- **User responsibility**: Codex CLI on PATH, Python 3 on PATH, Codex MCP server configuration (`.codex/config.toml`). The plugin does not manage Codex config.
- **Hook config**: `.claude/settings.json` is generated/updated by the bootstrap script or install step, referencing the hook scripts
- **Git**: Bootstrap creates worktrees under `.worktrees/` with dedicated branches

## 1. Plugin Structure

- [ ] 1.1 Create plugin directory structure: `plugin/hooks/`, `plugin/skills/`, `plugin/schemas/`
- [ ] 1.2 Create a README or install instructions documenting prerequisites (codex CLI on PATH, Python 3 on PATH, user-managed `.codex/config.toml`)

## 2. Codex Review Schema

- [ ] 2.1 Create `plugin/schemas/codex_review_schema.json` with the structured output schema (`is_optimal`, `blocking_issues`, `recommended_changes`, `annotated_plan_markdown`, `summary`)
- [ ] 2.2 Validate the schema is valid JSON Schema draft-07

## 3. PostToolUse Hook — Plan Review (`plan_review.py`)

- [ ] 3.1 Scaffold `plugin/hooks/plan_review.py` with stdin JSON parsing and path resolution logic
- [ ] 3.2 Implement plan path matching: resolve `tool_input.file_path` to absolute path via `os.path.realpath`, compare to `<cwd>/docs/plan.md`
- [ ] 3.3 Implement approval invalidation: delete `approval.json`, `codex_thread_id`, and reset `version_counter` to 0 when plan is written and approval exists
- [ ] 3.4 Implement plan structure validation: check for all 6 required headings (`## Goal`, `## Context`, `## Approach`, `## Changes`, `## Risks`, `## Open Questions`), return `decision: "block"` with missing sections if validation fails
- [ ] 3.5 Implement version counter: read/increment `.claude/review/version_counter`, snapshot `docs/plan.md` to `.claude/review/plan_v{N}.snapshot.md`
- [ ] 3.6 Implement Codex session management: check for `.claude/review/codex_thread_id`, run `codex exec resume <ID>` if exists, else run `codex exec --json`. Parse `thread.started` event stream-agnostically: scan both stdout and stderr for JSONL lines with `"type": "thread.started"`, extract `thread_id`, store in `.claude/review/codex_thread_id`. Error if event not found in either stream.
- [ ] 3.7 Implement Codex invocation: build prompt with plan text, pass `--output-schema`, `-o .claude/review/plan_v{N}.codex.json`, `--cd <cwd>`, pipe prompt via stdin
- [ ] 3.8 Implement Codex output parsing: read `.claude/review/plan_v{N}.codex.json`, validate required fields, extract `annotated_plan_markdown` to `.claude/review/plan_v{N}.annotated.md`
- [ ] 3.9 Implement gating logic: if `is_optimal: false`, return `decision: "block"` + `reason` (summary of blocking issues) + `additionalContext` (evaluation instruction + review file path); if `is_optimal: true`, write `approval.json` and return `additionalContext` telling Claude to present plan and ask user
- [ ] 3.10 Implement max revision threshold: after N revisions (default 5), block and tell Claude to stop revising and present impasse to user
- [ ] 3.11 Implement Codex CLI error handling: timeout, non-zero exit, unparseable output all return `decision: "block"` with error details
- [ ] 3.12 Implement resume fallback: if `codex exec resume` fails, fall back to fresh `codex exec`, capture new thread ID

## 4. PreToolUse Hook — Enforcement Gate (`enforce_approval.py`)

- [ ] 4.1 Scaffold `plugin/hooks/enforce_approval.py` with stdin JSON parsing
- [ ] 4.2 Implement Write|Edit rules: allow `docs/plan.md`, deny all writes to `.claude/review/*` (entire directory is hook-owned), deny all other paths unless approval is valid
- [ ] 4.3 Implement approval validation: read `approval.json`, compute SHA-256 of current `docs/plan.md`, compare to `plan_hash`, verify `is_optimal` is `true`
- [ ] 4.4 Implement Bash read-only allowlist: reject commands with shell write operators (`|`, `;`, `&&`, `||`, `>`, `>>`, `<`, `$(`, backticks), allow only known read-only first-token commands (`rg`, `grep`, `ls`, `cat`, `head`, `tail`, `wc`, `file`, `git` with read-only subcommands)
- [ ] 4.5 Implement Bash interpreter/writer blocklist: `python`, `node`, `bash`, `sh`, `sed`, `awk`, `tee`, `xargs`, `npm`, `touch`, `mv`, `cp`, `rm`, `mkdir`, etc.
- [ ] 4.6 Implement post-approval mode: when `approval.json` is valid, allow all Write|Edit and Bash commands

## 5. PostToolUse Hook — Bash Drift Check

- [ ] 5.1 Implement drift detection in a separate hook script `plugin/hooks/bash_drift_check.py`: after Bash executes, run `git status --porcelain`, check for file changes outside `docs/plan.md` and `.claude/review/`; if unexpected changes detected, return `decision: "block"` telling Claude to revert

## 6. Claude Code Skills

- [ ] 6.1 Create `plugin/skills/plan-with-review.md` skill file with: strategy doc reading instruction, codebase research instruction, required plan format (`## Goal`, `## Context`, `## Approach`, `## Changes`, `## Risks`, `## Open Questions`), plan output path (`docs/plan.md`), Codex feedback handling instruction, max revision behavior, post-approval behavior (ask user "ready to execute?")
- [ ] 6.2 Create `plugin/skills/implement-approved-plan.md` skill file with: approval validation steps (read `approval.json`, compute SHA-256 of `docs/plan.md`, compare hashes, check `is_optimal`), failure messages for missing/invalid approval, implementation guidance from `## Changes` and `## Approach` sections

## 7. Bootstrap / Install Script

- [ ] 7.1 Create `bootstrap.sh` at plugin root: accept optional base branch argument (default `main`)
- [ ] 7.2 Implement prerequisite validation: check `codex` on PATH, check `python3` on PATH
- [ ] 7.3 Implement worktree creation: `git worktree add -b plan-review/<timestamp> .worktrees/plan-review-<timestamp> <base-branch>`
- [ ] 7.4 Implement plugin install into worktree: copy hook scripts to `.claude/hooks/`, skills to `.claude/skills/`, schema to `.claude/hooks/`, generate `.claude/settings.json` with correct hook references (PostToolUse matcher `"Write|Edit"` timeout 600s, PreToolUse matcher `"Write|Edit|Bash"`, PostToolUse Bash drift check matcher `"Bash"`)
- [ ] 7.5 Implement Claude launch: `cd` into worktree and exec `claude`

## 8. Testing & Validation

- [ ] 8.1 Test PostToolUse hook: write to `docs/plan.md` triggers Codex review, write to other files is ignored
- [ ] 8.2 Test PreToolUse hook: Write|Edit to non-plan files denied before approval, allowed after approval
- [ ] 8.3 Test Bash gating: read-only commands allowed pre-approval, write commands denied pre-approval
- [ ] 8.4 Test approval lifecycle: approval created on Codex approve, deleted on plan re-edit, hash validated
- [ ] 8.5 Test session management: thread ID captured on first run, resume used on subsequent runs, reset on new cycle
- [ ] 8.6 Test max revision threshold: hook blocks after 5 revisions, tells Claude to present impasse
- [ ] 8.7 Test path matching: nested `docs/plan.md` in subdirectory does not false-trigger
- [ ] 8.8 Test review directory protection: Claude cannot write to any file under `.claude/review/` via Write|Edit
- [ ] 8.9 Test Bash drift check: unexpected file changes after Bash are detected and reported
- [ ] 8.10 Test bootstrap script: validates prerequisites, creates worktree, installs plugin files, generates settings.json, launches Claude

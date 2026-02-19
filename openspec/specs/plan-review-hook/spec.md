# plan-review-hook Specification

## Purpose
TBD - created by archiving change codex-plan-review-hook. Update Purpose after archive.
## Requirements
### Requirement: PostToolUse hook triggers Codex review on plan writes
The system SHALL register a `PostToolUse` hook with matcher `"Write|Edit"` in `.claude/settings.json`. When the hook fires, it SHALL resolve `tool_input.file_path` to an absolute path using `os.path.realpath` and compare it to `<cwd>/docs/plan.md`. If the paths do not match, the hook SHALL exit 0 (no-op).

#### Scenario: Plan file written triggers review
- **WHEN** Claude writes or edits `docs/plan.md`
- **THEN** the hook resolves the file path to an absolute path, confirms it matches `<cwd>/docs/plan.md`, and initiates a Codex review

#### Scenario: Non-plan file write is ignored
- **WHEN** Claude writes a file that is not `docs/plan.md`
- **THEN** the hook exits 0 immediately without running Codex

#### Scenario: Nested path does not false-trigger
- **WHEN** Claude writes a file at `some/nested/docs/plan.md`
- **THEN** the hook resolves the absolute path, finds it does not match `<cwd>/docs/plan.md`, and exits 0

### Requirement: Hook validates plan structure before sending to Codex
The system SHALL validate that `docs/plan.md` contains all required section headings (`## Goal`, `## Context`, `## Approach`, `## Changes`, `## Risks`, `## Open Questions`) before sending to Codex. If any required heading is missing, the hook SHALL return `decision: "block"` with a reason listing the missing sections.

#### Scenario: Valid plan structure passes validation
- **WHEN** `docs/plan.md` contains all required headings
- **THEN** the hook proceeds to send the plan to Codex for review

#### Scenario: Missing headings block review
- **WHEN** `docs/plan.md` is missing `## Risks` and `## Open Questions`
- **THEN** the hook returns `decision: "block"` with reason "Missing required sections: ## Risks, ## Open Questions"

### Requirement: Hook returns structured feedback when Codex rejects plan
When Codex returns `is_optimal: false`, the hook SHALL return a JSON response with `decision: "block"`, `reason` containing a summary of Codex's blocking issues, and `hookSpecificOutput.additionalContext` containing the path to the full Codex review JSON and the evaluation instruction for Claude.

#### Scenario: Codex rejects plan
- **WHEN** Codex returns `is_optimal: false` with blocking issues
- **THEN** the hook returns `decision: "block"` with reason summarizing issues and `additionalContext` containing the Codex review file path and the instruction to evaluate each claim against the code

#### Scenario: Codex approves plan
- **WHEN** Codex returns `is_optimal: true`
- **THEN** the hook writes `approval.json`, returns no `decision` field (allow), and sets `additionalContext` telling Claude to present the plan and ask the user if ready to execute

### Requirement: Hook invalidates previous approval on new plan write
When a write to `docs/plan.md` is detected and `.claude/review/approval.json` exists, the hook SHALL delete `approval.json` before running the Codex review. This prevents stale approvals from a prior planning cycle.

#### Scenario: Previous approval exists when plan is re-edited
- **WHEN** Claude writes to `docs/plan.md` and `.claude/review/approval.json` exists
- **THEN** the hook deletes `approval.json` and resets `version_counter` to 0 before running Codex review

### Requirement: Hook fails closed after max revisions
After a configurable threshold (default: 5 revisions), the hook SHALL block and tell Claude to stop revising and present the situation to the user. The hook SHALL NOT auto-approve. The user MUST manually create a valid `approval.json` to force-approve.

#### Scenario: Revision count exceeds threshold
- **WHEN** the version counter reaches the configured maximum (default 5)
- **THEN** the hook returns `decision: "block"` with reason telling Claude to stop revising, explain the impasse to the user, and note that manual override is required

#### Scenario: User force-approves after impasse
- **WHEN** the user manually writes `approval.json` with correct `plan_hash` and `is_optimal: true`
- **THEN** the PreToolUse gate allows implementation to proceed

### Requirement: Hook configuration in project-local settings
The hook SHALL be configured in `.claude/settings.json` at the project root (not `~/.claude/settings.json`). The timeout SHALL be set to at least 600 seconds.

#### Scenario: Hook is configured project-locally
- **WHEN** the project is set up
- **THEN** `.claude/settings.json` contains a `PostToolUse` entry with matcher `"Write|Edit"` and timeout >= 600

### Requirement: Hook handles Codex CLI failure gracefully
If the Codex CLI invocation fails (non-zero exit code, timeout, or unparseable output), the hook SHALL return `decision: "block"` with the error details in reason and tell Claude to inform the user of the failure.

#### Scenario: Codex CLI times out
- **WHEN** Codex CLI does not respond within the hook timeout
- **THEN** the hook returns `decision: "block"` with reason describing the timeout

#### Scenario: Codex CLI returns unparseable output
- **WHEN** the Codex output JSON file cannot be parsed
- **THEN** the hook returns `decision: "block"` with reason describing the parse error


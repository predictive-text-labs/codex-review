## MODIFIED Requirements

### Requirement: Hook returns structured feedback when Codex rejects plan
When Codex returns `is_optimal: false`, the hook SHALL return a JSON response with `decision: "block"`, `reason` containing a summary of Codex's blocking issues, and `hookSpecificOutput.additionalContext` containing the path to the annotated plan markdown and the evaluation instruction for Claude. The raw Codex JSON path SHALL be included as a secondary reference.

#### Scenario: Codex rejects plan
- **WHEN** Codex returns `is_optimal: false` with blocking issues
- **THEN** the hook returns `decision: "block"` with reason summarizing issues and `additionalContext` instructing Claude to read the annotated plan markdown file for inline feedback, with the raw Codex JSON path as secondary reference

#### Scenario: Codex approves plan
- **WHEN** Codex returns `is_optimal: true`
- **THEN** the hook writes `approval.json`, returns no `decision` field (allow), and sets `additionalContext` telling Claude to present the plan and ask the user if ready to execute

#### Scenario: Annotated plan markdown is empty
- **WHEN** Codex returns `is_optimal: false` and `annotated_plan_markdown` is empty
- **THEN** the hook falls back to referencing the raw Codex JSON path as the primary artifact in `additionalContext`

### Requirement: Hook invalidates previous approval on new plan write
When a write to `docs/plan.md` is detected and `.claude/review/approval.json` exists, the hook SHALL delete `approval.json`, `codex_thread_id`, all `plan_v*.snapshot.md`, `plan_v*.codex.json`, and `plan_v*.annotated.md` files from `.claude/review/`, and reset `version_counter` to 0 before running the Codex review.

#### Scenario: Previous approval exists when plan is re-edited
- **WHEN** Claude writes to `docs/plan.md` and `.claude/review/approval.json` exists
- **THEN** the hook deletes `approval.json`, `codex_thread_id`, all versioned review artifacts, and resets `version_counter` to 0 before running Codex review

#### Scenario: Old artifacts from previous cycle are cleaned up
- **WHEN** a new planning cycle starts and `.claude/review/` contains `plan_v1.snapshot.md`, `plan_v2.codex.json`, etc. from a prior cycle
- **THEN** all `plan_v*` files are deleted before the new cycle begins

## ADDED Requirements

### Requirement: Bash drift check is approval-aware
The `bash_drift_check.py` PostToolUse hook SHALL check whether a valid approval exists (`.claude/review/approval.json` with `is_optimal: true` and `plan_hash` matching `docs/plan.md`). If a valid approval exists, the hook SHALL skip drift detection and exit silently.

#### Scenario: Drift check skipped during implementation
- **WHEN** a Bash command runs and a valid `approval.json` exists with matching `plan_hash`
- **THEN** the hook exits silently without checking git status

#### Scenario: Drift check active during planning
- **WHEN** a Bash command runs and no valid `approval.json` exists
- **THEN** the hook checks git status for unexpected file changes as before

### Requirement: Enforcement hook fails closed on malformed input
The `enforce_approval.py` PreToolUse hook SHALL deny the tool use if hook input JSON cannot be parsed from stdin. The hook SHALL NOT allow actions when it cannot determine the tool name or context.

#### Scenario: Malformed JSON input
- **WHEN** the hook receives invalid JSON on stdin
- **THEN** the hook outputs a deny decision with reason "Hook received malformed input"

#### Scenario: Valid JSON input
- **WHEN** the hook receives valid JSON on stdin
- **THEN** the hook proceeds with normal validation logic

### Requirement: Enforcement hook allows validate_approval.py before approval
The `enforce_approval.py` PreToolUse hook SHALL allow Bash commands that run `python3` with `validate_approval.py` as the script argument, even before plan approval exists. This permits the implementation skill to validate approval status.

#### Scenario: validate_approval.py allowed before approval
- **WHEN** Claude runs `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/validate_approval.py` before approval exists
- **THEN** the hook allows the command

#### Scenario: Other python3 commands still blocked before approval
- **WHEN** Claude runs `python3 some_other_script.py` before approval exists
- **THEN** the hook denies the command


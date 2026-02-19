## ADDED Requirements

### Requirement: Snapshot plan before each Codex review
Before sending the plan to Codex, the hook SHALL copy `docs/plan.md` to `.claude/review/plan_v{N}.snapshot.md` where `{N}` is the current version counter value.

#### Scenario: Plan is snapshotted
- **WHEN** the hook is about to invoke Codex
- **THEN** `docs/plan.md` is copied to `.claude/review/plan_v{N}.snapshot.md`

#### Scenario: Snapshot directory is created if missing
- **WHEN** `.claude/review/` does not exist
- **THEN** the hook creates the directory before writing the snapshot

### Requirement: Codex output stored as versioned artifacts
Codex structured output SHALL be written to `.claude/review/plan_v{N}.codex.json`. The `annotated_plan_markdown` field from Codex output SHALL be extracted and written to `.claude/review/plan_v{N}.annotated.md`.

#### Scenario: Codex review produces versioned artifacts
- **WHEN** Codex completes a review for version N
- **THEN** `.claude/review/plan_v{N}.codex.json` and `.claude/review/plan_v{N}.annotated.md` both exist

### Requirement: Version counter management
The version counter SHALL be stored in `.claude/review/version_counter` as a plain integer. It SHALL start at 0 for each planning cycle and increment by 1 before each Codex review.

#### Scenario: Counter increments per review
- **WHEN** the hook runs a Codex review
- **THEN** the version counter is incremented by 1 and the new value is used for snapshot file names

#### Scenario: Counter resets on new planning cycle
- **WHEN** `approval.json` is deleted (new plan written after previous approval)
- **THEN** `version_counter` is reset to 0

#### Scenario: Counter starts at 0 in fresh worktree
- **WHEN** `.claude/review/version_counter` does not exist
- **THEN** the counter defaults to 0

### Requirement: approval.json as structured approval record
When Codex returns `is_optimal: true`, the hook SHALL write `.claude/review/approval.json` with the following fields:
- `is_optimal`: boolean (always `true` when written by hook)
- `plan_hash`: SHA-256 hex digest of `docs/plan.md` content
- `review_version`: integer (the version counter value)
- `approved_at`: ISO 8601 timestamp
- `codex_thread_id`: the Codex session thread UUID

#### Scenario: Approval record is written on Codex approval
- **WHEN** Codex returns `is_optimal: true`
- **THEN** `.claude/review/approval.json` is written with all required fields and `plan_hash` matching the SHA-256 of current `docs/plan.md`

#### Scenario: Approval record is deleted on new plan write
- **WHEN** Claude writes to `docs/plan.md` and `approval.json` exists
- **THEN** `approval.json` is deleted before Codex review begins

### Requirement: All review artifacts are project-local
All snapshot, annotation, review, and approval files SHALL be stored under `.claude/review/` within the project directory. No files SHALL be written to global `~/` paths.

#### Scenario: Artifacts are in project directory
- **WHEN** any review artifact is created
- **THEN** its path is under `<project_root>/.claude/review/`

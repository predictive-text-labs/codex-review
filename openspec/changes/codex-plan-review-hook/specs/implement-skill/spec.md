## ADDED Requirements

### Requirement: Skill file at project-local path
The system SHALL provide a Claude Code skill file at `.claude/skills/implement-approved-plan.md` invokable via `/implement-approved-plan`.

#### Scenario: Skill is invokable
- **WHEN** the user types `/implement-approved-plan` in Claude Code
- **THEN** the skill is loaded and Claude follows its instructions

### Requirement: Skill validates approval before proceeding
As its first step, the skill SHALL instruct Claude to:
1. Read `docs/plan.md`
2. Read `.claude/review/approval.json`
3. Compute the SHA-256 hash of `docs/plan.md` content
4. Compare the computed hash to `approval.json.plan_hash`
5. Verify `approval.json.is_optimal` is `true`

#### Scenario: Valid approval — hashes match
- **WHEN** `approval.json` exists, `is_optimal` is `true`, and `plan_hash` matches the SHA-256 of current `docs/plan.md`
- **THEN** Claude proceeds with implementation

#### Scenario: approval.json missing
- **WHEN** `.claude/review/approval.json` does not exist
- **THEN** Claude stops and tells the user: "No approved plan found. Run /plan-with-review first."

#### Scenario: Hash mismatch — plan was modified after approval
- **WHEN** `approval.json.plan_hash` does not match the SHA-256 of current `docs/plan.md`
- **THEN** Claude stops and tells the user: "Plan has been modified since approval. Run /plan-with-review to re-approve."

#### Scenario: is_optimal is false
- **WHEN** `approval.json.is_optimal` is `false`
- **THEN** Claude stops and tells the user: "Plan was not approved as optimal. Run /plan-with-review to complete the review."

### Requirement: Skill instructs Claude to follow the plan
After validation, the skill SHALL instruct Claude to implement the changes described in `docs/plan.md`, following the `## Changes` section for file-level detail and the `## Approach` section for architectural guidance.

#### Scenario: Claude follows plan during implementation
- **WHEN** approval is validated
- **THEN** Claude uses the `## Changes` and `## Approach` sections of `docs/plan.md` to guide implementation

### Requirement: Skill is independent of planning skill
The implementation skill SHALL NOT depend on the planning skill having been invoked in the same session. It operates solely on the artifacts (`docs/plan.md` and `approval.json`). The user MAY `/clear` context between planning and implementation.

#### Scenario: Implementation after context clear
- **WHEN** the user clears context and invokes `/implement-approved-plan`
- **THEN** Claude reads the plan and approval artifacts fresh and proceeds with implementation

### Requirement: Skill does not bypass hook guarantee
The skill provides guidance for correct implementation workflow. The PreToolUse hook (D10) provides the hard guarantee. Even if the skill validation is somehow skipped, the hook SHALL still deny Write|Edit to non-plan files without valid approval.

#### Scenario: Skill validation and hook validation are independent
- **WHEN** Claude attempts to write a non-plan file
- **THEN** the PreToolUse hook independently validates `approval.json` regardless of whether the skill was invoked

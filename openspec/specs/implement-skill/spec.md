# implement-skill Specification

## Purpose
TBD - created by archiving change codex-plan-review-hook. Update Purpose after archive.
## Requirements
### Requirement: Skill file at project-local path
The system SHALL provide a Claude Code skill file at `.claude/skills/implement-approved-plan.md` invokable via `/implement-approved-plan`.

#### Scenario: Skill is invokable
- **WHEN** the user types `/implement-approved-plan` in Claude Code
- **THEN** the skill is loaded and Claude follows its instructions

### Requirement: Skill validates approval before proceeding
As its first step, the skill SHALL instruct Claude to run `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/validate_approval.py` and parse the JSON output. If the result has `valid: false`, Claude SHALL stop and show the `reason` to the user. If `valid: true`, Claude SHALL proceed with implementation.

#### Scenario: Valid approval — script confirms
- **WHEN** `validate_approval.py` outputs `{"valid": true}`
- **THEN** Claude proceeds with implementation

#### Scenario: approval.json missing — script reports
- **WHEN** `validate_approval.py` outputs `{"valid": false, "reason": "..."}`
- **THEN** Claude stops and shows the reason to the user

#### Scenario: Hash mismatch — script reports
- **WHEN** `validate_approval.py` outputs `{"valid": false, "reason": "..."}`
- **THEN** Claude stops and shows the reason to the user

#### Scenario: is_optimal is false — script reports
- **WHEN** `validate_approval.py` outputs `{"valid": false, "reason": "..."}`
- **THEN** Claude stops and shows the reason to the user

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


# approval-validation-cli Specification

## Purpose
TBD - created by archiving change skill-improvements. Update Purpose after archive.
## Requirements
### Requirement: Standalone approval validation script
The system SHALL provide a script at `plugin/hooks/validate_approval.py` that validates `approval.json` against `docs/plan.md` and outputs a structured JSON result to stdout.

#### Scenario: Valid approval
- **WHEN** `validate_approval.py` is run and `.claude/review/approval.json` exists with `is_optimal: true` and `plan_hash` matching the SHA-256 of `docs/plan.md`
- **THEN** the script outputs `{"valid": true}` to stdout and exits 0

#### Scenario: Missing approval.json
- **WHEN** `validate_approval.py` is run and `.claude/review/approval.json` does not exist
- **THEN** the script outputs `{"valid": false, "reason": "No approved plan found. Run /plan-with-review first to create and get approval for a plan."}` to stdout and exits 0

#### Scenario: Hash mismatch
- **WHEN** `validate_approval.py` is run and `plan_hash` in `approval.json` does not match the SHA-256 of `docs/plan.md`
- **THEN** the script outputs `{"valid": false, "reason": "The plan has been modified since it was approved. The approval is no longer valid. Run /plan-with-review to re-approve the current plan."}` to stdout and exits 0

#### Scenario: is_optimal is false
- **WHEN** `validate_approval.py` is run and `approval.json` has `is_optimal: false`
- **THEN** the script outputs `{"valid": false, "reason": "The plan was not approved as optimal by Codex. Run /plan-with-review to complete the review process."}` to stdout and exits 0

#### Scenario: Missing docs/plan.md
- **WHEN** `validate_approval.py` is run and `docs/plan.md` does not exist
- **THEN** the script outputs `{"valid": false, "reason": "No plan file found at docs/plan.md."}` to stdout and exits 0

### Requirement: Script uses cwd for path resolution
The script SHALL resolve `docs/plan.md` and `.claude/review/approval.json` relative to the current working directory.

#### Scenario: Paths resolved from cwd
- **WHEN** the script is invoked from the project root
- **THEN** it reads `<cwd>/docs/plan.md` and `<cwd>/.claude/review/approval.json`


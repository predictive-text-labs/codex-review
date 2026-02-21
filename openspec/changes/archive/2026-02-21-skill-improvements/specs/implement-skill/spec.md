## MODIFIED Requirements

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

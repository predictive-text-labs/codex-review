## ADDED Requirements

### Requirement: Structured output schema for Codex reviews
The system SHALL provide a JSON Schema file at `.claude/hooks/codex_review_schema.json` that constrains Codex's output to the following structure:

```json
{
  "type": "object",
  "properties": {
    "is_optimal": { "type": "boolean" },
    "blocking_issues": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "severity": { "type": "string", "enum": ["high", "medium", "low"] },
          "claim": { "type": "string" },
          "evidence": { "type": "string" },
          "fix": { "type": "string" }
        },
        "required": ["severity", "claim", "evidence", "fix"]
      }
    },
    "recommended_changes": {
      "type": "array",
      "items": { "type": "string" }
    },
    "annotated_plan_markdown": { "type": "string" },
    "summary": { "type": "string" }
  },
  "required": ["is_optimal", "blocking_issues", "recommended_changes", "annotated_plan_markdown", "summary"],
  "additionalProperties": false
}
```

#### Scenario: Schema file exists at expected path
- **WHEN** the project is set up
- **THEN** `.claude/hooks/codex_review_schema.json` exists and is valid JSON Schema

### Requirement: Codex invoked with --output-schema
The system SHALL pass `--output-schema .claude/hooks/codex_review_schema.json` to every `codex exec` invocation. The output file SHALL be written to `.claude/review/plan_v{N}.codex.json` using the `-o` flag.

#### Scenario: Codex output conforms to schema
- **WHEN** Codex completes a review
- **THEN** the output file at `.claude/review/plan_v{N}.codex.json` is valid JSON conforming to the schema

### Requirement: Hook parses and validates Codex output
After Codex completes, the hook SHALL parse the output JSON file and validate that all required fields are present. If parsing fails or required fields are missing, the hook SHALL treat it as a Codex failure and block with an error message.

#### Scenario: Valid Codex output is parsed
- **WHEN** the Codex output file contains valid JSON with all required fields
- **THEN** the hook reads `is_optimal` to determine the gating decision

#### Scenario: Malformed Codex output
- **WHEN** the Codex output file is not valid JSON or missing required fields
- **THEN** the hook returns `decision: "block"` with reason describing the parse/validation error

### Requirement: is_optimal drives the gating decision
The hook SHALL use the `is_optimal` boolean as the sole determinant for gating. `true` means the plan passes; `false` means feedback is returned to Claude.

#### Scenario: is_optimal is true
- **WHEN** Codex output has `is_optimal: true`
- **THEN** the hook writes `approval.json` and allows the tool use

#### Scenario: is_optimal is false
- **WHEN** Codex output has `is_optimal: false`
- **THEN** the hook returns `decision: "block"` with feedback from `blocking_issues` and `summary`

## ADDED Requirements

### Requirement: Skill instructs Claude to resolve Open Questions before writing the plan
After researching the codebase and before writing `docs/plan.md`, the skill SHALL instruct Claude to present any open questions or ambiguities to the user and wait for answers. Claude SHALL NOT write the plan until the user has addressed the open questions or explicitly deferred them.

#### Scenario: Claude has open questions after research
- **WHEN** Claude identifies ambiguities or unresolved questions during codebase research
- **THEN** Claude presents the questions to the user and waits for answers before writing `docs/plan.md`

#### Scenario: User defers questions
- **WHEN** the user says to proceed despite open questions
- **THEN** Claude writes the plan with the unresolved items captured in the `## Open Questions` section

#### Scenario: No open questions
- **WHEN** Claude has no ambiguities after research
- **THEN** Claude proceeds directly to writing the plan

## MODIFIED Requirements

### Requirement: Skill instructs Claude to handle Codex feedback
The skill SHALL instruct Claude that after writing `docs/plan.md`, the PostToolUse hook will run Codex review. If Claude receives a `decision: "block"` response with Codex feedback, Claude SHALL:
1. Read the annotated plan markdown at the path provided in `additionalContext`
2. Evaluate each inline comment against the actual code
3. Revise `docs/plan.md` to address valid issues
4. Write the revised plan (which re-triggers the hook)

#### Scenario: Claude receives Codex rejection feedback
- **WHEN** the hook blocks with Codex feedback
- **THEN** Claude reads the annotated plan markdown, evaluates inline comments against code, and revises the plan

#### Scenario: Claude receives Codex approval
- **WHEN** the hook allows (Codex approved)
- **THEN** Claude asks the user "The plan has been approved by Codex. Ready to execute?"

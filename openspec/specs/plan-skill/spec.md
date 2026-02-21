# plan-skill Specification

## Purpose
TBD - created by archiving change codex-plan-review-hook. Update Purpose after archive.
## Requirements
### Requirement: Skill file at project-local path
The system SHALL provide a Claude Code skill file at `.claude/skills/plan-with-review.md` invokable via `/plan-with-review`.

#### Scenario: Skill is invokable
- **WHEN** the user types `/plan-with-review` in Claude Code
- **THEN** the skill is loaded and Claude follows its instructions

### Requirement: Skill instructs Claude to read strategy input
The skill SHALL instruct Claude to read the strategy document (path provided as argument or defaulting to `docs/strategy.md`) before drafting the plan.

#### Scenario: Strategy doc provided as argument
- **WHEN** the user invokes `/plan-with-review docs/my-strategy.md`
- **THEN** Claude reads `docs/my-strategy.md` as the strategy input

#### Scenario: Default strategy path
- **WHEN** the user invokes `/plan-with-review` with no argument
- **THEN** Claude reads `docs/strategy.md` as the strategy input

### Requirement: Skill instructs Claude to research the codebase
The skill SHALL instruct Claude to use available tools (Grep, Glob, Read, Bash read-only commands, MCP servers) to thoroughly research the codebase before writing the plan. Claude SHALL NOT write the plan before understanding the relevant code.

#### Scenario: Claude researches before writing
- **WHEN** the skill is invoked
- **THEN** Claude uses codebase exploration tools before producing `docs/plan.md`

### Requirement: Skill enforces required plan format
The skill SHALL specify that `docs/plan.md` MUST contain these sections in order: `## Goal`, `## Context`, `## Approach`, `## Changes`, `## Risks`, `## Open Questions`.

#### Scenario: Plan written with required sections
- **WHEN** Claude writes `docs/plan.md`
- **THEN** the file contains all 6 required section headings

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

### Requirement: Skill instructs Claude to stop after approval
After Codex approves the plan, the skill SHALL instruct Claude to present the final plan to the user and ask "Ready to execute?" Claude SHALL NOT begin implementation. The user can then `/clear` context and invoke `/implement-approved-plan`.

#### Scenario: Claude stops after approval
- **WHEN** Codex approves the plan
- **THEN** Claude presents the plan summary and asks the user to confirm, without starting implementation

### Requirement: Skill instructs Claude on max revision behavior
The skill SHALL instruct Claude that if the hook reports the max revision threshold has been reached, Claude SHALL stop revising, explain the situation to the user, and list the remaining unresolved issues from the latest Codex review.

#### Scenario: Max revisions reached
- **WHEN** the hook reports revision threshold exceeded
- **THEN** Claude stops revising and presents the impasse to the user with remaining issues

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


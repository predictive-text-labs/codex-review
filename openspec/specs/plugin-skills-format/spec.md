# plugin-skills-format Specification

## Purpose
TBD - created by archiving change plugin-restructure. Update Purpose after archive.
## Requirements
### Requirement: Skills use directory format
Each skill SHALL be a directory under `plugin/skills/` containing a `SKILL.md` file, replacing the flat `skills/<name>.md` format.

#### Scenario: plan-with-review skill structure
- **WHEN** the plugin directory is inspected
- **THEN** `plugin/skills/plan-with-review/SKILL.md` EXISTS and `plugin/skills/plan-with-review.md` does NOT exist

#### Scenario: implement-approved-plan skill structure
- **WHEN** the plugin directory is inspected
- **THEN** `plugin/skills/implement-approved-plan/SKILL.md` EXISTS and `plugin/skills/implement-approved-plan.md` does NOT exist

### Requirement: Skill frontmatter uses description field
Skill SKILL.md files SHALL use `description` in frontmatter (not `name`). The skill name is derived from the directory name.

#### Scenario: plan-with-review frontmatter
- **WHEN** `plugin/skills/plan-with-review/SKILL.md` frontmatter is parsed
- **THEN** it SHALL contain a `description` field and SHALL NOT contain a `name` field

#### Scenario: implement-approved-plan frontmatter
- **WHEN** `plugin/skills/implement-approved-plan/SKILL.md` frontmatter is parsed
- **THEN** it SHALL contain a `description` field and SHALL NOT contain a `name` field


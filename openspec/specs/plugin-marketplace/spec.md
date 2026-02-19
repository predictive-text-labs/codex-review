# plugin-marketplace Specification

## Purpose
TBD - created by archiving change plugin-restructure. Update Purpose after archive.
## Requirements
### Requirement: Marketplace manifest at repo root
The repository SHALL have a `.claude-plugin/marketplace.json` at the repo root defining a marketplace with the plugin as an entry.

#### Scenario: Valid marketplace manifest exists
- **WHEN** the repo root is inspected
- **THEN** `.claude-plugin/marketplace.json` EXISTS and is valid JSON with `name`, `owner`, and `plugins` fields

### Requirement: Marketplace references plugin via relative path
The marketplace manifest SHALL reference the plugin using a relative path source (`"./plugin"`).

#### Scenario: Plugin source is relative path
- **WHEN** the `plugins` array in `marketplace.json` is inspected
- **THEN** there SHALL be exactly one entry with `"source": "./plugin"` and `"name": "codex-plan-review"`

### Requirement: Marketplace is installable
Users SHALL be able to add the marketplace and install the plugin using standard Claude Code commands.

#### Scenario: Marketplace add and plugin install
- **WHEN** a user runs `/plugin marketplace add <repo-url>`
- **AND** then runs `/plugin install codex-plan-review@codex-plan-review`
- **THEN** the plugin SHALL be installed with its hooks, skills, and schema available

### Requirement: Marketplace validates cleanly
The marketplace SHALL pass `claude plugin validate .` without errors.

#### Scenario: Validation passes
- **WHEN** `claude plugin validate .` is run from the repo root
- **THEN** it SHALL exit with zero status and no errors


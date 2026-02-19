## ADDED Requirements

### Requirement: Plugin manifest file
The plugin SHALL have a manifest at `plugin/.claude-plugin/plugin.json` containing `name`, `description`, and `version` fields as valid JSON.

#### Scenario: Valid manifest exists
- **WHEN** the plugin directory is inspected
- **THEN** `plugin/.claude-plugin/plugin.json` EXISTS and is valid JSON with `name`, `description`, and `version` string fields

### Requirement: Hook configuration file
The plugin SHALL have a `plugin/hooks/hooks.json` file defining all hook registrations using `${CLAUDE_PLUGIN_ROOT}` for script paths.

#### Scenario: hooks.json defines PostToolUse hooks
- **WHEN** `hooks.json` is parsed
- **THEN** it SHALL contain a `PostToolUse` array with entries for `Write|Edit` (plan_review.py, timeout 600) and `Bash` (bash_drift_check.py, timeout 30)

#### Scenario: hooks.json defines PreToolUse hooks
- **WHEN** `hooks.json` is parsed
- **THEN** it SHALL contain a `PreToolUse` array with an entry for `Write|Edit|Bash` (enforce_approval.py, timeout 10)

#### Scenario: Hook commands use plugin root variable
- **WHEN** any hook command in `hooks.json` is inspected
- **THEN** the command path SHALL use `${CLAUDE_PLUGIN_ROOT}/hooks/<script>` format

### Requirement: Schema co-located with hooks
The Codex review schema SHALL be located at `plugin/hooks/codex_review_schema.json` and the `plugin/schemas/` directory SHALL NOT exist.

#### Scenario: Schema file in hooks directory
- **WHEN** the plugin directory is inspected
- **THEN** `plugin/hooks/codex_review_schema.json` EXISTS and `plugin/schemas/` does NOT exist

### Requirement: Script-relative schema resolution
`plan_review.py` SHALL resolve the schema path relative to its own `__file__` location, not relative to cwd.

#### Scenario: Schema path uses __file__
- **WHEN** `plan_review.py` resolves the schema path
- **THEN** it SHALL use `Path(__file__).parent / "codex_review_schema.json"`

## ADDED Requirements

### Requirement: Bootstrap uses --plugin-dir
`bootstrap.sh` SHALL launch Claude Code with `--plugin-dir "$PLUGIN_DIR"` instead of manually copying files and generating settings.json.

#### Scenario: Claude launched with plugin-dir flag
- **WHEN** `bootstrap.sh` executes the final launch command
- **THEN** it SHALL run `exec claude --plugin-dir "$PLUGIN_DIR"` where `$PLUGIN_DIR` is the plugin directory path

### Requirement: Bootstrap removes file-copying logic
`bootstrap.sh` SHALL NOT copy hooks, skills, schema, or generate `settings.json` into the worktree. It SHALL only handle prerequisite validation, worktree creation, and Claude launch.

#### Scenario: No file copying in bootstrap
- **WHEN** `bootstrap.sh` is inspected
- **THEN** it SHALL NOT contain `cp` commands for hooks, skills, or schema files
- **AND** it SHALL NOT contain `cat > ... settings.json` or equivalent settings generation

### Requirement: Bootstrap retains prerequisite validation
`bootstrap.sh` SHALL still validate that `codex` and `python3` are on PATH before proceeding.

#### Scenario: Missing codex CLI
- **WHEN** `codex` is not on PATH
- **THEN** `bootstrap.sh` SHALL exit with error message and non-zero status

#### Scenario: Missing python3
- **WHEN** `python3` is not on PATH
- **THEN** `bootstrap.sh` SHALL exit with error message and non-zero status

### Requirement: Bootstrap retains worktree creation
`bootstrap.sh` SHALL still create an isolated git worktree for the review session.

#### Scenario: Worktree created
- **WHEN** `bootstrap.sh` runs successfully
- **THEN** a git worktree SHALL be created at `.worktrees/plan-review-<timestamp>` on branch `plan-review/<timestamp>`

# worktree-bootstrap Specification

## Purpose
TBD - created by archiving change codex-plan-review-hook. Update Purpose after archive.
## Requirements
### Requirement: Bootstrap script creates isolated worktree
The system SHALL provide a `bootstrap.sh` script that creates a git worktree under `.worktrees/` with a dedicated branch.

#### Scenario: Worktree is created with dedicated branch
- **WHEN** the user runs `./bootstrap.sh`
- **THEN** a new git worktree is created at `.worktrees/plan-review-<timestamp>/` with a branch named `plan-review/<timestamp>`

### Requirement: Bootstrap installs plugin into worktree
After creating the worktree, the script SHALL copy the plugin files into the worktree's `.claude/` directory: hook scripts to `.claude/hooks/`, skills to `.claude/skills/`, schema to `.claude/hooks/`. The script SHALL generate `.claude/settings.json` with the correct hook references and timeouts.

#### Scenario: Plugin files are installed
- **WHEN** the worktree is created
- **THEN** `.claude/hooks/plan_review.py`, `.claude/hooks/enforce_approval.py`, `.claude/hooks/bash_drift_check.py`, `.claude/hooks/codex_review_schema.json`, `.claude/skills/plan-with-review.md`, and `.claude/skills/implement-approved-plan.md` exist in the worktree

#### Scenario: Settings.json is generated
- **WHEN** the worktree is created
- **THEN** `.claude/settings.json` exists with PostToolUse (matcher `"Write|Edit"`, timeout 600s), PreToolUse (matcher `"Write|Edit|Bash"`), and PostToolUse Bash drift check (matcher `"Bash"`) hook entries referencing the installed scripts

### Requirement: Bootstrap validates prerequisites
The bootstrap script SHALL verify that `codex` CLI is available on PATH and that Python 3 is available. If either is missing, the script SHALL exit with a clear error message before creating the worktree.

#### Scenario: codex CLI is missing
- **WHEN** `codex` is not found on PATH
- **THEN** the script exits with error: "codex CLI not found. Install it before running bootstrap."

#### Scenario: Python 3 is missing
- **WHEN** `python3` is not found on PATH
- **THEN** the script exits with error: "Python 3 not found. Install it before running bootstrap."

### Requirement: Bootstrap accepts optional base branch argument
The script SHALL accept an optional argument for the base branch (default: `main`).

#### Scenario: Custom base branch
- **WHEN** the user runs `./bootstrap.sh develop`
- **THEN** the worktree is created from the `develop` branch

#### Scenario: Default base branch
- **WHEN** the user runs `./bootstrap.sh` with no arguments
- **THEN** the worktree is created from the `main` branch

### Requirement: Bootstrap launches Claude Code in worktree
After installing the plugin and validating prerequisites, the script SHALL `cd` into the worktree and launch `claude`.

#### Scenario: Claude Code is launched in worktree
- **WHEN** prerequisites are validated and plugin is installed
- **THEN** the script changes directory to the worktree and executes `claude`

### Requirement: Bootstrap does not manage Codex configuration
The script SHALL NOT create, modify, or inspect `.codex/config.toml` or any Codex-specific configuration. Codex MCP server setup is the user's responsibility.

#### Scenario: No Codex config touched
- **WHEN** the bootstrap script runs
- **THEN** no `.codex/` files are created or modified

### Requirement: Bootstrap does not install to global paths
The script SHALL NOT modify any global configuration files (`~/.claude/`, `~/.codex/`, etc.).

#### Scenario: No global config modified
- **WHEN** the bootstrap script runs
- **THEN** no files under `~/` are created or modified


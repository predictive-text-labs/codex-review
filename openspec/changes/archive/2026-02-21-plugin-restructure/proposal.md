## Why

The current `plugin/` directory uses an ad-hoc structure where `bootstrap.sh` manually copies files into `.claude/` and generates `settings.json`. Claude Code plugins have a native format (`.claude-plugin/plugin.json` manifest, `hooks/hooks.json`, `skills/<name>/SKILL.md`) that handles loading automatically via `--plugin-dir`. Adopting this format eliminates the manual copy step and makes the plugin installable without a bootstrap script modifying the worktree. Additionally, Claude Code supports plugin marketplaces — the repo itself should serve as a marketplace so users can install the plugin via `/plugin marketplace add` and `/plugin install`.

## What Changes

- **BREAKING**: New plugin manifest at `plugin/.claude-plugin/plugin.json`
- **BREAKING**: Hook configuration moves from generated `settings.json` to `plugin/hooks/hooks.json` using `${CLAUDE_PLUGIN_ROOT}` variable for paths
- **BREAKING**: Skills restructured from `skills/<name>.md` to `skills/<name>/SKILL.md` with `description` frontmatter instead of `name`
- Schema file moves from `plugin/schemas/` to `plugin/hooks/` (co-located with the hook that uses it)
- `plan_review.py` schema path resolution changes from cwd-relative to `__file__`-relative
- `bootstrap.sh` removes all file-copying logic, launches Claude with `--plugin-dir`
- `plugin/schemas/` directory removed
- Root-level `.claude-plugin/marketplace.json` added so the repo itself is a plugin marketplace

## Capabilities

### New Capabilities
- `plugin-manifest`: Plugin manifest file and hooks.json configuration for native Claude Code plugin loading
- `plugin-skills-format`: Skills restructured to `skills/<name>/SKILL.md` directory format with updated frontmatter
- `plugin-bootstrap`: Simplified bootstrap script using `--plugin-dir` instead of manual file copying
- `plugin-marketplace`: Root-level marketplace manifest so the repo can be added as a marketplace and the plugin installed via `/plugin install`

### Modified Capabilities

(none - no existing specs)

## Impact

- All files under `plugin/` are affected (moves, edits, new files, deletions)
- `plugin/hooks/plan_review.py` — schema path resolution changes
- `plugin/bootstrap.sh` — major rewrite removing copy logic
- `plugin/README.md` — updated structure docs
- `plugin/tests/` — test adjustments for moved schema file
- Users of the existing bootstrap flow will need to use the new `--plugin-dir` invocation
- Root `.claude-plugin/marketplace.json` added — users can install via `/plugin marketplace add <repo>` then `/plugin install codex-plan-review@codex-plan-review`

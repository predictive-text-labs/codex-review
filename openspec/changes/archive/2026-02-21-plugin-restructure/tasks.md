## 1. Plugin Manifest, Hook Configuration & Marketplace

- [x] 1.1 Create `plugin/.claude-plugin/plugin.json` with name, description, version
- [x] 1.2 Create `plugin/hooks/hooks.json` with PostToolUse and PreToolUse hook configuration using `${CLAUDE_PLUGIN_ROOT}` paths
- [x] 1.3 Create `.claude-plugin/marketplace.json` at repo root with marketplace name, owner, and plugin entry sourced from `./plugin`

## 2. File Moves & Deletions

- [x] 2.1 Move `plugin/schemas/codex_review_schema.json` to `plugin/hooks/codex_review_schema.json`
- [x] 2.2 Delete `plugin/schemas/` directory
- [x] 2.3 Move `plugin/skills/plan-with-review.md` to `plugin/skills/plan-with-review/SKILL.md`
- [x] 2.4 Move `plugin/skills/implement-approved-plan.md` to `plugin/skills/implement-approved-plan/SKILL.md`

## 3. Skill Frontmatter Updates

- [x] 3.1 Update `plan-with-review/SKILL.md` frontmatter: remove `name`, keep `description`
- [x] 3.2 Update `implement-approved-plan/SKILL.md` frontmatter: remove `name`, keep `description`

## 4. Hook Path Resolution

- [x] 4.1 Update `plan_review.py` schema path from `Path(cwd) / ".claude" / "hooks" / "codex_review_schema.json"` to `Path(__file__).parent / "codex_review_schema.json"`

## 5. Bootstrap Script

- [x] 5.1 Remove file-copying logic from `bootstrap.sh` (hooks, skills, schema, settings.json generation)
- [x] 5.2 Change Claude launch to `exec claude --plugin-dir "$PLUGIN_DIR"`
- [x] 5.3 Keep prerequisite validation and worktree creation

## 6. Documentation & Tests

- [x] 6.1 Update `plugin/README.md` to reflect new structure, `--plugin-dir` usage, and marketplace installation
- [x] 6.2 Update test imports/paths for moved schema file

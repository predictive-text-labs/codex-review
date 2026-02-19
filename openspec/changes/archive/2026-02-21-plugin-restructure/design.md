## Context

The plugin currently uses a manual installation approach: `bootstrap.sh` copies hooks, skills, and schema into `.claude/` within a worktree and generates `settings.json`. Claude Code supports a native plugin format where a directory containing `.claude-plugin/plugin.json`, `hooks/hooks.json`, and `skills/<name>/SKILL.md` can be loaded directly via `--plugin-dir`. This eliminates the copy step entirely.

Current structure:
```
plugin/
├── bootstrap.sh          # Copies files + generates settings.json
├── hooks/*.py            # Hook scripts
├── skills/*.md           # Flat skill files
└── schemas/*.json        # Schema in separate directory
```

Target structure:
```
.claude-plugin/marketplace.json  # Marketplace manifest (repo root)
plugin/
├── .claude-plugin/plugin.json   # Plugin manifest
├── bootstrap.sh                 # Simplified: worktree + --plugin-dir
├── hooks/
│   ├── hooks.json               # Hook configuration (was settings.json)
│   ├── plan_review.py
│   ├── enforce_approval.py
│   ├── bash_drift_check.py
│   └── codex_review_schema.json # Moved from schemas/
├── skills/
│   ├── plan-with-review/SKILL.md
│   └── implement-approved-plan/SKILL.md
└── tests/
```

## Goals / Non-Goals

**Goals:**
- Adopt the Claude Code plugin format so the plugin loads natively via `--plugin-dir`
- Co-locate schema with hooks (the only consumer)
- Make `plan_review.py` schema path resolution independent of cwd
- Simplify `bootstrap.sh` to only handle worktree creation and plugin loading
- Make the repo a plugin marketplace so users can install via `/plugin marketplace add` + `/plugin install`

**Non-Goals:**
- Changing hook behavior or logic (purely structural)
- Adding new hooks or skills
- Modifying the Codex CLI invocation pattern
- Supporting backwards compatibility with the old manual install

## Decisions

### 1. Schema co-location with hooks
Move `schemas/codex_review_schema.json` into `hooks/` rather than keeping a separate directory. Only `plan_review.py` uses the schema, and it's simpler to resolve relative to `__file__` than to navigate a sibling directory.

**Alternative**: Keep `schemas/` and resolve via `Path(__file__).parent.parent / "schemas"`. Rejected because it adds unnecessary directory traversal and the schema is a hook implementation detail.

### 2. `__file__`-relative schema path in plan_review.py
Change from `Path(cwd) / ".claude" / "hooks" / "codex_review_schema.json"` to `Path(__file__).parent / "codex_review_schema.json"`. In plugin format, hooks run from the project root but the schema lives in the plugin directory, so cwd-relative paths won't work.

### 3. Hook paths use `${CLAUDE_PLUGIN_ROOT}`
In `hooks.json`, hook commands reference scripts via `${CLAUDE_PLUGIN_ROOT}/hooks/<script>`. This variable is expanded by Claude Code at runtime to the plugin directory path, making the configuration portable.

### 4. Skills use `description` frontmatter
The plugin format uses `description` (not `name`) in skill frontmatter. The skill name is derived from the directory name. Existing `name` fields are removed, `description` is kept as-is.

### 5. Repo as marketplace
The repo root gets `.claude-plugin/marketplace.json` with a single plugin entry using `"source": "./plugin"` (relative path). This means the repo is both the marketplace and the plugin host. Users add the marketplace via the repo URL, then install the plugin. The marketplace name matches the plugin name: `codex-plan-review`.

**Alternative**: Host marketplace and plugin in separate repos. Rejected because this is a single-plugin project and co-location is simpler.

## Risks / Trade-offs

- **[Breaking change]** Users with existing worktrees using the old format will need to re-bootstrap. → No migration needed since worktrees are ephemeral by design.
- **[Test adjustments]** Tests that reference `schemas/` path will break. → Update test imports; the schema is now at `hooks/codex_review_schema.json`.
- **[`--plugin-dir` availability]** If a user's Claude Code version doesn't support `--plugin-dir`, bootstrap fails. → The flag is in current Claude Code; document minimum version if needed.

## Context

Claude Code produces implementation plans that go straight to execution without independent review. The strategy calls for an automated review loop: Claude writes a plan, Codex evaluates it, and the loop repeats until Codex deems the plan optimal. This must be fully programmatic — no prompt hacks, no CLAUDE.md routing tricks, no manual copy-paste between agents.

Claude Code hooks provide lifecycle interception points that can run shell commands and return structured JSON to influence Claude's behavior. Codex CLI provides a non-interactive `exec` mode with structured output, JSON event streams, and session resume by explicit thread ID. These two systems compose naturally: a `PostToolUse` hook intercepts plan file writes, shells out to Codex CLI, and returns feedback via the hook's `decision`/`additionalContext` JSON response.

Both agents share the same git worktree, giving Codex full access to the codebase Claude is planning against. All configuration, hooks, skills, review artifacts, and Codex config live inside the project directory — nothing is installed to `~/` paths. This makes the tool portable, self-contained, and version-controllable.

## Goals / Non-Goals

**Goals:**

- Deterministic, artifact-based handoff between Claude and Codex (no prompt routing)
- Persistent Codex review sessions with explicit thread ID tracking (no `--last`)
- Structured Codex output (`is_optimal` boolean) for programmatic gating
- Versioned snapshots of each plan revision and Codex annotation for auditability
- Clean terminal state: Claude asks "ready to execute?" only after Codex approves
- Isolated worktree so the review workflow doesn't pollute the main branch

**Non-Goals:**

- Real-time streaming of Codex review progress to Claude (batch result is sufficient)
- Codex making code changes (Codex is reviewer only, not implementer)
- Supporting multiple concurrent review loops in the same worktree
- MCP-based Codex invocation from within Claude (hooks call Codex CLI directly)
- Automatic plan execution after approval (user must explicitly consent)

## Decisions

### D1: PostToolUse hook on Write|Edit, not TaskCompleted

**Choice**: Use `PostToolUse` with matcher `"Write|Edit"` to detect plan file changes.

**Alternatives considered**:
- `TaskCompleted`: Only supports exit-code blocking (no `additionalContext` injection). Requires Claude to emit a specific task as a signal, which is brittle — Claude may create extra tasks, skip tasks, or fail to re-complete after revision. Has no matcher filtering.
- `Stop` hook: Fires on every Claude response, not just plan writes. Would need complex filtering and risks infinite loops.

**Rationale**: `PostToolUse` fires after Claude writes `plan.md`, which is the exact artifact boundary we care about. It supports the full JSON decision protocol: `decision: "block"` + `reason` + `hookSpecificOutput.additionalContext`. The matcher `"Write|Edit"` scopes it to file operations. The hook script resolves `tool_input.file_path` to an absolute path and compares it to `<repo_root>/docs/plan.md` (using `os.path.realpath` to handle symlinks and `..` traversal). Simple `endswith()` is insufficient — it would match `nested/docs/plan.md` in subdirectories.

### D2: Codex CLI exec with --json + --output-schema, not codex-mcp-server

**Choice**: Call `codex exec` directly from the hook script.

**Alternatives considered**:
- `codex-mcp-server`: Sessions are in-memory per server process. If the MCP server restarts, sessions are lost. Also, hooks cannot invoke MCP tools — they can only run shell commands.
- `codex mcp-server` (official): Known resume limitations where the MCP interface can't find sessions that the CLI can.

**Rationale**: Direct CLI invocation is the most reliable path. `--json` gives us the `thread.started` event with `thread_id` for persistence. `--output-schema` ensures Codex returns machine-parseable JSON. The hook script is a shell command, so CLI is the natural interface.

### D3: Explicit thread ID persistence, never --last

**Choice**: Capture `thread_id` from the `thread.started` JSON event on first run, store it in `.claude/review/codex_thread_id` (project-local), and use `codex exec resume <THREAD_ID>` on subsequent runs. The hook SHALL parse both stdout and stderr for JSONL events (Codex `--json` mode emits events on stdout, but progress/errors may appear on stderr). The parsing must be stream-agnostic: scan all lines from both streams for valid JSON objects with `"type": "thread.started"`.

**Alternatives considered**:
- `--last`: Non-deterministic in multi-worktree setups. "Latest" depends on what else has run.
- Session name files in Codex's own `~/.codex/sessions/`: Global, implementation-specific, could change, and breaks the "everything in project" constraint.

**Rationale**: Explicit IDs stored in the project directory are deterministic regardless of concurrent worktrees or other Codex sessions running on the machine. Project-local storage means the state is portable and inspectable.

### D4: Hook script in Python, not bash

**Choice**: Python 3 for the hook script (`.claude/hooks/plan_review.py`).

**Alternatives considered**:
- Bash: Parsing JSON event streams line-by-line in bash is fragile. Capturing `thread_id` from JSONL stderr while reading structured output from a file requires careful fd management.
- Node.js: Would work but adds a runtime dependency beyond what's already needed.

**Rationale**: Python's `json` module, `subprocess`, and `pathlib` make the hook logic straightforward. Python 3 is near-universal on macOS/Linux. The hook needs to: parse JSON stdin, read a plan file, run a subprocess, parse JSONL stderr, parse JSON output, and return JSON stdout — all natural in Python.

### D5: Plan file at a fixed canonical path

**Choice**: `docs/plan.md` is the single source of truth. The hook detects writes to this path.

**Rationale**: A fixed path makes the trigger deterministic. The hook resolves `tool_input.file_path` to an absolute path and compares it to `<cwd>/docs/plan.md` (the `cwd` field from hook input). It ignores all other Write/Edit operations. Claude is instructed to write plans to this location.

### D6: Versioned snapshots in .claude/review/

**Choice**: Before each Codex review, the hook copies `docs/plan.md` to `.claude/review/plan_v{N}.snapshot.md`. Codex output goes to `.claude/review/plan_v{N}.codex.json` and `.claude/review/plan_v{N}.annotated.md`.

**Rationale**: Auditability. You can trace the evolution of the plan and see exactly what Codex said at each revision. The version counter is stored in `.claude/review/version_counter` (simple integer file).

**version_counter lifecycle**: The counter resets to 0 when `approval.json` is deleted (which happens on the first new write to `docs/plan.md` after a previous approval). This ties the counter to a planning cycle: each fresh planning cycle starts at v0, increments on each Codex review, and resets when the next cycle begins. In a new worktree, the counter starts at 0 because `.claude/review/` is empty. The counter is never carried across planning cycles.

### D7: Worktree bootstrap as a standalone shell script

**Choice**: A `bootstrap.sh` script that creates a git worktree, copies/installs the plugin files (`.claude/hooks/`, `.claude/skills/`, `.claude/settings.json`), validates prerequisites, and launches Claude Code in the worktree.

**Rationale**: The bootstrap is the plugin's install-and-run entry point. It copies the plugin's hook scripts and skills into the worktree's `.claude/` directory, writes the `.claude/settings.json` that references them, validates that `codex` and `python3` are on PATH, and launches Claude. It does NOT manage Codex config (`.codex/config.toml`) — that's the user's responsibility.

### D8: Two skills — skill = guidance, hook = guarantee

**Choice**: Two Claude Code skills with distinct responsibilities:

1. **`/plan-with-review`** (`.claude/skills/plan-with-review.md`) — the planning skill. Guides Claude to:
   - Read the strategy doc
   - Research the codebase
   - Write `docs/plan.md` with required sections: `## Goal`, `## Context`, `## Approach`, `## Changes` (file-level detail), `## Risks`, `## Open Questions`
   - Handle Codex feedback revisions (read `.claude/review/plan_vN.codex.json`, evaluate each claim against the code, revise)
   - When Codex approves, ask the user "ready to execute?"

2. **`/implement-approved-plan`** (`.claude/skills/implement-approved-plan.md`) — the implementation skill. First step:
   - Read `docs/plan.md` and `.claude/review/approval.json`
   - Validate that `approval.json.plan_hash` matches the SHA-256 of current `docs/plan.md`
   - Confirm `approval.json.is_optimal` is `true`
   - If mismatch or not approved → stop and tell Claude to run `/plan-with-review`
   - If valid → proceed with implementation following the plan

**Alternatives considered**:
- Single skill: Combining planning and implementation in one skill bloats context and makes it impossible to `/clear` between phases. Separate skills let you clear context after planning and start implementation fresh.
- CLAUDE.md instructions: Always-on, pollutes every session, violates the "no prompt hacks" constraint.

**Rationale**: Skills are guidance — they tell Claude *how* to do the right thing. But skills can be bypassed (user could just type "implement the plan" without invoking the skill). The hooks (D9) are the guarantee layer that enforces correctness regardless of how Claude is invoked.

### D9: approval.json as the structured approval record

**Choice**: When Codex returns `is_optimal: true`, the PostToolUse hook writes `.claude/review/approval.json`:

```json
{
  "is_optimal": true,
  "plan_hash": "<SHA-256 of docs/plan.md>",
  "review_version": 3,
  "approved_at": "2026-02-20T14:30:00Z",
  "codex_thread_id": "<thread UUID>"
}
```

**Lifecycle**:
- **Created**: By the PostToolUse hook when Codex approves.
- **Invalidated**: On the next write to `docs/plan.md`, the PostToolUse hook deletes `approval.json` before running Codex review. Any plan edit invalidates the previous approval.
- **Validated**: By the PreToolUse hook (D10) and the `/implement-approved-plan` skill. Both check that the file exists, `is_optimal` is `true`, and `plan_hash` matches the SHA-256 of the current `docs/plan.md`.

This replaces the simple sentinel file — it's machine-readable, auditable, and carries enough metadata for both skills and hooks to validate against.

### D10: PreToolUse gate — the hard guarantee

**Choice**: A `PreToolUse` hook on `Write|Edit|Bash` that enforces approval before any mutation.

**Write|Edit rules** (before approval):
- `docs/plan.md` → always allowed (planning phase)
- `.claude/review/*` → **always denied** for Claude. The entire `.claude/review/` directory is hook-owned. Only hook scripts (external processes) write here. This prevents Claude from tampering with `approval.json`, `version_counter`, `codex_thread_id`, snapshots, or review outputs. Claude can still *read* these files via the Read tool (which is not gated).
- All other paths → denied unless `approval.json` is valid

**Bash rules** (before approval) — read-only allowlist:
- Reject any command containing shell write operators: `|`, `;`, `&&`, `||`, `>`, `>>`, `<`, `$(`, backticks
- Allow only known read-only first-token commands: `rg`, `grep`, `ls`, `cat`, `head`, `tail`, `wc`, `file`, `git` (with read-only subcommands: `status`, `diff`, `show`, `log`, `rev-parse`, `grep`, `branch`)
- Block interpreters and writers: `python`, `node`, `bash`, `sh`, `sed`, `awk`, `tee`, `xargs`, `npm`, `touch`, `mv`, `cp`, `rm`, `mkdir`, etc.
- After approval, all Bash commands are allowed

**PostToolUse drift check on Bash**: After any Bash command executes, check if files outside `docs/plan.md` and `.claude/review/` were modified (via `git status --porcelain`). If unexpected file changes detected, block and tell Claude to revert or ask the user.

**Rationale**: Bash is a write channel — `echo "..." > file`, `sed -i`, `python -c "..."` can all bypass Write|Edit gating. The read-only allowlist closes this hole while still letting Claude research the codebase during planning. The `.claude/review/` write-deny rule prevents Claude from tampering with any control-state artifacts: `approval.json`, `version_counter`, `codex_thread_id`, snapshots, and review outputs. Only hook scripts (running as external processes, not as Claude) can write to this directory.

## Risks / Trade-offs

**[Hook timeout]** Codex review can take 2-10+ minutes depending on plan complexity and codebase size.
→ Set hook timeout to 600s (10 min). If Codex consistently exceeds this, the hook fails and Claude gets an error message. User can increase timeout or simplify the review prompt.

**[Codex resume degradation]** There are reports that Codex resume can lose context in certain situations.
→ The hook always includes the full plan text in the prompt, so even if Codex's memory of prior turns degrades, it has the complete current plan. The resume is primarily for maintaining the "reviewer persona" context, not for remembering the plan itself.

**[PostToolUse cannot undo writes]** By the time the hook fires, Claude has already written plan.md. The hook can only feed back.
→ This is actually fine. We *want* the plan to be written. The hook's job is to evaluate it and tell Claude to revise if needed. The plan file is the artifact boundary.

**[False triggers]** Claude might write to other files matching `Write|Edit` that aren't the plan.
→ The hook resolves the absolute path from `tool_input.file_path` and compares to `<cwd>/docs/plan.md`. No substring matching — exact resolved path only. All other files exit 0 (allow, no-op).

**[Codex CLI availability]** The hook assumes `codex` is on PATH.
→ The bootstrap script validates this upfront. If codex is missing, the bootstrap fails before launching Claude.

**[Infinite revision loops]** If Codex never approves, the loop runs forever.
→ Fail closed by default: the hook never auto-approves a non-optimal plan. After a configurable threshold (default: 5 revisions), the hook blocks and tells Claude to stop revising and present the situation to the user. The user can manually write `approval.json` with `is_optimal: true` and the correct `plan_hash` to force-approve, but this requires deliberate action. No silent bypass.

**[MCP server configuration]** Codex benefits from MCP servers (Serena, Context7, Convex) for deep code review, but configuring them is the user's responsibility. The plugin does not manage `.codex/config.toml`.
→ The bootstrap script warns if `codex` is not on PATH, but does not inspect or modify Codex's own configuration.

## Open Questions

- **Codex model selection**: Should the bootstrap script pin a specific Codex model (e.g., `o3`), or use whatever the user has configured?

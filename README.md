# Codex Plan Review

A Claude Code plugin that adds an automated review loop: Claude writes an implementation plan, Codex CLI evaluates it for accuracy and optimality, and the loop repeats until Codex approves. Once approved, implementation is gated behind the approved plan — Claude can only write code that was reviewed.

## Why

LLM-generated plans can contain inaccurate claims about the codebase, miss edge cases, or propose suboptimal approaches. This plugin adds a second model (Codex) as an automated reviewer that validates plan claims against the actual code before any implementation begins.

The review is enforced at the hook level — Claude physically cannot write files other than the plan until Codex approves it.

## How It Works

```
User invokes /plan-with-review
        │
        ▼
Claude researches codebase, writes docs/plan.md
        │
        ▼
PostToolUse hook sends plan to Codex CLI ◄──┐
        │                                   │
        ▼                                   │
   Codex reviews                            │
        │                                   │
    ┌───┴───┐                               │
    ▼       ▼                               │
Approved  Rejected ─── Claude revises ──────┘
    │
    ▼
approval.json written (hash-locked to plan)
    │
    ▼
User runs /implement-approved-plan
    │
    ▼
PreToolUse hook validates approval, unlocks file writes
    │
    ▼
Claude implements the approved plan
```

## Quick Start

Prerequisites: [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Codex CLI](https://github.com/openai/codex) (`codex` on PATH), Python 3.

```bash
# Launch Claude Code with the plugin
claude --plugin-dir ./plugin

# Then inside Claude Code:
/codex-plan-review:plan-with-review            # plan from docs/strategy.md
/codex-plan-review:plan-with-review path.md    # plan from a specific file
/codex-plan-review:plan-with-review add auth   # plan from free-text description

# After approval:
/codex-plan-review:implement-approved-plan
```

See [plugin/README.md](plugin/README.md) for full installation options, plugin structure, and runtime artifacts.

## Project Structure

```
├── plugin/                  # Claude Code plugin (hooks, skills, tests)
├── openspec/                # Specifications (OpenSpec format)
└── docs/                    # Runtime artifacts (plan.md, generated at runtime)
```

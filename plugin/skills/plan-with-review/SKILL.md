---
description: Create an implementation plan that will be reviewed by Codex. Guides you through reading strategy, researching the codebase, writing a structured plan to docs/plan.md, and handling the Codex review feedback loop.
---

# Plan with Codex Review

You are creating an implementation plan that will be automatically reviewed by Codex CLI via a PostToolUse hook. Follow these steps exactly.

## Step 1: Read the Strategy

Read the strategy document to understand what needs to be planned.

- If an argument was provided (e.g., `/plan-with-review docs/my-strategy.md`), read that file.
- If no argument was provided, read `docs/strategy.md`.
- If the strategy file doesn't exist, ask the user where the strategy document is.

## Step 2: Research the Codebase

Before writing ANY plan, thoroughly research the codebase to understand:

- The current architecture and code structure
- Existing patterns and conventions
- Files that will be affected by the changes
- Dependencies and integration points
- Potential risks and edge cases

Use all available tools: Grep, Glob, Read, and read-only Bash commands (e.g., `git log`, `git diff`, `ls`, `rg`). Use MCP servers if available.

**Do NOT write the plan until you have a thorough understanding of the relevant code.**

## Step 3: Write the Plan

Write your plan to `docs/plan.md`. The plan MUST contain these sections in this order:

```
## Goal
What this plan achieves. One paragraph.

## Context
Relevant codebase context that informs the approach. Reference specific files and patterns.

## Approach
High-level architectural approach. Why this approach over alternatives.

## Changes
File-level detail of what changes. For each file:
- What changes and why
- New files to create
- Dependencies affected

## Risks
What could go wrong. Mitigation strategies.

## Open Questions
Unresolved questions that need user input.
```

All six sections are required. The PostToolUse hook will reject the plan if any are missing.

## Step 4: Handle Codex Review Feedback

After you write `docs/plan.md`, the PostToolUse hook will automatically:
1. Snapshot your plan
2. Send it to Codex CLI for review
3. Return the result

**If Codex rejects the plan** (you receive a `decision: "block"` response):
1. Read the Codex review JSON at the path provided in the feedback.
2. For EACH blocking issue, evaluate the claim against the actual code. Do not blindly accept or dismiss.
3. Revise `docs/plan.md` to address valid issues.
4. Write the revised plan (this re-triggers the review automatically).

**If the max revision threshold is reached** (you receive a message about revision limit):
1. STOP revising immediately.
2. Explain to the user that the plan has been revised multiple times without reaching approval.
3. List the remaining unresolved issues from the latest Codex review.
4. Let the user decide how to proceed.

## Step 5: After Codex Approval

When Codex approves your plan:
1. Present a summary of the final plan to the user.
2. Ask: **"The plan has been reviewed and approved by Codex. Ready to execute?"**
3. Do NOT begin implementation.
4. The user can `/clear` context and then run `/implement-approved-plan` to start implementation.

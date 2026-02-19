---
description: Implement an approved plan. Validates that approval.json exists and matches the current plan hash before proceeding with implementation.
---

# Implement Approved Plan

You are implementing a plan that has been reviewed and approved by Codex. Follow these steps exactly.

## Step 1: Validate Approval

Before writing ANY code, validate the approval:

1. Read `docs/plan.md`.
2. Read `.claude/review/approval.json`.
3. Compute the SHA-256 hash of `docs/plan.md` content.
4. Compare the computed hash to `approval.json.plan_hash`.
5. Verify `approval.json.is_optimal` is `true`.

**You can compute the SHA-256 hash with:** `sha256sum docs/plan.md` or `shasum -a 256 docs/plan.md`

### If approval.json is MISSING:
Stop and tell the user:
> "No approved plan found. Run `/plan-with-review` first to create and get approval for a plan."

### If plan_hash does NOT match:
Stop and tell the user:
> "The plan has been modified since it was approved. The approval is no longer valid. Run `/plan-with-review` to re-approve the current plan."

### If is_optimal is FALSE:
Stop and tell the user:
> "The plan was not approved as optimal by Codex. Run `/plan-with-review` to complete the review process."

## Step 2: Implement the Plan

Once approval is validated:

1. Read `docs/plan.md` carefully, focusing on:
   - `## Approach` for architectural guidance
   - `## Changes` for file-level implementation detail
   - `## Risks` for things to watch out for

2. Implement the changes described in the plan:
   - Follow the file-level detail in `## Changes`
   - Respect the architectural approach in `## Approach`
   - Keep changes focused and minimal
   - Write tests where appropriate

3. Work through the changes systematically, one file/component at a time.

## Important Notes

- This skill operates solely on artifacts (`docs/plan.md` and `approval.json`). It does NOT depend on the planning skill having been invoked in the same session.
- You can `/clear` context between planning and implementation.
- The PreToolUse hook independently validates approval for every Write|Edit operation — this skill validation is an additional safety layer, not the only one.

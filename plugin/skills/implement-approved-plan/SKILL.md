---
description: Implement an approved plan. Validates that approval.json exists and matches the current plan hash before proceeding with implementation.
---

# Implement Approved Plan

You are implementing a plan that has been reviewed and approved by Codex. Follow these steps exactly.

## Step 1: Validate Approval

Before writing ANY code, run the validation script:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/hooks/validate_approval.py
```

Parse the JSON output:
- If `{"valid": true}` — proceed to Step 2.
- If `{"valid": false, "reason": "..."}` — stop and show the `reason` to the user. Do NOT proceed.

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

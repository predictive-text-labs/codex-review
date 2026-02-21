## Why

The plugin skills contain procedural steps that ask Claude to manually execute deterministic logic (SHA-256 hash computation, file existence checks, JSON parsing). This is fragile — an LLM can get these wrong. Meanwhile, the hooks contain feedback instructions that point Claude to raw JSON files when a better artifact (the annotated plan) already exists. Several hooks also have behavioral issues: `bash_drift_check.py` blocks during implementation, `enforce_approval.py` fails open on malformed input, and the `plan-with-review` skill doesn't prompt users to resolve Open Questions before triggering Codex review.

## What Changes

- Extract approval validation into a standalone script that `implement-approved-plan` skill invokes instead of manual 5-step procedure
- Change `plan_review.py` rejection feedback to point Claude to the annotated plan markdown instead of raw Codex JSON
- Make `bash_drift_check.py` approval-aware: skip drift detection when a valid approval exists (implementation phase)
- Make `enforce_approval.py` fail closed (deny) on malformed hook input instead of failing open (allow)
- Update `plan-with-review` skill Step 3 to instruct Claude to ask the user about Open Questions before writing the plan
- Clean up old review artifacts in `plan_review.py` `invalidate_approval()` when a new planning cycle begins

## Capabilities

### New Capabilities
- `approval-validation-cli`: Standalone script that validates approval.json against docs/plan.md and returns structured JSON result

### Modified Capabilities
- `plan-review-hook`: Change rejection feedback to reference annotated plan instead of raw JSON; clean up old artifacts on invalidation
- `implement-skill`: Replace manual validation steps with script invocation
- `plan-skill`: Add Open Questions checkpoint before writing the plan

## Impact

- `plugin/hooks/plan_review.py` — feedback text changes, artifact cleanup in `invalidate_approval()`
- `plugin/hooks/enforce_approval.py` — fail-closed default, allowlist addition
- `plugin/hooks/bash_drift_check.py` — approval-aware skip logic
- `plugin/skills/plan-with-review/SKILL.md` — Open Questions step
- `plugin/skills/implement-approved-plan/SKILL.md` — script-based validation
- New file: `plugin/hooks/validate_approval.py`

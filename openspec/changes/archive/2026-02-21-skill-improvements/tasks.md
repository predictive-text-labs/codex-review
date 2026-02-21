## 1. Approval Validation Script

- [x] 1.1 Create `plugin/hooks/validate_approval.py` that reads `approval.json` and `docs/plan.md`, compares SHA-256 hashes, and outputs `{"valid": true}` or `{"valid": false, "reason": "..."}` to stdout
- [x] 1.2 Add tests for `validate_approval.py` covering: valid approval, missing approval.json, missing plan.md, hash mismatch, is_optimal false

## 2. Hook Fixes

- [x] 2.1 In `enforce_approval.py`, change the malformed-input catch block to output deny instead of allow
- [x] 2.1b In `enforce_approval.py`, allowlist `python3 ...validate_approval.py` in `check_bash_command()` so it's not blocked before approval
- [x] 2.2 In `bash_drift_check.py`, add approval validation check at the top of `main()` — if valid approval exists, exit silently (skip drift detection)
- [x] 2.4 In `plan_review.py` `invalidate_approval()`, add cleanup of `plan_v*.snapshot.md`, `plan_v*.codex.json`, and `plan_v*.annotated.md` files
- [x] 2.5 In `plan_review.py` rejection feedback, change `additionalContext` to reference annotated plan as primary artifact and raw JSON as secondary fallback
- [x] 2.6 In `plan_review.py` rejection feedback, add fallback for empty `annotated_plan_markdown` — use raw JSON path as primary if annotated plan is empty

## 3. Skill Updates

- [x] 3.1 Update `implement-approved-plan/SKILL.md` Step 1 to run `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/validate_approval.py` and parse JSON output instead of manual 5-step procedure
- [x] 3.2 Update `plan-with-review/SKILL.md` to add Open Questions checkpoint between Step 2 (Research) and Step 3 (Write the Plan)
- [x] 3.3 Update `plan-with-review/SKILL.md` Step 4 to instruct Claude to read the annotated plan markdown instead of the raw Codex JSON

## 4. Tests

- [x] 4.1 Update `test_enforce_approval.py` to verify deny on malformed input
- [x] 4.2 Update `test_bash_drift_check.py` to verify skip when valid approval exists
- [x] 4.3 Update `test_plan_review.py` to verify artifact cleanup in `invalidate_approval()`
- [x] 4.4 Update `test_plan_review.py` to verify annotated plan referenced in rejection feedback

## Context

The codex-plan-review plugin has two skills and three hooks. During review we identified several issues:
1. The `implement-approved-plan` skill asks Claude to manually compute SHA-256 hashes and compare them — deterministic logic that should be a script
2. The `plan_review.py` hook tells Claude to read raw Codex JSON on rejection, when the annotated plan markdown is a better artifact for revision
3. `bash_drift_check.py` blocks during implementation because it doesn't check approval state
4. `enforce_approval.py` fails open on malformed hook input
5. The `plan-with-review` skill doesn't prompt users to resolve Open Questions before Codex review
6. Old review artifacts accumulate across planning cycles
7. `sha256sum`/`shasum` are not in the Bash allowlist

## Goals / Non-Goals

**Goals:**
- Make deterministic procedures script-based instead of LLM-executed
- Fix hook behavioral issues (drift check, fail-open, allowlist)
- Improve the feedback loop by using annotated plans instead of raw JSON
- Add an Open Questions checkpoint to the planning skill
- Clean up stale review artifacts between cycles

**Non-Goals:**
- Changing the Codex review schema or prompt
- Modifying the plugin manifest or bootstrap script
- Adding new skills or hooks
- Changing the plan section format

## Decisions

### D1: Standalone validation script vs. CLI mode on enforce_approval.py

**Decision**: Create a new `validate_approval.py` script.

**Rationale**: `enforce_approval.py` is a PreToolUse hook with a specific I/O contract (reads stdin JSON, writes stdout JSON). Adding a `--check` CLI mode would mix two concerns. A standalone script has a clear contract: exit 0 + JSON `{"valid": true}` on success, exit 0 + JSON `{"valid": false, "reason": "..."}` on failure. The validation logic (`validate_approval()` function) can be imported from `enforce_approval.py` to avoid duplication.

**Alternative considered**: Add `--check` flag to `enforce_approval.py`. Rejected because it conflates hook protocol with CLI tool interface.

### D2: How to reference annotated plan in rejection feedback

**Decision**: Change `plan_review.py` rejection `additionalContext` to reference the annotated plan markdown as the primary artifact. Keep the raw JSON path as a secondary reference for edge cases.

**Rationale**: The annotated plan shows Codex's feedback inline with the plan text, which is exactly what Claude needs to understand what to revise and where. The raw JSON has the same information but detached from context. Claude should read the annotated plan, not parse JSON.

### D3: How bash_drift_check.py determines implementation phase

**Decision**: Reuse the `validate_approval()` logic from `enforce_approval.py`. Import the function or duplicate the minimal check (read `approval.json`, verify `is_optimal` and `plan_hash`).

**Rationale**: If approval exists and is valid, we're in implementation phase — drift is expected because Claude is writing code. The same approval check used by enforce_approval is the right signal.

**Alternative considered**: Check for existence of `approval.json` without hash verification. Rejected because a stale/invalid approval shouldn't suppress drift detection.

### D4: Artifact cleanup strategy

**Decision**: In `invalidate_approval()`, delete all `plan_v*.snapshot.md`, `plan_v*.codex.json`, and `plan_v*.annotated.md` files from `.claude/review/` when starting a new planning cycle.

**Rationale**: These are artifacts from the previous cycle and cause confusion when version numbers restart at 1. Fresh cycle = fresh artifacts.

### D5: Open Questions checkpoint placement

**Decision**: Add guidance after Step 2 (Research) and before Step 3 (Write the Plan). If Claude identifies open questions during research, it SHALL present them to the user and wait for answers before writing the plan.

**Rationale**: Writing a plan with unresolved questions wastes a Codex review cycle. Better to resolve them upfront.

## Risks / Trade-offs

- [Importing validate_approval across scripts] → If the import path is fragile, duplicate the ~15 lines of validation logic instead. The duplication cost is low.
- [Annotated plan may be empty] → Codex could return an empty `annotated_plan_markdown`. The feedback should fall back to the summary + blocking issues already embedded in the hook output.
- [Artifact cleanup deletes review history] → Users lose the ability to compare across cycles. This is acceptable — the current cycle's artifacts are what matter, and git history preserves everything.

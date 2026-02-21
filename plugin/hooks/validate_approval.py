#!/usr/bin/env python3
"""Standalone approval validation script.

Validates that approval.json exists, is_optimal is true, and plan_hash
matches the SHA-256 of docs/plan.md. Outputs structured JSON to stdout.

Usage: python3 validate_approval.py
Exit code is always 0. Check the JSON output for {"valid": true/false}.
"""

import hashlib
import json
import sys
from pathlib import Path


def validate(cwd: str) -> dict:
    """Validate approval and return structured result."""
    review_dir = Path(cwd) / ".claude" / "review"
    approval_path = review_dir / "approval.json"
    plan_path = Path(cwd) / "docs" / "plan.md"

    if not plan_path.exists():
        return {"valid": False, "reason": "No plan file found at docs/plan.md."}

    if not approval_path.exists():
        return {
            "valid": False,
            "reason": "No approved plan found. Run /plan-with-review first to create and get approval for a plan.",
        }

    try:
        with open(approval_path) as f:
            approval = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"valid": False, "reason": "approval.json is corrupted or unreadable."}

    if not approval.get("is_optimal"):
        return {
            "valid": False,
            "reason": "The plan was not approved as optimal by Codex. Run /plan-with-review to complete the review process.",
        }

    stored_hash = approval.get("plan_hash", "")
    try:
        with open(plan_path, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return {"valid": False, "reason": "Could not read docs/plan.md to verify hash."}

    if stored_hash != actual_hash:
        return {
            "valid": False,
            "reason": "The plan has been modified since it was approved. The approval is no longer valid. Run /plan-with-review to re-approve the current plan.",
        }

    return {"valid": True}


def main():
    import os

    cwd = os.getcwd()
    result = validate(cwd)
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

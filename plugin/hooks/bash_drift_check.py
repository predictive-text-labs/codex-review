#!/usr/bin/env python3
"""PostToolUse hook: Bash Drift Check.

After any Bash command executes, checks git status for unexpected file changes
outside docs/plan.md and .claude/review/. Blocks if drift is detected.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def output_decision(decision: str, reason: str, additional_context: str = ""):
    """Print a hook decision JSON to stdout."""
    result = {}
    if decision:
        result["decision"] = decision
    if reason:
        result["reason"] = reason
    if additional_context:
        result["hookSpecificOutput"] = {"additionalContext": additional_context}
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")


def is_allowed_path(file_path: str) -> bool:
    """Check if a changed file is in an allowed location."""
    # Normalize path
    normalized = file_path.strip()

    # Allow docs/plan.md
    if normalized == "docs/plan.md":
        return True

    # Allow anything under .claude/review/
    if normalized.startswith(".claude/review/") or normalized == ".claude/review":
        return True

    return False


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    # Only check after Bash tool use
    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    cwd = hook_input.get("cwd", os.getcwd())

    # Run git status --porcelain to detect file changes
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Can't check, allow
        sys.exit(0)

    if proc.returncode != 0:
        sys.exit(0)

    # Parse changed files
    unexpected_changes = []
    for line in proc.stdout.strip().splitlines():
        if not line:
            continue
        # git status --porcelain format: XY filename
        # First two chars are status, then a space, then the filename
        if len(line) < 4:
            continue
        file_path = line[3:].strip()
        # Handle renamed files (old -> new)
        if " -> " in file_path:
            file_path = file_path.split(" -> ")[1]
        # Remove quotes if present
        file_path = file_path.strip('"')

        if not is_allowed_path(file_path):
            unexpected_changes.append(file_path)

    if unexpected_changes:
        files_list = "\n".join(f"  - {f}" for f in unexpected_changes[:20])
        output_decision(
            "block",
            "Unexpected file changes detected after Bash command.",
            f"The following files were modified outside of allowed paths "
            f"(docs/plan.md and .claude/review/):\n\n{files_list}\n\n"
            f"This may indicate unintended side effects from the Bash command. "
            f"Please revert these changes or inform the user.",
        )
    # If no unexpected changes, exit silently (allow)


if __name__ == "__main__":
    main()

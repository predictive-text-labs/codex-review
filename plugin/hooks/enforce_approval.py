#!/usr/bin/env python3
"""PreToolUse hook: Enforcement Gate.

Denies Write|Edit to non-plan files and restricts Bash commands until
a valid approval.json exists with a matching plan hash.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

# Read-only commands allowed before approval
READONLY_COMMANDS = {
    "rg",
    "grep",
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "file",
    "fd",
    "tree",
    "which",
    "echo",
    "pwd",
    "date",
    "env",
    "printenv",
}

# Git subcommands that are read-only
GIT_READONLY_SUBCOMMANDS = {
    "status",
    "diff",
    "show",
    "log",
    "rev-parse",
    "grep",
    "branch",
    "remote",
    "tag",
    "describe",
    "shortlog",
    "stash",
    "ls-files",
    "ls-tree",
    "cat-file",
}

# Interpreters and writers that are always blocked before approval
BLOCKED_COMMANDS = {
    "python",
    "python3",
    "node",
    "bash",
    "sh",
    "zsh",
    "fish",
    "sed",
    "awk",
    "tee",
    "xargs",
    "npm",
    "npx",
    "yarn",
    "pnpm",
    "bun",
    "touch",
    "mv",
    "cp",
    "rm",
    "mkdir",
    "rmdir",
    "chmod",
    "chown",
    "dd",
    "install",
    "ln",
    "mktemp",
    "perl",
    "ruby",
    "php",
    "curl",
    "wget",
    "docker",
    "kubectl",
    "make",
    "cmake",
}

# Shell operators that indicate write/pipe operations
SHELL_OPERATORS = ["|", ";", "&&", "||", ">", ">>", "<", "$(", "`"]


def output_allow():
    """Allow the tool use."""
    json.dump({}, sys.stdout)
    sys.stdout.write("\n")


def output_deny(reason: str):
    """Deny the tool use with a reason."""
    result = {
        "hookSpecificOutput": {
            "permissionDecision": "deny",
            "reason": reason,
        }
    }
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")


def validate_approval(cwd: str) -> bool:
    """Check if approval.json exists, is_optimal is true, and plan_hash matches."""
    review_dir = Path(cwd) / ".claude" / "review"
    approval_path = review_dir / "approval.json"
    plan_path = Path(cwd) / "docs" / "plan.md"

    if not approval_path.exists():
        return False
    if not plan_path.exists():
        return False

    try:
        with open(approval_path) as f:
            approval = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    if not approval.get("is_optimal"):
        return False

    stored_hash = approval.get("plan_hash", "")
    try:
        with open(plan_path, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return False

    return stored_hash == actual_hash


def is_plan_path(file_path: str, cwd: str) -> bool:
    """Check if the resolved file path is docs/plan.md."""
    resolved = os.path.realpath(
        os.path.join(cwd, file_path) if not os.path.isabs(file_path) else file_path
    )
    expected = os.path.realpath(os.path.join(cwd, "docs", "plan.md"))
    return resolved == expected


def is_review_dir_path(file_path: str, cwd: str) -> bool:
    """Check if the resolved file path is under .claude/review/."""
    resolved = os.path.realpath(
        os.path.join(cwd, file_path) if not os.path.isabs(file_path) else file_path
    )
    review_dir = os.path.realpath(os.path.join(cwd, ".claude", "review"))
    return resolved.startswith(review_dir + os.sep) or resolved == review_dir


def check_bash_command(command: str) -> str | None:
    """Check if a bash command is allowed before approval.

    Returns None if allowed, or a denial reason string if blocked.
    """
    # Check for shell operators
    for op in SHELL_OPERATORS:
        if op in command:
            return f"Bash command contains shell operator '{op}' which is not allowed before plan approval. Only simple read-only commands are permitted during planning."

    # Extract the first token (command name)
    tokens = command.strip().split()
    if not tokens:
        return None

    first_token = os.path.basename(tokens[0])

    # Allow validate_approval.py even though python3 is blocked
    if first_token in ("python", "python3") and len(tokens) >= 2:
        script = os.path.basename(tokens[1])
        if script == "validate_approval.py":
            return None

    # Check blocklist first
    if first_token in BLOCKED_COMMANDS:
        return f"Command '{first_token}' is not allowed before plan approval. Only read-only commands are permitted during planning."

    # Check git with subcommand validation
    if first_token == "git":
        if len(tokens) < 2:
            return None  # bare 'git' is fine
        subcommand = tokens[1]
        if subcommand in GIT_READONLY_SUBCOMMANDS:
            return None
        return f"git {subcommand} is not allowed before plan approval. Only read-only git subcommands are permitted: {', '.join(sorted(GIT_READONLY_SUBCOMMANDS))}"

    # Check allowlist
    if first_token in READONLY_COMMANDS:
        return None

    # Unknown command — block it
    return f"Command '{first_token}' is not in the read-only allowlist and is not allowed before plan approval."


def handle_write_edit(hook_input: dict):
    """Handle PreToolUse for Write or Edit tools."""
    cwd = hook_input.get("cwd", os.getcwd())
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        output_allow()
        return

    # Always deny writes to .claude/review/ — hook-owned directory
    if is_review_dir_path(file_path, cwd):
        output_deny(
            "The .claude/review/ directory is managed by the review hooks. "
            "You cannot write to files in this directory."
        )
        return

    # Always allow writes to docs/plan.md
    if is_plan_path(file_path, cwd):
        output_allow()
        return

    # For all other paths, check approval
    if validate_approval(cwd):
        output_allow()
    else:
        output_deny(
            "Cannot write to files other than docs/plan.md until the plan is approved. "
            "Complete the plan review process first."
        )


def handle_bash(hook_input: dict):
    """Handle PreToolUse for Bash tool."""
    cwd = hook_input.get("cwd", os.getcwd())
    tool_input = hook_input.get("tool_input", {})
    command = tool_input.get("command", "")

    # If approved, allow everything
    if validate_approval(cwd):
        output_allow()
        return

    # Before approval, enforce read-only allowlist
    denial = check_bash_command(command)
    if denial:
        output_deny(denial)
    else:
        output_allow()


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_deny("Hook received malformed input")
        return

    tool_name = hook_input.get("tool_name", "")

    if tool_name in ("Write", "Edit"):
        handle_write_edit(hook_input)
    elif tool_name == "Bash":
        handle_bash(hook_input)
    else:
        output_allow()


if __name__ == "__main__":
    main()

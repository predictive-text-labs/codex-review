#!/usr/bin/env python3
"""PostToolUse hook: Plan Review via Codex CLI.

Triggers when Claude writes/edits docs/plan.md. Sends the plan to Codex CLI
for structured review, manages persistent Codex sessions, and gates plan
completion via the hook decision protocol.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_REVISIONS = 5
REQUIRED_HEADINGS = [
    "## Goal",
    "## Context",
    "## Approach",
    "## Changes",
    "## Risks",
    "## Open Questions",
]
REQUIRED_OUTPUT_FIELDS = [
    "is_optimal",
    "blocking_issues",
    "recommended_changes",
    "annotated_plan_markdown",
    "summary",
]


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


def resolve_plan_path(hook_input: dict) -> str | None:
    """Resolve the file path from hook input and check if it's docs/plan.md."""
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return None

    cwd = hook_input.get("cwd", os.getcwd())
    resolved = os.path.realpath(os.path.join(cwd, file_path) if not os.path.isabs(file_path) else file_path)
    expected = os.path.realpath(os.path.join(cwd, "docs", "plan.md"))

    if resolved == expected:
        return resolved
    return None


def validate_plan_structure(plan_text: str) -> list[str]:
    """Check that the plan contains all required section headings."""
    missing = []
    for heading in REQUIRED_HEADINGS:
        if heading not in plan_text:
            missing.append(heading)
    return missing


def get_review_dir(cwd: str) -> Path:
    """Get the .claude/review/ directory, creating it if needed."""
    review_dir = Path(cwd) / ".claude" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    return review_dir


def invalidate_approval(review_dir: Path):
    """Delete approval.json, codex_thread_id, old review artifacts, and reset version_counter."""
    for fname in ["approval.json", "codex_thread_id"]:
        f = review_dir / fname
        if f.exists():
            f.unlink()
    # Clean up versioned artifacts from previous cycle
    for pattern in ["plan_v*.snapshot.md", "plan_v*.codex.json", "plan_v*.annotated.md"]:
        for f in review_dir.glob(pattern):
            f.unlink()
    # Reset version counter
    (review_dir / "version_counter").write_text("0")


def read_version_counter(review_dir: Path) -> int:
    """Read the current version counter, defaulting to 0."""
    counter_file = review_dir / "version_counter"
    if counter_file.exists():
        try:
            return int(counter_file.read_text().strip())
        except ValueError:
            return 0
    return 0


def increment_version_counter(review_dir: Path) -> int:
    """Increment and return the new version counter value."""
    current = read_version_counter(review_dir)
    new_val = current + 1
    (review_dir / "version_counter").write_text(str(new_val))
    return new_val


def snapshot_plan(plan_path: str, review_dir: Path, version: int):
    """Copy docs/plan.md to .claude/review/plan_v{N}.snapshot.md."""
    shutil.copy2(plan_path, review_dir / f"plan_v{version}.snapshot.md")


def get_codex_thread_id(review_dir: Path) -> str | None:
    """Read the stored Codex thread ID, if any."""
    tid_file = review_dir / "codex_thread_id"
    if tid_file.exists():
        tid = tid_file.read_text().strip()
        if tid:
            return tid
    return None


def store_codex_thread_id(review_dir: Path, thread_id: str):
    """Store the Codex thread ID."""
    (review_dir / "codex_thread_id").write_text(thread_id)


def parse_thread_id(stdout_data: bytes, stderr_data: bytes) -> str | None:
    """Scan stdout and stderr for JSONL thread.started event, extract thread_id."""
    for data in [stdout_data, stderr_data]:
        for line in data.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and obj.get("type") == "thread.started":
                    tid = obj.get("thread_id") or obj.get("id")
                    if tid:
                        return tid
            except (json.JSONDecodeError, ValueError):
                continue
    return None


def run_codex_fresh(cwd: str, schema_path: str, output_path: str, prompt: str) -> tuple[subprocess.CompletedProcess, str | None]:
    """Run a fresh codex exec --json session. Returns (process, thread_id)."""
    cmd = [
        "codex", "exec",
        "--json",
        "--cd", cwd,
        "--output-schema", schema_path,
        "-o", output_path,
        "-",
    ]
    proc = subprocess.run(
        cmd,
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=540,  # Leave margin for hook timeout
    )
    thread_id = parse_thread_id(proc.stdout, proc.stderr)
    return proc, thread_id


def run_codex_resume(cwd: str, schema_path: str, output_path: str, prompt: str, thread_id: str) -> subprocess.CompletedProcess:
    """Run codex exec resume <THREAD_ID>. Returns process."""
    cmd = [
        "codex", "exec",
        "resume", thread_id,
        "--cd", cwd,
        "--output-schema", schema_path,
        "-o", output_path,
        "-",
    ]
    return subprocess.run(
        cmd,
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=540,
    )


def build_codex_prompt(plan_text: str, version: int) -> str:
    """Build the prompt sent to Codex for plan review."""
    if version <= 1:
        intro = (
            "Maximally evaluate this plan. Is it accurate? "
            "You are to maximally evaluate the claims against the code."
        )
    else:
        intro = (
            "Here is the revised plan. Maximally evaluate this plan. Is it accurate? "
            "Moreover, is it !OPTIMAL!? You are to maximally evaluate the claims against the code. "
            "Is it solid AND !OPTIMAL! now?"
        )

    return f"""{intro}

You have no token or cost constraints. You are to MAXIMALLY evaluate this plan.

Use all available MCP servers extensively to help you do this.

--- PLAN START ---
{plan_text}
--- PLAN END ---

Return your evaluation using the provided output schema. Set is_optimal to true ONLY if the plan is solid, accurate, and optimal. Otherwise set it to false and provide detailed blocking_issues.
"""


def parse_codex_output(output_path: str) -> dict | None:
    """Parse and validate the Codex output JSON file."""
    try:
        with open(output_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return None

    for field in REQUIRED_OUTPUT_FIELDS:
        if field not in data:
            return None

    return data


def write_approval(review_dir: Path, plan_path: str, version: int, thread_id: str | None):
    """Write approval.json with plan hash and metadata."""
    with open(plan_path, "rb") as f:
        plan_hash = hashlib.sha256(f.read()).hexdigest()

    approval = {
        "is_optimal": True,
        "plan_hash": plan_hash,
        "review_version": version,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "codex_thread_id": thread_id or "",
    }
    with open(review_dir / "approval.json", "w") as f:
        json.dump(approval, f, indent=2)


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Can't parse hook input, exit silently (no-op)
        sys.exit(0)

    # Check if this is a plan.md write
    plan_path = resolve_plan_path(hook_input)
    if plan_path is None:
        # Not a plan.md write, no-op
        sys.exit(0)

    cwd = hook_input.get("cwd", os.getcwd())
    review_dir = get_review_dir(cwd)
    schema_path = str(Path(__file__).parent / "codex_review_schema.json")

    # 3.3: Invalidate previous approval if it exists
    if (review_dir / "approval.json").exists():
        invalidate_approval(review_dir)

    # Read the plan
    try:
        with open(plan_path) as f:
            plan_text = f.read()
    except OSError as e:
        output_decision("block", f"Failed to read plan file: {e}")
        sys.exit(0)

    # 3.4: Validate plan structure
    missing = validate_plan_structure(plan_text)
    if missing:
        output_decision(
            "block",
            f"Missing required sections: {', '.join(missing)}",
            "Your plan must include all required sections: "
            + ", ".join(REQUIRED_HEADINGS)
            + ". Please add the missing sections and write the plan again.",
        )
        sys.exit(0)

    # 3.5: Increment version counter and snapshot
    version = increment_version_counter(review_dir)

    # 3.10: Check max revision threshold
    if version > MAX_REVISIONS:
        output_decision(
            "block",
            f"Maximum revision threshold reached ({MAX_REVISIONS} revisions). "
            "Stop revising the plan.",
            "You have reached the maximum number of plan revisions. "
            "STOP revising the plan. Instead, present the situation to the user:\n"
            "1. Explain that the plan has been revised multiple times without reaching approval.\n"
            "2. Summarize the remaining unresolved issues from the latest Codex review.\n"
            "3. Let the user decide how to proceed (they can manually approve by creating "
            ".claude/review/approval.json with the correct plan_hash).\n"
            "Do NOT attempt another revision.",
        )
        sys.exit(0)

    snapshot_plan(plan_path, review_dir, version)

    # Build prompt
    prompt = build_codex_prompt(plan_text, version)
    output_json_path = str(review_dir / f"plan_v{version}.codex.json")

    # 3.6 + 3.12: Codex session management with resume fallback
    thread_id = get_codex_thread_id(review_dir)
    proc = None
    new_thread_id = thread_id

    try:
        if thread_id:
            # Try resume
            proc = run_codex_resume(cwd, schema_path, output_json_path, prompt, thread_id)
            if proc.returncode != 0:
                # Resume failed, fall back to fresh session
                proc, new_thread_id_fresh = run_codex_fresh(cwd, schema_path, output_json_path, prompt)
                if new_thread_id_fresh:
                    new_thread_id = new_thread_id_fresh
                    store_codex_thread_id(review_dir, new_thread_id)
        else:
            # Fresh session
            proc, new_thread_id = run_codex_fresh(cwd, schema_path, output_json_path, prompt)
            if new_thread_id:
                store_codex_thread_id(review_dir, new_thread_id)

    except subprocess.TimeoutExpired:
        output_decision(
            "block",
            "Codex CLI timed out during plan review.",
            "The Codex review process timed out. This may be due to plan complexity or "
            "Codex server issues. Please inform the user of this timeout. They may want to:\n"
            "1. Try again (re-write the plan to re-trigger review)\n"
            "2. Simplify the plan\n"
            "3. Manually approve if they're confident in the plan",
        )
        sys.exit(0)
    except FileNotFoundError:
        output_decision(
            "block",
            "Codex CLI not found on PATH.",
            "The 'codex' command was not found. Ensure Codex CLI is installed and on PATH.",
        )
        sys.exit(0)

    # 3.11: Check for Codex CLI errors
    if proc and proc.returncode != 0:
        stderr_tail = proc.stderr.decode("utf-8", errors="replace")[-2000:]
        output_decision(
            "block",
            f"Codex CLI failed with exit code {proc.returncode}.",
            f"Codex CLI returned an error. Please inform the user.\n\nError output:\n{stderr_tail}",
        )
        sys.exit(0)

    # 3.8: Parse Codex output
    review = parse_codex_output(output_json_path)
    if review is None:
        output_decision(
            "block",
            "Failed to parse Codex review output.",
            f"The Codex output at {output_json_path} could not be parsed or is missing required fields. "
            "Please inform the user of this error.",
        )
        sys.exit(0)

    # Extract annotated plan markdown
    annotated_md = review.get("annotated_plan_markdown", "")
    if annotated_md:
        annotated_path = review_dir / f"plan_v{version}.annotated.md"
        annotated_path.write_text(annotated_md)

    # 3.9: Gating logic
    if review.get("is_optimal"):
        # Plan approved
        write_approval(review_dir, plan_path, version, new_thread_id)
        output_decision(
            "",  # No decision = allow
            "",
            "Codex has approved the plan as optimal. Present the final plan to the user "
            "and ask: 'The plan has been reviewed and approved by Codex. Ready to execute?' "
            "Do NOT begin implementation. Wait for the user to confirm.",
        )
    else:
        # Plan rejected — provide feedback
        issues_summary = review.get("summary", "No summary provided.")
        blocking = review.get("blocking_issues", [])
        if blocking:
            issue_lines = []
            for i, issue in enumerate(blocking, 1):
                severity = issue.get("severity", "unknown")
                claim = issue.get("claim", "")
                issue_lines.append(f"  {i}. [{severity}] {claim}")
            issues_detail = "\n".join(issue_lines)
        else:
            issues_detail = "  (No specific blocking issues listed)"

        annotated_plan_path = review_dir / f"plan_v{version}.annotated.md"
        if annotated_md:
            primary_artifact = f"Annotated plan: {annotated_plan_path}"
            read_instruction = "1. Read the annotated plan at the path above to see Codex's inline feedback."
        else:
            primary_artifact = f"Codex review: {output_json_path}"
            read_instruction = "1. Read the Codex review JSON at the path above."

        output_decision(
            "block",
            f"Codex review (v{version}): {issues_summary}",
            f"A co-worker has reviewed your plan and found issues. You must maximally evaluate "
            f"each claim against the code to assess whether it is accurate.\n\n"
            f"Blocking issues:\n{issues_detail}\n\n"
            f"{primary_artifact}\n\n"
            f"Instructions:\n"
            f"{read_instruction}\n"
            f"2. For each blocking issue, evaluate the claim against the actual code.\n"
            f"3. Revise docs/plan.md to address valid issues.\n"
            f"4. Write the revised plan to re-trigger review.\n"
            f"Do NOT dismiss feedback without verifying against the code.",
        )

    sys.exit(0)


if __name__ == "__main__":
    main()

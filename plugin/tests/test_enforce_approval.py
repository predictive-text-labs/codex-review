#!/usr/bin/env python3
"""Tests for enforce_approval.py PreToolUse hook."""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
import enforce_approval


class TestWriteEditRules(unittest.TestCase):
    """Test 8.2 + 8.8: Write|Edit rules."""

    def test_plan_md_always_allowed(self):
        """docs/plan.md is always allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertTrue(enforce_approval.is_plan_path("docs/plan.md", tmpdir))

    def test_review_dir_always_denied(self):
        """8.8: .claude/review/* is always denied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertTrue(
                enforce_approval.is_review_dir_path(
                    ".claude/review/approval.json", tmpdir
                )
            )
            self.assertTrue(
                enforce_approval.is_review_dir_path(
                    ".claude/review/version_counter", tmpdir
                )
            )
            self.assertTrue(
                enforce_approval.is_review_dir_path(
                    ".claude/review/codex_thread_id", tmpdir
                )
            )
            self.assertTrue(
                enforce_approval.is_review_dir_path(
                    ".claude/review/plan_v1.snapshot.md", tmpdir
                )
            )

    def test_non_plan_denied_before_approval(self):
        """Non-plan files denied before approval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertFalse(enforce_approval.validate_approval(tmpdir))

    def test_non_plan_allowed_after_approval(self):
        """8.2: Non-plan files allowed after valid approval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create plan and approval
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            plan_content = "test plan"
            (docs_dir / "plan.md").write_text(plan_content)

            review_dir = Path(tmpdir) / ".claude" / "review"
            review_dir.mkdir(parents=True)
            plan_hash = hashlib.sha256(plan_content.encode()).hexdigest()
            approval = {
                "is_optimal": True,
                "plan_hash": plan_hash,
            }
            (review_dir / "approval.json").write_text(json.dumps(approval))

            self.assertTrue(enforce_approval.validate_approval(tmpdir))


class TestApprovalValidation(unittest.TestCase):
    """Test approval hash validation."""

    def test_hash_mismatch_rejects(self):
        """Approval with wrong hash is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            (docs_dir / "plan.md").write_text("current plan")

            review_dir = Path(tmpdir) / ".claude" / "review"
            review_dir.mkdir(parents=True)
            approval = {
                "is_optimal": True,
                "plan_hash": "wrong-hash",
            }
            (review_dir / "approval.json").write_text(json.dumps(approval))

            self.assertFalse(enforce_approval.validate_approval(tmpdir))

    def test_not_optimal_rejects(self):
        """Approval with is_optimal=false is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            plan_content = "test plan"
            (docs_dir / "plan.md").write_text(plan_content)

            review_dir = Path(tmpdir) / ".claude" / "review"
            review_dir.mkdir(parents=True)
            plan_hash = hashlib.sha256(plan_content.encode()).hexdigest()
            approval = {
                "is_optimal": False,
                "plan_hash": plan_hash,
            }
            (review_dir / "approval.json").write_text(json.dumps(approval))

            self.assertFalse(enforce_approval.validate_approval(tmpdir))

    def test_missing_approval_rejects(self):
        """Missing approval.json is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertFalse(enforce_approval.validate_approval(tmpdir))

    def test_missing_plan_rejects(self):
        """Missing plan file is invalid even with approval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            review_dir = Path(tmpdir) / ".claude" / "review"
            review_dir.mkdir(parents=True)
            approval = {"is_optimal": True, "plan_hash": "abc"}
            (review_dir / "approval.json").write_text(json.dumps(approval))

            self.assertFalse(enforce_approval.validate_approval(tmpdir))


class TestBashGating(unittest.TestCase):
    """Test 8.3: Bash command gating."""

    def test_readonly_commands_allowed(self):
        """Read-only commands allowed pre-approval."""
        for cmd in ["rg pattern", "grep -r foo", "ls -la", "cat file.txt",
                     "head -n 10 file", "tail -f log", "wc -l file",
                     "file image.png"]:
            result = enforce_approval.check_bash_command(cmd)
            self.assertIsNone(result, f"Command should be allowed: {cmd}")

    def test_git_readonly_allowed(self):
        """Read-only git subcommands allowed."""
        for cmd in ["git status", "git diff", "git show HEAD", "git log --oneline",
                     "git rev-parse HEAD", "git grep pattern", "git branch -a"]:
            result = enforce_approval.check_bash_command(cmd)
            self.assertIsNone(result, f"Command should be allowed: {cmd}")

    def test_git_write_denied(self):
        """Write git subcommands denied."""
        for cmd in ["git add .", "git commit -m 'test'", "git push",
                     "git checkout -b new", "git reset --hard"]:
            result = enforce_approval.check_bash_command(cmd)
            self.assertIsNotNone(result, f"Command should be denied: {cmd}")

    def test_write_commands_denied(self):
        """Write commands denied pre-approval."""
        for cmd in ["python script.py", "node app.js", "bash script.sh",
                     "sed -i 's/a/b/' file", "touch newfile",
                     "mv a b", "cp a b", "rm file", "mkdir dir"]:
            result = enforce_approval.check_bash_command(cmd)
            self.assertIsNotNone(result, f"Command should be denied: {cmd}")

    def test_shell_operators_denied(self):
        """Shell operators denied pre-approval."""
        for cmd in ["ls | grep foo", "ls && rm file", "ls; rm file",
                     "echo foo > file", "echo foo >> file",
                     "cat < file", "$(whoami)", "ls `pwd`"]:
            result = enforce_approval.check_bash_command(cmd)
            self.assertIsNotNone(result, f"Command should be denied: {cmd}")


if __name__ == "__main__":
    unittest.main()

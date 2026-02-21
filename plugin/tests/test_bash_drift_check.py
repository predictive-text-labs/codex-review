#!/usr/bin/env python3
"""Tests for bash_drift_check.py PostToolUse hook."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
import bash_drift_check


class TestDriftDetection(unittest.TestCase):
    """Test 8.9: Bash drift check."""

    def test_plan_md_allowed(self):
        """docs/plan.md changes are allowed."""
        self.assertTrue(bash_drift_check.is_allowed_path("docs/plan.md"))

    def test_review_dir_allowed(self):
        """Changes under .claude/review/ are allowed."""
        self.assertTrue(
            bash_drift_check.is_allowed_path(".claude/review/version_counter")
        )
        self.assertTrue(
            bash_drift_check.is_allowed_path(".claude/review/approval.json")
        )
        self.assertTrue(
            bash_drift_check.is_allowed_path(
                ".claude/review/plan_v1.snapshot.md"
            )
        )

    def test_other_files_not_allowed(self):
        """Changes to other files are flagged."""
        self.assertFalse(bash_drift_check.is_allowed_path("src/main.py"))
        self.assertFalse(bash_drift_check.is_allowed_path("README.md"))
        self.assertFalse(bash_drift_check.is_allowed_path(".claude/settings.json"))


class TestApprovalAwareSkip(unittest.TestCase):
    """Test drift check skips when valid approval exists."""

    def _create_valid_approval(self, tmpdir):
        """Helper to create a valid approval setup."""
        docs_dir = Path(tmpdir) / "docs"
        docs_dir.mkdir()
        plan_content = "test plan"
        (docs_dir / "plan.md").write_text(plan_content)

        review_dir = Path(tmpdir) / ".claude" / "review"
        review_dir.mkdir(parents=True)
        plan_hash = hashlib.sha256(plan_content.encode()).hexdigest()
        approval = {"is_optimal": True, "plan_hash": plan_hash}
        (review_dir / "approval.json").write_text(json.dumps(approval))

    def test_skips_with_valid_approval(self):
        """Drift check exits early when valid approval exists."""
        import io
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_valid_approval(tmpdir)

            hook_input = json.dumps({
                "tool_name": "Bash",
                "cwd": tmpdir,
                "tool_input": {"command": "npm install"},
            })
            stdin = io.StringIO(hook_input)

            with patch("sys.stdin", stdin):
                with self.assertRaises(SystemExit) as ctx:
                    bash_drift_check.main()
                self.assertEqual(ctx.exception.code, 0)

    def test_checks_without_approval(self):
        """Drift check runs normally when no approval exists."""
        import io
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            # No approval — drift check should proceed (and find no git repo, so exit 0)
            hook_input = json.dumps({
                "tool_name": "Bash",
                "cwd": tmpdir,
                "tool_input": {"command": "ls"},
            })
            stdin = io.StringIO(hook_input)

            with patch("sys.stdin", stdin):
                # Will exit 0 because git status fails in a non-git dir
                with self.assertRaises(SystemExit) as ctx:
                    bash_drift_check.main()
                self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()

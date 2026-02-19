#!/usr/bin/env python3
"""Tests for bash_drift_check.py PostToolUse hook."""

import sys
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


if __name__ == "__main__":
    unittest.main()

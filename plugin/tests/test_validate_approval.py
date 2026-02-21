#!/usr/bin/env python3
"""Tests for validate_approval.py standalone script."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
import validate_approval


class TestValidateApproval(unittest.TestCase):
    """Test validate_approval.validate() function."""

    def test_valid_approval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            plan_content = "test plan"
            (docs_dir / "plan.md").write_text(plan_content)

            review_dir = Path(tmpdir) / ".claude" / "review"
            review_dir.mkdir(parents=True)
            plan_hash = hashlib.sha256(plan_content.encode()).hexdigest()
            approval = {"is_optimal": True, "plan_hash": plan_hash}
            (review_dir / "approval.json").write_text(json.dumps(approval))

            result = validate_approval.validate(tmpdir)
            self.assertEqual(result, {"valid": True})

    def test_missing_approval_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            (docs_dir / "plan.md").write_text("plan")

            result = validate_approval.validate(tmpdir)
            self.assertFalse(result["valid"])
            self.assertIn("Run /plan-with-review", result["reason"])

    def test_missing_plan_md(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_approval.validate(tmpdir)
            self.assertFalse(result["valid"])
            self.assertIn("No plan file", result["reason"])

    def test_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            (docs_dir / "plan.md").write_text("current plan")

            review_dir = Path(tmpdir) / ".claude" / "review"
            review_dir.mkdir(parents=True)
            approval = {"is_optimal": True, "plan_hash": "wrong-hash"}
            (review_dir / "approval.json").write_text(json.dumps(approval))

            result = validate_approval.validate(tmpdir)
            self.assertFalse(result["valid"])
            self.assertIn("modified since", result["reason"])

    def test_is_optimal_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            plan_content = "test plan"
            (docs_dir / "plan.md").write_text(plan_content)

            review_dir = Path(tmpdir) / ".claude" / "review"
            review_dir.mkdir(parents=True)
            plan_hash = hashlib.sha256(plan_content.encode()).hexdigest()
            approval = {"is_optimal": False, "plan_hash": plan_hash}
            (review_dir / "approval.json").write_text(json.dumps(approval))

            result = validate_approval.validate(tmpdir)
            self.assertFalse(result["valid"])
            self.assertIn("not approved as optimal", result["reason"])

    def test_corrupted_approval_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            (docs_dir / "plan.md").write_text("plan")

            review_dir = Path(tmpdir) / ".claude" / "review"
            review_dir.mkdir(parents=True)
            (review_dir / "approval.json").write_text("not json{{{")

            result = validate_approval.validate(tmpdir)
            self.assertFalse(result["valid"])
            self.assertIn("corrupted", result["reason"])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Tests for plan_review.py PostToolUse hook."""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path so we can import the hook
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
import plan_review


class TestResolvePlanPath(unittest.TestCase):
    """Test 8.1 + 8.7: Plan path matching."""

    def test_plan_md_triggers(self):
        """Write to docs/plan.md triggers review."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir) / "docs"
            plan_dir.mkdir()
            plan_file = plan_dir / "plan.md"
            plan_file.write_text("test")

            hook_input = {
                "cwd": tmpdir,
                "tool_input": {"file_path": "docs/plan.md"},
            }
            result = plan_review.resolve_plan_path(hook_input)
            self.assertIsNotNone(result)

    def test_other_file_ignored(self):
        """Write to other files is ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hook_input = {
                "cwd": tmpdir,
                "tool_input": {"file_path": "src/main.py"},
            }
            result = plan_review.resolve_plan_path(hook_input)
            self.assertIsNone(result)

    def test_nested_plan_md_no_false_trigger(self):
        """8.7: Nested docs/plan.md in subdirectory does not false-trigger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a nested plan.md that should NOT trigger
            nested_dir = Path(tmpdir) / "some" / "nested" / "docs"
            nested_dir.mkdir(parents=True)
            (nested_dir / "plan.md").write_text("test")

            hook_input = {
                "cwd": tmpdir,
                "tool_input": {"file_path": "some/nested/docs/plan.md"},
            }
            result = plan_review.resolve_plan_path(hook_input)
            self.assertIsNone(result)

    def test_absolute_path_plan_md(self):
        """Absolute path to docs/plan.md triggers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir) / "docs"
            plan_dir.mkdir()
            plan_file = plan_dir / "plan.md"
            plan_file.write_text("test")

            abs_path = str(plan_file)
            hook_input = {
                "cwd": tmpdir,
                "tool_input": {"file_path": abs_path},
            }
            result = plan_review.resolve_plan_path(hook_input)
            self.assertIsNotNone(result)


class TestPlanStructureValidation(unittest.TestCase):
    """Test 8.1: Plan structure validation."""

    def test_valid_plan(self):
        plan = """## Goal
Something
## Context
Something
## Approach
Something
## Changes
Something
## Risks
Something
## Open Questions
Something"""
        missing = plan_review.validate_plan_structure(plan)
        self.assertEqual(missing, [])

    def test_missing_sections(self):
        plan = """## Goal
Something
## Context
Something"""
        missing = plan_review.validate_plan_structure(plan)
        self.assertIn("## Approach", missing)
        self.assertIn("## Changes", missing)
        self.assertIn("## Risks", missing)
        self.assertIn("## Open Questions", missing)


class TestApprovalLifecycle(unittest.TestCase):
    """Test 8.4: Approval lifecycle."""

    def test_invalidate_approval(self):
        """Approval deleted on plan re-edit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            review_dir = Path(tmpdir) / ".claude" / "review"
            review_dir.mkdir(parents=True)

            # Create approval and related files
            (review_dir / "approval.json").write_text('{"is_optimal": true}')
            (review_dir / "codex_thread_id").write_text("test-thread-id")
            (review_dir / "version_counter").write_text("3")

            plan_review.invalidate_approval(review_dir)

            self.assertFalse((review_dir / "approval.json").exists())
            self.assertFalse((review_dir / "codex_thread_id").exists())
            self.assertEqual(
                (review_dir / "version_counter").read_text().strip(), "0"
            )

    def test_write_approval(self):
        """Approval created on Codex approve with correct hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            review_dir = Path(tmpdir) / ".claude" / "review"
            review_dir.mkdir(parents=True)
            plan_path = Path(tmpdir) / "plan.md"
            plan_content = "test plan content"
            plan_path.write_text(plan_content)

            plan_review.write_approval(review_dir, str(plan_path), 2, "thread-123")

            approval = json.loads((review_dir / "approval.json").read_text())
            self.assertTrue(approval["is_optimal"])
            self.assertEqual(approval["review_version"], 2)
            self.assertEqual(approval["codex_thread_id"], "thread-123")

            expected_hash = hashlib.sha256(plan_content.encode()).hexdigest()
            self.assertEqual(approval["plan_hash"], expected_hash)


class TestVersionCounter(unittest.TestCase):
    """Test version counter management."""

    def test_starts_at_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            review_dir = Path(tmpdir)
            self.assertEqual(plan_review.read_version_counter(review_dir), 0)

    def test_increment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            review_dir = Path(tmpdir)
            v1 = plan_review.increment_version_counter(review_dir)
            self.assertEqual(v1, 1)
            v2 = plan_review.increment_version_counter(review_dir)
            self.assertEqual(v2, 2)


class TestSessionManagement(unittest.TestCase):
    """Test 8.5: Session management."""

    def test_thread_id_capture(self):
        """Thread ID captured from thread.started event."""
        stdout = b'{"type": "thread.started", "thread_id": "abc-123"}\n'
        stderr = b""
        tid = plan_review.parse_thread_id(stdout, stderr)
        self.assertEqual(tid, "abc-123")

    def test_thread_id_from_stderr(self):
        """Thread ID captured from stderr."""
        stdout = b""
        stderr = b'{"type": "thread.started", "thread_id": "def-456"}\n'
        tid = plan_review.parse_thread_id(stdout, stderr)
        self.assertEqual(tid, "def-456")

    def test_thread_id_missing(self):
        """No thread.started event found."""
        stdout = b'{"type": "other_event"}\n'
        stderr = b"some error output\n"
        tid = plan_review.parse_thread_id(stdout, stderr)
        self.assertIsNone(tid)

    def test_store_and_get_thread_id(self):
        """Thread ID stored and retrieved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            review_dir = Path(tmpdir)
            plan_review.store_codex_thread_id(review_dir, "test-tid")
            self.assertEqual(
                plan_review.get_codex_thread_id(review_dir), "test-tid"
            )

    def test_reset_on_new_cycle(self):
        """Thread ID deleted on approval invalidation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            review_dir = Path(tmpdir)
            (review_dir / "codex_thread_id").write_text("old-tid")
            (review_dir / "approval.json").write_text("{}")
            plan_review.invalidate_approval(review_dir)
            self.assertIsNone(plan_review.get_codex_thread_id(review_dir))


class TestMaxRevisionThreshold(unittest.TestCase):
    """Test 8.6: Max revision threshold."""

    def test_threshold_blocks(self):
        """Hook blocks after MAX_REVISIONS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            review_dir = Path(tmpdir)
            (review_dir / "version_counter").write_text(
                str(plan_review.MAX_REVISIONS)
            )
            version = plan_review.increment_version_counter(review_dir)
            self.assertGreater(version, plan_review.MAX_REVISIONS)


class TestCodexOutputParsing(unittest.TestCase):
    """Test Codex output parsing."""

    def test_valid_output(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "is_optimal": True,
                    "blocking_issues": [],
                    "recommended_changes": [],
                    "annotated_plan_markdown": "# Plan\nLooks good.",
                    "summary": "Plan is optimal.",
                },
                f,
            )
            f.flush()
            result = plan_review.parse_codex_output(f.name)
            self.assertIsNotNone(result)
            self.assertTrue(result["is_optimal"])
            os.unlink(f.name)

    def test_missing_fields(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"is_optimal": True}, f)
            f.flush()
            result = plan_review.parse_codex_output(f.name)
            self.assertIsNone(result)
            os.unlink(f.name)

    def test_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            f.flush()
            result = plan_review.parse_codex_output(f.name)
            self.assertIsNone(result)
            os.unlink(f.name)

    def test_missing_file(self):
        result = plan_review.parse_codex_output("/nonexistent/path.json")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

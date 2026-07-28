from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from delivery_gate import gate


class DeliveryGateTest(unittest.TestCase):
    def test_emits_human_review_not_merge_eligibility(self) -> None:
        replies = iter([
            "/tmp/repo", "", "feature/poc", "", "abc123",
            "tests passed", json.dumps({"number": 61, "url": "https://example.test/pr/61", "isDraft": True,
                                          "headRefName": "feature/poc", "baseRefName": "main", "state": "OPEN"}),
        ])
        with patch("delivery_gate.run", side_effect=lambda *_: next(replies)):
            evidence = gate(Path("/tmp/repo"), "main", "61", "python3 -m unittest")
        self.assertTrue(evidence["ready_for_human_review"])
        self.assertFalse(evidence["merge_eligible"])
        self.assertEqual("abc123", evidence["git_sha"])

    def test_rejects_shell_composition(self) -> None:
        replies = iter(["/tmp/repo", "", "feature/poc", "", "abc123"])
        with patch("delivery_gate.run", side_effect=lambda *_: next(replies)):
            with self.assertRaisesRegex(RuntimeError, "direct executable"):
                gate(Path("/tmp/repo"), "main", "61", "pytest && curl")

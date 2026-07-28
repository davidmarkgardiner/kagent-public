#!/usr/bin/env python3
"""Offline proof for correlation, required messageId, and duplicate suppression."""
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from delivery_controller import IncomingTask, Ledger, handle


class DeliveryControllerTest(unittest.TestCase):
    def setUp(self):
        self.db = tempfile.NamedTemporaryFile(delete=False)
        self.db.close()
        self.ledger = Ledger(self.db.name)
        self.task = IncomingTask("buzz-event-1", "channel-1", "sample", "#1", "Hello", "Add a greeting")
        self.calls = []

    def tearDown(self):
        os.unlink(self.db.name)

    def invoke(self, payload):
        self.calls.append(payload)
        return {"result": {"status": {"state": "completed", "taskId": "a2a-1"},
                            "artifacts": [{"parts": [{"text": "BUILD_EVIDENCE: sample"}]}]}}

    def test_message_id_is_source_event_and_result_never_allows_merge(self):
        reply = handle(self.task, self.ledger, self.invoke)
        self.assertEqual("buzz-event-1", self.calls[0]["params"]["message"]["messageId"])
        self.assertEqual("completed", reply["state"])
        self.assertFalse(reply["merge_eligible"])
        self.assertEqual("a2a-1", reply["a2a_task_id"])

    def test_duplicate_does_not_invoke_kagent_twice(self):
        handle(self.task, self.ledger, self.invoke)
        reply = handle(self.task, self.ledger, self.invoke)
        self.assertTrue(reply["duplicate"])
        self.assertEqual(1, len(self.calls))


if __name__ == "__main__":
    unittest.main()

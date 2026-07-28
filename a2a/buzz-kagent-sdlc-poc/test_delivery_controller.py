#!/usr/bin/env python3
"""Offline proof for correlation, required messageId, and duplicate suppression."""
import os
import pathlib
import sys
import tempfile
import unittest
import json

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from delivery_controller import IncomingTask, Ledger, handle
from buzz_bridge import process_once


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

    def test_private_buzz_task_is_replied_to_in_the_same_thread(self):
        sent = []
        event = {"id": "buzz-event-2", "content": json.dumps({
            "schema": "buzz-kagent-sdlc.v1", "type": "sdlc.task.request",
            "project": "sample", "issue_id": "#2", "title": "Hello", "body": "Add greeting",
        })}
        def buzz(args, *, content=None):
            if args[1] == "get": return json.dumps([event])
            sent.append((args, json.loads(content)))
            return '{"event_id":"reply"}'
        self.assertEqual(1, process_once("channel-1", self.ledger, self.invoke, buzz))
        self.assertIn("--reply-to", sent[0][0])
        self.assertEqual("buzz-event-2", sent[0][1]["reply_to"])
        self.assertFalse(sent[0][1]["merge_eligible"])

    def test_input_required_becomes_a_structured_buzz_approval_request(self):
        def pending(_):
            return {"result": {"status": {"state": "input_required", "taskId": "a2a-pending"}}}
        reply = handle(self.task, self.ledger, pending)
        self.assertEqual("sdlc.approval_required", reply["type"])
        self.assertTrue(reply["approval"]["resume_same_a2a_task"])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Offline proof for correlation, required messageId, and duplicate suppression."""
import os
import pathlib
import sys
import tempfile
import unittest
import json

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from delivery_controller import IncomingTask, Ledger, handle, resume
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

    def test_a2a_wire_state_and_result_id_are_normalized_for_resume(self):
        ledger = Ledger(":memory:")
        task = IncomingTask("event-wire", "channel", "project", "#1", "title", "body")
        reply = handle(task, ledger, lambda _: {"result": {"id": "wire-task", "status": {"state": "input-required"}}})
        self.assertEqual("input_required", reply["state"])
        self.assertEqual("wire-task", reply["a2a_task_id"])

    def test_approval_resumes_the_same_task(self):
        handle(self.task, self.ledger, lambda _: {"result": {"status": {"state": "input_required", "taskId": "pending-1"}}})
        sent = []
        reply = resume("buzz-event-1", "approve", self.ledger, lambda payload: (sent.append(payload) or {"result": {"status": {"state": "completed", "taskId": "pending-1"}}}))
        self.assertEqual("pending-1", sent[0]["params"]["message"]["taskId"])
        self.assertEqual("approve", sent[0]["params"]["message"]["parts"][0]["data"]["decision_type"])
        self.assertEqual("completed", reply["state"])

    def test_threaded_buzz_approval_resumes_pending_work(self):
        handle(self.task, self.ledger, lambda _: {"result": {"status": {"state": "input_required", "taskId": "pending-2"}}})
        sent = []
        decision = {"id": "decision-1", "content": json.dumps({"schema": "buzz-kagent-sdlc.v1", "type": "sdlc.approval.decision", "source_event_id": "buzz-event-1", "decision": "approve"}), "tags": [["e", "approval-event-1"]]}
        def buzz(args, *, content=None):
            if args[1] == "get": return json.dumps([decision])
            sent.append((args, json.loads(content))); return '{"event_id":"reply"}'
        self.assertEqual(1, process_once("channel-1", self.ledger, lambda _: {"result": {"status": {"state": "completed", "taskId": "pending-2"}}}, buzz))
        self.assertEqual("completed", sent[0][1]["state"])

    def test_replayed_decision_does_not_resume_twice(self):
        handle(self.task, self.ledger, lambda _: {"result": {"status": {"state": "input_required", "taskId": "pending-3"}}})
        calls = []
        decision = {"id": "decision-replay", "content": json.dumps({
            "schema": "buzz-kagent-sdlc.v1", "type": "sdlc.approval.decision",
            "source_event_id": "buzz-event-1", "decision": "approve",
        }), "tags": [["e", "approval-event-1"]]}
        def buzz(args, *, content=None):
            if args[1] == "get": return json.dumps([decision])
            return '{"event_id":"reply"}'
        invoke = lambda payload: (calls.append(payload) or {"result": {"status": {"state": "completed", "taskId": "pending-3"}}})
        process_once("channel-1", self.ledger, invoke, buzz)
        process_once("channel-1", self.ledger, invoke, buzz)
        self.assertEqual(1, len(calls))

    def test_resume_attempt_limit_blocks_without_another_invoke(self):
        handle(self.task, self.ledger, lambda _: {"result": {"status": {"state": "input_required", "taskId": "pending-4"}}})
        calls = []
        pending = lambda payload: (calls.append(payload) or {"result": {"status": {"state": "input_required", "taskId": "pending-4"}}})
        resume("buzz-event-1", "approve", self.ledger, pending, "decision-limit-1")
        resume("buzz-event-1", "approve", self.ledger, pending, "decision-limit-2")
        reply = resume("buzz-event-1", "approve", self.ledger, pending, "decision-limit-3")
        self.assertEqual(2, len(calls))
        self.assertEqual("blocked", reply["state"])


if __name__ == "__main__":
    unittest.main()

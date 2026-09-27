"""Small regression checks for durable board resumption."""

import unittest
from datetime import datetime, timezone
from urllib.error import HTTPError

from board_poller import Board, GitLab, KubeLease


SHA = "a" * 40


class FakeGitLab:
    def __init__(self):
        self.labels = ["sdlc-rig-poc", "agent:plan"]
        self.child_issue = {"iid": 42}
        self.merge_request = None
        self.transitions = []
        self.notes_posted = []

    def child(self, iid):
        return self.child_issue

    def issue(self, iid):
        return {"labels": self.labels}

    def transition(self, iid, expected, destination):
        self.transitions.append((iid, expected, destination))
        self.labels = ["sdlc-rig-poc", destination]
        return True

    def post_once(self, iid, key, detail):
        self.notes_posted.append((iid, key))

    def branch(self, name):
        return {"commit": {"id": SHA if name != "main" else "b" * 40}}

    def changed_paths(self, branch):
        return ["package.json"]

    def pipeline(self, branch, sha):
        return {"id": 99, "status": "success"}

    def mr(self, branch):
        return self.merge_request


class BoardResumeTests(unittest.TestCase):
    def test_existing_child_skips_model_and_advances(self):
        gitlab = FakeGitLab()
        board = Board(gitlab, "http://unused")
        board.call_pm = lambda *args: self.fail("model should not run")
        self.assertTrue(board.process({"iid": 40, "labels": gitlab.labels}))
        self.assertEqual(gitlab.transitions, [(40, "agent:plan", "agent:build")])

    def test_new_mr_returns_before_reviewer_turn(self):
        gitlab = FakeGitLab()
        gitlab.labels = ["sdlc-rig-poc", "agent:review"]
        board = Board(gitlab, "http://unused")
        calls = []

        def call_pm(stage, iid, details):
            calls.append(stage)
            gitlab.merge_request = {"iid": 10, "draft": True, "sha": SHA}
            return "MR opened"

        board.call_pm = call_pm
        self.assertTrue(board.process({"iid": 40, "labels": gitlab.labels}))
        self.assertEqual(calls, ["MR"])
        self.assertEqual(gitlab.transitions, [])


class LeaseTests(unittest.TestCase):
    def test_active_holder_prevents_second_job(self):
        lease = object.__new__(KubeLease)
        lease.identity = "second-job"
        lease.duration = 240
        renewed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        lease.request = lambda method, data=None: {
            "metadata": {"resourceVersion": "8"},
            "spec": {"holderIdentity": "first-job", "renewTime": renewed,
                     "leaseDurationSeconds": 240},
        } if method == "GET" else self.fail("second job must not update active lease")
        self.assertFalse(lease.acquire())

    def test_resource_version_conflict_prevents_racing_job(self):
        lease = object.__new__(KubeLease)
        lease.identity = "racing-job"
        lease.duration = 240
        def request(method, data=None):
            if method == "GET":
                return {"metadata": {"resourceVersion": "8"}, "spec": {}}
            raise HTTPError("https://kubernetes.default.svc", 409, "Conflict", {}, None)
        lease.request = request
        self.assertFalse(lease.acquire())

class BoardReworkTests(unittest.TestCase):
    def test_failed_new_sha_requires_rework_after_older_review(self):
        gitlab = FakeGitLab()
        gitlab.labels = ["sdlc-rig-poc", "agent:changes"]
        gitlab.merge_request = {"iid": 10, "draft": True, "sha": SHA}
        gitlab.pages = lambda path: [{"sha": SHA, "id": 99, "status": "failed"}]
        gitlab.notes = lambda kind, iid: [{
            "id": 1, "body": "<!-- sdlc-rig-review parent=40 sha=" + "c" * 40 + " -->\nREVIEW_VERDICT: PASS"
        }]
        board = Board(gitlab, "http://unused")
        calls = []
        board.call_pm = lambda stage, iid, details: calls.append((stage, details))
        board.attempt = lambda *args: True
        self.assertTrue(board.process({"iid": 40, "labels": gitlab.labels}))
        self.assertEqual(calls[0][0], "REWORK")
        self.assertIn("pipeline 99 ended failed", calls[0][1])
        self.assertEqual(gitlab.transitions, [])


class DiffScopeTests(unittest.TestCase):
    def test_renamed_file_checks_old_and_new_paths(self):
        gitlab = object.__new__(GitLab)
        gitlab.default_branch = "main"
        gitlab.request = lambda method, path: {"diffs": [
            {"old_path": "outside.txt", "new_path": "README.md", "renamed_file": True}
        ]}
        self.assertEqual(gitlab.changed_paths("agentic/sdlc-rig-40"),
                         ["README.md", "outside.txt"])


if __name__ == "__main__":
    unittest.main()

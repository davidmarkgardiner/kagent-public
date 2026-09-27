#!/usr/bin/env python3
"""Advance one labelled sandbox issue through one verified SDLC checkpoint.

GitLab labels and artifacts are the durable state. A2A replies are hints until
the corresponding GitLab child, commit, pipeline, MR, or review note exists.
The CronJob runs one instance at a time and performs at most one model turn.
"""

import json
import os
from pathlib import Path
import re
import ssl
import sys
import time
from datetime import datetime, timedelta, timezone
import urllib.error
import urllib.parse
import urllib.request
import uuid


STATES = ("agent:plan", "agent:build", "agent:test", "agent:review", "agent:changes", "agent:accepted", "agent:blocked")
ACTIVE = set(STATES[:-2])
ALLOWED_PATHS = {"README.md", "package.json", "tests/calculator.test.mjs", ".gitlab-ci.yml"}
REVIEW_RE = re.compile(r"<!-- sdlc-rig-review parent=(\d+) sha=([0-9a-f]{40}) -->")


class ApiError(RuntimeError):
    def __init__(self, code, path):
        super().__init__(f"GitLab HTTP {code} for {path}")
        self.code = code


def log(event, **fields):
    print(json.dumps({"event": event, **fields}, sort_keys=True), flush=True)


class KubeLease:
    """Serialize scheduled and manual Jobs through one pre-created Lease."""

    def __init__(self, name="sdlc-board-poller", namespace="sdlc-rig", duration=240):
        host = os.environ["KUBERNETES_SERVICE_HOST"]
        port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
        service_account = Path("/var/run/secrets/kubernetes.io/serviceaccount")
        self.token = (service_account / "token").read_text().strip()
        self.context = ssl.create_default_context(cafile=str(service_account / "ca.crt"))
        self.url = (f"https://{host}:{port}/apis/coordination.k8s.io/v1"
                    f"/namespaces/{namespace}/leases/{name}")
        self.identity = "board-" + uuid.uuid4().hex
        self.duration = duration

    def request(self, method, data=None):
        body = json.dumps(data).encode() if data is not None else None
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=10, context=self.context) as response:
            return json.load(response)

    def acquire(self):
        lease = self.request("GET")
        spec = lease.get("spec") or {}
        holder = spec.get("holderIdentity")
        renew = spec.get("renewTime")
        if holder and renew:
            renewed = datetime.fromisoformat(renew.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) < renewed + timedelta(seconds=spec.get("leaseDurationSeconds", self.duration)):
                return False
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        lease["spec"] = {"holderIdentity": self.identity,
                         "acquireTime": now, "renewTime": now,
                         "leaseDurationSeconds": self.duration}
        try:
            self.request("PUT", lease)
        except urllib.error.HTTPError as exc:
            if exc.code == 409:
                return False
            raise
        return True

    def release(self):
        try:
            lease = self.request("GET")
            if lease.get("spec", {}).get("holderIdentity") != self.identity:
                return
            lease["spec"].pop("holderIdentity", None)
            lease["spec"].pop("renewTime", None)
            self.request("PUT", lease)
        except Exception as exc:
            log("lease_release_error", error=type(exc).__name__)


class GitLab:
    def __init__(self, token, project, api_url="https://gitlab.com/api/v4", default_branch="main"):
        parsed = urllib.parse.urlparse(api_url)
        if (parsed.scheme != "https" or not parsed.netloc or parsed.path.rstrip("/") != "/api/v4"
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("GitLab API URL must be an HTTPS /api/v4 endpoint")
        self.token = token
        self.default_branch = default_branch
        self.base = api_url.rstrip("/") + "/projects/" + urllib.parse.quote(project, safe="")

    def request(self, method, path, data=None, missing_ok=False):
        url = self.base + path
        body = json.dumps(data).encode() if data is not None else None
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            if missing_ok and exc.code == 404:
                return None
            raise ApiError(exc.code, path) from None

    def pages(self, path):
        result = []
        for page in range(1, 6):
            separator = "&" if "?" in path else "?"
            batch = self.request("GET", f"{path}{separator}per_page=100&page={page}")
            result.extend(batch)
            if len(batch) < 100:
                return result
        raise RuntimeError("GitLab pagination exceeded the 500-item safety bound")

    def issue(self, iid):
        return self.request("GET", f"/issues/{iid}")

    def queue(self):
        issues = self.pages("/issues?state=opened&labels=sdlc-rig-poc")
        return sorted(issues, key=lambda item: item["iid"])

    def child(self, parent_iid):
        # Search is a hint; exact parent annotation is the identity check.
        query = urllib.parse.quote(f"Child of #{parent_iid}", safe="")
        matches = self.pages(f"/issues?state=all&search={query}")
        children = [item for item in matches
                    if item.get("title", "").startswith(f"Child of #{parent_iid}:")
                    and item.get("description", "").startswith(f"Parent: #{parent_iid}")]
        if len(children) > 1:
            raise RuntimeError(f"multiple child issues for parent {parent_iid}")
        return children[0] if children else None

    def branch(self, name):
        return self.request("GET", "/repository/branches/" + urllib.parse.quote(name, safe=""), missing_ok=True)

    def changed_paths(self, branch):
        query = urllib.parse.urlencode({"from": self.default_branch, "to": branch})
        comparison = self.request("GET", "/repository/compare?" + query)
        return sorted({path for diff in comparison.get("diffs", [])
                       for path in (diff.get("old_path"), diff.get("new_path")) if path})

    def pipeline(self, branch, sha):
        query = urllib.parse.urlencode({"ref": branch})
        items = self.pages("/pipelines?" + query)
        return next((item for item in items if item.get("sha") == sha), None)

    def mr(self, branch):
        query = urllib.parse.urlencode({"state": "opened", "source_branch": branch})
        items = self.pages("/merge_requests?" + query)
        if len(items) > 1:
            raise RuntimeError(f"multiple open MRs for {branch}")
        return items[0] if items else None

    def notes(self, kind, iid):
        return self.pages(f"/{kind}/{iid}/notes")

    def post_once(self, iid, key, message):
        marker = f"<!-- sdlc-rig:v1:{iid}:{key} -->"
        if any(marker in note.get("body", "") for note in self.notes("issues", iid)):
            return
        self.request("POST", f"/issues/{iid}/notes", {"body": marker + "\n" + message})

    def transition(self, iid, expected, destination):
        issue = self.issue(iid)
        labels = issue.get("labels", [])
        if "sdlc-rig-poc" not in labels or expected not in labels:
            log("state_changed_elsewhere", iid=iid, expected=expected, labels=labels)
            return False
        other_states = set(labels).intersection(STATES) - {expected}
        if other_states:
            raise RuntimeError(f"conflicting board labels on issue {iid}: {sorted(other_states)}")
        self.request("PUT", f"/issues/{iid}", {
            "add_labels": destination,
            "remove_labels": expected,
        })
        actual = self.issue(iid).get("labels", [])
        if destination not in actual or expected in actual:
            raise RuntimeError(f"label transition did not stick for issue {iid}")
        log("transition", iid=iid, old=expected, new=destination)
        return True


def a2a(pm_url, stage, prompt, timeout):
    request_id = "board-" + uuid.uuid4().hex
    payload = {
        "jsonrpc": "2.0", "id": request_id, "method": "message/send",
        "params": {"message": {
            "kind": "message", "messageId": request_id,
            "contextId": "context-" + request_id, "role": "user",
            "parts": [{"kind": "text", "text": prompt}],
        }},
    }
    req = urllib.request.Request(pm_url.rstrip("/") + "/", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as response:
        result = json.load(response)
    task = result.get("result", {})
    state = task.get("status", {}).get("state")
    if state != "completed" or result.get("error"):
        raise RuntimeError(f"PM A2A {stage} ended in {state or 'error'}")
    artifacts = task.get("artifacts") or []
    parts = [part.get("text", "") for artifact in artifacts for part in artifact.get("parts", [])
             if part.get("kind") == "text"]
    if not parts:
        for event in reversed(task.get("history") or []):
            if event.get("role") == "agent":
                parts = [part.get("text", "") for part in event.get("parts", [])
                         if part.get("kind") == "text"]
                if parts:
                    break
    text = "\n".join(parts)
    log("a2a", stage=stage, elapsed_s=round(time.monotonic() - started, 1),
        completed=bool(text), reply_chars=len(text))
    if not text:
        raise RuntimeError(f"PM A2A {stage} returned no text")
    return text


class Board:
    def __init__(self, gitlab, pm_url, timeout=150, target_branch="main", allowed_paths=ALLOWED_PATHS):
        self.gitlab = gitlab
        self.pm_url = pm_url
        self.timeout = timeout
        self.target_branch = target_branch
        self.allowed_paths = set(allowed_paths)

    def call_pm(self, stage, iid, details):
        prompt = f"BOARD_STAGE={stage}\nParent issue IID: {iid}.\n{details}\n"
        return a2a(self.pm_url, stage, prompt, self.timeout)

    def attempt(self, iid, stage, cause, expected):
        notes = self.gitlab.notes("issues", iid)
        prefix = f"<!-- sdlc-rig-attempt:v1:{iid}:{stage}:"
        count = sum(prefix in note.get("body", "") for note in notes) + 1
        marker = f"{prefix}{count} -->"
        self.gitlab.request("POST", f"/issues/{iid}/notes", {
            "body": marker + "\n" + cause[:500]
        })
        log("attempt", iid=iid, stage=stage, number=count, cause=cause[:120])
        if count >= 3:
            self.gitlab.transition(iid, expected, "agent:blocked")
        return True

    def advance(self, iid, expected, destination, key, detail):
        self.gitlab.post_once(iid, key, detail)
        self.gitlab.transition(iid, expected, destination)
        return True

    def committed(self, branch):
        found = self.gitlab.branch(branch)
        if not found:
            return None
        base = self.gitlab.branch(self.target_branch)
        sha = found["commit"]["id"]
        if sha == base["commit"]["id"]:
            return None
        paths = self.gitlab.changed_paths(branch)
        if not paths or not set(paths).issubset(self.allowed_paths):
            raise RuntimeError(f"branch {branch} has unapproved or no changed paths")
        return sha, paths

    def review_note(self, iid, mr_iid, sha):
        for note in sorted(self.gitlab.notes("merge_requests", mr_iid),
                           key=lambda item: item["id"], reverse=True):
            body = note.get("body", "")
            match = REVIEW_RE.search(body)
            if match and int(match.group(1)) == iid and match.group(2) == sha:
                if "REVIEW_VERDICT: PASS" in body:
                    return note, "PASS"
                if "REVIEW_VERDICT: CHANGES_REQUESTED" in body:
                    return note, "CHANGES_REQUESTED"
        return None, None

    def process(self, issue):
        iid = issue["iid"]
        labels = set(issue.get("labels", []))
        states = labels.intersection(STATES)
        if len(states) != 1:
            log("skip_invalid_labels", iid=iid, states=sorted(states))
            return False
        state = states.pop()
        if state not in ACTIVE:
            return False
        branch = f"agentic/sdlc-rig-{iid}"
        child = self.gitlab.child(iid)
        log("picked", iid=iid, state=state, child=child["iid"] if child else None)

        if state == "agent:plan":
            if not child:
                try:
                    self.call_pm("PLAN", iid, "Read this issue and create exactly one child with the required Parent annotation. Do not call workers or change labels.")
                except Exception as exc:
                    log("pm_error", iid=iid, stage="plan", error=type(exc).__name__)
                child = self.gitlab.child(iid)
            if not child:
                return self.attempt(iid, "plan", "PM did not create a verifiable child issue.", state)
            return self.advance(iid, state, "agent:build", "planned",
                                f"PM created child issue #{child['iid']}; builder assigned branch `{branch}`.")

        if not child:
            raise RuntimeError(f"issue {iid} reached {state} without a child issue")

        if state in ("agent:build", "agent:changes"):
            previous = None
            feedback = ""
            if state == "agent:changes":
                pipelines = self.gitlab.pages("/pipelines?" + urllib.parse.urlencode({"ref": branch}))
                latest_pipeline = pipelines[0] if pipelines else None
                if latest_pipeline and latest_pipeline["status"] not in ("success", "created", "pending", "preparing", "running", "waiting_for_resource"):
                    previous = latest_pipeline["sha"]
                    feedback = (f"GitLab pipeline {latest_pipeline['id']} ended "
                                f"{latest_pipeline['status']} on SHA {previous}. Inspect its failed job trace and correct CI.")
                mr = self.gitlab.mr(branch)
                if mr:
                    notes = self.gitlab.notes("merge_requests", mr["iid"])
                    reviews = sorted(
                        (note for note in notes if REVIEW_RE.search(note.get("body", ""))),
                        key=lambda item: item["id"], reverse=True)
                    rejected = [note for note in reviews
                                if "REVIEW_VERDICT: CHANGES_REQUESTED" in note.get("body", "")]
                    if len(rejected) >= 3:
                        return self.advance(iid, state, "agent:blocked", "review-limit",
                                            "Three rejected review cycles exhausted; human inspection required.")
                    if reviews:
                        if not previous:
                            previous = REVIEW_RE.search(reviews[0]["body"]).group(2)
                        feedback += "\nOutstanding reviewer feedback: " + reviews[0]["body"][:1200]
                        followups = [note for note in notes
                                     if note["id"] > reviews[0]["id"] and not note.get("system")]
                        if followups:
                            feedback += "\nFollow-up finding: " + max(
                                followups, key=lambda item: item["id"])["body"][:800]
            commit = self.committed(branch)
            if commit and (state == "agent:build" or commit[0] != previous):
                sha, paths = commit
                return self.advance(iid, state, "agent:test", "built-" + sha[:12],
                                    f"Builder commit `{sha}` on `{branch}` changed: {', '.join(paths)}. Tester assigned.")
            stage = "REWORK" if state == "agent:changes" else "BUILD"
            try:
                self.call_pm(stage, iid,
                             f"Child issue IID: {child['iid']}. Exact branch: {branch}. "
                             f"Delegate sdlc-builder once. Feedback: {feedback or 'none'}")
            except Exception as exc:
                log("pm_error", iid=iid, stage=stage.lower(), error=type(exc).__name__)
            commit = self.committed(branch)
            if not commit or (state == "agent:changes" and commit[0] == previous):
                return self.attempt(iid, stage.lower(), "No new verifiable branch commit after builder call.", state)
            sha, paths = commit
            return self.advance(iid, state, "agent:test", "built-" + sha[:12],
                                f"Builder commit `{sha}` on `{branch}` changed: {', '.join(paths)}. Tester assigned.")

        commit = self.committed(branch)
        if not commit:
            raise RuntimeError(f"issue {iid} reached {state} without a branch commit")
        sha, paths = commit
        pipeline = self.gitlab.pipeline(branch, sha)
        if not pipeline or pipeline["status"] in ("created", "pending", "preparing", "running", "waiting_for_resource"):
            log("waiting_ci", iid=iid, pipeline=pipeline["id"] if pipeline else None)
            return False
        if pipeline["status"] != "success":
            return self.advance(iid, state, "agent:changes", "ci-failed-" + sha[:12],
                                f"Pipeline {pipeline['id']} ended `{pipeline['status']}` on `{sha}`; builder rework assigned.")

        if state == "agent:test":
            try:
                reply = self.call_pm("TEST", iid,
                                     f"Child IID {child['iid']}; exact branch {branch}; SHA {sha}; "
                                     f"pipeline {pipeline['id']} is success; changed paths {', '.join(paths)}. "
                                     "Delegate sdlc-tester once. Return exactly TEST_VERDICT: PASS or BLOCKED.")
            except Exception as exc:
                log("pm_error", iid=iid, stage="test", error=type(exc).__name__)
                reply = ""
            if not re.search(r"(?m)^TEST_VERDICT:\s*PASS\s*$", reply):
                return self.attempt(iid, "test-" + sha[:12], "Tester PASS receipt missing after green CI.", state)
            return self.advance(iid, state, "agent:review", "tested-" + sha[:12],
                                f"Tester PASS for pipeline {pipeline['id']} on `{sha}`. Reviewer assigned.")

        if state == "agent:review":
            mr = self.gitlab.mr(branch)
            if not mr:
                try:
                    self.call_pm("MR", iid,
                                 f"Child IID {child['iid']}; branch {branch}; SHA {sha}; "
                                 f"pipeline {pipeline['id']} is success. Create exactly one draft MR. No reviewer call yet.")
                except Exception as exc:
                    log("pm_error", iid=iid, stage="mr", error=type(exc).__name__)
                mr = self.gitlab.mr(branch)
                if not mr:
                    return self.attempt(iid, "mr", "No draft MR exists after PM call.", state)
                self.gitlab.post_once(iid, "mr-" + sha[:12],
                                      f"Draft MR !{mr['iid']} opened for `{sha}`; reviewer queued.")
                return True
            if not mr.get("draft") or mr.get("sha") != sha:
                raise RuntimeError(f"MR !{mr['iid']} is not a draft at expected SHA")
            note, verdict = self.review_note(iid, mr["iid"], sha)
            if not note:
                try:
                    self.call_pm("REVIEW", iid,
                                 f"Child IID {child['iid']}; draft MR IID {mr['iid']}; "
                                 f"exact branch {branch}; full SHA {sha}; pipeline {pipeline['id']} success; "
                                 f"changed paths {', '.join(paths)}. Delegate reviewer once. "
                                 f"The MR note must contain <!-- sdlc-rig-review parent={iid} sha={sha} --> "
                                 "and a REVIEW_VERDICT line.")
                except Exception as exc:
                    log("pm_error", iid=iid, stage="review", error=type(exc).__name__)
                note, verdict = self.review_note(iid, mr["iid"], sha)
                if not note:
                    return self.attempt(iid, "review-" + sha[:12], "No tagged MR review note after PM call.", state)
                self.gitlab.post_once(iid, "reviewed-" + sha[:12],
                                      f"Reviewer note {note['id']} gave {verdict} on draft MR !{mr['iid']}.")
                return True
            if verdict == "CHANGES_REQUESTED":
                return self.advance(iid, state, "agent:changes", "review-changes-" + sha[:12],
                                    f"Reviewer note {note['id']} requested changes on draft MR !{mr['iid']}.")
            try:
                reply = self.call_pm("ACCEPT", iid,
                                     f"Child IID {child['iid']}; branch {branch}; SHA {sha}; "
                                     f"pipeline {pipeline['id']} success; draft MR !{mr['iid']}; "
                                     f"GitLab-verified reviewer PASS note {note['id']}. "
                                     "Finish with one unformatted line exactly PM_VERDICT: ACCEPT if "
                                     "all criteria pass, else PM_VERDICT: BLOCKED.")
            except Exception as exc:
                log("pm_error", iid=iid, stage="accept", error=type(exc).__name__)
                reply = ""
            if not re.search(r"(?m)^PM_VERDICT:\s*ACCEPT\s*$", reply):
                verdict_lines = [line[:100] for line in reply.splitlines()
                                 if line.strip().startswith("PM_VERDICT:")]
                log("missing_accept_receipt", iid=iid, verdict_lines=verdict_lines)
                return self.attempt(iid, "accept-" + sha[:12], "PM acceptance receipt missing.", state)
            return self.advance(iid, state, "agent:accepted", "accepted-" + sha[:12],
                                f"PM accepted child #{child['iid']}; pipeline {pipeline['id']} success, "
                                f"draft MR !{mr['iid']}, reviewer PASS note {note['id']}. Merge remains human owned.")
        return False


def main():
    token = os.environ["GITLAB_TOKEN"]
    project = os.environ["GITLAB_PROJECT_PATH"]
    pm_url = os.environ.get("PM_A2A_URL", "http://kagent-controller.kagent.svc.cluster.local:8083/api/a2a/sdlc-rig/sdlc-pm/")
    api_url = os.environ.get("GITLAB_API_URL", "https://gitlab.com/api/v4")
    target_branch = os.environ.get("GITLAB_TARGET_BRANCH", "main")
    allowed_paths = json.loads(os.environ.get("GITLAB_ALLOWED_FILES", json.dumps(sorted(ALLOWED_PATHS))))
    if not isinstance(allowed_paths, list) or not allowed_paths or not all(isinstance(p, str) for p in allowed_paths):
        raise ValueError("GITLAB_ALLOWED_FILES must be a nonempty JSON string array")
    board = Board(GitLab(token, project, api_url, target_branch), pm_url,
                  int(os.environ.get("A2A_TIMEOUT", "150")), target_branch, allowed_paths)
    lease = KubeLease() if os.environ.get("BOARD_LEASE_REQUIRED") == "true" else None
    if lease and not lease.acquire():
        log("lease_busy")
        return 0
    try:
        for issue in board.gitlab.queue():
            if board.process(issue):
                return 0
        log("idle")
        return 0
    finally:
        if lease:
            lease.release()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        log("fatal", error=type(exc).__name__, detail=str(exc)[:200])
        sys.exit(1)

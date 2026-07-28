#!/usr/bin/env python3
"""Durable, bounded Buzz -> kagent SDLC task controller.

This is deliberately a small policy-bearing adapter, not an autonomous agent.
It accepts one trusted Buzz task event at a time, persists its correlation to a
kagent A2A task, invokes an allowlisted coordinator, and emits a safe threaded
result.  Git, tests, staging and merge evidence are external deterministic
gates; a model response alone can never mark a task ready to merge.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Callable
from urllib import error, request


MAX_ATTEMPTS = 3
TERMINAL_STATES = {"completed", "failed", "input_required", "blocked"}


@dataclass(frozen=True)
class IncomingTask:
    source_event_id: str
    channel_id: str
    project: str
    issue_id: str
    title: str
    body: str

    @classmethod
    def from_json(cls, value: dict[str, object]) -> "IncomingTask":
        required = ("source_event_id", "channel_id", "project", "issue_id", "title", "body")
        missing = [key for key in required if not isinstance(value.get(key), str) or not value[key]]
        if missing:
            raise ValueError("missing required task fields: " + ", ".join(missing))
        return cls(**{key: value[key] for key in required})  # type: ignore[arg-type]


class Ledger:
    def __init__(self, path: str) -> None:
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                source_event_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                a2a_request_id TEXT NOT NULL,
                a2a_context_id TEXT NOT NULL,
                a2a_task_id TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                state TEXT NOT NULL,
                result TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )"""
        )
        self.connection.commit()

    def get(self, source_event_id: str) -> dict[str, object] | None:
        row = self.connection.execute(
            "SELECT source_event_id, channel_id, a2a_request_id, a2a_context_id, "
            "a2a_task_id, attempts, state, result FROM tasks WHERE source_event_id = ?",
            (source_event_id,),
        ).fetchone()
        if row is None:
            return None
        keys = ("source_event_id", "channel_id", "a2a_request_id", "a2a_context_id", "a2a_task_id", "attempts", "state", "result")
        return dict(zip(keys, row, strict=True))

    def create(self, task: IncomingTask) -> dict[str, object]:
        now = int(time.time())
        record = {
            "source_event_id": task.source_event_id,
            "channel_id": task.channel_id,
            "a2a_request_id": f"buzz-{uuid.uuid4()}",
            "a2a_context_id": f"buzz-{task.source_event_id}",
            "attempts": 0,
            "state": "accepted",
        }
        self.connection.execute(
            "INSERT INTO tasks (source_event_id, channel_id, a2a_request_id, a2a_context_id, attempts, state, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (*record.values(), now, now),
        )
        self.connection.commit()
        return record

    def update(self, source_event_id: str, *, state: str, task_id: str | None, result: str) -> dict[str, object]:
        self.connection.execute(
            "UPDATE tasks SET attempts = attempts + 1, state = ?, a2a_task_id = ?, result = ?, updated_at = ? "
            "WHERE source_event_id = ?",
            (state, task_id, result, int(time.time()), source_event_id),
        )
        self.connection.commit()
        record = self.get(source_event_id)
        assert record is not None
        return record


def safe_text(value: object, limit: int = 2000) -> str:
    """Keep error/result data renderable and avoid returning control characters."""
    text = str(value).replace("\x00", "").strip()
    return text[:limit]


def a2a_request(task: IncomingTask, record: dict[str, object]) -> dict[str, object]:
    # The source Buzz event is the required A2A messageId and the dedupe key.
    prompt = (
        "You are handling one bounded SDLC task. Return structured evidence, not a merge decision.\n"
        f"Project: {task.project}\nIssue: {task.issue_id} — {task.title}\n"
        f"Request:\n{task.body}\n\n"
        "Use your allowlisted role tools only. Do not run arbitrary shell commands, mutate "
        "infrastructure, merge code, or create follow-up work. If the work needs a follow-up, "
        "return FOLLOWUP_PROPOSED with a concise reason and dependency."
    )
    return {
        "jsonrpc": "2.0",
        "id": record["a2a_request_id"],
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "role": "user",
                "messageId": task.source_event_id,
                "parts": [{"kind": "text", "text": prompt}],
            },
            "metadata": {"contextId": record["a2a_context_id"], "conversationId": task.source_event_id},
        },
    }


def a2a_resume_request(record: dict[str, object], decision: str) -> dict[str, object]:
    if decision not in {"approve", "reject"} or not record.get("a2a_task_id"):
        raise ValueError("a pending A2A task and explicit approve/reject decision are required")
    return {"jsonrpc": "2.0", "id": f"buzz-resume-{uuid.uuid4()}", "method": "message/send",
            "params": {"message": {"kind": "message", "role": "user", "taskId": record["a2a_task_id"],
            "messageId": f"buzz-decision-{uuid.uuid4()}", "parts": [
                {"kind": "data", "data": {"decision_type": decision}, "metadata": {}},
                {"kind": "text", "text": f"Buzz approval decision: {decision}"}]},
            "metadata": {"contextId": record["a2a_context_id"], "conversationId": record["source_event_id"]}}}


def resume(source_event_id: str, decision: str, ledger: Ledger, invoke: Callable[[dict[str, object]], dict[str, object]]) -> dict[str, object]:
    record = ledger.get(source_event_id)
    if record is None or record["state"] != "input_required":
        raise ValueError("no pending approval for this source event")
    state, task_id, result = normalize_a2a(invoke(a2a_resume_request(record, decision)))
    return buzz_reply(ledger.update(source_event_id, state=state, task_id=task_id or str(record["a2a_task_id"]), result=result))


def post_json(url: str, payload: dict[str, object], timeout: int) -> dict[str, object]:
    body = json.dumps(payload).encode()
    req = request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as response:  # noqa: S310 -- allowlisted config URL
            return json.loads(response.read())
    except error.URLError as exc:
        raise RuntimeError(f"A2A transport failed: {exc.reason}") from exc


def normalize_a2a(response: dict[str, object]) -> tuple[str, str | None, str]:
    if "error" in response:
        return "failed", None, safe_text(response["error"])
    result = response.get("result")
    if not isinstance(result, dict):
        return "failed", None, "A2A response omitted result"
    status = result.get("status") if isinstance(result.get("status"), dict) else {}
    # A2A uses wire values such as input-required; the controller ledger uses
    # underscore names so internal approval handling is explicit and stable.
    state = str(status.get("state", "failed")).replace("-", "_")
    # kagent's BYO proxy returns the A2A task id in result.id; some runtimes
    # also mirror it in status.taskId. Preserve either form for same-task resume.
    task_id = status.get("taskId") or result.get("taskId") or result.get("id")
    artifacts = result.get("artifacts", [])
    parts = [part.get("text", "") for item in artifacts if isinstance(item, dict)
             for part in item.get("parts", []) if isinstance(part, dict) and part.get("text")]
    return state if state in TERMINAL_STATES else "failed", str(task_id) if task_id else None, safe_text("\n".join(parts) or state)


def buzz_reply(record: dict[str, object], *, duplicate: bool = False) -> dict[str, object]:
    state = str(record["state"])
    reply = {
        "schema": "buzz-kagent-sdlc.v1",
        "type": "sdlc.approval_required" if state == "input_required" else "sdlc.result",
        "reply_to": record["source_event_id"],
        "channel_id": record["channel_id"],
        "duplicate": duplicate,
        "a2a_request_id": record["a2a_request_id"],
        "a2a_context_id": record["a2a_context_id"],
        "a2a_task_id": record.get("a2a_task_id"),
        "state": state,
        "attempts": record["attempts"],
        "result": safe_text(record.get("result", "accepted")),
        "merge_eligible": False,
    }
    if state == "input_required":
        reply["approval"] = {
            "required": True,
            "resume_same_a2a_task": True,
            "instruction": "Reply with an explicit approved or rejected decision; the controller must resume the stored task/context.",
        }
    return reply


def handle(task: IncomingTask, ledger: Ledger, invoke: Callable[[dict[str, object]], dict[str, object]]) -> dict[str, object]:
    existing = ledger.get(task.source_event_id)
    if existing is not None:
        return buzz_reply(existing, duplicate=True)
    record = ledger.create(task)
    response = invoke(a2a_request(task, record))
    state, task_id, result = normalize_a2a(response)
    updated = ledger.update(task.source_event_id, state=state, task_id=task_id, result=result)
    return buzz_reply(updated)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: delivery_controller.py TASK.json", file=sys.stderr)
        return 2
    endpoint = os.environ.get("KAGENT_A2A_URL")
    database = os.environ.get("LEDGER_PATH", "buzz-kagent-sdlc.sqlite3")
    if not endpoint:
        print("KAGENT_A2A_URL is required", file=sys.stderr)
        return 2
    task = IncomingTask.from_json(json.loads(open(sys.argv[1], encoding="utf-8").read()))
    ledger = Ledger(database)
    print(json.dumps(handle(task, ledger, lambda payload: post_json(endpoint, payload, timeout=120)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

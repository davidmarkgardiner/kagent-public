#!/usr/bin/env python3
"""One bounded private-Buzz-channel intake pass for the kagent SDLC POC."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

from delivery_controller import IncomingTask, Ledger, handle, post_json, resume


def run_buzz(args: list[str], *, content: str | None = None) -> str:
    command = [os.environ.get("BUZZ_BIN", "buzz"), "--format", "json", *args]
    timeout = int(os.environ.get("BUZZ_COMMAND_TIMEOUT", "20"))
    try:
        completed = subprocess.run(command, input=content, text=True, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Buzz command exceeded {timeout}s: {' '.join(args[:2])}") from exc
    if completed.returncode:
        raise RuntimeError(f"Buzz command failed ({completed.returncode}): {completed.stderr.strip()}")
    return completed.stdout


def parse_task(event: dict[str, object], channel: str) -> IncomingTask | None:
    """Accept only explicitly schema-marked task requests from this channel."""
    if event.get("id") is None or event.get("content") is None:
        return None
    try:
        content = json.loads(str(event["content"]))
    except json.JSONDecodeError:
        return None
    if content.get("schema") != "buzz-kagent-sdlc.v1" or content.get("type") != "sdlc.task.request":
        return None
    return IncomingTask.from_json({
        "source_event_id": str(event["id"]), "channel_id": channel,
        "project": content.get("project"), "issue_id": content.get("issue_id"),
        "title": content.get("title"), "body": content.get("body"),
    })


def parse_decision(event: dict[str, object]) -> tuple[str, str, str] | None:
    """Return (decision_event_id, source_event_id, decision) for strict decisions."""
    try:
        content = json.loads(str(event["content"]))
    except (KeyError, json.JSONDecodeError):
        return None
    if content.get("schema") != "buzz-kagent-sdlc.v1" or content.get("type") != "sdlc.approval.decision":
        return None
    decision = content.get("decision")
    tags = event.get("tags", [])
    parents = [tag[1] for tag in tags if isinstance(tag, list) and len(tag) > 1 and tag[0] == "e"]
    source_event_id = content.get("source_event_id")
    decision_event_id = event.get("id")
    if (decision not in {"approve", "reject"} or not parents
            or not isinstance(source_event_id, str) or not isinstance(decision_event_id, str)):
        return None
    return decision_event_id, source_event_id, str(decision)


def process_once(channel: str, ledger: Ledger, invoke: Callable[[dict[str, object]], dict[str, object]], buzz: Callable[..., str] = run_buzz) -> int:
    events = json.loads(buzz(["messages", "get", "--channel", channel, "--limit", "50"]))
    processed = 0
    for event in events:
        task = parse_task(event, channel)
        if task is not None:
            reply = handle(task, ledger, invoke)
            reply_to = task.source_event_id
        else:
            parsed = parse_decision(event)
            if parsed is None:
                continue
            decision_event_id, reply_to, decision = parsed
            reply = resume(reply_to, decision, ledger, invoke, decision_event_id)
        # Only publish after the durable ledger update. A crash after publish is
        # safe: replayed intake returns the stored result rather than reinvoking.
        buzz(["messages", "send", "--channel", channel, "--reply-to", reply_to, "--content", "-"], content=json.dumps(reply))
        processed += 1
    return processed


def main() -> int:
    channel = os.environ.get("BUZZ_CHANNEL_ID")
    endpoint = os.environ.get("KAGENT_A2A_URL")
    if not channel or not endpoint:
        print("BUZZ_CHANNEL_ID and KAGENT_A2A_URL are required", file=sys.stderr)
        return 2
    ledger = Ledger(os.environ.get("LEDGER_PATH", str(Path("buzz-kagent-sdlc.sqlite3"))))
    count = process_once(channel, ledger, lambda payload: post_json(endpoint, payload, timeout=120))
    print(json.dumps({"processed": count}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

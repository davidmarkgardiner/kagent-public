#!/usr/bin/env python3
"""Disposable live Buzz -> A2A approval and same-task resume proof."""
from __future__ import annotations

import json
import os
import subprocess
import uuid

from buzz_bridge import process_once
from delivery_controller import Ledger, post_json

ADMIN = os.environ.get("BUZZ_ADMIN", "buzz-admin")
BUZZ = os.environ.get("BUZZ_BIN", "buzz")
RELAY = os.environ["BUZZ_RELAY_URL"]
ENDPOINT = os.environ["KAGENT_A2A_URL"]


def call(command: list[str], *, env: dict[str, str] | None = None, input: str | None = None) -> str:
    result = subprocess.run(command, text=True, input=input, env=env, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "command failed")
    return result.stdout


def keypair() -> tuple[str, str]:
    values = dict(line.split(":", 1) for line in call([ADMIN, "generate-key"]).splitlines() if ":" in line)
    return values["Secret key"].strip(), values["Public key"].strip()


def main() -> int:
    suffix = uuid.uuid4().hex[:12]
    identities = [keypair() for _ in range(3)]
    (bridge_secret, bridge_pub), (request_secret, request_pub), (approver_secret, approver_pub) = identities
    base = os.environ | {"BUZZ_RELAY_URL": RELAY}
    bridge_env = base | {"BUZZ_PRIVATE_KEY": bridge_secret}
    request_env = base | {"BUZZ_PRIVATE_KEY": request_secret}
    approver_env = base | {"BUZZ_PRIVATE_KEY": approver_secret}
    channel = None
    original_key = os.environ.get("BUZZ_PRIVATE_KEY")
    try:
        for pubkey in (bridge_pub, request_pub, approver_pub):
            call([ADMIN, "add-member", "--pubkey", pubkey, "--role", "member"])
        channel = json.loads(call([BUZZ, "channels", "create", "--name", f"buzz-kagent-approval-{suffix}", "--type", "stream", "--visibility", "private", "--description", "disposable approval proof"], env=bridge_env))["channel_id"]
        for pubkey in (request_pub, approver_pub):
            call([BUZZ, "channels", "add-member", "--channel", channel, "--pubkey", pubkey, "--role", "member"], env=bridge_env)
        task = {"schema": "buzz-kagent-sdlc.v1", "type": "sdlc.task.request", "project": "smoke", "issue_id": "#approval", "title": "Prove approval resume", "body": "Run the deterministic approval fixture only."}
        source_event_id = json.loads(call([BUZZ, "messages", "send", "--channel", channel, "--content", "-"], env=request_env, input=json.dumps(task)))["event_id"]
        os.environ["BUZZ_PRIVATE_KEY"] = bridge_secret
        ledger = Ledger(":memory:")
        first_count = process_once(channel, ledger, lambda payload: post_json(ENDPOINT, payload, timeout=30))
        thread = json.loads(call([BUZZ, "messages", "thread", "--channel", channel, "--event", source_event_id], env=bridge_env))
        approval_event = next((item for item in thread if json.loads(item.get("content", "{}")).get("type") == "sdlc.approval_required"), None)
        if first_count != 1 or approval_event is None:
            raise RuntimeError("approval request was not published")
        approval = json.loads(approval_event["content"])
        pending_task_id = approval.get("a2a_task_id")
        decision = {"schema": "buzz-kagent-sdlc.v1", "type": "sdlc.approval.decision", "source_event_id": source_event_id, "decision": "approve"}
        call([BUZZ, "messages", "send", "--channel", channel, "--reply-to", approval_event["id"], "--content", "-"], env=approver_env, input=json.dumps(decision))
        process_once(channel, ledger, lambda payload: post_json(ENDPOINT, payload, timeout=30))
        thread = json.loads(call([BUZZ, "messages", "thread", "--channel", channel, "--event", source_event_id], env=bridge_env))
        completed = [json.loads(item.get("content", "{}")) for item in thread if json.loads(item.get("content", "{}")).get("type") == "sdlc.result"]
        final = completed[-1] if completed else {}
        if final.get("state") != "completed" or final.get("a2a_task_id") != pending_task_id:
            raise RuntimeError("approval did not resume the same A2A task to completion")
        print(json.dumps({"live_approval_smoke": "passed", "source_event_id": source_event_id, "a2a_task_id": pending_task_id, "final_state": final["state"]}))
        return 0
    finally:
        if original_key is None:
            os.environ.pop("BUZZ_PRIVATE_KEY", None)
        else:
            os.environ["BUZZ_PRIVATE_KEY"] = original_key
        if channel:
            subprocess.run([BUZZ, "channels", "delete", "--channel", channel], env=bridge_env, capture_output=True, text=True)
        for _, pubkey in identities:
            subprocess.run([ADMIN, "remove-member", "--pubkey", pubkey], capture_output=True, text=True)


if __name__ == "__main__":
    raise SystemExit(main())

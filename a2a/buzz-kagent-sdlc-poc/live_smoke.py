#!/usr/bin/env python3
"""Disposable live Buzz -> kagent smoke. Secrets are never printed or written."""
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
    bridge_secret, bridge_pub = keypair()
    request_secret, request_pub = keypair()
    base = os.environ | {"BUZZ_RELAY_URL": RELAY}
    bridge_env, request_env = base | {"BUZZ_PRIVATE_KEY": bridge_secret}, base | {"BUZZ_PRIVATE_KEY": request_secret}
    channel = None
    original_key = os.environ.get("BUZZ_PRIVATE_KEY")
    try:
        for pubkey in (bridge_pub, request_pub):
            call([ADMIN, "add-member", "--pubkey", pubkey, "--role", "member"])
        channel = json.loads(call([BUZZ, "channels", "create", "--name", f"buzz-kagent-smoke-{suffix}", "--type", "stream", "--visibility", "private", "--description", "disposable bridge smoke"], env=bridge_env))["channel_id"]
        call([BUZZ, "channels", "add-member", "--channel", channel, "--pubkey", request_pub, "--role", "member"], env=bridge_env)
        request = {"schema": "buzz-kagent-sdlc.v1", "type": "sdlc.task.request", "project": "smoke", "issue_id": "#smoke", "title": "Return bounded SDLC evidence", "body": "Plan only. Do not change anything."}
        event_id = json.loads(call([BUZZ, "messages", "send", "--channel", channel, "--content", "-"], env=request_env, input=json.dumps(request)))["event_id"]
        # The bridge process owns this identity; it is restored before exit.
        os.environ["BUZZ_PRIVATE_KEY"] = bridge_secret
        count = process_once(channel, Ledger(":memory:"), lambda payload: post_json(ENDPOINT, payload, timeout=180))
        thread = json.loads(call([BUZZ, "messages", "thread", "--channel", channel, "--event", event_id], env=bridge_env))
        if count != 1 or not any(json.loads(item.get("content", "{}")).get("type") == "sdlc.result" for item in thread):
            raise RuntimeError("bridge result was not published in source thread")
        print(json.dumps({"live_smoke": "passed", "processed": count, "source_event_id": event_id}))
        return 0
    finally:
        if original_key is None:
            os.environ.pop("BUZZ_PRIVATE_KEY", None)
        else:
            os.environ["BUZZ_PRIVATE_KEY"] = original_key
        if channel:
            subprocess.run([BUZZ, "channels", "delete", "--channel", channel], env=bridge_env, capture_output=True, text=True)
        for pubkey in (bridge_pub, request_pub):
            subprocess.run([ADMIN, "remove-member", "--pubkey", pubkey], capture_output=True, text=True)


if __name__ == "__main__":
    raise SystemExit(main())

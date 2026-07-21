#!/usr/bin/env python3
"""Validate and normalize a GitLab Issue Note webhook for the feedback spike."""
import json
import sys


def labels(payload):
    issue = payload.get("issue") or {}
    values = issue.get("labels") or payload.get("labels") or []
    return {item.get("title", "") if isinstance(item, dict) else str(item) for item in values}


def result(accepted, reason, payload):
    note = payload.get("object_attributes") or {}
    user = payload.get("user") or {}
    text = (note.get("note") or "").strip()
    command = text.removeprefix("@platform-agent").strip()
    action = "approval_requested" if command.lower() == "approve" else "feedback"
    return {"accepted": accepted, "reason": reason, "action": action if accepted else "ignored", "note_id": str(note.get("id", "")), "issue_iid": str((payload.get("issue") or {}).get("iid", "")), "project_id": str(payload.get("project_id", "")), "author": user.get("username", ""), "feedback": command if accepted else ""}


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: validate-feedback.py PAYLOAD_JSON ALLOWED_USERS BOT_USERNAME")
    payload = json.loads(sys.argv[1])
    allowed = {value.strip() for value in sys.argv[2].split(",") if value.strip()}
    bot = sys.argv[3]
    note = payload.get("object_attributes") or {}
    user = payload.get("user") or {}
    text = (note.get("note") or "").strip()
    if payload.get("object_kind") != "note" or note.get("noteable_type") != "Issue":
        output = result(False, "not_an_issue_note", payload)
    elif user.get("username") == bot:
        output = result(False, "self_authored_note", payload)
    elif user.get("username") not in allowed:
        output = result(False, "author_not_allowlisted", payload)
    elif "agent:waiting-for-human" not in labels(payload):
        output = result(False, "issue_not_waiting_for_human", payload)
    elif not text.startswith("@platform-agent") or not text.removeprefix("@platform-agent").strip():
        output = result(False, "agent_not_mentioned", payload)
    else:
        output = result(True, "accepted", payload)
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()

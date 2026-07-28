"""A deterministic A2A approval fixture used only by the Buzz SDLC POC.

First message/send returns the A2A wire value input-required. A later message/send carrying a
decision_type data part for that same task returns a completed task. It makes
no model, filesystem, Git, Kubernetes, or network calls.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException

app = FastAPI()
tasks: dict[str, dict[str, str]] = {}


@app.get("/.well-known/agent-card.json")
async def agent_card() -> dict[str, Any]:
    return {
        "name": "Buzz SDLC deterministic approval fixture",
        "description": "Returns input_required once and completes on explicit decision.",
        "url": "http://buzz-sdlc-hitl-fixture.kagent:8080/",
        "version": "0.1.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
        "skills": [{"id": "approval-fixture", "name": "Approval fixture", "description": "Deterministic A2A approval/resume test."}],
    }


def message(text: str, message_id: str, task_id: str, context_id: str) -> dict[str, Any]:
    return {"kind": "message", "messageId": message_id, "taskId": task_id,
            "contextId": context_id, "role": "agent", "parts": [{"kind": "text", "text": text}]}


@app.post("/")
async def a2a(body: dict[str, Any]) -> dict[str, Any]:
    if body.get("method") != "message/send":
        raise HTTPException(400, "only message/send is supported")
    params = body.get("params", {})
    request_message = params.get("message", {})
    request_id = str(body.get("id", uuid.uuid4()))
    task_id = request_message.get("taskId")
    metadata = params.get("metadata", {})
    if not task_id:
        task_id = str(uuid.uuid4())
        context_id = str(metadata.get("contextId") or uuid.uuid4())
        tasks[task_id] = {"context_id": context_id}
        status_message = message(
            "Approval required for the simulated, non-mutating delete_file action.",
            f"approval-{task_id}", task_id, context_id,
        )
        status_message["parts"].append({"kind": "data", "data": {"action_requests": [{"name": "delete_file", "args": {"path": "/tmp/buzz-sdlc-probe"}}]}})
        result = {"kind": "task", "id": task_id, "contextId": context_id,
                  "status": {"state": "input-required", "taskId": task_id, "message": status_message}}
    else:
        task = tasks.get(str(task_id))
        if task is None:
            raise HTTPException(404, "unknown task")
        decision = next((part.get("data", {}).get("decision_type") for part in request_message.get("parts", [])
                         if isinstance(part, dict) and isinstance(part.get("data"), dict)), None)
        if decision not in {"approve", "reject"}:
            raise HTTPException(400, "explicit approve or reject decision required")
        text = f"Simulated delete_file action {'approved and completed' if decision == 'approve' else 'rejected; no action taken'}."
        context_id = task["context_id"]
        result = {"kind": "task", "id": task_id, "contextId": context_id,
                  "status": {"state": "completed", "taskId": task_id,
                             "message": message(text, f"completed-{task_id}", task_id, context_id)},
                  "artifacts": [{"parts": [{"kind": "text", "text": text}]}]}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}

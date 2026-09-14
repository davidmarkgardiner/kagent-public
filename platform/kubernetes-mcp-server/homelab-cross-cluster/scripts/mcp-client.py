#!/usr/bin/env python3
"""Deterministic, bounded Streamable HTTP client for the homelab proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Callable


HOST_ALIAS = "red-homelab"
TARGET_ALIAS = "proxmox-homelab"
ENDPOINT = "http://kubernetes-mcp-server.kubernetes-mcp-cross-cluster-poc.svc:8080/mcp"
EXPECTED_TOOLS = [
    "configuration_contexts_list",
    "events_list",
    "namespaces_list",
    "pods_get",
    "pods_list",
    "pods_list_in_namespace",
    "pods_log",
    "resources_get",
    "resources_list",
]
BLOCKED_TOOLS = [
    "configuration_view",
    "pods_exec",
    "resources_create_or_update",
    "resources_delete",
    "resources_scale",
]


class MCPError(RuntimeError):
    pass


def _decode_message(body: bytes, content_type: str) -> dict[str, Any] | None:
    if not body:
        return None
    text = body.decode("utf-8")
    if "text/event-stream" in content_type:
        messages = []
        for line in text.splitlines():
            if line.startswith("data:"):
                messages.append(json.loads(line[5:].strip()))
        if not messages:
            raise MCPError("Streamable HTTP response contained no data event")
        return messages[-1]
    return json.loads(text)


class HTTPTransport:
    def __init__(self, endpoint: str) -> None:
        if endpoint != ENDPOINT:
            raise MCPError("the client endpoint must be the fixed in-cluster Service")
        self.endpoint = endpoint
        self.session_id: str | None = None

    def __call__(self, payload: dict[str, Any], notification: bool = False) -> dict[str, Any] | None:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if response.headers.get("Mcp-Session-Id"):
                    self.session_id = response.headers["Mcp-Session-Id"]
                message = _decode_message(response.read(), response.headers.get("Content-Type", ""))
        except urllib.error.HTTPError as exc:
            message = _decode_message(exc.read(), exc.headers.get("Content-Type", ""))
            if message is None:
                raise MCPError("MCP request was rejected without a JSON response") from exc
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise MCPError("MCP transport failed") from exc
        if notification:
            return None
        if message is None:
            raise MCPError("MCP request returned no response")
        return message


def _rpc(
    transport: Callable[[dict[str, Any], bool], dict[str, Any] | None],
    request_id: int,
    method: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params
    response = transport(payload, False)
    if response is None:
        raise MCPError("missing JSON-RPC response")
    if "error" in response:
        raise MCPError("JSON-RPC request was rejected")
    result = response.get("result")
    if not isinstance(result, dict):
        raise MCPError("JSON-RPC result is malformed")
    return result


def _tool_call(
    transport: Callable[[dict[str, Any], bool], dict[str, Any] | None],
    request_id: int,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    result = _rpc(transport, request_id, "tools/call", {"name": name, "arguments": arguments})
    if result.get("isError") is True:
        raise MCPError("tool call was rejected")
    return result


def _structured(result: dict[str, Any]) -> Any:
    if "structuredContent" not in result:
        raise MCPError("tool result omitted structuredContent")
    return result["structuredContent"]


def _node_fingerprint(items: Any) -> tuple[int, str]:
    if not isinstance(items, list) or not items:
        raise MCPError("node result is empty or malformed")
    uids = []
    for item in items:
        if not isinstance(item, dict):
            raise MCPError("node result item is malformed")
        metadata = item.get("metadata")
        if not isinstance(metadata, dict) or not isinstance(metadata.get("uid"), str):
            raise MCPError("node result omitted a UID")
        uids.append(metadata["uid"])
    material = ("\n".join(sorted(uids)) + "\n").encode("utf-8")
    return len(uids), hashlib.sha256(material).hexdigest()


def run_proof(
    transport: Callable[[dict[str, Any], bool], dict[str, Any] | None],
    expected_fingerprints: dict[str, str],
) -> tuple[dict[str, Any], bool]:
    request_id = 1
    initialized = _rpc(
        transport,
        request_id,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "homelab-cross-cluster-proof", "version": "1"},
        },
    )
    if initialized.get("protocolVersion") not in {"2025-03-26", "2025-06-18"}:
        raise MCPError("server negotiated an unexpected MCP protocol")
    request_id += 1
    transport({"jsonrpc": "2.0", "method": "notifications/initialized"}, True)

    listed = _rpc(transport, request_id, "tools/list", {})
    request_id += 1
    tools = listed.get("tools")
    if not isinstance(tools, list):
        raise MCPError("tools/list response is malformed")
    tool_names = sorted(tool.get("name") for tool in tools if isinstance(tool, dict))
    if tool_names != EXPECTED_TOOLS:
        raise MCPError("advertised tool surface does not match the allowlist")

    contexts_result = _tool_call(transport, request_id, "configuration_contexts_list", {})
    request_id += 1
    contexts_payload = _structured(contexts_result)
    if not isinstance(contexts_payload, dict) or not isinstance(contexts_payload.get("contexts"), list):
        raise MCPError("context inventory is malformed")
    context_names = sorted(
        item.get("name") for item in contexts_payload["contexts"] if isinstance(item, dict)
    )
    if context_names != [TARGET_ALIAS, HOST_ALIAS]:
        raise MCPError("context inventory contains an unexpected alias")

    requests = []
    crossover_count = 0
    expected_counts = {HOST_ALIAS: 1, TARGET_ALIAS: 3}
    for sequence in range(1, 21):
        alias = HOST_ALIAS if sequence % 2 else TARGET_ALIAS
        result = _tool_call(
            transport,
            request_id,
            "resources_list",
            {"apiVersion": "v1", "kind": "Node", "context": alias},
        )
        request_id += 1
        count, fingerprint = _node_fingerprint(_structured(result))
        passed = count == expected_counts[alias] and fingerprint == expected_fingerprints[alias]
        if not passed:
            crossover_count += 1
        requests.append(
            {"sequence": sequence, "context": alias, "nodeCount": count, "status": "PASS" if passed else "FAIL"}
        )

    blocked_results = []
    blocked_ok = True
    for tool in BLOCKED_TOOLS:
        rejected = False
        try:
            _tool_call(transport, request_id, tool, {})
        except MCPError:
            rejected = True
        request_id += 1
        blocked_results.append({"tool": tool, "status": "REJECTED" if rejected else "FAIL"})
        blocked_ok = blocked_ok and rejected

    passed = crossover_count == 0 and blocked_ok
    summary = {
        "schema": "homelab-cross-cluster-mcp/v1",
        "status": "PASS" if passed else "FAIL",
        "contexts": [
            {"alias": HOST_ALIAS, "nodeCount": 1},
            {"alias": TARGET_ALIAS, "nodeCount": 3},
        ],
        "toolNames": tool_names,
        "blockedTools": blocked_results,
        "requests": requests,
        "crossoverCount": crossover_count,
    }
    return summary, passed


class FakeTransport:
    def __init__(self) -> None:
        self.nodes = {
            HOST_ALIAS: [{"metadata": {"uid": "fixture-red-node"}}],
            TARGET_ALIAS: [
                {"metadata": {"uid": "fixture-proxmox-node-a"}},
                {"metadata": {"uid": "fixture-proxmox-node-b"}},
                {"metadata": {"uid": "fixture-proxmox-node-c"}},
            ],
        }

    def __call__(self, payload: dict[str, Any], notification: bool = False) -> dict[str, Any] | None:
        if notification:
            return None
        method = payload["method"]
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": payload["id"], "result": {"protocolVersion": "2025-06-18"}}
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {"tools": [{"name": name} for name in EXPECTED_TOOLS]},
            }
        name = payload["params"]["name"]
        if name == "configuration_contexts_list":
            structured = {
                "defaultContext": HOST_ALIAS,
                "contexts": [{"name": HOST_ALIAS}, {"name": TARGET_ALIAS}],
            }
            return {"jsonrpc": "2.0", "id": payload["id"], "result": {"structuredContent": structured}}
        if name == "resources_list":
            alias = payload["params"]["arguments"]["context"]
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {"structuredContent": self.nodes[alias]},
            }
        return {"jsonrpc": "2.0", "id": payload["id"], "result": {"isError": True}}


def _expected_from_fake(fake: FakeTransport) -> dict[str, str]:
    return {alias: _node_fingerprint(items)[1] for alias, items in fake.nodes.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_test:
            fake = FakeTransport()
            summary, passed = run_proof(fake, _expected_from_fake(fake))
        else:
            if args.endpoint != ENDPOINT:
                raise MCPError("the fixed in-cluster endpoint is required")
            expected = {
                HOST_ALIAS: os.environ.get("RED_EXPECTED_SHA256", ""),
                TARGET_ALIAS: os.environ.get("PROXMOX_EXPECTED_SHA256", ""),
            }
            if any(re.fullmatch(r"[0-9a-f]{64}", value) is None for value in expected.values()):
                raise MCPError("controller-owned fingerprints are missing")
            summary, passed = run_proof(HTTPTransport(args.endpoint), expected)
    except MCPError:
        print(json.dumps({"schema": "homelab-cross-cluster-mcp/v1", "status": "FAIL"}, sort_keys=True))
        return 1

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

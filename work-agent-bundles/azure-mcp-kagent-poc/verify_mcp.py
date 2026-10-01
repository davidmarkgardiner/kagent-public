#!/usr/bin/env python3
"""Credential-free Streamable HTTP discovery and gateway enforcement probe."""
import datetime
import json
import pathlib
import urllib.error
import urllib.request


class Client:
    def __init__(self, url):
        self.url = url
        self.session = None
        self.protocol = "2025-03-26"
        self.counter = 0

    def request(self, method, params=None, notification=False):
        self.counter += 1
        payload = {"jsonrpc": "2.0", "method": method}
        if not notification:
            payload["id"] = self.counter
        if params is not None:
            payload["params"] = params
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        if method != "initialize":
            headers["MCP-Protocol-Version"] = self.protocol
        req = urllib.request.Request(self.url, json.dumps(payload).encode(), headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            self.session = response.headers.get("Mcp-Session-Id", self.session)
            if notification or response.status == 202:
                return {}
            if "text/event-stream" in response.headers.get("Content-Type", ""):
                # Read until our response; an SSE connection may stay open afterwards.
                for line in response:
                    if line.startswith(b"data:"):
                        item = json.loads(line[5:])
                        if item.get("id") == payload["id"]:
                            return item
                raise RuntimeError("SSE ended without response")
            return json.load(response)

    def initialize(self):
        result = self.request("initialize", {
            "protocolVersion": self.protocol,
            "capabilities": {},
            "clientInfo": {"name": "azure-mcp-kagent-poc", "version": "1"},
        })
        self.protocol = result["result"]["protocolVersion"]
        self.request("notifications/initialized", notification=True)
        return result["result"]["serverInfo"]

    def tools(self):
        tools, cursor = [], None
        for _ in range(10):
            result = self.request("tools/list", {"cursor": cursor} if cursor else {})["result"]
            tools.extend(result["tools"])
            cursor = result.get("nextCursor")
            if not cursor:
                return tools
        raise RuntimeError("Tool discovery exceeded pagination budget")

    def close(self):
        if self.session:
            req = urllib.request.Request(self.url, method="DELETE", headers={
                "Mcp-Session-Id": self.session, "MCP-Protocol-Version": self.protocol})
            try:
                urllib.request.urlopen(req, timeout=5).close()
            except urllib.error.HTTPError as error:
                if error.code not in (404, 405):
                    raise


def denied(result):
    return "error" in result or result.get("result", {}).get("isError") is True


def main():
    direct = Client("http://127.0.0.1:18081/mcp")
    gateway = Client("http://127.0.0.1:18080/azure/mcp")
    try:
        info = direct.initialize()
        gateway_info = gateway.initialize()
        upstream = direct.tools()
        expected = {"group_list", "group_resource_list", "monitor_activitylog_list"}
        # Tool identifiers are deliberately asserted, never guessed or silently rewritten.
        assert {t["name"] for t in upstream} == expected, "Upstream tool names changed; review schema"
        assert all(t.get("annotations", {}).get("readOnlyHint") is True for t in upstream), "Read-only annotation missing"
        exposed = gateway.tools()
        names = {t["name"] for t in exposed}
        # Gateways may prefix target identifiers. Record exact client-visible names.
        resource = [n for n in names if n.endswith("group_resource_list")]
        activity = [n for n in names if n.endswith("monitor_activitylog_list")]
        assert len(resource) == len(activity) == 1, "Approved tools missing or ambiguous"
        assert not any(n.endswith("group_list") for n in names), "Gateway exposed excluded tool"
        assert len(names) == 2, "Gateway exposed unexpected tools"
        # Missing mandatory scope must be rejected before an Azure operation.
        result = gateway.request("tools/call", {"name": resource[0], "arguments": {}})
        assert denied(result), "Missing required resource-group was accepted"
        serialized = json.dumps(result)
        assert "resource-group" in serialized, "Expected parameter validation error missing"
        checks = {}
        for candidate in ("group_list", "azure_group_list", "storage_account_create", "azure_storage_account_create"):
            try:
                checks[candidate] = denied(gateway.request("tools/call", {"name": candidate, "arguments": {}}))
            except urllib.error.HTTPError as error:
                checks[candidate] = error.code in (400, 403, 404)
        assert all(checks.values()), "Excluded or write tool was accepted"
        receipt = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "PASS_LOCAL_MCP_ONLY", "azure_operations_executed": False,
            "kagent_a2a_executed": False, "azure_mcp_server": info,
            "gateway_server": gateway_info, "upstream_tools": sorted(expected),
            "gateway_tools": sorted(names), "missing_required_parameter_rejected": True, "negative_calls_denied": checks,
        }
        target = pathlib.Path(__file__).parent / "evidence" / "local-mcp-receipt.json"
        target.write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2))
    finally:
        direct.close()
        gateway.close()


if __name__ == "__main__":
    main()

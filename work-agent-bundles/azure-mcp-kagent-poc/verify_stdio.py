#!/usr/bin/env python3
"""Probe a preinstalled azmcp binary without credentials, network, or npm install."""
import datetime
import json
import os
import pathlib
import selectors
import subprocess
import sys
import tempfile
import time

TOOLS = ["group_list", "group_resource_list", "monitor_activitylog_list"]


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 verify_stdio.py /absolute/path/to/azmcp")
    binary = str(pathlib.Path(sys.argv[1]).resolve(strict=True))
    with tempfile.TemporaryDirectory(prefix="azure-mcp-discovery-") as temporary:
        env = {"PATH": os.defpath, "HOME": temporary, "TMPDIR": temporary,
               "AZURE_MCP_COLLECT_TELEMETRY": "false",
               "AZURE_MCP_COLLECT_TELEMETRY_MICROSOFT": "false"}
        args = [binary, "server", "start", "--read-only", "--disable-proxy-tools"]
        for tool in TOOLS:
            args.extend(["--tool", tool])
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(args, env=env, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=errors, text=False)
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            counter = 0

            def request(method, params=None, notification=False):
                nonlocal counter
                counter += 1
                data = {"jsonrpc": "2.0", "method": method}
                if not notification:
                    data["id"] = counter
                if params is not None:
                    data["params"] = params
                process.stdin.write((json.dumps(data) + "\n").encode())
                process.stdin.flush()
                if notification:
                    return {}
                # Read bytes without buffered readline, so timeout also bounds partial lines.
                buffered = b""
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if not selector.select(timeout=1):
                        continue
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        raise RuntimeError("azmcp exited before responding")
                    buffered += chunk
                    while b"\n" in buffered:
                        line, buffered = buffered.split(b"\n", 1)
                        item = json.loads(line)
                        if item.get("id") == counter:
                            return item
                raise TimeoutError("azmcp did not respond within 30 seconds")

            try:
                initialized = request("initialize", {"protocolVersion": "2025-03-26",
                    "capabilities": {}, "clientInfo": {"name": "azure-mcp-poc", "version": "1"}})
                request("notifications/initialized", notification=True)
                tools = request("tools/list", {})["result"]["tools"]
                names = {t["name"] for t in tools}
                assert names == set(TOOLS), f"Unexpected tool identifiers: {sorted(names)}"
                assert all(t.get("annotations", {}).get("readOnlyHint") is True for t in tools)
                result = request("tools/call", {"name": "group_resource_list", "arguments": {}})
                assert "error" in result or result.get("result", {}).get("isError")
                assert "resource-group" in json.dumps(result), "Required-parameter rejection missing"
                negative = request("tools/call", {"name": "storage_account_create", "arguments": {}})
                assert "error" in negative or negative.get("result", {}).get("isError")
                receipt = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "status": "PASS_STDIO_DISCOVERY_ONLY", "azure_operations_executed": False,
                    "gateway_runtime_verified": False, "kagent_a2a_executed": False,
                    "server": initialized["result"]["serverInfo"], "tools": sorted(names),
                    "read_only_annotations": True, "missing_required_parameter_rejected": True,
                    "unregistered_write_tool_denied": True,
                    "parameter_names": {t["name"]: sorted(t["inputSchema"].get("properties", {})) for t in tools}}
                target = pathlib.Path(__file__).parent / "evidence" / "stdio-receipt.json"
                target.write_text(json.dumps(receipt, indent=2) + "\n")
                print(json.dumps(receipt, indent=2))
            finally:
                selector.close()
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    main()

"""Start the synthetic MCP server with a patched, non-Azure fixture token."""

import os
import sys

sys.path.insert(0, "/app")

os.environ["DENODO_HOST"] = "denodo.example.invalid"
os.environ["DENODO_DATABASE"] = "synthetic"
os.environ["DENODO_APPROVED_VIEW"] = "approved_namespace_inventory"

import jdbc  # noqa: E402

jdbc.access_token = lambda: "lab-token"

import server  # noqa: E402

server.mcp.run(transport="streamable-http", host="127.0.0.1", port=8000, path="/mcp", show_banner=False)

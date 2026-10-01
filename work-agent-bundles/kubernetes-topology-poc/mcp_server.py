"""MCP read tools over the same fresh Kubernetes graph as the local viewer.

Run with: KUBE_CONTEXT={{KUBE_CONTEXT}} mcp run mcp_server.py
"""

import json
import os
from pathlib import Path

from mcp.server import MCPServer

from topology import collect, neighborhood

mcp = MCPServer("kubernetes-topology")


def graph():
    context = os.environ.get("KUBE_CONTEXT")
    if not context:
        raise ValueError("KUBE_CONTEXT must name an explicit cluster")
    path = os.environ.get("KUBE_TOPOLOGY_KNOWLEDGE")
    knowledge = json.loads(Path(path).read_text()) if path else None
    return collect(context, knowledge)


@mcp.tool()
def find_connections(resource_id: str, depth: int = 1) -> dict:
    """Return bounded Kubernetes relationships, evidence, health, and snapshot freshness for one resource ID."""
    return neighborhood(graph(), resource_id, depth, limit=50)


@mcp.tool()
def find_namespace_health(namespace: str) -> dict:
    """Summarize the current tracked health of one namespace, without claiming application SLO health."""
    if not namespace or len(namespace) > 63 or "/" in namespace:
        raise ValueError("namespace must be a Kubernetes namespace name")
    snapshot = graph()
    selected = [node for node in snapshot["nodes"] if node["namespace"] == namespace]
    namespace_node = next((node for node in snapshot["nodes"]
                           if node["id"] == f"Namespace:{namespace}"), None)
    if not namespace_node:
        return {"status": "not_found", "namespace": namespace,
                "observed_at": snapshot["observed_at"], "complete": snapshot["complete"]}
    concerns = [{"id": node["id"], "health": node["health"]} for node in selected
                if node["health"] == "unhealthy"]
    return {"status": "found", "namespace": namespace, "health": namespace_node["health"],
            "tracked_resources": len(selected), "concerns": concerns[:50],
            "truncated": len(concerns) > 50, "observed_at": snapshot["observed_at"],
            "complete": snapshot["complete"]}


if __name__ == "__main__":
    # Local proof only. Deployment needs an authenticated Gateway and scoped
    # Kubernetes credentials before a remote agent can reach this endpoint.
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8766,
            stateless_http=True, json_response=True)

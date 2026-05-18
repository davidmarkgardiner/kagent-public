# Memory Integration — mcp-memory-server

Deployed 2026-05-18. Shared persistent knowledge graph for all kagent agents.

## Deployment

```bash
helm install mcp-memory-server oci://ghcr.io/foxj77/charts/mcp-memory-server \
  --namespace kagent -f platform/mcp-memory-server/helm-values.yaml
```

In-cluster endpoint: `http://mcp-memory-server.kagent.svc.cluster.local:3000/mcp`

## Wired Agents

| Agent | Access Tier | Tools |
|-------|-------------|-------|
| dev-coordinator-agent | Full RW | create_entities, create_relations, add_observations, search_nodes, open_nodes, read_graph |
| k8s-agent | Full RW | same |
| platform-knowledge-agent | Observe+Read | add_observations, search_nodes, open_nodes, read_graph |
| dev-coder-agent | Observe+Read | same |
| dev-reviewer-agent | Observe+Read | same |

## Wiring a New Agent

Add to the agent's `tools:` list:

```yaml
# Full RW (coordinator / resolver agents)
- type: McpServer
  mcpServer:
    apiGroup: kagent.dev
    kind: RemoteMCPServer
    name: memory-mcp
    toolNames: [create_entities, create_relations, add_observations, search_nodes, open_nodes, read_graph]

# Observe+Read (specialist agents)
- type: McpServer
  mcpServer:
    apiGroup: kagent.dev
    kind: RemoteMCPServer
    name: memory-mcp
    toolNames: [add_observations, search_nodes, open_nodes, read_graph]

# Read-only (general agents)
- type: McpServer
  mcpServer:
    apiGroup: kagent.dev
    kind: RemoteMCPServer
    name: memory-mcp
    toolNames: [search_nodes, open_nodes, read_graph]
```

## Entity Naming Convention

`agent-type/entity-slug` — e.g. `task/add-auth-middleware`, `incident/oom-2026-05-16`, `k8s/node-homelab`

## Known Limitation

Concurrent writes from multiple agents cause silent data loss (read-modify-write, no file lock). Use sequential writes or implement a write queue before high-concurrency deployment.

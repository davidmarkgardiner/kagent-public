# A2A Protocol

Agent-to-Agent (A2A) protocol enables kagent agents to collaborate and hand off tasks.

Upstream spec: https://a2aproject.org  
Upstream repo: https://github.com/google/a2a

## Usage in this repo

For the full MIL-126 demo of three agents, skill loading, A2A calls, and a
human approval gate, see [kagent-hitl-skills-demo](kagent-hitl-skills-demo/).

For a copyable platform-memory demo that combines shared `memory-mcp`, A2A
context continuity, and an Argo suspend/resume gate, see
[platform-memory-showcase-demo](platform-memory-showcase-demo/).

For a smart-triage coordinator fan-out demo with Kubernetes, network/Hubble,
Grafana, GitOps dry-run specialists, incident synthesis, and HITL proof
markers, see [smart-triage-fanout-demo](smart-triage-fanout-demo/).

All kagent agent-to-agent calls use:

- **Method:** `POST /api/a2a/kagent/{agent-name}/` (trailing slash REQUIRED — omitting it returns 404)
- **Protocol:** JSON-RPC 2.0
- **Method name:** `message/send`

### Request format

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{ "kind": "text", "text": "your message here" }]
    }
  }
}
```

Note: `parts` MUST include `"kind": "text"` — omitting it causes a parse error.

### Response

The agent's response is at: `result.artifacts[].parts[].text`

Status is at: `result.status.state`

## kagent Memory

kagent v0.8.0+ supports agent memory. See [memory-reference.md](memory-reference.md) for the full reference and [sanitized live evidence](../docs/kagent-memory/README.md) from the non-production validation.

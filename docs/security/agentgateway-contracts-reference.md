# agentgateway Contracts Reference

This note captures the agentgateway contracts used by
`governed-agent-runtime-epic.md` so reviewers have a repo-local reference point.

Source snapshot:

- Local upstream checkout: `../agentgateway`
- Files consulted:
  - `../agentgateway/README.md`
  - `../agentgateway/examples/authorization/README.md`
  - `../agentgateway/examples/authorization/config.yaml`

Refresh rule: treat this file as a local summary. Re-check the upstream files,
installed chart, and installed CRDs before changing production policy or
manifests.

## Gateway role

The upstream project describes agentgateway as a proxy for AI-native protocols:

- LLM traffic from agents to model providers.
- MCP traffic from agents to tool servers.
- A2A traffic between agents.

For this repo's governance epic, agentgateway is the central runtime control
point for authentication, authorization, routing, rate limiting, guardrails, and
telemetry.

## LLM gateway contract

Governance-relevant capabilities from the upstream README:

| Capability | Governance use |
|---|---|
| Unified model routing | Agents can use approved `ModelConfig` routes instead of direct provider endpoints. |
| Budget and spend controls | Token usage and rate limits can be attributed to teams, agents, and routes. |
| Prompt enrichment | Platform policy can add organization-wide instructions at the gateway. |
| Load balancing and failover | Gateway routes can shift between approved model backends without changing agent specs. |
| Guardrails | Prompt and content filtering can be applied centrally where supported. |
| OpenTelemetry | Requests can be logged, metered, traced, and used as compliance evidence. |

## MCP gateway contract

Governance-relevant capabilities from the upstream README and authorization
example:

| Capability | Governance use |
|---|---|
| MCP gatewaying and federation | Multiple MCP targets can sit behind a gateway route. |
| OAuth, JWT, and API-key authentication | Tool access can depend on user, workload, or agent identity. |
| CEL authorization | Policies can decide which caller may access which MCP tool. |
| `tools/list` filtering | Unauthorized tools are hidden during discovery. |
| `tools/call` denial | Unauthorized execution is blocked even if a caller attempts the call directly. |
| Transport support | HTTP, SSE, Streamable HTTP, stdio, and OpenAPI-derived tool paths may be supported depending on deployment mode and CRD version. |

Example policy shape from the local upstream authorization sample:

```yaml
mcpAuthorization:
  rules:
    - 'mcp.tool.name == "echo"'
    - 'jwt.sub == "test-user" && mcp.tool.name == "add"'
    - 'mcp.tool.name == "printEnv" && jwt.nested.key == "value"'
```

Governance interpretation:

- The policy can bind tool access to authenticated claims.
- The policy can filter discovery and deny execution.
- In production, plain caller-supplied headers are not sufficient identity
  unless the network path prevents spoofing.
- `ToolGrant` should be rendered into gateway MCP authorization rules so the
  grant is enforced at runtime, not only recorded in Git.

## A2A gateway contract

The upstream README describes agentgateway as supporting secure agent-to-agent
communication using A2A.

Governance interpretation:

- Treat A2A endpoints as privileged APIs.
- Every A2A route needs a caller/callee inventory entry, owner, purpose, expiry,
  identity requirement, and denial test.
- The installed CRD version matters. In this repo's current schema-gated demo
  notes, native gateway-side A2A authorization was not available on the tested
  release, so the identity gate is documented at the Istio/ingress layer while
  agentgateway provides routing, timeout, rate-limit, and telemetry.

## Current repo references

Use these repo-local files before jumping to the sibling upstream checkout:

| File | Purpose |
|---|---|
| `platform/agentgateway/README.md` | Local gateway deployment and runtime pattern. |
| `platform/agentgateway/DEMO-SCHEMA-GATE.md` | Installed CRD support verdicts and A2A/MCP caveats from prior validation. |
| `docs/agentgateway-mcp-tool-auth/TOOL-AUTH-DISCOVERY.md` | Repo-local design note for using agentgateway as MCP auth and discovery layer. |
| `docs/agentgateway-mcp-tool-auth/mcp-tool-auth-discovery-demo.yaml` | Demonstrative object flow for catalog, grant, gateway, and kagent resources. |

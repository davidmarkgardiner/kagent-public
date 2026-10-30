# OpenAPI-to-MCP compatibility

The copied bundle includes a direct HTTP route in
[21-http-api-route.yaml](../examples/21-http-api-route.yaml). That route keeps
the API as HTTP. It does not provide MCP tool discovery or conversion.

The repository's 14 May 2026 schema probe rejected
`AgentgatewayBackend.spec.mcp.targets[].openapi` on the inspected cluster.
The retained Argo conversion example therefore carries a do-not-apply warning.
This is historical evidence for that installation, not a current assessment
of the incoming team's cluster.

For an agent-consumable API, select one of these reviewed paths:

1. Verify native OpenAPI conversion against the installed Kubernetes CRD and
   runtime. Confirm exact exposed tool names and test both an allowed operation
   and an unapproved operation before advertising the route.
2. If native conversion is unavailable, implement a small MCP adapter for the
   selected read-only API operations. Register that adapter using
   [07-mcp-backend.yaml](../examples/07-mcp-backend.yaml) and the matching
   routing, identity, and resource-scope controls.

The [official standalone OpenAPI example](https://agentgateway.dev/docs/standalone/latest/integrations/mcp/servers/openapi/)
uses a different configuration mode. Its existence does not establish support
for a Kubernetes CRD field.

Optional online provenance is available in the repository's
[dated schema probe](https://github.com/davidmarkgardiner/kagent-public/blob/f3d7c8560e655298567a021207237cc294f382fb/platform/agentgateway/DEMO-SCHEMA-GATE.md)
and [blocked Argo example](https://github.com/davidmarkgardiner/kagent-public/blob/f3d7c8560e655298567a021207237cc294f382fb/platform/agentgateway/backend-argo-openapi-mcp.yaml).
Those files are not required to read or copy this bundle.

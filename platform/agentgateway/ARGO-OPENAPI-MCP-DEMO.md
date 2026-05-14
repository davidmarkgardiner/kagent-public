# Argo OpenAPI → MCP demo (PR 3 runbook)

Companion runbook for `backend-argo-openapi-mcp.yaml`,
`policy-argo-openapi-mcp.yaml`, `argo-openapi-spec-configmap.yaml`, and
`remotemcpserver-argo.yaml`.

The headline claim is: **"agentgateway can expose a REST API as MCP tools
to kagent agents, with gateway-side authorization, and no custom MCP
server."** Only make that claim in the PR description after every step
below is green.

## Schema verdict captured

Fill these from PR 0 (`DEMO-SCHEMA-GATE.md`) before applying anything:

| Capability | Verdict | Evidence |
|---|---|---|
| `agentgatewaybackend.spec.mcp.targets[].openapi` | UNVERIFIED | _paste `kubectl explain` first lines_ |
| OpenAPI sub-field name (`schema.configMapRef` / `.file` / `.inline`) | UNVERIFIED | _paste `kubectl explain ...targets.openapi.schema`_ |
| `agentgatewaypolicy.spec.backend.mcp.authorization` CEL | supported (locally) | `mcp-tool-auth-discovery-demo.yaml` already in repo |

If the OpenAPI target is `unsupported`:
- Stop here. Do not merge this set of files claiming "no custom MCP server".
- Either defer PR 3 until an agentgateway chart/CRD upgrade ships the
  field, or rewrite this PR as a thin Argo MCP shim (Service of a small
  MCP server that wraps argo-server REST). Update README + this file to
  reflect the new scope.

## Spec source captured

| Item | Value |
|---|---|
| Argo Server version on this cluster | UNVERIFIED (`kubectl get deploy -n argo argo-server -o jsonpath='{.spec.template.spec.containers[0].image}'`) |
| OpenAPI source URL | UNVERIFIED (live `argo-server/api/v1/docs/openapi.json` or release-tagged swagger.json) |
| Captured at | UNVERIFIED (ISO 8601) |
| ConfigMap `data.argo-openapi.json` checksum | `sha256: <fill in after population>` |

After populating, mirror those four lines into the annotations on
`argo-openapi-spec` (see `argo-openapi-spec-configmap.yaml`).

## Auth assumptions

| Question | Decision |
|---|---|
| Argo Server auth mode | UNVERIFIED (`--auth-mode=client` vs `server`) |
| Source of the bearer token | UNVERIFIED (e.g. `argo auth token` for SA `agentgateway-argo-reader`) |
| Token rotation strategy | UNVERIFIED |
| Argo SSO required for write tools? | UNVERIFIED |

If Argo runs with `--auth-mode=server` (no auth, trusted network), explicitly
record that here and remove the `argo-server-token` Secret from
`backend-argo-openapi-mcp.yaml` before applying. Do not ship a Secret whose
value is literally `Bearer REPLACE_WITH_ARGO_SERVER_TOKEN` to a cluster.

## Tool inventory

Run this after the ConfigMap is populated to confirm the policy operates
on the right tool names:

```bash
jq -r '.paths
  | to_entries[]
  | .value
  | to_entries[]
  | select(.value.operationId)
  | "\(.key | ascii_upcase)\t\(.value.operationId)"' \
  argo-openapi.json | sort
```

Update `policy-argo-openapi-mcp.yaml` if the real operationIds differ from
the placeholders (`WorkflowService_ListWorkflows`, etc.).

## Apply order

```bash
# Management cluster
kubectl apply -f argo-openapi-spec-configmap.yaml         # must NOT be the placeholder
kubectl apply -f backend-argo-openapi-mcp.yaml
kubectl apply -f policy-argo-openapi-mcp.yaml

# Worker cluster
kubectl apply -f remotemcpserver-argo.yaml
```

## Read-only smoke test (must pass)

```bash
kubectl port-forward -n agentgateway-system svc/ai-gateway 8080:80 &

# tools/list — should return only the read operations the policy allows
curl -s -X POST http://localhost:8080/openapi-mcp/argo \
  -H "Content-Type: application/json" \
  -H "x-kagent-agent: argo-workflows-agent" \
  -H "x-kagent-namespace: argo-demo" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list"}' | jq '.result.tools[].name'

# tools/call list — should return real workflow data
curl -s -X POST http://localhost:8080/openapi-mcp/argo \
  -H "Content-Type: application/json" \
  -H "x-kagent-agent: argo-workflows-agent" \
  -H "x-kagent-namespace: argo-demo" \
  -d '{"jsonrpc":"2.0","id":"2","method":"tools/call",
       "params":{"name":"WorkflowService_ListWorkflows",
                 "arguments":{"namespace":"argo-demo"}}}' | jq .
```

## Write-denial smoke test (must reject)

```bash
# Same agent but a non-allowlisted namespace — must be denied by CEL policy.
curl -s -X POST http://localhost:8080/openapi-mcp/argo \
  -H "Content-Type: application/json" \
  -H "x-kagent-agent: argo-workflows-agent" \
  -H "x-kagent-namespace: kube-system" \
  -d '{"jsonrpc":"2.0","id":"3","method":"tools/call",
       "params":{"name":"WorkflowService_SubmitWorkflow",
                 "arguments":{"namespace":"kube-system","workflow":{}}}}' \
  | jq .

# Wrong agent identity — must be denied.
curl -s -X POST http://localhost:8080/openapi-mcp/argo \
  -H "Content-Type: application/json" \
  -H "x-kagent-agent: unknown-agent" \
  -H "x-kagent-namespace: argo-demo" \
  -d '{"jsonrpc":"2.0","id":"4","method":"tools/list"}' | jq .

# tools/call against a tool that isn't in the allowlist (e.g. delete) — must be denied.
curl -s -X POST http://localhost:8080/openapi-mcp/argo \
  -H "Content-Type: application/json" \
  -H "x-kagent-agent: argo-workflows-agent" \
  -H "x-kagent-namespace: argo-demo" \
  -d '{"jsonrpc":"2.0","id":"5","method":"tools/call",
       "params":{"name":"WorkflowService_DeleteWorkflow",
                 "arguments":{"namespace":"argo-demo","name":"foo"}}}' \
  | jq .
```

Record the actual responses in the PR description so the reviewer can see
both the allow and deny outcomes.

## Rollback

```bash
# Worker
kubectl delete -f remotemcpserver-argo.yaml

# Management
kubectl delete -f policy-argo-openapi-mcp.yaml
kubectl delete -f backend-argo-openapi-mcp.yaml
kubectl delete -f argo-openapi-spec-configmap.yaml
```

agentgateway, kagent, and argo-server are untouched after rollback.

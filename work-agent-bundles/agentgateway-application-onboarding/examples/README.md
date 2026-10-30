# Configuration examples to copy with this bundle

These annotated YAML files are local to the work bundle. Copy the entire
`agentgateway-application-onboarding` folder, then open
`04-BYO-INTEGRATIONS-WALKTHROUGH.md`. No sibling checkout is needed to read the
walkthrough, configuration, intake forms, or acceptance checklist.

## Reading order

| File | What to explain |
|---|---|
| [00-model-backend-route.yaml](00-model-backend-route.yaml) | Register an OpenAI-compatible provider and rewrite the gateway path to its API path |
| [05-model-garden.yaml](05-model-garden.yaml) | Point a kagent model client at that gateway route |
| [07-mcp-backend.yaml](07-mcp-backend.yaml) | Register an existing MCP Service and its transport |
| [08-http-routes.yaml](08-http-routes.yaml) | Route MCP traffic and, separately, named A2A invocation traffic |
| [09-reference-grants.yaml](09-reference-grants.yaml) | Permit exact cross-namespace backend references |
| [06-remote-mcp.yaml](06-remote-mcp.yaml) | Connect kagent to the gateway MCP URL with a privately supplied credential |
| [10-entra-jwks.yaml](10-entra-jwks.yaml) | Retrieve signing keys over validated TLS |
| [12-application-to-agent-policy.yaml](12-application-to-agent-policy.yaml) | Illustrate app-to-agent identity checks |
| [13-agent-to-mcp-policy.yaml](13-agent-to-mcp-policy.yaml) | Illustrate separate agent-to-MCP identity and tool checks |
| [14-mcp-network-boundary.yaml](14-mcp-network-boundary.yaml) | Restrict MCP ingress to the intended gateway pods |
| [15-model-traffic-limits.yaml](15-model-traffic-limits.yaml) | Apply illustrative per-proxy model limits |
| [18-gateway-podmonitor.yaml](18-gateway-podmonitor.yaml) | Select gateway pods for Prometheus scraping |
| [21-http-api-route.yaml](21-http-api-route.yaml) | Route an approved HTTP method/path to a private API Service |

File numbers preserve the original meeting order. Missing numbers are
intentional. The A2A lane is optional background for an existing Agent. The
bundle does not create an Agent or install its runtime.

## Prerequisites and proof limits

These are adaptation examples, not a complete platform install. There is no
root Kustomization and no instruction to apply the directory wholesale.

- The platform supplies the namespaces, Gateway, and existing HTTPS listeners
  named `model`, `mcp`, `a2a`, and `api` for whichever lanes are selected.
- Existing model, MCP, API, and optional kagent controller services must match
  the chosen manifests. The API route is independent of the Kubernetes MCP
  example. No application or MCP server workload is installed by these files.
- The installed agentgateway and kagent CRDs must accept the selected fields.
  Gateway API, NetworkPolicy enforcement, and optional Prometheus Operator
  support are separate prerequisites.
- The model and API route files demonstrate routing only. Their caller
  authorization policies are not supplied. They must not be published until
  the platform adds and proves the intended identity and model/resource checks.
- The MCP and A2A identity policies illustrate Entra access-token validation.
  Verify actual token claim semantics and API-role assignments before adapting
  them. Do not assume an application's client ID equals its principal ID.
- The client and provider credential references have different purposes.
  Secret values, Entra provisioning, token acquisition, rotation, and client
  reload are intentionally external prerequisites. Keep their values out of Git.
- The MCP ingress example does not supply all cluster egress, API network
  boundaries, admission controls, or RBAC. Audit additive NetworkPolicies and
  ensure team administrators cannot defeat platform enforcement.
- Passing YAML parsing does not establish API-server acceptance or runtime
  authorization. Collect the local [acceptance checklist](../evidence/ACCEPTANCE-CHECKLIST.md)
  in the target environment before claiming availability.

## Configuration

Replace quoted `{{PLACEHOLDER}}` values privately during adaptation.

| Placeholder | Meaning |
|---|---|
| `MODEL_PROVIDER_HOST` | Approved upstream hostname without a scheme or path |
| `MODEL_DEPLOYMENT` | Approved model or deployment name |
| `MODEL_GATEWAY_HOST`, `MCP_GATEWAY_HOST` | Approved HTTPS gateway hostnames |
| `ENTRA_TENANT_ID` | Tenant trusted by the reviewed token policy |
| `MCP_API_CLIENT_ID`, `A2A_API_CLIENT_ID` | Correct audiences for the two APIs |
| `CHILD_AGENT_ID` | Illustrative child identity value. Map each claim to the actual issued token |
| `CALLER_UAMI_CLIENT_ID`, `CALLER_UAMI_PRINCIPAL_ID` | Distinct caller application and principal identifiers |
| `PROMETHEUS_RELEASE` | Label selected by the existing Prometheus installation |

Also review example object names, namespaces, listeners, Service ports, MCP
tool names, API roles, and network selectors. The credential Secret objects
named in files 00, 05, and 06 are prerequisites, not generated assets.

## Sources

Files 05 through 18 are copied from the
[Microsoft annotated YAML walkthrough](https://github.com/davidmarkgardiner/kagent-public/tree/f3d7c8560e655298567a021207237cc294f382fb/docs/demos/microsoft-2026-10-15/yaml-walkthrough).
Only file 05's gateway base path changes to `/team/v1` so it matches file 00.
Their original offline validation is historical, not a new target-runtime proof.

File 00 adapts the repository's OpenAI-compatible backend/HTTPRoute pattern
with placeholder provider values. File 21 adapts the official
[HTTP routing pattern](https://agentgateway.dev/docs/kubernetes/latest/documentation/quickstart/non-agentic-http/).
Both are presentation examples with local YAML validation only.

OpenAPI-to-MCP compatibility is documented in the local
[compatibility note](../reference/OPENAPI-COMPATIBILITY.md).

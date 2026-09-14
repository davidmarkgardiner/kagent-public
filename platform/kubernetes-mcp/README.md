# Kubernetes MCP production security boundary

This document records the security decision for replacing the remotely hosted
AKS-MCP service with `containers/kubernetes-mcp-server`. It covers the MCP
server and its cluster-credential path. Agent roles and remediation permissions
remain separate controls.

The target use is read-only Kubernetes triage and analysis across an approved
set of clusters. This design is suitable for production after the acceptance
tests in this document pass in the workplace environment.

## Decision

Use Kubernetes MCP for Kubernetes data-plane evidence. Do not use AKS-MCP
v0.0.20 as a remote server. That release supports local `stdio` only and removes
HTTP, SSE, OAuth, container images, and Kubernetes deployment support.

Kubernetes MCP narrows the deployed capability set because it uses native
Kubernetes clients and an exact tool allowlist. The previous AKS-MCP service
included broader `az`, `kubectl`, `helm`, `cilium`, and `hubble` command paths.

Kubernetes MCP does not replace Azure management-plane evidence. Keep AKS
detectors, Azure Monitor and control-plane logs, Advisor, Fleet, VMSS details,
and Azure network diagnostics behind separate, bounded Azure tools where those
capabilities are required.

## Accepted credential model

The credential job owns target-cluster discovery, authentication configuration,
validation, and publication. Kubernetes MCP only reads the completed
kubeconfig.

The production design must have these properties:

- The credential job publishes contexts only for clusters in the approved
  inventory. Subscription-wide discovery alone is not an allowlist.
- Each context has a stable, unique alias and an expected API endpoint and CA.
- The kubeconfig uses the approved workload identity path and contains no
  embedded long-lived token, client certificate, or client key.
- The pod mounts the kubeconfig read-only.
- The identity has read-only Kubernetes access to the resources needed for
  triage.
- Credential renewal and revocation fail closed. The previous validated
  credential remains active if a refresh fails.

`cluster_auth_mode=kubeconfig` means every Kubernetes API call uses the shared
MCP workload identity. This is an accepted service-identity model, not
per-caller delegation. Gateway audit data must retain the original caller,
tool, cluster context, and result.

## Required access controls

Apply each control independently:

1. The gateway authenticates every caller.
2. Gateway authorization permits only approved agent or workload identities to
   use the Kubernetes MCP route.
3. The gateway and the MCP server expose the same exact tool allowlist.
4. Network policy or workload-aware network authorization permits only the
   approved gateway workload to reach the MCP service.
5. The MCP server requires an approved context on every tool call.
6. Kubernetes RBAC remains the final resource authorization boundary on every
   target cluster.

Tool-name authorization does not authenticate a caller. Namespace-based
network policy also does not authenticate a workload. Use caller identity at
the gateway and workload identity or mTLS on the backend connection.

## MCP-specific differences from AKS-MCP

The following differences need explicit controls. They do not prevent the
migration.

### Remote HTTP endpoints

AKS-MCP v0.0.20 has no supported network listener. Kubernetes MCP v0.0.66
supports remote HTTP and exposes `/mcp`, `/sse`, `/message`, discovery routes,
and operational endpoints. Protect every reachable route. Keep health,
statistics, and metrics endpoints available only to approved monitoring
clients.

Use TLS or another authenticated encrypted connection wherever MCP results
cross a trust boundary. Reject direct calls that bypass the gateway.

### Cluster context selection

Kubernetes MCP v0.0.66 treats `context` as optional and otherwise uses the
kubeconfig's current context. Agent instructions cannot enforce the target.

The production path must reject an omitted, empty, unknown, or unauthorized
context before the MCP sends a Kubernetes API request. Implement this check in
the server or an argument-aware gateway adapter. Use one MCP endpoint per
cluster if the shared endpoint cannot enforce it.

### Generic resource reads

`resources_get` and `resources_list` accept arbitrary Kubernetes resource
kinds. Restrict their effective access with Kubernetes RBAC. Add MCP
`denied_resources` entries for Secrets, ConfigMaps, ServiceAccounts,
TokenRequests, and RBAC resources as a second control.

Test the MCP denial with an intentionally over-permitted canary identity. This
test proves that the MCP rule works even if target-cluster RBAC changes later.

### Configuration export

The `configuration_view` tool is marked read-only, but it can serialize raw
kubeconfig data. Do not enable the `config` toolset. Keep an exact non-empty
`enabled_tools` list and reject a direct `configuration_view` call.

An empty `enabled_tools` value means that the server does not filter the tools
in the selected toolsets. Deployment validation must reject an empty list.

### Output size and sensitive data

Read-only results can still contain credentials written to application logs,
attacker-controlled text, internal addresses, and workload metadata. Limit the
number of returned objects, pod-log lines, and client-visible response bytes.
Return explicit truncation metadata.

Keep production MCP logging below levels that record complete tool parameters,
results, or headers. Test logs and telemetry with synthetic credential and
prompt-injection canaries.

## Production acceptance tests

Run these tests through the deployed gateway and against the final image
digest:

1. Confirm that an unauthenticated request, an expired token, a wrong issuer,
   a wrong audience, and an unauthorized caller all fail.
2. Confirm that an approved caller can use only the approved Kubernetes MCP
   route and tools.
3. Confirm that a pod outside the approved gateway workload cannot reach any
   MCP HTTP endpoint.
4. Confirm that `/mcp`, `/sse`, `/message`, health, statistics, metrics, and
   discovery endpoints have the intended reachability and authentication.
5. Confirm that tool discovery returns exactly the approved tool names.
6. Confirm that `configuration_view`, mutation, exec, attach, port-forward,
   TokenRequest, Secret, ConfigMap, ServiceAccount, and RBAC access fail.
7. Confirm that omitted, empty, unknown, and unauthorized contexts fail before
   a Kubernetes API request occurs.
8. Run at least 20 alternating concurrent calls across two approved contexts.
   Confirm the target cluster for every response from API audit evidence.
9. Add an unapproved cluster to a configured subscription. Confirm that the
   credential job does not publish a context for it.
10. Exercise workload identity against at least two real AKS clusters. Confirm
    allowed reads, denied operations, renewal across token expiry, and failure
    after revocation.
11. Request oversized pod logs and large resource lists. Confirm the response
    byte limit, timeout, resource bound, and truncation result.
12. Confirm that audit records contain the caller, tool, approved context, and
    outcome without tokens or returned Kubernetes data.
13. Pin the runtime image by digest. Record its provenance, SBOM, signature
    result, and approved vulnerability scan.

Production approval requires all applicable tests to pass. Record any accepted
exception with an owner, an expiry date, and the compensating control.

## Evidence status

The public proof has already established these properties in a home lab:

- the exact eight-tool inventory;
- denied Secret, ServiceAccount, RBAC, mutation, pod-exec, and token-creation
  operations;
- explicit routing to two contexts; and
- 20 alternating gateway calls with no cluster crossover.

The home-lab proof does not establish workplace caller authentication, real AKS
workload identity, server-side missing-context rejection, the workplace cluster
inventory, or the final internal image. Collect those receipts before
production approval.

## Version snapshot and sources

This decision was checked against Kubernetes MCP v0.0.66 and AKS-MCP v0.0.20
on 2026-09-14. Recheck the selected release before production rollout.

- AKS-MCP v0.0.20 release:
  https://github.com/Azure/aks-mcp/releases/tag/v0.0.20
- AKS-MCP supported deployment and security model:
  https://github.com/Azure/aks-mcp/blob/v0.0.20/README.md
- Kubernetes MCP v0.0.66:
  https://github.com/containers/kubernetes-mcp-server/tree/v0.0.66
- Kubernetes MCP configuration:
  https://github.com/containers/kubernetes-mcp-server/blob/v0.0.66/docs/configuration.md
- Kubernetes MCP HTTP endpoints:
  https://github.com/containers/kubernetes-mcp-server/blob/v0.0.66/pkg/http/http.go
- Kubernetes MCP context handling:
  https://github.com/containers/kubernetes-mcp-server/blob/v0.0.66/pkg/mcp/tool_mutator.go
- Kubernetes MCP configuration tool:
  https://github.com/containers/kubernetes-mcp-server/blob/v0.0.66/pkg/toolsets/config/configuration.go

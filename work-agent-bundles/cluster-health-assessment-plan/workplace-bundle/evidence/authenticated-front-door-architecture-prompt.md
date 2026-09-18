# Architecture challenge: authenticated cluster-health agent access

Review this proposed trust design for a Kubernetes cluster-health bundle.

## Required outcome

- Only the Argo Workflow ServiceAccount may invoke the kagent A2A endpoint by default.
- The caller cannot choose another kagent namespace or agent.
- The investigator can read pods, bounded logs, events and workload state only in the same namespaces monitored by the collector.
- It may read node state, but cannot read Secrets, ConfigMaps, service-account tokens or RBAC objects and cannot mutate resources.
- The design must remain public-safe and require live negative tests before promotion.

## Proposed controls

1. Argo receives a one-hour projected ServiceAccount JWT with a dedicated audience.
2. A route-level AgentgatewayPolicy performs Strict JWT validation against the management-cluster OIDC issuer/JWKS and allows only `system:serviceaccount:argo-events:cluster-health-investigation-workflow`.
3. One POST-only HTTPRoute rewrites `/a2a/cluster-health/` to `/api/a2a/kagent/cluster-health-investigator/`; a ReferenceGrant permits only the named kagent Service.
4. The Workflow NetworkPolicy allows A2A egress to agentgateway, not directly to the kagent namespace.
5. The agent exposes only `call_kubectl`.
6. A dedicated AKS-MCP ServiceAccount receives a read-only ClusterRole through one RoleBinding per monitored namespace and a second narrow ClusterRoleBinding for node reads. The AKS-MCP chart's default broad ClusterRoleBinding must be disabled.
7. The Workflow validates payload namespaces are a subset of a checked-in ConfigMap generated from the same namespace inventory; Kubernetes RBAC remains the authoritative boundary.
8. Human/Entra access is not enabled in the default route.

Identify security or operability defects, especially authentication bypasses, confused-deputy paths, RBAC amplification, JWT validation mistakes, namespace drift, and version-sensitive agentgateway fields. Give concrete repairs and end with exactly one line:

ARCH_STATUS: APPROVED

or

ARCH_STATUS: REVISE

# Authenticated and namespace-scoped agent access

The default deployment is service-to-service only. The daily Argo Workflow is
the sole caller of the cluster-health kagent API. Human access is not enabled
by these manifests.

## Enforcement chain

```text
Argo Workflow ServiceAccount
  -> one-hour projected JWT for {{AGENTGATEWAY_AUDIENCE}}
  -> agentgateway Strict JWT validation
  -> exact ServiceAccount subject allow rule
  -> fixed POST /a2a/cluster-health/ route
  -> fixed kagent/cluster-health-investigator A2A endpoint
  -> call_kubectl only
  -> dedicated AKS-MCP ServiceAccount
  -> RoleBinding in each monitored namespace plus read-only node access
```

The event payload, agent prompt, `RemoteMCPServer.allowedNamespaces`, and MCP
tool list are not Kubernetes resource authorization boundaries. Kubernetes
RBAC on the MCP identity is authoritative. The Workflow additionally rejects
an alert whose `scope.namespaces` is not a subset of the checked-in namespace
inventory.

## Required platform configuration

1. Configure the agentgateway Gateway to accept `HTTPRoute` resources from
   `{{AGENTGATEWAY_NAMESPACE}}`. The named listener must be internal-only; the
   route is pinned to that listener and the in-cluster Service hostname.
2. Put the management cluster's exact OIDC issuer and public JWKS URI in the
   private values file. Use a dedicated `api://` audience. This is a Kubernetes
   projected-token audience string, not an Entra application registration or
   proof of a human identity.
3. Run AKS-MCP with the dedicated ServiceAccount named by
   `AKS_MCP_SERVICE_ACCOUNT_NAME` and `AKS_MCP_SERVICE_ACCOUNT_NAMESPACE`.
4. Disable the AKS-MCP chart's default RBAC creation/ClusterRoleBinding. Any
   additional binding on this ServiceAccount widens every agent call.
5. Configure AKS-MCP `accessLevel=readonly`, enable only the Kubernetes
   component required for `call_kubectl`, and set its `allowNamespaces` to the
   exact `fox-mesh/namespaces.json` list.
6. Do not grant the AKS-MCP Azure identity permission to retrieve cluster user
   or admin credentials, including
   `Microsoft.ContainerService/managedClusters/listClusterUserCredential/action`
   or `listClusterAdminCredential/action`. `call_az` is deliberately absent.
7. Use only the in-cluster ServiceAccount context. Do not mount a fleet
   kubeconfig or expose alternate contexts to `call_kubectl`.
8. Keep the kagent controller and MCP Services private. The Workflow egress
   policy permits the agentgateway namespace, not a direct controller path.

The supplied RBAC and NetworkPolicy are only for the current single-cluster
rehearsal, where manager, agent and worker API are in one cluster. If these are
split, stop: do not deploy these RoleBindings as if they crossed clusters.
Design a separately authenticated worker-side MCP endpoint, bind the identity
actually presented to that worker API to the same namespaced permissions, and
repeat every authorization and network test on each side.

The ServiceAccount subject gate is not a boundary against a principal that can
create pods, workflows, or TokenRequests as that ServiceAccount. Keep
`argo-events` tightly administered, use Argo workflow restrictions where
available, and review who can create pods/workflows or request tokens in that
namespace before promotion.

Also inventory principals that can create pods, exec or port-forward, use
service/pod proxy subresources, or change the Agent, RemoteMCPServer,
HTTPRoute, AgentgatewayPolicy, ReferenceGrant, ServiceAccount, RoleBinding, or
NetworkPolicy in `kagent`, `agentgateway-system`, `aks-mcp`, and `argo-events`.
Port-forward traffic is not constrained by NetworkPolicy. Any unexpected
principal or additive policy that reopens a denied path blocks promotion.

## Human access

Do not add people to the Workflow route. If interactive access is approved,
create a separate route and policy with Entra JWT validation, a dedicated app
role such as `Kagent.ClusterHealth.Invoke`, and the same fixed backend. Anyone
allowed to call remote AKS-MCP inherits that MCP process identity, so the role
must be limited to trusted SRE operators and the MCP identity must remain
least-privileged.

## Version gate

The exact `AgentgatewayPolicy` schema is version-sensitive. Before apply:

```bash
kubectl explain agentgatewaypolicy.spec.traffic.jwtAuthentication
kubectl explain agentgatewaypolicy.spec.traffic.authorization
kubectl apply --dry-run=server -f rendered/manager.yaml
```

If the installed CRD does not support both fields, stop. Do not deploy the
route unauthenticated. Upgrade agentgateway or use a separately reviewed Istio
JWT ingress policy as the identity enforcement point.

## Required negative proof

- no token and a wrong-audience token return `401`;
- a valid token for another ServiceAccount returns `403`;
- the dedicated MCP identity can read pods/logs/events in an approved
  namespace and nodes cluster-wide;
- it cannot read an unapproved namespace, Secrets, ConfigMaps, RBAC or tokens;
- it cannot create, patch, delete, exec or port-forward;
- it cannot use `nodes/proxy`, alternate kubeconfig contexts, or Azure
  credential-retrieval actions;
- `call_kubectl` rejects attempts to supply `--server`, `--token`,
  `--kubeconfig`, `--as`, or `--raw` and cannot select another context;
- the Workflow cannot connect directly to the kagent controller or MCP;
- one valid event still creates one bounded investigation.

Treat these as promotion gates, not documentation assertions.

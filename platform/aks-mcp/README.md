# AKS MCP — deployment and authentication

This directory deploys [AKS-MCP](https://github.com/Azure/aks-mcp), the MCP
server that exposes Azure-aware Kubernetes tools such as `call_kubectl` to
kagent. It documents the repository's intended identity model; every value
that is specific to an Azure environment remains a placeholder.

## The important distinction

Azure workload identity answers **which Azure identity the AKS-MCP process can
become**. It does not by itself grant access to Kubernetes APIs, make remote
clusters reachable, or give an agent the MCP tool.

```
kagent agent
  └─ RemoteMCPServer / ToolCatalogEntry ──HTTP──► AKS-MCP Service
                                                   │
                                                   ├─ Kubernetes ServiceAccount + Kubernetes RBAC
                                                   │     └─ Kubernetes API operations
                                                   │
                                                   └─ Azure Workload Identity → UAMI
                                                         └─ Azure Resource Manager / AKS operations
```

The agent does not mount the tool. It calls the in-cluster MCP endpoint. The
bootstrap catalog uses:

```text
http://aks-mcp.aks-mcp.svc.cluster.local:8000/mcp
```

See [`infra/byo-kagent/bootstrap-catalog/toolcatalogentry-aks-mcp.yaml`](../../infra/byo-kagent/bootstrap-catalog/toolcatalogentry-aks-mcp.yaml).

## How workload identity reaches the AKS-MCP container

When `workloadIdentity.enabled=true`, the chart:

1. annotates the AKS-MCP ServiceAccount with
   `azure.workload.identity/client-id: "{{UAMI_CLIENT_ID}}"`;
2. labels the pod template `azure.workload.identity/use: "true"`;
3. relies on the AKS workload-identity webhook to inject the projected
   service-account token and Azure identity environment into the pod at
   admission time; and
4. lets Azure AD exchange that projected token for an access token for the
   UAMI, provided a matching federated credential exists.

The projected token is injected by AKS; it is not a bespoke AKS-MCP volume in
this chart. `kubeconfig.enabled` is separate and only mounts the named
Kubernetes Secret at `/home/mcp/.kube`.

The trust tuple must match exactly:

```text
issuer:   the AKS cluster's OIDC issuer URL
subject:  system:serviceaccount:aks-mcp:aks-mcp
audience: api://AzureADTokenExchange
UAMI:     {{UAMI_NAME}}
```

The management-cluster ASO examples automate one `FederatedIdentityCredential`
per target cluster and ServiceAccount. See
[`infra/workload-identity/README.md`](../../infra/workload-identity/README.md)
and [`infra/workload-identity/02-federated-credentials.yaml`](../../infra/workload-identity/02-federated-credentials.yaml).

## Deployment models

| Model | Where AKS-MCP runs | Federation required | What remains to configure |
|---|---|---|---|
| Per-worker-cluster | Each worker cluster | That worker cluster's OIDC issuer → its local `aks-mcp` ServiceAccount | UAMI Azure roles and local Kubernetes RBAC |
| Central MCP | Management cluster | The management cluster's OIDC issuer → the central `aks-mcp` ServiceAccount | UAMI Azure roles, remote-cluster credential/context or supported connection path, and remote Kubernetes authorization |

Therefore, federating all worker-cluster issuers is sufficient only for the
first model. It does **not** automatically authorize a management-cluster MCP
pod to call worker-cluster Kubernetes APIs. The central deployment option is
explicitly treated as a separate readiness item in
[`observability/PRODUCTION-READINESS.md`](../../observability/PRODUCTION-READINESS.md).

## Required authorization bindings

Federation is authentication only. Configure both authorization planes:

| Plane | Required binding | Why |
|---|---|---|
| Azure | Assign the UAMI least-privilege Azure roles at the AKS resource or resource-group scope. `Reader` supports discovery; choose appropriate AKS cluster-user/admin and/or Azure Kubernetes RBAC permissions for the required operation. | AKS-MCP Azure/AKS API calls otherwise return authorization failures. |
| Kubernetes | Bind the AKS-MCP ServiceAccount to the required Kubernetes `Role`/`ClusterRole` on every API server it operates. | Kubernetes API authorization is independent of Azure token exchange. |
| Agent-to-tool | Give the agent an explicit tool allowlist through its MCP server reference. | A tool executes with AKS-MCP's permissions, not the agent pod's ServiceAccount permissions. |

The packaged chart creates a read-only `ClusterRole` and `ClusterRoleBinding`
by default. It deliberately excludes Secret reads unless
`rbac.includeSecrets=true` is explicitly approved. See
[`chart/templates/rbac.yaml`](chart/templates/rbac.yaml).

## Configuration

Example Helm values, with public-safe placeholders:

```yaml
azure:
  tenantId: "{{AZURE_TENANT_ID}}"
  clientId: "{{UAMI_CLIENT_ID}}"
  subscriptionId: "{{AZURE_SUBSCRIPTION_ID}}"

workloadIdentity:
  enabled: true

app:
  accessLevel: readonly

rbac:
  create: true
  includeSecrets: false
```

Before deployment, verify that the target AKS cluster has OIDC issuer and
workload identity enabled, the workload-identity webhook is running, the
ServiceAccount subject matches the Azure federated credential, and the UAMI
has the necessary Azure role assignments. A pod restart is required after
changing the pod label, ServiceAccount annotation, or federated credential.

## Local validation

Render the chart without a cluster:

```bash
helm template aks-mcp ./chart \
  --namespace aks-mcp \
  --set workloadIdentity.enabled=true \
  --set-string azure.tenantId=AZURE_TENANT_ID \
  --set-string azure.clientId=UAMI_CLIENT_ID \
  --set-string azure.subscriptionId=AZURE_SUBSCRIPTION_ID \
  > /tmp/aks-mcp-rendered.yaml
```

Confirm the rendered deployment carries `azure.workload.identity/use: "true"`,
the ServiceAccount carries the UAMI client-ID annotation, and the rendered RBAC
matches the intended access level. Use server-side dry-run only against an
approved compatible cluster:

```bash
kubectl apply --dry-run=server -f /tmp/aks-mcp-rendered.yaml
```

### Evidence from the local chart build

The chart was rendered on 2026-07-22 with workload identity enabled and
placeholder-only values. The following checks passed:

| Check | Result |
|---|---|
| `helm lint platform/aks-mcp/chart` | 1 chart linted; 0 failed |
| `helm template` with workload identity enabled | Render succeeded |
| Rendered pod label | `azure.workload.identity/use: "true"` present |
| Rendered ServiceAccount annotation | `azure.workload.identity/client-id: "UAMI_CLIENT_ID"` present |
| Rendered authorization | `ClusterRoleBinding` present; default RBAC contains no Secret-read rule |
| `scripts/lint-yaml.sh --quiet` | 7 files checked; 0 failed |

This is an offline rendering check, not proof that a live cluster has its OIDC
issuer, webhook, federated credential, Azure role assignments, or remote API
connectivity configured.

## Quick start

```bash
helm upgrade --install aks-mcp ./chart \
  --namespace aks-mcp --create-namespace \
  -f chart/values.yaml
```

When specifying `toolNames` in `RemoteMCPServer`, list tools explicitly;
`None` causes a validation error.

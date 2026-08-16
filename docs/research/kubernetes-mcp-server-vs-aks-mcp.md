# Kubernetes MCP Server vs AKS-MCP — source-backed comparison

Research report for [issue #83](https://github.com/davidmarkgardiner/kagent-public/issues/83):
evaluate [containers/kubernetes-mcp-server](https://github.com/containers/kubernetes-mcp-server/tree/3b7a4da9d8f59565d7d72a64695949e2798b6c49)
("Kubernetes MCP Server") against [Azure/aks-mcp](https://github.com/Azure/aks-mcp/tree/8d28bece75d1f572293364d7f50a7e9d2e425efa) for this
platform, and decide complement / replace / named read-only role / do not use.

This issue is documentation-only. It runs no `kubectl` command, contacts no cluster, deploys
nothing, creates no identity or credential, and changes no RBAC. It adds exactly one document;
the POC below is a design to be reviewed and executed only in a future, separately approved
change.

Upstream revisions inspected (all upstream claims are pinned to these commits; they are
versioned research, not evidence about any live platform):

- `containers/kubernetes-mcp-server` at `3b7a4da9d8f59565d7d72a64695949e2798b6c49`
- `Azure/aks-mcp` at `8d28bece75d1f572293364d7f50a7e9d2e425efa`

Checked-out repository evidence is limited to `platform/aks-mcp/` (including the bootstrap-catalog
entry its README references), `platform/agentgateway/`, `infra/workload-identity/`, `agents/`,
and the shared helper scripts named by the plan.

## Executive recommendation

**Complement — do not replace.** Adopt Kubernetes MCP Server, if at all, only as a separately
bounded, non-production Kubernetes workload-inspection server serving a named
`kubernetes-readonly-triage` role, and only after the POC evidence gates in this report pass.
AKS-MCP's Azure/AKS-specific diagnostic and control-plane capability (ARM, AKS cluster and
nodepool operations, Azure networking, Fleet, Azure Monitor detectors, Advisor) has no
equivalent in the general Kubernetes server, so no current-tool removal follows from this
report.

Two constraints frame the decision:

1. **Current upstream AKS-MCP is a local, single-trusted-user stdio tool.** At the pinned
   revision, upstream states that AKS-MCP is designed to be run locally by a single trusted
   user, supports only stdio, and must not be exposed through HTTP, SSE, a container service,
   Helm, Kubernetes, a proxy, or a gateway; anyone who can invoke its tools effectively holds
   the full Azure and Kubernetes privileges of the server-process identity
   ([aks-mcp README](https://github.com/Azure/aks-mcp/blob/8d28bece75d1f572293364d7f50a7e9d2e425efa/README.md)).
   The repository's existing networked `platform/aks-mcp/` chart (in-cluster Deployment,
   streamable-HTTP Service, kagent `RemoteMCPServer`/`ToolCatalogEntry` wiring) is therefore a
   **repository-local pattern** built on an older upstream release; it must not be extended or
   represented as current upstream-supported architecture, and any future continuation of that
   pattern needs its own explicit risk acceptance against the upstream security boundary
   statement.
2. **Kubernetes MCP Server is favourable only as a bounded read-only complement.** It is a
   native Kubernetes API client (not a `kubectl` wrapper) with an explicit read-only mode,
   toolset/tool allowlisting, denied-resource filtering, an in-cluster ServiceAccount provider,
   streamable HTTP/SSE transports, and optional OIDC client authentication
   ([README](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/README.md),
   [configuration.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/configuration.md)).
   It has no Azure ARM/AKS surface, so it cannot replace AKS-MCP for Azure control-plane or
   cluster-lifecycle questions, and its write/exec/Helm/config capabilities mean a default
   deployment is broader than the platform's read-only triage need (see the defaults callout
   under Capability comparison).

The recommendation is conditional on the Bounded POC design gates below. Nothing in this issue
authorizes production adoption.

## Capability comparison

| Dimension | Kubernetes MCP Server (`3b7a4da`) | AKS-MCP current upstream (`8d28bec`) | Repository AKS-MCP chart pattern (local) |
|---|---|---|---|
| Operational focus | Generic Kubernetes/OpenShift resource operations: pods, events, generic resources, optional Helm/Tekton/Kiali/KubeVirt toolsets | Azure/AKS-centric operations via `call_az`, `call_kubectl` and Azure-aware diagnostic tools | Same AKS-MCP tool family as upstream, deployed in-cluster |
| Implementation | Go native Kubernetes API client; core tools call the API server directly, no CLI dependency ([README](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/README.md)) | Executes `az`/`kubectl`/`helm`/`cilium`/`hubble` CLI commands using the server-process identity ([aks-mcp README](https://github.com/Azure/aks-mcp/blob/8d28bece75d1f572293364d7f50a7e9d2e425efa/README.md)) | Containerized AKS-MCP Deployment with `streamable-http` transport, port 8000 (`platform/aks-mcp/chart/values.yaml`) |
| Read-only Kubernetes triage | `pods_list_in_namespace`, `pods_get`, `pods_log`, `events_list` plus generic `resources_get`/`resources_list` in the `core` toolset ([README tools](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/README.md)) | Kubernetes reach via `call_kubectl` and debugging surfaces | `call_kubectl` over the in-cluster HTTP endpoint |
| Azure/AKS control plane | None — out of scope by design | ARM/AKS CRUD, nodepools, VNets/NSGs/subnets, Fleet, Azure Monitor/detectors, VMSS, Advisor, Cilium/Hubble | Same components selectable via `config.enabledComponents` (`az_cli`, `monitor`, `fleet`, `network`, `compute`, `detectors`, `advisor`, `inspektorgadget`, `kubectl`, `helm`, `cilium`, `hubble`) |
| Explicit tool controls | `read_only`, `disable_destructive`, `toolsets`, `enabled_tools` allowlist, `disabled_tools` denylist, `denied_resources` GVK filters, `--disable-multi-cluster` ([configuration.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/configuration.md)) | `--access-level` (guardrail, explicitly not a security boundary), `AZURE_ENABLED_COMPONENTS`, credential-command denylist (explicitly not a security boundary) | Chart `app.accessLevel`, `config.enabledComponents`, `config.allowNamespaces` (`platform/aks-mcp/chart/values.yaml`) |
| Connection model | In-cluster ServiceAccount provider or kubeconfig provider; stdio when local, streamable HTTP (`/mcp`) and SSE (`/sse`) when `--port` is set ([configuration.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/configuration.md)) | Local stdio subprocess only; remote/HTTP deployment removed and explicitly unsupported | In-cluster pod, ClusterIP Service, optional ingress, optional kubeconfig Secret mounted at `/home/mcp/.kube`; documented central-MCP topology reaching worker clusters (`platform/aks-mcp/README.md`) |
| Multi-cluster | Enabled by default under the kubeconfig provider (every tool gains a `context` argument); disabled with `--disable-multi-cluster` | Possible through credential/context connection paths | Central management-cluster MCP reaching worker APIs is the documented local pattern |
| Observability | Optional OpenTelemetry tracing/metrics (tool name, status, duration; HTTP request traces) and a `/stats` endpoint; log redaction is best-effort ([OTEL.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/OTEL.md), [logging.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/logging.md)) | Not assessed beyond the pinned README (no equivalent claims made here) | Repository Agent Gateway/kagent monitoring pattern (`platform/agentgateway/monitoring.yaml`, `platform/agentgateway/kagent-values-otel.yaml`) |
| kagent / gateway fit | HTTP endpoint suits a kagent `RemoteMCPServer` (`STREAMABLE_HTTP`) with explicit `toolNames`, behind an Agent Gateway MCP policy that filters `tools/list`/`tools/call` | Current upstream stdio cannot serve a kagent `RemoteMCPServer` HTTP route | Existing wired example: `infra/byo-kagent/bootstrap-catalog/toolcatalogentry-aks-mcp.yaml` and `platform/aks-mcp/README.md` |

### Defaults that must be overridden

The candidate's defaults are broader than the platform's read-only triage need, and each of
these facts is pinned to the inspected revision:

- **Toolsets default to `config` and `core`.** The `config` toolset's `configuration_view`
  returns the current kubeconfig content as YAML — including credential material — so it must
  never be enabled on a shared server ([README tools](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/README.md)).
- **`core` is larger than the POC needs.** It includes `pods_delete`, `pods_exec`, `pods_run`,
  `resources_create_or_update`, `resources_delete`, `resources_scale`, and `nodes_log`
  (kubelet API proxy access) alongside the read-only tools.
- **HTTP listener defaults to all interfaces** (`bind_address = "0.0.0.0"`), with a logged
  warning only when combined with no TLS and no OAuth
  ([configuration.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/configuration.md)).
- **The chart defaults are expansive:** image tag defaults to `latest` and the ingress is
  enabled by default ([chart values](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/charts/kubernetes-mcp-server/values.yaml)).

Do not read any of the candidate's controls as authorization. `read_only` only hides tools
annotated `readOnlyHint`; `enabled_tools`/`denied_resources` only shape the tool surface. MCP
tool discovery and tool hints are not Kubernetes RBAC: what a call may actually do on the API
server is decided solely by the identity the server presents and the Role/RoleBinding bound to
it ([Kubernetes RBAC docs](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)).

## Authentication and authorization

Four distinct identity paths appear in this comparison. They answer different questions and
must not be collapsed into one "workload identity" narrative.

| # | Path | Authenticates | Authorizes | Where it applies here |
|---|---|---|---|---|
| 1 | **Kubernetes ServiceAccount + Kubernetes RBAC** | The server pod to the *local Kubernetes API*, via the projected ServiceAccount token (in-cluster provider) | A Role/RoleBinding (or a consciously justified ClusterRoleBinding) bound to that ServiceAccount | The only Kubernetes API identity and authorization path in the proposed POC. The candidate chart auto-mounts the token by default for exactly this in-cluster use ([chart values](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/charts/kubernetes-mcp-server/values.yaml)); the upstream getting-started guide also models a dedicated read-only ServiceAccount ([getting-started-kubernetes.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/getting-started-kubernetes.md)) |
| 2 | **Azure UAMI / Microsoft Entra Workload Identity (for Azure APIs)** | A workload's projected token, exchanged by Entra ID federation (issuer + `system:serviceaccount:*` subject, audience `api://AzureADTokenExchange`) for an Azure identity token | Azure RBAC roles assigned to the UAMI at an AKS/resource-group scope | Authorizes ARM/AKS API operations only. It does not authenticate the server to Kubernetes APIs and confers no Kubernetes RBAC. This is the path the repository's AKS-MCP chart documents (`platform/aks-mcp/README.md`, `infra/workload-identity/README.md`) and one of the ordered modes current upstream AKS-MCP uses for `az login` (`AZURE_FEDERATED_TOKEN_FILE` federated-token login in its [README](https://github.com/Azure/aks-mcp/blob/8d28bece75d1f572293364d7f50a7e9d2e425efa/README.md)); federation mechanics per [AKS workload identity docs](https://learn.microsoft.com/azure/aks/workload-identity-overview) |
| 3 | **kubeconfig or kubelogin paths** | A client or server to a Kubernetes API via a kubeconfig credential (static token/cert, exec plugin, or Entra token via kubelogin) | Whatever subject that credential maps to on the target cluster | An alternate Kubernetes API credential/connection path. The candidate supports a kubeconfig provider, and reaching a *remote* cluster from a pod requires an explicitly mounted kubeconfig plus `cluster_provider_strategy = "kubeconfig"` ([configuration.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/configuration.md)). Any kubelogin/exec arrangement is a credential dependency *inside* the kubeconfig, not proof that the server natively presents a UAMI as its Kubernetes API identity. The inspected upstream candidate documentation establishes no direct UAMI-to-AKS-Kubernetes-API mode: treat it as unsupported/unproven for this decision and exclude it from the POC. A mounted kubeconfig also broadens credential and target-cluster exposure (the local AKS-MCP chart mounts one at `/home/mcp/.kube` when enabled); a kubeconfig must never be placed in this report |
| 4 | **Client OIDC to the MCP server** | An MCP client/caller to the *HTTP server*, separately from the server's own Kubernetes API identity | Nothing on the Kubernetes API; it only gates entry to the server | The candidate supports optional Entra OIDC with on-behalf-of token exchange or passthrough modes ([ENTRA_ID_SETUP.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/ENTRA_ID_SETUP.md)), and explicitly rejects `require_oauth = true` combined with shared-ServiceAccount cluster access (`cluster_auth_mode = "kubeconfig"`) at startup because a single ServiceAccount collapses per-user audit identity. For the machine-to-machine POC, Agent Gateway's strict JWT/OIDC front-door policy is the client-authentication boundary — applied only after installed-CRD validation — and it changes nothing about Kubernetes API authorization (`platform/agentgateway/AUTHENTICATION.md`) |

### Agent tool lists versus runtime enforcement

A kagent agent's `toolNames` list (as in
`agents/skills/responsible-kagent-operation/assets/responsible-readonly-triage-agent.yaml`) is
a useful narrowing control and should be retained, but it is a client-side declaration: it is
not the enforcement point. The intended independent allowlist is the Agent Gateway MCP policy
filtering `tools/list` and `tools/call` for the route, with Kubernetes RBAC as the final
authority on the API server. The `agentgatewaypolicy.spec.backend.mcp.authorization` CEL shape
is recorded as supported on the one cluster inspected to date, while other MCP target shapes
were not — so every future MCP route/policy needs a fresh schema gate against the installed
CRD (`platform/agentgateway/DEMO-SCHEMA-GATE.md`, `platform/agentgateway/policy-argo-openapi-mcp.yaml`).
Plain `x-kagent-*` headers are routing hints, not identity, unless a trusted authenticated
ingress/JWT/mTLS boundary establishes and protects them (`platform/agentgateway/AUTHENTICATION.md`).

## Safety and governance

Controls are layered; no layer substitutes for another:

1. **Authenticated gateway ingress** — strict JWT/OIDC validation at the gateway front door;
   requests without a valid token are rejected (`platform/agentgateway/AUTHENTICATION.md`).
2. **Agent Gateway MCP allowlist** — a policy that filters discovery and calls to the four
   permitted tools for the named agent and default-denies everything else, gated on the
   installed CRD version (repository baseline is agentgateway v1.3.1; the CEL MCP
   authorization shape must be re-verified per target, not assumed from historical evidence).
3. **Server configuration** — the candidate's own toolset/tool/denied-resource filters below.
4. **Kubernetes RBAC** — the namespace-scoped Role; the definitive permission boundary.
5. **Network and namespace scoping** — ClusterIP-only exposure, default-deny egress/ingress
   NetworkPolicy, and an isolated server namespace (pattern: `platform/agentgateway/networkpolicy.yaml`).
6. **Agent/system-message constraints** — a purpose-built read-only agent that escalates
   mutations to GitOps/HITL paths rather than executing them
   (`agents/skills/responsible-kagent-operation/assets/responsible-readonly-triage-agent.yaml`).

**POC server posture.** No `config` toolset, no Helm, no exec/run-image, no delete/create/
update/scale tools, no multi-cluster access: `read_only = true`, `toolsets = ["core"]`,
`enabled_tools = ["pods_list_in_namespace", "pods_get", "pods_log", "events_list"]`, an
explicit `disabled_tools` list as defence in depth, and `denied_resources` covering at least
`Secret`, `ConfigMap`, `ServiceAccount`, `Role`, `RoleBinding`, `ClusterRole`, and
`ClusterRoleBinding` ([configuration.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/configuration.md)).
Denied resources *supplement* — never replace — the Role's lack of permission: they shape the
tool surface, while RBAC decides the actual API outcome.

**Why current upstream AKS-MCP cannot be the shared endpoint.** Upstream states that callers
inherit the server-process identity, that `--access-level` is a guardrail against accidental
damage rather than a security boundary, and that its credential-command denylist is not a
security boundary and does not cover the `kubectl`/`helm`/`cilium`/`hubble` surfaces
([aks-mcp README](https://github.com/Azure/aks-mcp/blob/8d28bece75d1f572293364d7f50a7e9d2e425efa/README.md)).
That disqualifies its current upstream form as a shared, network-reachable kagent tool
endpoint for anything other than a single trusted local user.

**Audit and observability boundaries.** Retain: tool name and result status per call,
authenticated caller/agent identity, Kubernetes audit subject and denial status, request/trace
correlation IDs, and the A2A receipt. Do not retain or log: credential values of any kind,
kubeconfig contents, Secret data, raw pod-log payloads, or high-verbosity MCP request/result
dumps — the candidate's redaction is documented as a best-effort denylist that lets unknown
shapes through, and its own guidance is to keep `log_level` at 0–5 in production
([logging.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/logging.md)).
Keep retained evidence under the platform's normal restricted retention.

**Additional hardening.** Conservative per-route/per-session rate limits and timeouts at the
gateway (pattern: `platform/agentgateway/ai-policy.yaml`), TLS termination at the trusted
ingress with the server reached only over the internal Service, an internal-only listener,
and default-deny network access to the server namespace. Treat Agent Gateway CRD
feature/version validation as a hard prerequisite for every gateway object; the repository's
single-cluster schema-gate verdicts are evidence for one cluster, not a universal truth
(`platform/agentgateway/DEMO-SCHEMA-GATE.md`).

## Bounded POC design

Design only — no manifests are added by this issue, and none of the following has been
executed. A future GitOps change would carry this design for separate review.

### Boundary and question

- One designated non-production namespace `{{POC_NAMESPACE}}` on one selected non-production
  cluster. No production cluster, no remote contexts, no cross-namespace inventory, no Azure
  control-plane action.
- One question: "identify a failing pod and its recent Warning events in `{{POC_NAMESPACE}}`;
  return evidence and a GitOps/HITL remediation recommendation, with no mutation."

### Dedicated Kubernetes identity and RBAC

- A dedicated `kubernetes-readonly-triage` ServiceAccount in an isolated MCP namespace
  `{{MCP_NAMESPACE}}`. This Kubernetes-only path needs no UAMI annotation and no federated
  credential.
- A namespace-scoped Role/RoleBinding in `{{POC_NAMESPACE}}` granting only `get`/`list` for
  `pods`, `events`, `deployments`, `replicasets`, `statefulsets`, and `jobs`, plus `get` for
  `pods/log`.
- No Secrets, no ConfigMaps, no RBAC resources, no workload writes, no `pods/exec`, no token
  creation, no cluster-scoped permissions. A cluster-wide question would require a separately
  reviewed ClusterRole and is out of scope. (This is deliberately tighter than the candidate's
  getting-started guide, which binds the built-in `view` ClusterRole cluster-wide, and tighter
  than the repository AKS-MCP chart's default read-only ClusterRole.)

### Candidate server configuration

```toml
# POC posture — Kubernetes MCP Server (pin the image release/digest in the future change)
port = "{{MCP_SERVER_PORT}}"
read_only = true
toolsets = ["core"]
enabled_tools = ["pods_list_in_namespace", "pods_get", "pods_log", "events_list"]
disabled_tools = [
  "configuration_view", "pods_delete", "pods_exec", "pods_run", "pods_top",
  "resources_create_or_update", "resources_delete", "resources_scale",
  "nodes_log", "nodes_stats_summary", "nodes_top",
]
cluster_provider_strategy = "in-cluster"   # local cluster only; multi-cluster disabled

[[denied_resources]]
group = ""
version = "v1"
kind = "Secret"
[[denied_resources]]
group = ""
version = "v1"
kind = "ConfigMap"
[[denied_resources]]
group = ""
version = "v1"
kind = "ServiceAccount"
[[denied_resources]]
group = "rbac.authorization.k8s.io"
version = "v1"
kind = "Role"
[[denied_resources]]
group = "rbac.authorization.k8s.io"
version = "v1"
kind = "RoleBinding"
[[denied_resources]]
group = "rbac.authorization.k8s.io"
version = "v1"
kind = "ClusterRole"
[[denied_resources]]
group = "rbac.authorization.k8s.io"
version = "v1"
kind = "ClusterRoleBinding"
```

ClusterIP-only Service exposure (no chart ingress), TLS terminated at the trusted ingress or
mesh, and a conservative per-session rate limit. Multi-cluster is explicitly disabled
(`--disable-multi-cluster`, equivalent to `cluster_provider_strategy = "disabled"` for the
single-context case), so no tool gains a `context` argument; the `in-cluster` provider reaches
only the local API server. Pin an image release/digest rather than the chart's `latest`
default.

### Gateway and agent wiring

- Subject the Agent Gateway MCP backend/route/policy to a preflight schema gate against the
  target installed version before anything is applied (method:
  `platform/agentgateway/DEMO-SCHEMA-GATE.md` and `preflight-check.sh`). Do not assume the
  repository's historical OpenAPI/A2A schema verdicts prove this MCP target works on any
  future cluster.
- Require strict caller JWT/OIDC validation (`platform/agentgateway/AUTHENTICATION.md`), a
  policy that permits exactly the same four tools for the named read-only agent and
  default-denies everything else (CEL pattern: `platform/agentgateway/policy-argo-openapi-mcp.yaml`),
  and a route that targets only the internal server Service.
- A kagent `RemoteMCPServer` (`STREAMABLE_HTTP`) pointing at that gateway route, with explicit
  `toolNames` — `None` is a validation error (`platform/aks-mcp/README.md`,
  `platform/agentgateway/remotemcpserver-argo.yaml`).
- A purpose-built read-only kagent agent that lists only the four tools, carries no
  apply/delete/exec tools, and submits any remediation through the existing GitOps/HITL
  workflow paths rather than acting itself.

### Required evidence gates

A favourable POC conclusion requires all five, captured without credential values, sensitive
log data, cluster endpoints, or private identifiers entering the public PR:

1. **Identity proof:** Kubernetes audit records show the dedicated
   `kubernetes-readonly-triage` ServiceAccount as the request subject, alongside the gateway's
   authenticated-agent identity for the same calls.
2. **Tool inventory:** a `tools/list` capture shows exactly the four allowed tools and none of
   the config/exec/Helm/write tools.
3. **RBAC denial:** an intentional denied request (cross-namespace list, or a Secret/RBAC
   read) returns an RBAC `Forbidden` response with no sensitive data disclosed.
4. **Bounded A2A invocation:** a successful end-to-end call using
   `scripts/kagent-a2a-invoke.sh`, with the receipt/correlation ID retained.
5. **Telemetry:** gateway/server/audit telemetry demonstrates both the allow path and the
   denial path (tool filter or RBAC) with correlated request IDs.

### Stop conditions and cleanup

Terminate the POC if any schema, identity, tool-inventory, RBAC-denial, or A2A evidence gate
fails. Cleanup in the future change, in order: remove the kagent Agent/tool reference; the
gateway route/policy/backend; the server workload, Service, config, and NetworkPolicy; the
RoleBinding/Role/ServiceAccount and the POC namespace; revoke any separately created client
registration/certificate/token and remove private evidence under the approved retention
policy; then confirm absence through the normal GitOps reconciliation/audit process. This
issue performs none of those actions.

## Sources

### Official primary upstream sources

All `containers/kubernetes-mcp-server` links are pinned to
`3b7a4da9d8f59565d7d72a64695949e2798b6c49`; the `Azure/aks-mcp` link is pinned to
`8d28bece75d1f572293364d7f50a7e9d2e425efa`.

| Source | Supports |
|---|---|
| [kubernetes-mcp-server README](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/README.md) | Native API client (no kubectl wrapper), core/config default toolsets, full `core` tool inventory (including `pods_delete`/`pods_exec`/`pods_run`/`nodes_log` and read-only pod/event tools), transports, multi-cluster default, OTEL/`/stats` |
| [docs/configuration.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/configuration.md) | `read_only`, `toolsets`, `enabled_tools`/`disabled_tools`, `denied_resources`, `cluster_provider_strategy` (in-cluster/kubeconfig and explicit remote-kubeconfig requirement), `--disable-multi-cluster`, `bind_address` default all-interfaces warning, OAuth/OIDC fields and `cluster_auth_mode` |
| [docs/ENTRA_ID_SETUP.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/ENTRA_ID_SETUP.md) | Optional Entra OIDC/OBO/passthrough client authentication; startup rejection of `require_oauth = true` with shared-ServiceAccount `cluster_auth_mode = "kubeconfig"` |
| [docs/getting-started-kubernetes.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/getting-started-kubernetes.md) | Dedicated read-only ServiceAccount + view-role binding and TokenRequest kubeconfig pattern that the POC deliberately narrows to a namespace Role |
| [charts/kubernetes-mcp-server/values.yaml](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/charts/kubernetes-mcp-server/values.yaml) | `automountToken` default for in-cluster access, RBAC-by-values design, `latest` image default, default-on ingress, Service/TLS options |
| [charts/kubernetes-mcp-server/templates/rbac.yaml](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/charts/kubernetes-mcp-server/templates/rbac.yaml) | No default RBAC rules shipped; permissions are operator-defined via values |
| [docs/logging.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/logging.md) | Best-effort (denylist) redaction of sensitive material; production log-level guidance |
| [docs/OTEL.md](https://github.com/containers/kubernetes-mcp-server/blob/3b7a4da9d8f59565d7d72a64695949e2798b6c49/docs/OTEL.md) | Optional OTEL tracing/metrics content (tool name, status, duration; HTTP traces) |
| [Azure/aks-mcp README](https://github.com/Azure/aks-mcp/blob/8d28bece75d1f572293364d7f50a7e9d2e425efa/README.md) | Stdio-only supported model; "do not expose through HTTP/SSE/container/Helm/Kubernetes/proxy/gateway"; server-identity inheritance; `--access-level` and credential denylist as non-boundaries; ordered Azure CLI authentication incl. federated-token workload identity |
| [Kubernetes RBAC documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/) | Role/RoleBinding as the Kubernetes authorization decision; tool hints are not authorization |
| [Kubernetes ServiceAccount documentation](https://kubernetes.io/docs/concepts/security/service-accounts/) | ServiceAccount as the in-pod Kubernetes identity |
| [AKS / Microsoft Entra Workload Identity overview](https://learn.microsoft.com/azure/aks/workload-identity-overview) | Federated-credential exchange (projected ServiceAccount token → Entra token) as the pod-to-Azure path, distinct from Kubernetes API authorization |

### Checked-out repository evidence

| Source | Supports |
|---|---|
| `platform/aks-mcp/README.md` | The repository's identity model (Kubernetes SA+RBAC versus Azure UAMI distinction), chart RBAC expectations, explicit-`toolNames` requirement, and the local in-cluster HTTP wiring pattern |
| `platform/aks-mcp/chart/values.yaml` | Local chart surface: `streamable-http` transport, `accessLevel`, `enabledComponents` list, `allowNamespaces`, kubeconfig Secret mount, OAuth block — i.e. the local pattern differs from current upstream's stdio-only model |
| `platform/aks-mcp/chart/templates/rbac.yaml` | Local default read-only ClusterRole/ClusterRoleBinding (cluster-scoped; Secrets gated by `includeSecrets`) that the POC deliberately narrows |
| `platform/aks-mcp/chart/Chart.yaml` | Local chart pins an older AKS-MCP appVersion, evidencing that the local pattern predates the pinned upstream stdio-only change |
| `infra/byo-kagent/bootstrap-catalog/toolcatalogentry-aks-mcp.yaml` (the bootstrap-catalog entry referenced by `platform/aks-mcp/README.md`) | Existing in-cluster MCP catalog wiring for kagent |
| `platform/agentgateway/README.md` | Gateway architecture, install baseline v1.3.1, empirical-validation caveat, monitoring files |
| `platform/agentgateway/AUTHENTICATION.md` | Strict JWT/OIDC front-door pattern, authorization-after-authentication, `x-kagent-*` headers not identity, CRD-version caution |
| `platform/agentgateway/DEMO-SCHEMA-GATE.md` | Read-only CRD schema-gate method and per-cluster verdicts (CEL MCP authorization supported; OpenAPI MCP target not supported on the inspected cluster) |
| `platform/agentgateway/policy-argo-openapi-mcp.yaml` | CEL MCP tool allowlist pattern and header-trust caution |
| `platform/agentgateway/remotemcpserver-argo.yaml` | kagent `RemoteMCPServer` pointing at a gateway MCP route, with schema gate |
| `platform/agentgateway/ai-policy.yaml`, `platform/agentgateway/networkpolicy.yaml`, `platform/agentgateway/monitoring.yaml` | Rate-limit/timeout, network-scoping, and monitoring patterns |
| `infra/workload-identity/README.md` | Federated credential mechanics (issuer/subject/audience `api://AzureADTokenExchange`) for the UAMI path |
| `agents/skills/responsible-kagent-operation/assets/responsible-readonly-triage-agent.yaml` | Read-only agent example: explicit `toolNames`, no-mutation system message, escalation to GitOps/HITL |
| `scripts/kagent-a2a-invoke.sh` | Shared A2A invocation helper named in evidence gate 4 |

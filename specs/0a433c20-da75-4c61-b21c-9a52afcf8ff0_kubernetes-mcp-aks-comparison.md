# Plan: Issue #83 Kubernetes MCP Server vs AKS-MCP research report

## Baseline and scope

- Start from the verified `origin/main` baseline `99a38ef96c3a534781158ade8deef5a0c2d4cff7`; it matches `HEAD` and the worktree was clean at planning time.
- Implement one documentation-only change: create `docs/research/kubernetes-mcp-server-vs-aks-mcp.md`. Do not alter `platform/aks-mcp/`, `platform/agentgateway/`, `infra/workload-identity/`, `agents/`, manifests, RBAC, credentials, or generated artifacts.
- Do not run `kubectl`, contact a cluster, deploy anything, create an identity/credential, change RBAC, use DeepSeek/OpenRouter, or merge the resulting PR. Research and offline inspection only.
- Treat upstream facts as versioned research, not live-platform proof. Record the upstream revisions inspected: `containers/kubernetes-mcp-server` `3b7a4da9d8f59565d7d72a64695949e2798b6c49` and `Azure/aks-mcp` `8d28bece75d1f572293364d7f50a7e9d2e425efa`; clearly identify the repository’s AKS-MCP Helm/HTTP pattern as a local pattern that differs from the current AKS-MCP upstream’s supported local-stdio model.

## Report implementation

Create the report with exactly these H2 headings, in this order and spelled exactly as required:

1. `## Executive recommendation`
2. `## Capability comparison`
3. `## Authentication and authorization`
4. `## Safety and governance`
5. `## Bounded POC design`
6. `## Sources`

Use concise prose, a comparison table where it makes the distinction easier to audit, and inline footnote-style links immediately next to material claims. Limit citations to official primary upstream sources and the permitted checked-out repository areas. Do not cite blogs, vendor summaries, copied examples, search-result snippets, or unverified claims.

### Executive recommendation

- State the decision unambiguously: **complement only, for a named `kubernetes-readonly-triage` role**. Do not replace AKS-MCP’s Azure/AKS-specific diagnostic and control-plane capability with the general server.
- State the important present-day constraint: current upstream AKS-MCP supports only a local trusted-user stdio subprocess and explicitly says not to expose it through HTTP/SSE, container services, Helm, Kubernetes, proxies, or gateways. Therefore do not extend or represent the repository’s existing networked `platform/aks-mcp/` chart pattern as current upstream-supported architecture.
- Explain why the candidate is favourable only as a separately bounded, non-production Kubernetes workload-inspection server: it is a native Kubernetes API client with read-only mode, explicit tool allowlisting, denied-resource filtering, in-cluster ServiceAccount support, HTTP transports, and optional OIDC; it is not an Azure ARM/AKS replacement.
- Make the recommendation conditional on the POC gates below; no production adoption or current-tool removal follows from this report.

### Capability comparison

Build a source-linked matrix for **containers/kubernetes-mcp-server**, **current upstream AKS-MCP**, and the **repository’s existing AKS-MCP deployment pattern**. At a minimum compare:

- operational focus and implementation (generic Kubernetes/OpenShift direct API client versus AKS-MCP’s `az`/`kubectl`/`helm`/Cilium/Hubble command surface);
- read-only Kubernetes triage coverage: namespace pod lists/details/logs, events, and generic Kubernetes resources versus AKS/Azure control plane, networking, fleet, Azure Monitor/detectors/VMSS and Advisor capability;
- explicit tool controls: candidate `read_only`, `toolsets`, `enabled_tools`/`disabled_tools`, `denied_resources`, and optional multi-cluster disable; AKS-MCP access levels/components and why they are guardrails rather than a caller-authorization boundary;
- connection and transport models: candidate in-cluster or kubeconfig provider plus streamable HTTP/SSE; current AKS-MCP local stdio-only support; repository’s older in-cluster `RemoteMCPServer`/Helm model;
- multi-cluster behavior and why it is deliberately excluded from the first POC;
- observability (candidate OTEL/stats and logging cautions; repository Agent Gateway/kagent monitoring pattern); and
- fit with existing kagent tool references and Agent Gateway’s intended MCP `tools/list`/`tools/call` filtering.

Call out unsafe/default-expansive capability precisely: the candidate defaults include `core` and `config`, its HTTP listener defaults to all interfaces, and `config` can expose kubeconfig content; its core toolset contains more than the POC needs. Do not imply that a read-only hint or MCP tool discovery alone is RBAC.

### Authentication and authorization

Use a clearly labeled four-path model, with a diagram/table if useful. Do not collapse these identities:

1. **Kubernetes ServiceAccount and Kubernetes RBAC:** for a candidate deployed in a cluster using `in-cluster`, the projected ServiceAccount token authenticates the server to the local Kubernetes API and a Role/RoleBinding (or a consciously justified ClusterRoleBinding) authorizes it. For the proposed POC this is the only Kubernetes API identity and authorization path.
2. **Azure UAMI / Microsoft Entra Workload Identity for Azure APIs:** it exchanges a workload token for an Azure identity/token and authorizes Azure Resource Manager/AKS API operations. It does not automatically authenticate the candidate to Kubernetes APIs or confer Kubernetes RBAC. Contrast this with the local AKS-MCP chart documentation’s UAMI workload-identity path and the current upstream AKS-MCP federated-token Azure CLI authentication order.
3. **Kubeconfig or kubelogin paths:** a kubeconfig is an alternate Kubernetes API credential/connection path. The candidate supports kubeconfig and requires an explicit mounted kubeconfig plus provider selection for a remote cluster; any exec/kubelogin/Entra-token arrangement is a kubeconfig credential dependency, not native proof that the general server directly supports UAMI as its Kubernetes API identity. The current upstream candidate documentation does not establish a direct UAMI-to-AKS-Kubernetes-API authentication mode; mark it unsupported/unproven for this decision and exclude it from the POC. Explain that a kubeconfig can also broaden target/credential exposure and must never be placed in the report.
4. **Client OIDC to the MCP server:** this authenticates an MCP client/caller to an HTTP server, separately from the server’s Kubernetes API identity. Describe the candidate’s optional Entra OIDC/OBO/passthrough modes and its documented rejection of `require_oauth=true` combined with shared-ServiceAccount (`cluster_auth_mode=kubeconfig`) access because it collapses per-user audit identity. For the machine-to-machine POC, make Agent Gateway’s strict JWT/OIDC front-door policy the client authentication boundary only after installed-CRD validation; do not claim it changes Kubernetes API authorization.

Also contrast kagent agent-side `toolNames` with runtime enforcement: retain an explicit agent tool list as a narrowing control, but describe Agent Gateway’s MCP policy/discovery filtering as the intended independent allowlist when supported by the installed CRD. State that plain `x-kagent-*` headers are not identity without a trusted ingress/JWT/mTLS boundary, using the repository’s existing caution.

### Safety and governance

- Separate the controls by layer: authenticated gateway ingress, explicit Agent Gateway MCP tool allowlist, candidate server configuration, Kubernetes RBAC, NetworkPolicy/egress and namespace scoping, and kagent agent/system-message constraints. State that no one layer substitutes for another.
- Document the candidate’s safe POC posture: no `config`, Helm, exec, run-image, delete/create/update/scale, or multi-cluster access; `read_only=true`; `toolsets=["core"]`; four-item `enabled_tools`; explicit `disabled_tools` as defence in depth; and denied GVKs including Secret, ConfigMap, ServiceAccount, and RBAC objects. Explain that denied resources supplement—not replace—the Role’s lack of permission.
- Contrast AKS-MCP current upstream’s warning that callers inherit the server-process identity and that `--access-level` and its credential-command denylist are not a security boundary. State that this disqualifies its current upstream form as a shared untrusted kagent tool endpoint.
- Cover audit/observability boundaries: retain minimal tool name/result-status, authenticated caller/agent identity, Kubernetes audit subject and denial status, request/trace correlation, and A2A receipt; do not log bearer tokens, kubeconfigs, Secret data, raw pod log payloads, or high-verbosity MCP request/result dumps. Cite the candidate’s best-effort redaction warning and retain logs under normal restricted retention.
- Include rate limits, timeouts, TLS, gateway ingress restriction, and default-deny network access. Flag Agent Gateway CRD feature/version validation as a hard prerequisite rather than relying on the repository’s historical single-cluster evidence.

### Bounded POC design

Design only; do not add the manifests or execute the POC in this issue. Make the proposal specific enough to be reviewed as a future GitOps POC:

- **Boundary and question:** one designated non-production namespace `{{POC_NAMESPACE}}`, one selected non-production cluster, no remote contexts, and one question such as “identify a failing pod and its recent Warning events in `{{POC_NAMESPACE}}`; return evidence and a GitOps/HITL recommendation, with no mutation.” No production cluster, Azure control-plane action, or cross-namespace inventory.
- **Dedicated Kubernetes identity/RBAC:** a dedicated `kubernetes-readonly-triage` ServiceAccount in an isolated MCP namespace; no UAMI annotation is needed for this Kubernetes-only path. Bind it through a namespace-scoped Role/RoleBinding in `{{POC_NAMESPACE}}` with only `get`/`list` for `pods`, `events`, `deployments`, `replicasets`, `statefulsets`, and `jobs`, plus `get` for `pods/log`. Do not grant Secrets, ConfigMaps, RBAC resources, workload writes, `pods/exec`, token creation, or cluster-scoped permissions. Note that a cluster-wide question would require a separately reviewed ClusterRole and is out of scope.
- **Candidate configuration:** in-cluster provider only; explicit single-cluster disable; `read_only=true`; `toolsets=["core"]`; `enabled_tools=["pods_list_in_namespace", "pods_get", "pods_log", "events_list"]`; deny the sensitive resources above; local/internal-only service exposure; TLS/ingress termination and a conservative per-session rate limit. Pin an image release/digest in the future POC rather than use `latest`.
- **Gateway and agent:** subject a candidate Agent Gateway MCP backend/route/policy to a preflight schema gate against the target installed version. Require strict caller JWT/OIDC validation, a policy that filters and permits only the same four tools for the named agent, default-denies everything else, and routes only to the internal server Service. The kagent `RemoteMCPServer` must point to that route, and a purpose-built read-only kagent agent must list only those four `toolNames`; it must not carry apply/delete/exec tools and must submit any remediation to existing GitOps/HITL workflow paths. Do not assume the existing historical OpenAPI/A2A schema verdict proves this MCP target works on a future target.
- **Required evidence gates before any favourable POC conclusion:** capture (a) workload identity proof that Kubernetes audit records the dedicated ServiceAccount subject, alongside gateway authenticated-agent identity; (b) `tools/list` inventory showing exactly the four allowed tools and none of the config/exec/Helm/write tools; (c) an intentional denied cross-namespace or Secret/RBAC request resulting in an RBAC `Forbidden` response without sensitive data disclosure; (d) a successful bounded A2A invocation using the shared `scripts/kagent-a2a-invoke.sh` helper and retained receipt/correlation ID; and (e) gateway/server/audit telemetry proving the allow and denial paths. State that no credential values, logs with sensitive data, cluster endpoints, or private identifiers may enter the public PR.
- **Stop/cleanup:** terminate the POC if schema, identity, tool inventory, RBAC-denial, or A2A evidence fails. In the future change, remove the kagent Agent/tool reference first, then gateway route/policy/backend, server workload/Service/config/NetworkPolicy, RoleBinding/Role/ServiceAccount and POC namespace; revoke any separately created client registration/cert/token and remove private evidence under the approved retention policy. Confirm absence through the normal GitOps reconciliation/audit process. This issue performs none of those actions.

### Sources

List only the exact source URLs used, grouped as “Official primary upstream sources” and “Checked-out repository evidence.” Use commit-pinned GitHub links for source-code/repository claims where possible. Include at least:

- `containers/kubernetes-mcp-server` README, configuration reference, Entra setup, Kubernetes deployment guide, Helm values/RBAC templates, logging, and OTEL docs at `3b7a4da9d8f59565d7d72a64695949e2798b6c49`;
- `Azure/aks-mcp` README at `8d28bece75d1f572293364d7f50a7e9d2e425efa`;
- official Kubernetes ServiceAccount and RBAC documentation;
- official Microsoft AKS/Entra workload-identity documentation only where needed to support the federation distinction; and
- only these local evidence areas: `platform/aks-mcp/README.md` plus its chart values/RBAC template and bootstrap catalog reference; `platform/agentgateway/README.md`, `AUTHENTICATION.md`, authentication/policy/schema-gate material; `infra/workload-identity/README.md`; and the cited read-only agent/tool/A2A examples under `agents/`.

Each source entry should state what assertion it supports. Preserve public-safe placeholders (for example `{{POC_NAMESPACE}}`, `{{TENANT_ID}}`) and never include URLs/IDs extracted from an environment.

## Verification, review, and PR

1. Inspect `git diff --check` and confirm the new report is the only implementation deliverable.
2. Use a small local Python/awk check to verify that each of the six required headings occurs exactly once as an H2, in the required order, and that the report contains an explicit documentation-only/non-action statement, the named-role recommendation, all four identity paths, and the five POC evidence gates. Fail the check rather than inferring compliance.
3. Manually inspect every external citation. Confirm it is a primary official source on the allowed upstream/project domains and that code links are commit-pinned; confirm all local citations are in the allowed repository areas. Check that no current-upstream claim is accidentally attributed to the older local AKS-MCP chart.
4. Run `scripts/public-safe-scan.sh --strict docs/research/kubernetes-mcp-server-vs-aks-mcp.md` and record its exit status/output as evidence. Also use a targeted placeholder/private-data sweep and inspect the diff for real tenant/subscription/client IDs, tokens, private FQDNs/IPs, kubeconfigs, credentials, or copied logs. Do not waive scanner findings without removing or replacing the value.
5. Obtain an independent documentation/security review of the completed diff (separate reviewer/agent, not the author) specifically against issue #83: source provenance, the four authentication distinctions, current AKS-MCP remote-deployment incompatibility, the recommendation wording, POC least privilege, Agent Gateway version caveat, evidence gates, and public safety. Wait for the review, resolve substantiated findings, then rerun every gate in steps 1–4.
6. Commit only the report with an imperative subject such as `docs: compare Kubernetes MCP Server and AKS-MCP`. Open exactly one draft PR against `main` using `gh pr create --draft`, with a title such as `docs: research Kubernetes MCP Server vs AKS-MCP`, and body that references `#83`, states the recommendation, declares documentation-only/no-cluster actions, links the upstream revisions, records command exit-status evidence, and summarizes the independent review. Do not merge it. Capture the returned draft PR URL/number as the final delivery evidence.

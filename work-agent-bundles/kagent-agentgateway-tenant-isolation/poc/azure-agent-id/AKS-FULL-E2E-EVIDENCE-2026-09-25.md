# Disposable AKS Agent ID isolation proof — 2026-09-25

This is a sanitized **home-lab Azure/AKS runtime receipt**, not evidence of work-tenant AACM approval or a production deployment. The test used one disposable, billable AKS worker node, a deterministic in-cluster model stub, and a dummy MCP incident. No work identifiers, real tokens, or business data are in this file. The cluster was deleted after the tests; the original identity-only PoC objects remain for review. The additional caller/rogue blueprints, A2A API, and pilot-only federation credentials were deleted after the run.

## Tested topology

```text
approved caller Pod/ServiceAccount ──AKS OIDC──> caller blueprint ──fmi_path──> caller Agent ID
                                                          │ A2A app role/token
                                                          ▼
                                                   agentgateway A2A :8081
                                                          │ role AND exact oid
                                                          ▼
runtime kagent Agent/ServiceAccount ──AKS OIDC──> runtime blueprint ──fmi_path──> runtime Agent ID
                                                          │ MCP app role/token
                                                          ▼
                                                   agentgateway MCP :8082
                                                          │ role AND exact oid AND lookup_incident only
                                                          ▼
                                                   namespaced dummy MCP

rogue Pod/ServiceAccount ──AKS OIDC──> separate rogue blueprint/Agent ID
                         └── same A2A and MCP roles, but wrong Agent ID oid: denied
```

The separate blueprints keep the pilot caller, runtime, and rogue Kubernetes credentials distinct. This is a narrower credential boundary than putting several child identities under one blueprint: possession of a blueprint credential can select a different child through `fmi_path`. The work identity team must approve blueprint granularity or a trusted broker before rollout.

## Environment and read-back

| Check | Live result |
|---|---|
| AKS worker | One Ready node, Kubernetes `v1.35.8` |
| AKS identity/network | OIDC issuer and Workload Identity enabled; Azure CNI overlay with Cilium dataplane and policy |
| Blueprint trust | One exact AKS OIDC federated credential each for runtime, approved caller, and rogue ServiceAccounts |
| Entra API permissions | Separate v2 MCP and A2A resource apps; application roles assigned to the intended child Agent ID principals; rogue deliberately received the same roles for subject-denial tests |
| Gateway | `Accepted=True`, `Programmed=True`; A2A and MCP routes `Accepted=True`, `ResolvedRefs=True`; both policies `Accepted=True`, `Attached=True` |
| Agent | `Accepted=True`, `Ready=True`; Deployment used `incident-adviser-id` and `azure.workload.identity/use=true` |
| Namespaces | `team-event` and `team-rogue` had default-deny NetworkPolicies plus explicit DNS, Entra, gateway, model, and controller flows |

## Live verdicts

| Path | Result |
|---|---|
| Runtime AKS ServiceAccount → runtime blueprint → child Agent ID MCP token | PASS: expected child `oid`, API audience and `team-event.mcp.use` role |
| MCP: no token; wrong audience | PASS: both `401`, before backend |
| MCP: approved child + `lookup_incident` | PASS: fixture `INC-1001` returned |
| MCP: forbidden `delete_everything` | PASS: rejected before backend; forbidden-backend counter stayed `0` |
| Approved caller AKS ServiceAccount → caller blueprint → child Agent ID A2A token | PASS: expected caller `oid`, A2A audience and `team-event.a2a.invoke` role |
| A2A: no token; wrong audience | PASS: both `401` |
| A2A: approved caller → Agent → MCP | PASS: completed answer for `INC-1001`; model stub recorded a tool request and response |
| MCP: caller token without MCP role | PASS: `403` |
| A2A and MCP: rogue token with the **same roles** but wrong child Agent ID | PASS after policy correction: both `403` |
| Rogue namespace → direct MCP Service; direct Agent Service | PASS: both network-denied, while the Gateway remained reachable |
| Rotate short-lived runtime token, update Secret, restart Agent Pod, repeat A2A→MCP | PASS: Secret value changed, patch Role/RoleBinding removed, new Agent Pod Ready, completed tool call |

The MCP fixture ended with `tenant_mcp_tool_calls_total=7` and `tenant_mcp_forbidden_tool_calls_total=0`. The count includes an **initial failed negative test** described below; do not treat all seven calls as approved traffic.

## Important defects and limits found

1. The proposed `AKS ServiceAccount → UAMI → blueprint` chain failed with `AADSTS700231`: the UAMI token had itself been obtained via federation and could not be used as another federated assertion. Direct AKS ServiceAccount → blueprint federation succeeded. Microsoft also documents that [Entra-issued tokens cannot be used for federated identity flows](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation). The older UAMI renderer in this PoC is **not** a work deployment template.
2. The first A2A/MCP policy listed role and `jwt.oid` as separate `Allow` match expressions. In this installed agentgateway version that behaved as **OR**; the rogue token with the role reached the Agent and caused one MCP call. The tested fix uses a **single** CEL expression: `"{{ROLE_VALUE}}" in jwt.roles && jwt.oid == "{{EXPECTED_AGENT_OBJECT_ID}}"`. After applying it, the same-role/wrong-ID A2A and MCP probes both returned `403`. Do not split these checks into separate `Allow` expressions. See the [agentgateway authorization semantics](https://agentgateway.dev/docs/kubernetes/latest/documentation/security/authorization/).
3. The first A2A run timed out because the Agent's NetworkPolicy omitted its session-service call to the kagent controller on port `8083`. Adding that **named, namespace-scoped** egress restored the path. A NetworkPolicy must include required control-plane dependencies as well as model and MCP traffic.
4. The tested A2A HTTPRoute targeted the **Agent Service** in `team-event` directly, with a named ReferenceGrant and Gateway-only ingress NetworkPolicy. The earlier controller `/api/a2a/...` route returned `401` under kagent `v0.10.1` trusted-proxy authentication when invoked without a trusted proxy identity. Use the [tested route shape](../../profiles/aks-entra/event-a2a-direct-route.yaml) or prove an approved controller-proxy identity path; do not assume the old rewrite route works unchanged. The gateway stripped the inbound caller token before forwarding to the Agent.
5. The lab token handoff was a temporary patch of a namespaced Secret and an Agent Pod restart. It did **not** prove automatic renewal, failure on expiry, a production credential broker, or a native kagent token provider. The temporary Secret patch Role and RoleBinding were removed and an authorization read-back returned `no`.
6. The lab used HTTP inside the cluster, a deterministic model fixture, and broad TCP/443 egress for the Workload Identity probes. Production needs TLS/ingress ownership, restricted Entra/JWKS egress, internal image supply, approved model routing, token lifecycle, and work-tenant AACM integration. No work environment was changed.

## Replication order for the work agent

1. Open the [copy-ready identity GitLab ticket](WORK-GITLAB-IDENTITY-TICKET.md). Have the infra ID/AACM owners approve blueprint isolation, child Agent IDs, MCP and A2A API app registrations/roles, exact AKS OIDC subjects, owners, and revocation. Keep the response private.
2. Inspect the **installed** AKS, kagent, agentgateway, Gateway API, and policy CRD versions. Confirm the work SPN's Azure RBAC separately from Microsoft Graph permissions. Do not self-grant or create an AKS cluster as part of the identity ticket.
3. Build a private GitOps diff for the three ServiceAccounts and direct blueprint federation, Agent, RemoteMCPServer/token provider, A2A/MCP routes and policies, ReferenceGrants, and default-deny/allow NetworkPolicies. Combine role and child-ID checks in one CEL expression per route. Server-dry-run and obtain the normal approvals.
4. Prove token claims (`iss`, `aud`, child `oid`, `roles`) inside the selected AKS Pods without printing tokens; then run A2A→Agent→MCP, negative missing/wrong-audience/missing-role/wrong-Agent-ID/forbidden-tool/direct-bypass tests, and a token rotation plus expiry/fail-closed test. Read backend counters to distinguish gateway denial from backend handling.
5. Keep work object IDs, issuer URLs, token material, manifests, and live evidence in approved private systems. Promote only when the token-refresh/broker and credential-boundary gates are closed.

For the agent-side implementation details and approval split, continue at [WORK-AGENT-START-HERE.md](../../profiles/aks-entra/WORK-AGENT-START-HERE.md). For a visual briefing, use the [current AKS walkthrough](aks-agentid-e2e-walkthrough.html). The earlier [architecture walkthrough](architecture-walkthrough.html) describes a superseded two-hop proposal.

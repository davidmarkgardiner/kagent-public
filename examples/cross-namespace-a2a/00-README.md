# Cross-Namespace A2A Through Agentgateway

This example proves a constrained two-agent pattern:

1. `team-alpha/orchestrator` is exposed through Agentgateway at
   `/a2a/team-alpha/orchestrator/`.
2. `team-alpha/orchestrator` has an agent tool reference to
   `team-beta/specialist`.
3. `team-beta/specialist` explicitly permits that cross-namespace reference
   with `spec.allowedNamespaces.from: Selector`.
4. `team-alpha/orchestrator` injects `X-Agent-Token` from a Secret in
   `team-alpha`; it does not need access to Secrets in `team-beta`.

Important boundary: on the currently deployed kagent shape, the native
agent-as-tool hop is rendered by kagent as a direct service URL such as
`http://specialist.team-beta:8080`, unless the kagent controller is configured
with a global proxy URL. Agentgateway proves the externally reachable A2A
entrypoint, routing, rewrite, policy and telemetry. kagent proves the
cross-namespace agent-to-agent authorization gate.

## Files

| File | Purpose |
|---|---|
| `01-namespaces.yaml` | Creates `team-alpha` and `team-beta` with labels used by `allowedNamespaces`. |
| `02-rbac.yaml` | Creates agent service accounts and intentionally grants no cross-namespace Secret access. |
| `03-network-policy.yaml` | Default-denies ingress in the team namespaces and allows only kagent, Agentgateway and the alpha-to-beta agent path. |
| `04-gateway-route.yaml` | Agentgateway `HTTPRoute` and `AgentgatewayPolicy` for the orchestrator A2A endpoint. The timeout is intentionally long enough for a cold local KubeAI model start. |
| `05-specialist-agent.yaml` | The target agent in `team-beta`; it opts in to references from namespaces labelled `team: alpha`. |
| `06-orchestrator-agent.yaml` | The source agent in `team-alpha`; it references `team-beta/specialist` and injects a local header from `team-alpha/a2a-agent-token`. |
| `07-rogue-agent-deny.yaml` | Negative-control agent in `team-gamma` that should be rejected because `team-beta/specialist` does not allow it. |
| `08-verify.sh` | Applies, waits, invokes through Agentgateway, and runs security checks. |
| `09-production-governance.md` | Production security-governance model for compliant agent-to-agent routing. |

## Run

```bash
examples/cross-namespace-a2a/08-verify.sh
```

The script uses the current kube context. It was written for the observed
management cluster shape where the Agentgateway `Gateway` is
`agentgateway-system/agent-gw` and kagent exposes A2A on
`kagent-controller.kagent:8083`.

## Expected Proof

- `team-beta/specialist` becomes `Accepted=True` and `Ready=True`.
- `team-alpha/orchestrator` becomes `Accepted=True` and `Ready=True`.
- `team-gamma/rogue-orchestrator` is not accepted; its reconcile status should
  mention that cross-namespace reference to `team-beta/specialist` is not
  allowed from `team-gamma`.
- A JSON-RPC request to Agentgateway `/a2a/team-alpha/orchestrator/` returns an
  A2A artifact from the orchestrator. The orchestrator prompt forces it to call
  the specialist and include `SPECIALIST_REPLY`, which is the runtime evidence
  for the cross-namespace agent-to-agent hop.
- Kubernetes auth proves the orchestrator service account cannot read
  `team-beta` Secrets.

## Security Notes

- `allowedNamespaces` is the real kagent cross-namespace authorization gate for
  an Agent used as a tool.
- `headersFrom` resolves from the source agent namespace. In this example the
  token comes from `team-alpha`, not `team-beta`.
- Kubernetes RBAC and namespace-scoped Secrets prevent the agent workload
  service account from reading target-namespace Secrets.
- NetworkPolicy constrains pod ingress, but exact enforcement depends on the
  cluster CNI.
- Current kagent server auth is still weak in this deployment family:
  `UnsecureAuthenticator` trusts request headers and `NoopAuthorizer` does not
  enforce resource authorization. Keep Agentgateway behind Istio
  `AuthorizationPolicy`, mTLS, and eventually OIDC/JWT before treating this as
  a production identity boundary.

For a production control model, read `09-production-governance.md` before
turning this demo into a tenant-facing pattern.

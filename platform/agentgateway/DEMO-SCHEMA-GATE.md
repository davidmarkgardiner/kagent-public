# DEMO-SCHEMA-GATE — read-only support verdict for the four MVP demos

**Status: verdicts captured against `proxmox-k8s` on 2026-05-14.** Re-run
the probes below against any other target cluster before merging the demo
PRs there — the verdicts in this file are evidence for one cluster, not a
universal truth.

PR 0 is intentionally read-only. Nothing in this file applies, deletes, or
patches anything.

## Versions captured (proxmox-k8s, 2026-05-14)

| Component | Version | Notes |
|---|---|---|
| `agentgatewaybackends.agentgateway.dev` storage version | `v1alpha1` | only version installed |
| `agentgatewaypolicies.agentgateway.dev` storage version | `v1alpha1` | only version installed |
| GatewayClass for agentgateway | `agentgateway` (controller `agentgateway.dev/agentgateway`) | Accepted=True |
| Gateway for agentgateway | `agent-gw` in `agentgateway-system` | Programmed=True, **not `ai-gateway`** — see Inventory caveat below |
| kagent | `kagent-v0.8.0-beta4` (Helm release `kagent` in `kagent`) | |
| kgateway (separate, parallel install) | `kgateway-v2.2.3` (Helm release `kgateway`) | uses `kgateway-system` ns and its own GatewayClass `kgateway` |
| agentgateway Helm release | **not separately listed** under `helm list -A` | likely installed out-of-band or rolled into another chart; record install method when found |

## CRD shape verdicts (proxmox-k8s, 2026-05-14)

| Capability | Used in PR | Verdict | Evidence |
|---|---|---|---|
| `agentgatewaypolicy.spec.backend.ai.prompt.prepend[]` (required: `role`, `content`) | PR 1 | **supported** | `kubectl explain agentgatewaypolicy.spec.backend.ai.prompt.prepend` — fields `content <string> required` + `role <string> required`, role doc explicitly mentions `SYSTEM` |
| `agentgatewaypolicy.spec.backend.ai.promptGuard.request[]` (`openAIModeration`, `regex`, `webhook`) | PR 1, PR 2 | **supported** | already proven by `ai-policy.yaml`; explain confirms `regex` and `response` sub-fields |
| `agentgatewaybackend.spec.ai.groups[]` priority failover | PR 2 | **supported** | `kubectl explain ...groups` — example in description literally shows two `azureopenai` providers as separate groups |
| Mixed provider types in one `groups[]` (e.g. KubeAI `openai` + Azure `azureopenai`) | PR 2 | **supported** | `groups.providers[]` accepts `anthropic`, `azureopenai`, `bedrock`, `gemini`, `openai` — all in one sibling list, no exclusion |
| `groups.providers[].policies.auth` (per-provider auth inside a group) | PR 2 | **supported** | explain shows `policies.auth` under `groups.providers` |
| `agentgatewaybackend.spec.ai.provider.azureopenai` shape | PR 2 fallback | **supported** | required `endpoint`, optional `deploymentName`, `apiVersion` — matches `backend-azure-openai.yaml` |
| `agentgatewaybackend.spec.mcp.targets[].openapi` | PR 3 | **NOT SUPPORTED** | `kubectl explain agentgatewaybackend.spec.mcp.targets.openapi` returns `error: field "openapi" does not exist`. Only `name`, `selector`, `static` are accepted. |
| `agentgatewaypolicy.spec.backend.mcp.authorization` CEL | PR 3 (if rescoped) | **supported** | explain shows `authorization` field with documented `list_tools` / `call_tool` semantics |
| `agentgatewaybackend.spec.a2a` | PR 4 | **NOT SUPPORTED** | `kubectl explain agentgatewaybackend.spec.a2a` returns `error: field "a2a" does not exist` |
| `agentgatewaypolicy.spec.backend.a2a.authorization` | PR 4 | **NOT SUPPORTED** | `kubectl explain agentgatewaypolicy.spec.backend.a2a` returns `error: field "a2a" does not exist` |

## Inventory captured (proxmox-k8s, 2026-05-14)

| Item | Value | Source |
|---|---|---|
| agentgateway Gateway name on this cluster | `agent-gw` (namespace `agentgateway-system`) | `kubectl get gateway -A` |
| agentgateway GatewayClass | `agentgateway` (controller `agentgateway.dev/agentgateway`) | `kubectl get gatewayclass` |
| Existing AgentgatewayBackends | **none** | `kubectl get agentgatewaybackend -A` → No resources found |
| Existing AgentgatewayPolicies | **none** | `kubectl get agentgatewaypolicy -A` → No resources found |
| Existing HTTPRoutes attached to `agent-gw` | **none** (the three HTTPRoutes that exist belong to `kgateway-system`: `kagent-ui-route`, `litellm-route`, `openwebui-route`) | `kubectl get httproute -A` |
| Path prefixes the plan reserves | `/llm/v1`, `/openapi-mcp/argo`, `/a2a/fleet/` | (all free — no existing routes on `agent-gw`) |
| KubeAI installed? | **no `kubeai` namespace, no Model CRDs found** | `kubectl get model -A` |
| Azure OpenAI backend already configured? | no (no AgentgatewayBackend resources at all) | `kubectl get agentgatewaybackend -A` |
| kagent controller Service | `kagent-controller` in `kagent`, ClusterIP, port `8083/TCP` | `kubectl get svc -n kagent` |
| Management-cluster fleet/incident agent candidates | `sre-triage-agent`, `sre-remediation-agent` (both Ready=True, Accepted=True) in `kagent` | `kubectl get agent -A` |
| Argo Server | `argo-server.argo.svc.cluster.local:2746` (ClusterIP) | `kubectl get svc -n argo` |

### Inventory caveats

1. **Gateway name is `agent-gw`, not `ai-gateway`.** The repo's
   `gateway-resources.yaml` creates a Gateway named `ai-gateway`; this
   cluster was provisioned out-of-band with the name `agent-gw`. Every
   new HTTPRoute in PR 1-4 currently has `parentRefs.name: ai-gateway`.
   Before applying any demo manifest on `proxmox-k8s`, either (a)
   override the `parentRefs.name` to `agent-gw` on that cluster, or
   (b) align the cluster with the repo by also creating `ai-gateway`
   via `gateway-resources.yaml`. Pick (b) for parity with the upstream
   docs; pick (a) for a quick demo.

2. **No prior `kubeai-route` / `azure-openai-route` exists.** PR 1's
   policy `org-prompt-enrichment` targets routes that this cluster
   doesn't yet have. Apply `gateway-resources.yaml` +
   `backend-kubeai.yaml` (or the route-only subset) first, or update
   PR 1's targetRefs to whichever LLM HTTPRoute name this cluster
   ends up with.

3. **Both `agentgateway` and `kgateway` GatewayClasses coexist** on
   this cluster. They are completely separate data-planes. Demo
   manifests are written for `agentgateway` (controller
   `agentgateway.dev/agentgateway`); do not accidentally point
   `parentRefs` at the `kgateway` Gateway `ai-platform-gw`.

## Schema corrections discovered during server-side dry-run (2026-05-14)

Three additional CRD-shape facts the original plan and the repo's
in-place `ai-policy.yaml` got wrong. These are now baked into the PR 1,
PR 2, and PR 4 manifests; flagging them here so the existing
`ai-policy.yaml` can be reviewed separately:

| Field | Wrong shape | Correct shape on v1alpha1 |
|---|---|---|
| Request timeout on `AgentgatewayPolicy` | `spec.traffic.requestTimeout: "90s"` (used by repo's current `ai-policy.yaml`) | `spec.traffic.timeouts.request: "90s"` |
| Regex prompt-guard `matches` | list of objects (`{pattern: "...", name: "..."}`) | `matches` is `[]string` — list of plain regex patterns; `action` lives at the regex root |
| Per-provider auth inside `groups[].providers[]` | included `azureAuth` for UAMI | only `aws`, `gcp`, `key`, `passthrough`, `secretRef`. UAMI **only** works at top-level `spec.policies.auth.azureAuth`, which applies to all providers in all groups. To mix KubeAI + Azure in one backend, Azure must auth via API-key `secretRef`; for UAMI failover use the route-level two-backend pattern in `FAILOVER-DEMO.md` §4. |

The repo's `platform/agentgateway/ai-policy.yaml` uses
`traffic.requestTimeout` which **will fail server-side dry-run on this
CRD release**. It hasn't been applied on `proxmox-k8s` (zero
AgentgatewayPolicies exist there). The README claims it works on "the
red cluster" — that's a different cluster with a different chart
version. Worth a separate cleanup PR.

### Additional gaps surfaced during review (2026-05-14)

| Gap | Where | Status |
|---|---|---|
| `kubeai-dummy-key` Secret in `backend-kubeai.yaml` uses key `api-key`; agentgateway secretRef requires key `Authorization` | `backend-kubeai.yaml:32` | PR 2 (`backend-llm-failover.yaml`) now ships its own dedicated `llm-failover-kubeai-key` Secret with the correct key. Fixing the upstream `kubeai-dummy-key` is part of the same `ai-policy.yaml` cleanup PR. |
| `istio-authorization-policy.yaml` only allows `/openai/v1/*`, `/azure/v1/*`, `/qwen/v1/*` — does not allow `/llm/v1/*`, `/openapi-mcp/argo*`, `/a2a/fleet/*` | `istio-authorization-policy.yaml:55` | Patched in this PR set to include all three demo paths and propagated to the commented API-key and JWT layer templates. |
| PR 4 runbook claimed "gateway-side authorization" — plan B has none on this CRD | `A2A-FLEET-DEMO.md` (pre-review) | Rewritten in this PR set to be explicit that identity lives at Istio, gateway provides routing/rate-limit/timeout/telemetry only. |
| PR 1 policy did not target the new `/llm/v1` route from PR 2 | `policy-prompt-enrichment.yaml` | Commented-out `llm-failover-route` targetRef added with a note about validating policy-merge behavior before uncommenting. |
| PR 4 path-prefix `/a2a/fleet/` may not match `/a2a/fleet` without trailing slash | `route-a2a-fleet-agent.yaml` | Trailing-slash variant tests added to `A2A-FLEET-DEMO.md`. Recommend always using the trailing slash; add a `RequestRedirect` filter if ergonomics demand otherwise. |

## Server-side dry-run results (proxmox-k8s, 2026-05-14)

```
PR 1 — policy-prompt-enrichment.yaml
  agentgatewaypolicy.agentgateway.dev/org-prompt-enrichment created (server dry run)

PR 2 — backend-llm-failover.yaml
  secret/azure-openai-api-key created (server dry run)
  agentgatewaybackend.agentgateway.dev/llm-failover-backend created (server dry run)
  httproute.gateway.networking.k8s.io/llm-failover-route created (server dry run)
  agentgatewaypolicy.agentgateway.dev/llm-failover-ai-policy created (server dry run)

PR 3 — backend-argo-openapi-mcp.yaml et al.
  NOT ATTEMPTED — manifest carries do-not-apply banner; CRD does not
  accept `spec.mcp.targets[].openapi`.

PR 4 — service-a2a-fleet-agent.yaml, route-a2a-fleet-agent.yaml, policy-a2a-fleet-agent.yaml
  referencegrant.gateway.networking.k8s.io/allow-agentgateway-to-kagent-controller created (server dry run)
  httproute.gateway.networking.k8s.io/a2a-fleet-route created (server dry run)
  agentgatewaypolicy.agentgateway.dev/a2a-fleet-policy created (server dry run)
```

Nothing was actually applied — every dry-run carries `(server dry run)`.

## Exit verdicts

| PR | Status | Why |
|---|---|---|
| PR 1 — Prompt enrichment | **GREEN** (apply after Inventory caveats 1+2 are resolved) | All required schema fields exist on `proxmox-k8s`. |
| PR 2 — Failover at `/llm/v1` | **GREEN** (apply after Inventory caveats 1+2 are resolved) | Schema confirms mixed-provider groups + per-provider auth. |
| PR 3 — Argo OpenAPI to MCP | **RED — blocked** | `agentgatewaybackend.spec.mcp.targets[].openapi` does not exist on this CRD release. Per the plan's PR 3 decision point: defer until an agentgateway release ships the field, or rescope as a thin Argo MCP shim (a small MCP server backed by argo-server REST). YAMLs in this PR carry a do-not-apply banner. |
| PR 4 — Cross-cluster A2A | **AMBER — rewrite to plan B** | Neither `AgentgatewayBackend.spec.a2a` nor `AgentgatewayPolicy.spec.backend.a2a` exists. Per the plan's PR 4 fallback: route to `kagent-controller.kagent.svc:8083` via plain HTTP + URL rewrite. Identity gate lives at the Istio AuthorizationPolicy layer; gateway-side traffic policies (rate limit, timeout) still apply. Plan-B variant is what `route-a2a-fleet-agent.yaml`, `service-a2a-fleet-agent.yaml`, and `policy-a2a-fleet-agent.yaml` describe — without `appProtocol: agentgateway.dev/a2a` and without `backend.a2a`. |

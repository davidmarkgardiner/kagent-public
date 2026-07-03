# kagent and agentgateway Release Review - 2026-06-30

## Baseline Decision

| Component | Latest checked | Repo baseline | Decision |
|---|---:|---:|---|
| kagent | `v0.10.0-beta1` | `v0.9.10` | Keep `v0.9.10` as the stable install baseline. Treat `v0.10.0-beta1` as lab-only until the A2A, memory, and UI flows pass. |
| agentgateway | `v1.3.1` | `v1.3.1` | Move install and preflight docs from `v1.1.0` to `v1.3.1`, then re-run the management-cluster validation flow. |

Sources checked:

- kagent `v0.9.10`: `https://github.com/kagent-dev/kagent/releases/tag/v0.9.10`
- kagent `v0.10.0-beta1`: `https://github.com/kagent-dev/kagent/releases/tag/v0.10.0-beta1`
- agentgateway `v1.3.0`: `https://github.com/agentgateway/agentgateway/releases/tag/v1.3.0`
- agentgateway `v1.3.1`: `https://github.com/agentgateway/agentgateway/releases/tag/v1.3.1`

## What Changed Upstream

### kagent `v0.9.10`

Useful changes for this repo:

- Helm support for configurable `grafana.prometheusDatasourceName` in the agent chart.
- Helm support for configuring agent memory.
- Security-context fixes across agent charts.
- Graceful degradation when substrate CRDs are absent.
- Substrate added as a subchart.
- OpenShift UI Route is gated behind `ui.route.enabled`.

Why this matters:

- The Grafana datasource setting is directly relevant to the LGTM/Grafana MCP story.
- The agent-memory Helm setting is worth revisiting before we keep custom memory workarounds.
- Security-context fixes reduce friction with Azure Policy and restricted AKS baselines.
- Graceful substrate behavior makes mixed environments safer while we evaluate substrate/ACP.

### kagent `v0.10.0-beta1`

Potential lab-only items:

- Configurable nginx, controller, and UI inactivity timeouts for streaming.
- Controller service annotations.
- UI chat overflow and stale-send fixes.
- Default declarative agent runtime changed to Go.
- ACP shim for communication with agents in substrate.

Hold this for lab testing first because it is a beta-named tag and changes runtime behavior.

### agentgateway `v1.3.0` and `v1.3.1`

Useful changes for this repo:

- New UI for LLM, MCP, and traffic management.
- Cost and token analysis for LLM requests.
- Virtual models for weighted routing, failover, and conditional routing.
- Reusable providers and guardrails.
- Broader LLM provider support.
- Stronger MCP support, including authentication, policy views, resource subscribe/unsubscribe, and MCP-aware auth/extproc.
- Request body buffering, richer external processing, expanded CEL helpers, and improved `agctl`.
- Better observability: request IDs, connection IDs, timing metrics, distributed trace detail, and config-sync metric.
- `v1.3.1` adds patch-level fixes around UI virtual models, schema accuracy, Vertex multi-region endpoints, controller pod labels, and gateway port/protocol handling.

Why this matters:

- Virtual models should replace hard-coded model routing in clients where possible.
- Cost and token metrics give us a better stakeholder value story than raw request counts.
- MCP improvements line up with Grafana MCP, Argo OpenAPI MCP, and future tool authorization demos.
- Request IDs and config-sync metrics make the gateway easier to operate during incident triage.

## Stack Improvements To Bring In

1. **Adopt agentgateway virtual models for model routing.**
   - Start with one logical model exposed to kagent, backed by Qwen/local primary and Azure OpenAI fallback.
   - Keep routing policy in agentgateway rather than in each agent or workflow template.

2. **Use agentgateway cost and token telemetry for value reporting.**
   - Track cost by client, team, model, and workflow where metadata is available.
   - Add dashboard panels for token usage, fallback events, and estimated avoided spend.

3. **Move prompt and safety guardrails closer to the gateway.**
   - Keep workflow-level business approval in Argo/HITL.
   - Put generic prompt, response, auth, and budget controls in agentgateway policy.

4. **Revisit kagent memory configuration.**
   - Replace bespoke memory overrides with chart-level memory settings where the upstream behavior is sufficient.
   - Keep pgvector or durable memory decisions explicit for production.

5. **Add a stable Grafana datasource value in kagent Helm values.**
   - Set `grafana.prometheusDatasourceName` instead of depending on default datasource naming.

6. **Retest Azure Policy posture after the chart upgrades.**
   - The kagent security-context fixes may remove some local exceptions.
   - agentgateway still needs live validation against the target AKS policy set.

## Hermes Integration Assessment

Repo search on 2026-06-30 found no existing Hermes integration references in this public repo. The official Agent Harness example documents `AgentHarness` for OpenClaw, NemoClaw, and Hermes sandboxes:

- `https://www.kagent.dev/docs/kagent/examples/agent-harness`

The local upstream kagent checkout also contains the newer `AgentHarness` CRD at:

- `{{LOCAL_KAGENT_CHECKOUT}}/go/api/config/crd/bases/kagent.dev_agentharnesses.yaml`

That changes the integration direction. Hermes should be evaluated through kagent `AgentHarness`, not as a completely separate sidecar idea.

Version warning:

- kagent `v0.9.10` has the OpenShell-style API that matches the public docs: `backend` supports `openclaw`, `nemoclaw`, and `hermes`; `runtime` defaults to `openshell`; `network.allowedDomains` is supported; `substrate` is optional and only valid when `runtime: substrate`.
- kagent `v0.10.0-beta1` and current upstream `main` have the Substrate-only API: `backend` supports `openclaw` and `hermes`; `spec.substrate` is required; `network.allowedDomains` is not accepted.
- Do not mix the public OpenShell example with the beta Substrate-required CRD.

What `AgentHarness` gives us:

- A namespaced CRD: `agentharnesses.kagent.dev`, kind `AgentHarness`, short name `ahr`.
- `spec.backend` selects the harness backend. In `v0.9.10`, this includes `openclaw`, `nemoclaw`, and `hermes`; in `v0.10.0-beta1`/main, this currently includes `openclaw` and `hermes`.
- `v0.9.10` defaults `runtime` to `openshell`; `v0.10.0-beta1`/main requires `spec.substrate`.
- `spec.modelConfigRef` points the harness at a kagent `ModelConfig`.
- `spec.channels` supports Slack and Telegram bindings, with Hermes-specific Slack options for allowed users and home channel.
- `status.conditions` exposes lifecycle progress and `status.backendRef` records the provisioned backend instance.

Minimal sanitized Hermes harness sketch:

```yaml
apiVersion: kagent.dev/v1alpha2
kind: AgentHarness
metadata:
  name: hermes-ops-harness
  namespace: kagent
spec:
  backend: hermes
  description: Hermes operator harness for read-first SRE investigation
  modelConfigRef: {{MODEL_CONFIG_NAME}}
  network:
    allowedDomains:
      - api.openai.com
      - slack.com
      - api.slack.com
      - wss-primary.slack.com
      - wss-backup.slack.com
  channels:
    - name: ops-slack
      type: slack
      slack:
        appToken:
          valueFrom:
            type: Secret
            name: {{HERMES_SLACK_SECRET_NAME}}
            key: app-token
        botToken:
          valueFrom:
            type: Secret
            name: {{HERMES_SLACK_SECRET_NAME}}
            key: bot-token
        hermes:
          allowedUserIDsFrom:
            type: ConfigMap
            name: {{HERMES_ALLOWED_USERS_CONFIGMAP}}
            key: allowed-users
          homeChannel: {{SLACK_HOME_CHANNEL_ID}}
          homeChannelName: {{SLACK_HOME_CHANNEL_NAME}}
```

Important constraint:

- The upstream design notes say `AgentHarness` resources are not automatically normal kagent agents yet: they are not invoked through `/api/a2a/{namespace}/{name}` unless the ACP bridge path is implemented/enabled. The long-term target is an A2A-to-ACP bridge so OpenClaw, Hermes, Codex, and similar ACP-capable harnesses can appear as first-class kagent agents.
- The reachable {{LAB_KUBE_CONTEXT}} lab cluster was upgraded from kagent `v0.8.0-beta4` to `v0.9.10` on 2026-06-30. It now has `agentharnesses.kagent.dev`, but a real Hermes harness still cannot become Ready until the OpenShell gateway or Substrate API endpoint is configured.

Proof run on 2026-06-30:

- {{LAB_KUBE_CONTEXT}} cluster before upgrade: `agentharnesses.kagent.dev` was absent; `kubectl apply --dry-run=server` accepted the newer CRD manifest itself, but no runtime reconciliation was attempted.
- {{LAB_KUBE_CONTEXT}} cluster upgrade: `helm upgrade kagent-crds ... --version 0.9.10` and `helm upgrade kagent ... --version 0.9.10 --atomic` completed. Controller, UI, tools, KMCP, and bundled PostgreSQL rolled out successfully. Existing `Agent`, `ModelConfig`, and `ToolServer` resources remained visible and existing agents reported `READY=True` / `ACCEPTED=True`.
- {{LAB_KUBE_CONTEXT}} cluster AgentHarness smoke: created temporary `AgentHarness/hermes-proof` with `backend: hermes`; Kubernetes accepted it and defaulted `runtime: openshell`. The kagent controller logged `AgentHarness controller disabled: set --openshell-gateway-url and/or --substrate-ate-api-endpoint`, proving the next blocker is backend configuration rather than CRD availability. The temporary object was deleted.
- Disposable kind cluster `kind-agentharness-proof`: installed kagent `v0.9.10` `agentharnesses.kagent.dev` CRD and created the public-doc-style Hermes manifest. Kubernetes accepted it and defaulted `RUNTIME` to `openshell`.
- Same proof rejected a Hermes Slack manifest with `slack.openclaw` settings, proving the CEL backend-specific validation works.
- Same proof installed the `v0.10.0-beta1` CRD and confirmed the public-doc-style manifest is rejected because `spec.network` is unknown; a minimal `spec.substrate.workerPoolRef.name` Hermes manifest passes server-side dry-run.

Substrate-only sketch for kagent `v0.10.0-beta1` or current upstream `main`:

```yaml
apiVersion: kagent.dev/v1alpha2
kind: AgentHarness
metadata:
  name: hermes-substrate
  namespace: kagent
spec:
  backend: hermes
  description: Hermes shell on Agent Substrate
  modelConfigRef: {{MODEL_CONFIG_NAME}}
  substrate:
    workerPoolRef:
      name: {{SUBSTRATE_WORKER_POOL_NAME}}
```

Recommended shape:

```
Hermes AgentHarness on Substrate
  -> read-only MCP tools for Grafana, GitLab, Argo, and Kubernetes evidence
  -> A2A/ACP bridge when available for first-class agent composition
  -> Argo Workflow submission for controlled remediation
  -> Teams/GitLab/ServiceNow update after HITL or workflow verdict
```

Hermes should be treated as an operator-facing harness, not as a direct cluster-mutating control plane:

- Read-only by default: query alerts, dashboards, workflow status, GitLab evidence, and runbook docs.
- Write actions go through Argo Workflows or approved platform APIs.
- Agent-to-agent work should use A2A or MCP through agentgateway where possible, so auth, policy, logs, and cost telemetry are centralized.
- High-risk actions need HITL gates before remediation.

Good first demo:

1. Hermes receives or is asked about an LGTM alert.
2. Hermes queries Grafana MCP for alert context and dashboard evidence.
3. Hermes queries GitLab for the workflow issue/comment thread.
4. Hermes asks the kagent triage agent for an analysis summary over A2A.
5. Hermes submits a dry-run Argo Workflow for the recommended remediation.
6. Argo posts the result back to GitLab/Teams, with ServiceNow only created if the workflow cannot remediate or needs human ownership.

## Upgrade Validation Gates

Before calling the upgrade complete:

- `helm template` agentgateway `v1.3.1` and inspect rendered images/resources.
- Apply agentgateway CRDs and controller in the management cluster.
- Re-run `platform/agentgateway/VALIDATE-MGMT.md`.
- Verify kagent can still call agentgateway through the ModelConfig route.
- Verify token/cost/request metrics are visible in Prometheus/Grafana.
- Run one A2A triage workflow end-to-end through Argo.
- In the lab only, install kagent `v0.10.0-beta1` and compare A2A, memory, UI, and streaming behavior before adopting it.

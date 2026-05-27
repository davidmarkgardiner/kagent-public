# Agent Replication Prompt

Use this prompt with a coding or platform agent to replicate the K-Agent and
Agent Gateway observability flow in a target work environment.

Before running it, provide the target environment values in the placeholder
block. Do not paste secrets into a public repo. Give the agent access to a
secret manager, local env vars, or a private notes file when credentials are
required.

Use [`agent-replication.env.example`](agent-replication.env.example) as the
fillable environment template.

## Required Bundle

Give the agent these paths, not only this `docs/observability/` folder:

```text
docs/observability/caf-style-observability-handoff.md
docs/observability/agent-replication.env.example
docs/observability/grafana-mcp-home-lab.md
docs/ai-grafana/end-to-end-hitl-demo.md
agents/skills/grafana-chaos-incident-triage/SKILL.md
k8s/observability/
observability/grafana/dashboards/k-agent-agentgateway-public-ready.json
observability/grafana/dashboards/agentgateway-traffic-quality.json
observability/grafana/provisioning/
observability/managed-lgtm-integration/rule-sync/
observability/managed-lgtm-integration/alerting/03-lokirules-k-agent-agentgateway.yaml
observability/grafana-argo-pipeline/README.md
platform/teams-hitl/
observability/prometheus-alertmanager/enhanced/04-workflow-template.yaml
scripts/observability/verify-k-agent-observability.sh
scripts/observability/smoke-grafana-mcp.sh
```

Optional broker/contact-point bundle:

```text
observability/confluent-cloud-pipeline/
```

Use that optional bundle only if the target environment cannot call the Argo
Events webhook directly or needs broker buffering/replay/fan-out.

## Placeholder Block

Fill these in before handing the prompt to the agent:

```text
KUBE_CONTEXT={{KUBE_CONTEXT}}
CLUSTER_NAME={{CLUSTER_NAME}}
MONITORING_NAMESPACE={{MONITORING_NAMESPACE}}
KAGENT_NAMESPACE={{KAGENT_NAMESPACE}}
GATEWAY_NAMESPACE_REGEX={{GATEWAY_NAMESPACE_REGEX}}
ARGO_EVENTS_NAMESPACE={{ARGO_EVENTS_NAMESPACE}}
ARGO_WORKFLOWS_NAMESPACE={{ARGO_WORKFLOWS_NAMESPACE}}

PROMETHEUS_REMOTE_WRITE_URL={{PROMETHEUS_REMOTE_WRITE_URL}}
LOKI_PUSH_URL={{LOKI_PUSH_URL}}
GRAFANA_URL={{GRAFANA_URL}}
GRAFANA_PROMETHEUS_DATASOURCE_UID={{GRAFANA_PROMETHEUS_DATASOURCE_UID}}
GRAFANA_LOKI_DATASOURCE_UID={{GRAFANA_LOKI_DATASOURCE_UID}}
GRAFANA_ALERTMANAGER_DATASOURCE_UID={{GRAFANA_ALERTMANAGER_DATASOURCE_UID}}
GRAFANA_CONTACT_POINT_NAME={{GRAFANA_CONTACT_POINT_NAME}}
GRAFANA_CONTACT_POINT_URL={{GRAFANA_CONTACT_POINT_URL}}
GRAFANA_MCP_REMOTEMCPSERVER={{GRAFANA_MCP_REMOTEMCPSERVER}}
GRAFANA_MCP_TOKEN_SECRET_NAME={{GRAFANA_MCP_TOKEN_SECRET_NAME}}

ALERTMANAGER_WEBHOOK_URL={{ALERTMANAGER_WEBHOOK_URL}}
ARGO_EVENTSOURCE_WEBHOOK_URL={{ARGO_EVENTSOURCE_WEBHOOK_URL}}
KAGENT_CONTROLLER_URL={{KAGENT_CONTROLLER_URL}}
KAGENT_TRIAGE_AGENT_NAME={{KAGENT_TRIAGE_AGENT_NAME}}
KAGENT_TRIAGE_A2A_URL={{KAGENT_TRIAGE_A2A_URL}}
MODEL_CONFIG_NAME={{MODEL_CONFIG_NAME}}
AKS_MCP_REMOTEMCPSERVER={{AKS_MCP_REMOTEMCPSERVER}}

TEAMS_BOT_ENDPOINT={{TEAMS_BOT_ENDPOINT}}
TEAMS_HITL_CALLBACK_URL={{TEAMS_HITL_CALLBACK_URL}}
TEAMS_APPROVAL_SECRET_NAME={{TEAMS_APPROVAL_SECRET_NAME}}
GITLAB_PROJECT={{GITLAB_PROJECT}}
GITLAB_TOKEN_SECRET_NAME={{GITLAB_TOKEN_SECRET_NAME}}

AUTH_NOTES={{WHERE_AUTH_TOKENS_OR_HEADERS_ARE_STORED}}
NETWORK_NOTES={{HOW_GRAFANA_ALERTING_OR_ALERTMANAGER_REACHES_ARGO_EVENTS}}
CHANGE_CONTROL_NOTES={{CHANGE_WINDOW_OR_APPROVAL_REFERENCE}}
```

## Prompt

```text
You are a platform engineering agent. Replicate the K-Agent and Agent Gateway
observability flow from this bundle into the target Kubernetes environment.

Goal:
Build a working, evidence-backed observability and HITL incident path:

Chaos fault or synthetic failure -> Alloy telemetry -> Prometheus/Mimir and
Loki -> Grafana dashboard -> Alertmanager or Grafana Alerting contact point ->
Argo Events -> Argo Workflow -> K-Agent observability-agent -> Grafana MCP /
optional AKS-MCP evidence -> agent-to-agent handoff or HITL approval agent ->
Teams approval -> Argo resume -> scoped remediation agent/workflow ->
verification -> GitLab update/closeout.

This is the showcase flow to prove:
1. Inject or simulate a bounded fault.
2. Alertmanager or Grafana Alerting fires.
3. The alert reaches Argo Events.
4. Argo creates a workflow and preserves the alert payload.
5. The analysis agent uses Grafana MCP to query metrics, logs, dashboards,
   alert metadata, and deeplinks.
6. The analysis agent optionally uses read-only AKS-MCP or Kubernetes tools for
   cluster evidence.
7. The workflow passes the evidence pack to an approval/HITL agent or Teams bot.
8. A human approves or rejects in Teams.
9. Argo resumes only after approval.
10. A separate scoped remediation agent or workflow performs the approved fix.
11. The workflow verifies recovery through Grafana MCP and Kubernetes read
    checks.
12. GitLab is updated with evidence, approval, action, verification, and
    closeout.

Use these values:

KUBE_CONTEXT={{KUBE_CONTEXT}}
CLUSTER_NAME={{CLUSTER_NAME}}
MONITORING_NAMESPACE={{MONITORING_NAMESPACE}}
KAGENT_NAMESPACE={{KAGENT_NAMESPACE}}
GATEWAY_NAMESPACE_REGEX={{GATEWAY_NAMESPACE_REGEX}}
ARGO_EVENTS_NAMESPACE={{ARGO_EVENTS_NAMESPACE}}
ARGO_WORKFLOWS_NAMESPACE={{ARGO_WORKFLOWS_NAMESPACE}}
PROMETHEUS_REMOTE_WRITE_URL={{PROMETHEUS_REMOTE_WRITE_URL}}
LOKI_PUSH_URL={{LOKI_PUSH_URL}}
GRAFANA_URL={{GRAFANA_URL}}
GRAFANA_PROMETHEUS_DATASOURCE_UID={{GRAFANA_PROMETHEUS_DATASOURCE_UID}}
GRAFANA_LOKI_DATASOURCE_UID={{GRAFANA_LOKI_DATASOURCE_UID}}
GRAFANA_ALERTMANAGER_DATASOURCE_UID={{GRAFANA_ALERTMANAGER_DATASOURCE_UID}}
GRAFANA_CONTACT_POINT_NAME={{GRAFANA_CONTACT_POINT_NAME}}
GRAFANA_CONTACT_POINT_URL={{GRAFANA_CONTACT_POINT_URL}}
GRAFANA_MCP_REMOTEMCPSERVER={{GRAFANA_MCP_REMOTEMCPSERVER}}
GRAFANA_MCP_TOKEN_SECRET_NAME={{GRAFANA_MCP_TOKEN_SECRET_NAME}}
ALERTMANAGER_WEBHOOK_URL={{ALERTMANAGER_WEBHOOK_URL}}
ARGO_EVENTSOURCE_WEBHOOK_URL={{ARGO_EVENTSOURCE_WEBHOOK_URL}}
KAGENT_CONTROLLER_URL={{KAGENT_CONTROLLER_URL}}
KAGENT_TRIAGE_AGENT_NAME={{KAGENT_TRIAGE_AGENT_NAME}}
KAGENT_TRIAGE_A2A_URL={{KAGENT_TRIAGE_A2A_URL}}
MODEL_CONFIG_NAME={{MODEL_CONFIG_NAME}}
AKS_MCP_REMOTEMCPSERVER={{AKS_MCP_REMOTEMCPSERVER}}
TEAMS_BOT_ENDPOINT={{TEAMS_BOT_ENDPOINT}}
TEAMS_HITL_CALLBACK_URL={{TEAMS_HITL_CALLBACK_URL}}
TEAMS_APPROVAL_SECRET_NAME={{TEAMS_APPROVAL_SECRET_NAME}}
GITLAB_PROJECT={{GITLAB_PROJECT}}
GITLAB_TOKEN_SECRET_NAME={{GITLAB_TOKEN_SECRET_NAME}}
AUTH_NOTES={{WHERE_AUTH_TOKENS_OR_HEADERS_ARE_STORED}}
NETWORK_NOTES={{HOW_GRAFANA_ALERTING_OR_ALERTMANAGER_REACHES_ARGO_EVENTS}}
CHANGE_CONTROL_NOTES={{CHANGE_WINDOW_OR_APPROVAL_REFERENCE}}

Rules:
1. Read `docs/observability/caf-style-observability-handoff.md` first.
   Then read `docs/ai-grafana/end-to-end-hitl-demo.md`,
   `docs/observability/grafana-mcp-home-lab.md`,
   `agents/skills/grafana-chaos-incident-triage/SKILL.md`, and
   `platform/teams-hitl/README.md`.
2. Do not commit secrets, tokens, private hostnames, cluster IPs, or tenant IDs.
   Keep environment-specific values in private env vars, Kubernetes Secrets, or
   the target environment's secret manager.
3. Use `{{PLACEHOLDER}}` values in any repo artifact you create.
4. Verify the target cluster before applying anything:
   - namespaces exist or are intentionally created
   - kagent is running
   - Agent Gateway or kgateway pods expose scrapeable metrics
   - Grafana has Prometheus/Mimir and Loki datasources
   - Grafana MCP is installed or can be installed, and kagent can reach it as a
     `RemoteMCPServer`
   - `observability-agent` exists and has current Grafana MCP read tool names
   - the `observability-agent` `modelConfig` points at a live Agent Gateway
     route to the local model, not directly at a dead LiteLLM/KubeAI service
     and not only an `Accepted` ModelConfig object
   - AKS-MCP is available only with read-only tools if you include it in the
     analysis agent
   - Argo Events and Argo Workflows are installed
   - the Teams HITL callback EventSource and Sensor can be deployed or already
     exist
   - GitLab issue creation/update credentials are available through a Secret
5. Apply the narrowest required artifacts:
   - `k8s/observability/k-agent-alloy.yaml`
   - `k8s/observability/k-agent-agentgateway-scrape.yaml`
   - `k8s/observability/k-agent-alerts.yaml`
   - `k8s/observability/k-agent-alertmanager-eventsource.yaml`
   - `k8s/observability/k-agent-alertmanager-triage-route.yaml`
   - `k8s/observability/k-agent-alert-triage-sensor.yaml`
   - Teams HITL EventSource/Sensor snippets from `platform/teams-hitl/` only
     after confirming the work bot endpoint and callback URL
6. If Grafana MCP is missing, deploy it before wiring the agent:
   - create a dedicated Grafana service account with read-only datasource,
     dashboard, query, and alert-inspection permissions
   - store the token in a Kubernetes Secret named by
     `GRAFANA_MCP_TOKEN_SECRET_NAME` or the environment's approved secret name
   - install the Grafana MCP server with the approved chart/image, pointing it
     at `GRAFANA_URL`
   - create or verify this kagent `RemoteMCPServer`:

   ```yaml
   apiVersion: kagent.dev/v1alpha2
   kind: RemoteMCPServer
   metadata:
     name: kagent-grafana-mcp
     namespace: kagent
   spec:
     description: Grafana MCP server for read-only observability triage
     protocol: STREAMABLE_HTTP
     sseReadTimeout: 5m0s
     terminateOnClose: true
     timeout: 30s
     url: http://kagent-grafana-mcp.kagent:8000/mcp
   ```

7. Deploy or patch `observability-agent` so it references Grafana MCP. Keep
   the normal analysis agent read-oriented. Use live discovered tool names from:

   ```bash
   kubectl --context {{KUBE_CONTEXT}} -n kagent get remotemcpserver kagent-grafana-mcp \
     -o jsonpath='{range .status.discoveredTools[*]}{.name}{"\n"}{end}' | sort
   ```

   The agent must include a `tools` entry like this, with stale or unavailable
   tools removed:

   ```yaml
   tools:
     - type: McpServer
       mcpServer:
         apiGroup: kagent.dev
         kind: RemoteMCPServer
         name: kagent-grafana-mcp
         toolNames:
           - list_datasources
           - get_datasource
           - search_dashboards
           - get_dashboard_summary
           - get_dashboard_panel_queries
           - query_prometheus
           - query_loki_logs
           - list_prometheus_metric_names
           - list_prometheus_label_names
           - list_prometheus_label_values
           - list_loki_label_names
           - list_loki_label_values
           - generate_deeplink
   ```

   Optional read-only AKS-MCP can be added as a second `McpServer` only if its
   tool list excludes apply/delete/mutation tools. Write-capable Kubernetes,
   Grafana, GitLab, and incident tools belong in the approved remediation
   workflow or a separate write-scoped agent, not in `observability-agent`.

8. Confirm the agent can be reached through A2A before connecting alerts:

   ```bash
   curl -sS -X POST {{KAGENT_TRIAGE_A2A_URL}} \
     -H 'Content-Type: application/json' \
     -d '{
       "jsonrpc": "2.0",
       "id": "observability-agent-smoke",
       "method": "message/send",
       "params": {
         "message": {
           "role": "user",
           "parts": [{
             "kind": "text",
             "text": "Use Grafana MCP to list datasources, run count(up), and return datasource UIDs plus the exact query used."
           }]
         }
       }
     }'
   ```

   If this fails, fix model backend, agent readiness, A2A routing, or MCP tool
   discovery before proceeding to the alert flow.

   Model backend checks must include:

   ```bash
   kubectl --context {{KUBE_CONTEXT}} -n kagent get agent observability-agent \
     -o jsonpath='{.spec.declarative.modelConfig}{"\n"}'
   kubectl --context {{KUBE_CONTEXT}} -n kagent get modelconfig {{MODEL_CONFIG_NAME}} -o yaml
   kubectl --context {{KUBE_CONTEXT}} -n agentgateway-system get agentgatewaybackend,httproute
   kubectl --context {{KUBE_CONTEXT}} get pods -A | grep -Ei 'litellm|kubeai|model|vllm|qwen'
   ```

   A `ModelConfig` with `Accepted=True` is not enough. The backing service and
   model pod must be reachable and healthy. If the target shape is local Qwen
   through Agent Gateway, use `platform/agentgateway/backend-kubeai-qwen.yaml`
   plus `platform/agentgateway/modelconfig-default-qwen.yaml` as the durable
   repo-backed version of the live routing.

9. Import both dashboards into Grafana and set their datasource variables to
   the target datasource UIDs:
   - `observability/grafana/dashboards/k-agent-agentgateway-public-ready.json`
   - `observability/grafana/dashboards/agentgateway-traffic-quality.json`
10. Configure the Grafana or Alertmanager contact point so alerts reach Argo
   Events:
   - prefer direct webhook to `ARGO_EVENTSOURCE_WEBHOOK_URL` when network
     routing allows it
   - use the broker bundle only when buffering, replay, fan-out, or network
     decoupling is required
   - preserve the original Alertmanager-shaped payload labels and annotations
   - required labels for the existing sensor are `kagent_path=webhook` and
     `route_to=triage`
11. Configure or verify alert rules for the demo:
   - one low-risk synthetic rule for route validation
   - one K-Agent or Agent Gateway signal rule from `k8s/observability/k-agent-alerts.yaml`
   - optional managed Loki rules only through the Loki ruler sync path
12. Configure the analysis agent session path:
   - confirm `KAGENT_TRIAGE_A2A_URL` accepts `message/send`
   - confirm the agent can call Grafana MCP read tools
   - confirm the agent returns evidence, uncertainty, and action tier
   - do not give the analysis agent write-capable Kubernetes or Grafana tools
13. Configure Teams HITL:
   - deploy or verify the Teams approval callback EventSource/Sensor
   - verify the bot endpoint can receive an approval request
   - verify approval callback can resume a suspended Argo workflow
   - include evidence summary, Grafana deeplinks, GitLab issue link, workflow
     link, proposed action, target, expiry, and approval id in the card
14. Configure GitLab closeout:
   - create or update an issue before requesting approval
   - add the evidence pack to the issue
   - after remediation, comment verification results
   - close the issue only if verification passes and the alert resolves
15. If Loki is not healthy, do not hide that with empty log panels. Show Loki
   health as a first-class finding and keep the dashboard metric-first until
   the Loki backend is repaired.
16. If `agentgateway_gen_ai_client_token_usage_*` samples are absent, inspect the
   raw Agent Gateway `/metrics` endpoint. If the HELP/TYPE lines are present but
   Prometheus has no series, document that no LLM traffic is producing token
   samples through this gateway path. Also check whether K-Agent `ModelConfig`
   resources send model calls directly to LiteLLM/KubeAI/OpenAI instead of
   routing them through Agent Gateway.
17. Use `Agent Gateway Traffic Quality` to report route/backend/status/reason
   for failed calls, 504/timeouts, calls slower than 30s, p95/p99 latency, and
   active request buildup. Treat those as the signal for agent runs that may
   have called an LLM or tool but never produced a final triage result.
18. Do not claim per-agent, per-tool, or per-model attribution unless the target
    gateway or agent runtime emits labels/spans/logs with those fields. If
    those labels are missing, report route/backend/status/reason as the current
    evidence and list the missing instrumentation.
19. For log alert rules, use the managed LGTM rule-sync path only if the target
   environment supports Mimir/Loki ruler sync. Do not apply LogQL rules to a
   vanilla Prometheus rule selector.
20. Keep remediation write permissions out of the analysis agent. The approved
    remediation step should run as a separate workflow service account or
    remediation agent with the narrowest permissions required for the demo
    target.

Verification required before reporting done:
1. Run static validation:
   `scripts/observability/verify-k-agent-observability.sh`
2. Run live validation:
   `scripts/observability/verify-k-agent-observability.sh --context {{KUBE_CONTEXT}}`
3. Run direct Grafana MCP validation:
   `scripts/observability/smoke-grafana-mcp.sh --context {{KUBE_CONTEXT}}`
4. Query Grafana or Prometheus/Mimir and report exact results for:
   - K-Agent running pods
   - Gateway scrape targets
   - Gateway request rate
   - Gateway p95 latency
   - token metric availability
   - Loki backend/gateway readiness
   - Argo workflow outcomes
5. Verify the contact point and alert route:
   - show the Grafana contact point or Alertmanager receiver configuration
   - send a test alert or run the synthetic alert route
   - report the created `k-agent-alert-triage-*` workflow name and phase
6. Verify the agent-mediated evidence path:
   - show the `observability-agent` A2A call succeeded or failed with a clear
     error
   - report the datasource UIDs, PromQL, LogQL, and Grafana deeplinks returned
     by the agent
7. Verify Teams HITL:
   - submit a harmless approval workflow or demo alert workflow
   - show the workflow suspended
   - show the approval id
   - approve through Teams or the approved mock/curl callback
   - show the workflow resumed
8. Verify scoped remediation:
   - use only the approved demo target, such as `chaos-demo/chaos-target`
   - show the exact resource changed
   - show verification after the change
9. Verify GitLab closeout:
   - show issue created or updated
   - show evidence comment
   - show closeout only after verification passes
10. If approved for the environment, run:
   `scripts/observability/verify-k-agent-observability.sh --context {{KUBE_CONTEXT}} --synthetic-alert`
   and report the created `k-agent-alert-triage-*` workflow name and phase.

Final report format:
- What was applied
- What was imported into Grafana
- Live query evidence with exact values
- Alert/contact point path selected and why
- Grafana MCP tools discovered and queries run
- K-Agent session or A2A evidence
- Teams approval id and decision
- Remediation action and verification result
- GitLab issue link and closeout status
- What is working
- What is blocked or degraded
- Follow-up fixes needed before production handover
```

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
k8s/observability/
observability/grafana/dashboards/k-agent-agentgateway-public-ready.json
observability/grafana/dashboards/agentgateway-traffic-quality.json
observability/grafana/provisioning/
observability/managed-lgtm-integration/rule-sync/
observability/managed-lgtm-integration/alerting/03-lokirules-k-agent-agentgateway.yaml
observability/grafana-argo-pipeline/README.md
scripts/observability/verify-k-agent-observability.sh
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

ALERTMANAGER_WEBHOOK_URL={{ALERTMANAGER_WEBHOOK_URL}}
ARGO_EVENTSOURCE_WEBHOOK_URL={{ARGO_EVENTSOURCE_WEBHOOK_URL}}

AUTH_NOTES={{WHERE_AUTH_TOKENS_OR_HEADERS_ARE_STORED}}
NETWORK_NOTES={{HOW_GRAFANA_ALERTING_OR_ALERTMANAGER_REACHES_ARGO_EVENTS}}
```

## Prompt

```text
You are a platform engineering agent. Replicate the K-Agent and Agent Gateway
observability flow from this bundle into the target Kubernetes environment.

Goal:
Build a working, evidence-backed observability path:

Alloy -> Prometheus/Mimir and Loki -> Grafana dashboard -> alert rules/contact
point -> Argo Events -> Argo Workflow -> K-Agent observability-agent.

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
ALERTMANAGER_WEBHOOK_URL={{ALERTMANAGER_WEBHOOK_URL}}
ARGO_EVENTSOURCE_WEBHOOK_URL={{ARGO_EVENTSOURCE_WEBHOOK_URL}}
AUTH_NOTES={{WHERE_AUTH_TOKENS_OR_HEADERS_ARE_STORED}}
NETWORK_NOTES={{HOW_GRAFANA_ALERTING_OR_ALERTMANAGER_REACHES_ARGO_EVENTS}}

Rules:
1. Read `docs/observability/caf-style-observability-handoff.md` first.
2. Do not commit secrets, tokens, private hostnames, cluster IPs, or tenant IDs.
   Keep environment-specific values in private env vars, Kubernetes Secrets, or
   the target environment's secret manager.
3. Use `{{PLACEHOLDER}}` values in any repo artifact you create.
4. Verify the target cluster before applying anything:
   - namespaces exist or are intentionally created
   - kagent is running
   - Agent Gateway or kgateway pods expose scrapeable metrics
   - Grafana has Prometheus/Mimir and Loki datasources
   - Argo Events and Argo Workflows are installed
5. Apply the narrowest required artifacts:
   - `k8s/observability/k-agent-alloy.yaml`
   - `k8s/observability/k-agent-agentgateway-scrape.yaml`
   - `k8s/observability/k-agent-alerts.yaml`
   - `k8s/observability/k-agent-alertmanager-eventsource.yaml`
   - `k8s/observability/k-agent-alertmanager-triage-route.yaml`
   - `k8s/observability/k-agent-alert-triage-sensor.yaml`
6. Import both dashboards into Grafana and set their datasource variables to
   the target datasource UIDs:
   - `observability/grafana/dashboards/k-agent-agentgateway-public-ready.json`
   - `observability/grafana/dashboards/agentgateway-traffic-quality.json`
7. If Loki is not healthy, do not hide that with empty log panels. Show Loki
   health as a first-class finding and keep the dashboard metric-first until
   the Loki backend is repaired.
8. If `agentgateway_gen_ai_client_token_usage_*` metrics are absent, keep the
   dashboard's explicit token-metric availability panel and document that token
   burn cannot be measured from metrics in this gateway build.
9. Use `Agent Gateway Traffic Quality` to report route/backend/status/reason
   for failed calls, 504/timeouts, calls slower than 30s, p95/p99 latency, and
   active request buildup. Treat those as the signal for agent runs that may
   have called an LLM or tool but never produced a final triage result.
10. Do not claim per-agent, per-tool, or per-model attribution unless the target
    gateway or agent runtime emits labels/spans/logs with those fields. If
    those labels are missing, report route/backend/status/reason as the current
    evidence and list the missing instrumentation.
11. For log alert rules, use the managed LGTM rule-sync path only if the target
   environment supports Mimir/Loki ruler sync. Do not apply LogQL rules to a
   vanilla Prometheus rule selector.
12. For the alert-to-triage loop, prefer the direct Argo Events webhook when
    Grafana Alerting or Alertmanager can reach it. Use the optional broker
    bundle only when direct routing is not possible or when replay/fan-out is
    required.

Verification required before reporting done:
1. Run static validation:
   `scripts/observability/verify-k-agent-observability.sh`
2. Run live validation:
   `scripts/observability/verify-k-agent-observability.sh --context {{KUBE_CONTEXT}}`
3. Query Grafana or Prometheus/Mimir and report exact results for:
   - K-Agent running pods
   - Gateway scrape targets
   - Gateway request rate
   - Gateway p95 latency
   - token metric availability
   - Loki backend/gateway readiness
   - Argo workflow outcomes
4. If approved for the environment, run:
   `scripts/observability/verify-k-agent-observability.sh --context {{KUBE_CONTEXT}} --synthetic-alert`
   and report the created `k-agent-alert-triage-*` workflow name and phase.

Final report format:
- What was applied
- What was imported into Grafana
- Live query evidence with exact values
- Alert/contact point path selected and why
- What is working
- What is blocked or degraded
- Follow-up fixes needed before production handover
```

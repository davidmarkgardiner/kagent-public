# CAF-Style K-Agent and Agent Gateway Observability Handoff

This is the operator handoff for replicating the working Proxmox observability
pattern in a work-owned Prometheus, Loki, and Grafana stack.

If you are handing this to another agent, use
[`agent-replication-prompt.md`](agent-replication-prompt.md). It includes the
required bundle paths, placeholders, and verification contract. Fill
[`agent-replication.env.example`](agent-replication.env.example) first so the
agent has the target endpoints, datasource UIDs, routing mode, and auth notes.

The flow is:

```text
K-Agent + Agent Gateway pods
  -> Alloy pod log tailing and Prometheus scraping
  -> Loki and Prometheus/Mimir endpoints
  -> Grafana dashboard and alert rules
  -> Grafana or Alertmanager contact point
  -> Argo Events webhook or broker EventSource
  -> Argo Workflow
  -> K-Agent SRE triage agent
```

Keep this as a GitOps package. The only environment-specific inputs should be
endpoint URLs, datasource UIDs, contact point URLs, tenant headers, and secrets.
Use placeholders in Git and inject real values through the target environment.

## Artifact Map

| Layer | Use this |
| --- | --- |
| Alloy metrics and logs | `k8s/observability/k-agent-alloy.yaml` |
| Gateway scrape coverage | `k8s/observability/k-agent-agentgateway-scrape.yaml` |
| Grafana dashboard JSON | `observability/grafana/dashboards/k-agent-agentgateway-public-ready.json` |
| Gateway traffic-quality dashboard | `observability/grafana/dashboards/agentgateway-traffic-quality.json` |
| Prometheus alerts | `k8s/observability/k-agent-alerts.yaml` |
| Loki log alerts | `observability/managed-lgtm-integration/alerting/03-lokirules-k-agent-agentgateway.yaml` |
| Alertmanager webhook EventSource | `k8s/observability/k-agent-alertmanager-eventsource.yaml` |
| Alertmanager route | `k8s/observability/k-agent-alertmanager-triage-route.yaml` |
| Argo triage Sensor | `k8s/observability/k-agent-alert-triage-sensor.yaml` |
| Rule-sync guide | `observability/managed-lgtm-integration/rule-sync/README.md` |
| Verification script | `scripts/observability/verify-k-agent-observability.sh` |

Optional broker-backed contact-point patterns live under
`observability/confluent-cloud-pipeline/` when the environment needs buffering,
replay, or fan-out between Grafana Alerting and Argo Events.

## Deployment Order

1. Confirm the target Grafana datasources:

   - Prometheus or Mimir datasource for metrics.
   - Loki datasource for pod logs and structured triage logs.
   - Alertmanager datasource if Grafana manages alerting or notification history.

2. Apply or reconcile Alloy:

   ```bash
   kubectl apply -f k8s/observability/k-agent-alloy.yaml
   kubectl -n monitoring set env deployment/k-agent-alloy \
     CLUSTER_NAME="{{CLUSTER_NAME}}" \
     LOKI_PUSH_URL="{{LOKI_PUSH_URL}}" \
     PROMETHEUS_REMOTE_WRITE_URL="{{PROMETHEUS_REMOTE_WRITE_URL}}"
   kubectl -n monitoring rollout status deployment/k-agent-alloy
   ```

3. Apply scrape coverage and metric alerts:

   ```bash
   kubectl apply -f k8s/observability/k-agent-agentgateway-scrape.yaml
   kubectl apply -f k8s/observability/k-agent-alerts.yaml
   ```

4. Import the dashboard:

   ```text
   observability/grafana/dashboards/k-agent-agentgateway-public-ready.json
   observability/grafana/dashboards/agentgateway-traffic-quality.json
   ```

   Set the `datasource_prom` and `datasource_loki` variables to the work
   stack datasource names at import time. The traffic-quality dashboard only
   needs `datasource_prom`.

5. Wire alert delivery back into Argo:

   ```bash
   kubectl apply -f k8s/observability/k-agent-alertmanager-eventsource.yaml
   kubectl apply -f k8s/observability/k-agent-alertmanager-triage-route.yaml
   kubectl apply -f k8s/observability/k-agent-alert-triage-sensor.yaml
   ```

6. If managed Mimir/Loki rulers are used, enable rule sync with the split
   Mimir and Loki paths in:

   ```text
   observability/managed-lgtm-integration/rule-sync/README.md
   ```

## Dashboard Standard

The dashboard is designed to answer five questions without making the user jump
between tools:

| Question | Panels |
| --- | --- |
| Is K-Agent available? | `K-Agent Running Pods`, `Restarts Last Hour` |
| Is Agent Gateway observable? | `Gateway Metrics Scraped`, `Agent Gateway Response Rate` |
| Is Agent Gateway healthy? | `Agent Gateway 5xx Ratio`, `Agent Gateway Upstream Latency p95` |
| Can this build expose token burn? | `Agent Gateway Token Metrics Available` |
| Is alert triage closed-loop? | `Triage Alerts Firing`, `Argo Workflow Outcomes Last 24h` |
| Is Loki healthy enough for logs? | `Loki Backend Ready`, `Loki Gateway Ready`, `Loki Pod Readiness`, `Cluster Node Readiness` |

Use `Agent Gateway Traffic Quality` when you need the gateway-specific view:

| Question | Panels |
| --- | --- |
| Are A2A or LLM-facing calls failing? | `Failed Gateway Calls Last Hour`, `Failed or Timed Out Call Rate`, `Top Failed Routes Last 24h` |
| Are calls timing out before an agent produces a final result? | `Timed Out Calls Last Hour`, `Calls Slower Than 30s Last 24h`, `Gateway Latency by Route` |
| Which route/backend is responsible? | route, backend, status, and reason labels on the traffic panels and tables |
| Is token burn available from this gateway path? | `Token Samples`, `Token Usage Per Minute`, `Top Token Users Last 24h` |
| Are requests piling up? | `Active Gateway Requests` |

For demos and handover, use a `Last 24 hours` time range. The working path can
have sparse event/log traffic, and a one-hour default makes useful panels look
blank even when the pipeline is healthy.

## Contact Point Options

Use the simplest path that meets the reliability requirement.

| Option | Path | Use when |
| --- | --- | --- |
| Direct Argo webhook | Grafana or Alertmanager -> Argo EventSource webhook | Low latency and the Grafana/Alertmanager network can reach the management cluster |
| AlertmanagerConfig | Prometheus Operator Alertmanager -> Argo EventSource webhook | Alerts originate from kube-prometheus-stack and stay Kubernetes-native |
| Broker-backed | Grafana or Alertmanager -> bridge/contact point -> Kafka/Event Hub -> Argo Events | Need buffering, replay, fan-out, or network decoupling |

The Argo-triggered workflow should call the read-only `observability-agent`.
Agents do not get resource-changing permissions; workflows hold the execution
service account.

## Verification Checklist

Run static checks first:

```bash
scripts/observability/verify-k-agent-observability.sh
```

Run live checks against the target cluster:

```bash
scripts/observability/verify-k-agent-observability.sh --context {{KUBE_CONTEXT}}
```

For the full loop, use the synthetic alert mode in a non-production or approved
test window:

```bash
scripts/observability/verify-k-agent-observability.sh \
  --context {{KUBE_CONTEXT}} \
  --synthetic-alert
```

Expected proof points:

- Grafana health API returns `database: ok`.
- Prometheus query for gateway scrape targets returns non-zero series.
- Prometheus query for K-Agent running pods returns non-zero series.
- Loki returns streams for `kagent`, gateway, and triage namespaces over the
  chosen time range.
- `ALERTS{route_to="triage", kagent_path="webhook"}` appears when the synthetic
  rule fires.
- Argo creates a `k-agent-alert-triage-*` workflow.
- The workflow logs either `K_AGENT_ALERT_TRIAGE_BEGIN` and a model response, or
  `K_AGENT_ALERT_TRIAGE_UNAVAILABLE` with a clear timeout or upstream error.

## Current Lab Evidence

Read-only checks against the local Proxmox validation cluster on 2026-05-26
showed:

| Check | Result |
| --- | --- |
| Grafana health | `database: ok`, Grafana `12.3.2` |
| Gateway scrape targets | `count(up{namespace=~"agentgateway-system|kgateway-system"} == 1)` returned `8` |
| K-Agent running pods | `count(kube_pod_status_phase{namespace="kagent",phase="Running"} == 1)` returned `21` |
| Gateway request metric | `envoy_cluster_external_upstream_rq_xx` returned a live `kgateway-system` 2xx series |
| Agent Gateway route labels | `agentgateway_requests_total` exposed `route`, `backend`, `status`, and `reason` labels for the cross-namespace A2A route |
| Token metric | the Agent Gateway data-plane `/metrics` endpoint advertised `agentgateway_gen_ai_client_token_usage`, but Prometheus had no token samples because the current K-Agent `ModelConfig` resources call LiteLLM/KubeAI directly instead of sending model traffic through Agent Gateway |
| Triage alert count | `ALERTS{route_to="triage", alertstate="firing"}` returned `0` at check time |
| Loki labels | `kagent`, `agentgateway-system`, `kgateway-system`, `argo`, `argo-events`, `kagent-poc`, `chaos-demo`, and `litmus` were present |
| Alert workflow history | Multiple `k-agent-alert-triage-*` workflows had succeeded from the prior route proof |

The live Grafana already had older LiteLLM-oriented dashboards. Those are useful
historically, but they do not prove the Agent Gateway path. For handover, use
`K-Agent and Agent Gateway Observability` from this repo because it tracks the
current gateway namespaces, the Alertmanager-to-Argo path, and the token metric
fallback.

The current gateway metrics do not expose per-tool-call or per-agent token
labels. To get exact attribution later, add structured gateway or agent spans
with agent name, tool name, model, token counts, and a trace/request ID. Until
then, route/backend/status/reason is the reliable public-safe breakdown.

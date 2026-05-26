# K-Agent and Agent Gateway Observability

This package is the copy/paste-ready observability set for K-Agent,
Agent Gateway, chaos validation, and the Alertmanager -> Argo Events -> K-Agent
triage path.

For the work-environment handoff and demo script, start with
[`caf-style-observability-handoff.md`](caf-style-observability-handoff.md).

## Artifact Set

| Purpose | File |
| --- | --- |
| CAF-style work handoff | `docs/observability/caf-style-observability-handoff.md` |
| Grafana MCP home-lab smoke | `docs/observability/grafana-mcp-home-lab.md` |
| Grafana dashboard import | `observability/grafana/dashboards/k-agent-agentgateway-public-ready.json` |
| Agent Gateway traffic dashboard | `observability/grafana/dashboards/agentgateway-traffic-quality.json` |
| Alloy metrics/log shipping | `k8s/observability/k-agent-alloy.yaml` |
| Gateway ServiceMonitor/PodMonitor coverage | `k8s/observability/k-agent-agentgateway-scrape.yaml` |
| Prometheus metric alerts | `k8s/observability/k-agent-alerts.yaml` |
| Argo Events Alertmanager webhook | `k8s/observability/k-agent-alertmanager-eventsource.yaml` |
| Alertmanager route to Argo Events | `k8s/observability/k-agent-alertmanager-triage-route.yaml` |
| Argo Events triage workflow trigger | `k8s/observability/k-agent-alert-triage-sensor.yaml` |
| Managed-Loki LogQL rules | `observability/managed-lgtm-integration/alerting/03-lokirules-k-agent-agentgateway.yaml` |
| Verification script | `scripts/observability/verify-k-agent-observability.sh` |
| Managed Mimir/Loki rule-sync guide | `observability/managed-lgtm-integration/rule-sync/README.md` |
| Local Mimir rule-sync proof | `k8s/observability/mimir-rule-sync-proof.yaml` |
| Rule-sync evidence | `docs/observability/mimir-rule-sync-evidence.md` |

The dashboard uses Grafana datasource variables, not fixed environment-specific UIDs:
`datasource_prom` for Prometheus/Mimir and `datasource_loki` for Loki.
Namespace variables default to the validation-cluster names but can be changed
at import time.

## Install Order

1. Import `observability/grafana/dashboards/k-agent-agentgateway-public-ready.json`.
2. Import `observability/grafana/dashboards/agentgateway-traffic-quality.json`.
3. Apply or reconcile `k8s/observability/k-agent-alloy.yaml` with the target
   Loki and Prometheus/Mimir endpoints.
4. Apply the scrape coverage from `k8s/observability/k-agent-agentgateway-scrape.yaml`.
5. Apply `k8s/observability/k-agent-alerts.yaml` for Prometheus/Mimir-compatible alerts.
6. Apply `k8s/observability/k-agent-alertmanager-eventsource.yaml` in the Argo Events cluster.
7. Apply `k8s/observability/k-agent-alertmanager-triage-route.yaml` after confirming Alertmanager can reach the Argo Events webhook service or the target webhook hub equivalent.
8. Apply `k8s/observability/k-agent-alert-triage-sensor.yaml` in the Argo Events cluster.
9. For log alerts, copy `observability/managed-lgtm-integration/alerting/03-lokirules-k-agent-agentgateway.yaml` into the managed LGTM rule-sync path. Do not apply it to a vanilla local Prometheus unless the Loki ruler sync convention is installed.

## Verification

Run static and client-side checks:

```bash
scripts/observability/verify-k-agent-observability.sh
```

Run the Grafana MCP smoke when the cluster has a `kagent-grafana-mcp`
`RemoteMCPServer`:

```bash
scripts/observability/smoke-grafana-mcp.sh --context {{KUBE_CONTEXT}}
```

For a work-computer replication of the Grafana MCP enrichment path, use
[`grafana-mcp-home-lab.md`](grafana-mcp-home-lab.md). It covers the safe
service-account shape, Secret-backed Helm install, `RemoteMCPServer`
registration, read-only agent tool selection, and the Alertmanager/Grafana
contact-point -> Argo Events -> `observability-agent` enrichment flow.

Run live cluster checks:

```bash
scripts/observability/verify-k-agent-observability.sh --context {{KUBE_CONTEXT}}
```

Run the destructive-but-reversible synthetic alert route test:

```bash
scripts/observability/verify-k-agent-observability.sh --context {{KUBE_CONTEXT}} --synthetic-alert
```

The synthetic mode creates a temporary `KagentObservabilitySyntheticTest`
PrometheusRule and deletes it on exit. It must fire with
`kagent_path=webhook` and `route_to=triage`, reach Alertmanager, reach the
`path-b-alertmanager-webhook` Argo EventSource, and create a
`k-agent-alert-triage-*` workflow.

## Live Evidence From Local Validation

Validated on a local Kubernetes validation cluster on 2026-05-19:

| Check | Result |
| --- | --- |
| Gateway scrape targets up | `count(up{namespace=~"agentgateway-system|kgateway-system"} == 1)` returned `8` |
| K-Agent pods running | `count(kube_pod_status_phase{namespace="kagent",phase="Running"} == 1)` returned `21` |
| Chaos jobs completed | chaos-demo succeeded pod query returned `5` |
| Gateway request metric | `envoy_cluster_external_upstream_rq_xx` returned a `kgateway-system` 2xx series |
| Loki gateway logs | `{namespace=~"agentgateway-system|kgateway-system"}` returned `1` stream |
| Loki chaos logs | `{namespace=~"chaos-demo|litmus"}` returned `1` stream |
| Loki triage logs | Argo/alertmanager triage LogQL returned `1` stream |
| Alert route | synthetic alert fired and Argo Events created triage workflows |
| K-Agent triage | after repairing the stale KubeAI model pod, `sre-triage-agent` returned HTTP 200 and the synthetic route produced `k-agent-alert-triage-7rq26` with `Succeeded` |

During testing, the first triage workflow reached the K-Agent controller but
timed out while the `qwen3-14b` model pod was stuck after an unhealthy GPU
allocation. The stale model pod was deleted, the replacement pod became Ready,
and the synthetic alert test was rerun successfully. The sensor now reports
future K-Agent timeouts as `K_AGENT_ALERT_TRIAGE_UNAVAILABLE` instead of failing
the workflow silently.

## Notes

- The Agent Gateway data-plane `/metrics` endpoint advertised the GenAI token
  histogram family, but Prometheus had no token samples because the current
  K-Agent `ModelConfig` resources call LiteLLM/KubeAI directly instead of
  sending model traffic through Agent Gateway.
- `Agent Gateway Traffic Quality` is metric-first and focuses on route/backend
  request rate, 5xx and timeout rate, p50/p95/p99 latency, calls slower than
  30s, active Envoy requests, response bytes, and token panels that activate
  when `agentgateway_gen_ai_client_token_usage_*` metrics are emitted.
- Per-agent tool-call attribution requires additional gateway, agent, or OTel
  labels such as agent name, tool name, model, and trace/request ID. Without
  those labels, the current safe proxy is route/backend/status/reason.
- The dashboard defaults to `Last 24 hours` so sparse alert/log flows are visible
  during handover; switch to `Last 1 hour` once the work cluster is producing
  steady traffic.
- `k8s/observability/k-agent-alloy.yaml` is the local shipping agent. Managed
  rule sync is represented by
  `observability/managed-lgtm-integration/alloy-snippets/04-rule-sync.alloy`,
  which now separates Mimir and Loki rule sync by `lgtm.engine`.
- Both `agentgateway-system` and `kgateway-system` are included intentionally
  because deployments may expose live gateway targets in either namespace.

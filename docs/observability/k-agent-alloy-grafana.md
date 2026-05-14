# K-Agent and agentgateway Observability

This plan proves the end-to-end LGTM path for kagent and agentgateway:

1. Alloy tails kagent and agentgateway logs from Kubernetes.
2. Alloy scrapes annotated kagent/agentgateway Prometheus endpoints plus kubelet cAdvisor container metrics.
3. Alloy writes logs to Loki and metrics to Prometheus or Mimir.
4. Grafana provisions the K-Agent dashboard against those data sources.
5. Prometheus/Loki rules alert on token spikes, gateway errors, missing metrics, kagent restarts, and suspicious log patterns.

All environment-specific values must stay outside Git. Use `k-agent-alloy-endpoints` for endpoint overrides and use secret-backed Alloy auth blocks if the target LGTM stack requires tokens.

## Files

| File | Purpose |
|---|---|
| `k8s/observability/k-agent-alloy.yaml` | Alloy Deployment, RBAC, log collection, metric scrape, remote write |
| `k8s/observability/k-agent-alerts.yaml` | Token usage, gateway, kagent, and log alert rules |
| `observability/grafana/provisioning/datasources/k-agent-lgtm.yaml` | Grafana datasource provisioning template |
| `observability/grafana/provisioning/dashboards/k-agent-dashboards.yaml` | Grafana dashboard provider |
| `observability/grafana/dashboards/k-agent-metrics.json` | Dashboard for token usage, gateway rates, kagent health, and logs |
| `scripts/observability/verify-k-agent-observability.sh` | Static and optional live validation |

## Deployment Plan

1. Confirm the LGTM endpoints:

   ```bash
   curl -fsS "${LOKI_PUSH_URL%/loki/api/v1/push}/ready"
   curl -fsS "${PROMETHEUS_REMOTE_WRITE_URL%/api/v1/push}/-/ready"
   ```

   For a raw Prometheus target, the server must have remote write receiver enabled and expose `/api/v1/write`. Mimir normally uses `/api/v1/push`.

2. Apply the Alloy bundle:

   ```bash
   kubectl apply -f k8s/observability/k-agent-alloy.yaml
   kubectl -n monitoring set env deployment/k-agent-alloy \
     CLUSTER_NAME="{{CLUSTER_NAME}}" \
     LOKI_PUSH_URL="http://{{LOKI_HOST}}/loki/api/v1/push" \
     PROMETHEUS_REMOTE_WRITE_URL="http://{{MIMIR_OR_PROMETHEUS_REMOTE_WRITE_URL}}"
   kubectl -n monitoring rollout status deployment/k-agent-alloy
   ```

3. Apply alert rules where Prometheus Operator CRDs are installed:

   ```bash
   kubectl apply -f k8s/observability/k-agent-alerts.yaml
   ```

4. Provision Grafana by mounting:

   ```text
   observability/grafana/provisioning/datasources/k-agent-lgtm.yaml
   observability/grafana/provisioning/dashboards/k-agent-dashboards.yaml
   observability/grafana/dashboards/k-agent-metrics.json
   ```

   Set `PROMETHEUS_URL` and `LOKI_URL` in the Grafana environment.

## Proof Queries

PromQL:

```promql
sum by (gen_ai_request_model, gen_ai_token_type) (
  rate(agentgateway_gen_ai_client_token_usage_sum[5m]) * 60
)

sum by (envoy_cluster_name, envoy_response_code_class) (
  rate(envoy_cluster_external_upstream_rq_xx[5m])
)

sum by (namespace, pod, container) (
  increase(kube_pod_container_status_restarts_total{namespace="kagent"}[1h])
)
```

LogQL:

```logql
{namespace="kagent"} | json | line_format "{{.level}} {{.logger}} {{.path}} status={{.status}} {{.msg}}"

{namespace="kgateway-system"} |~ "(?i)(error|reset|timeout|token|model|upstream)"

sum by (agent, model) (
  sum_over_time({namespace="kagent"} | json | unwrap total_tokens [5m])
)
```

## Live Lab Findings From 2026-05-13

Read-only checks on the lab Kubernetes context showed:

- `kagent` namespace is running the controller, tools, UI, and agent pods.
- `kgateway-system` is running `ai-gateway` and `kgateway`; `ai-gateway` exposes Prometheus annotations on port `9091`.
- Existing Alloy in `monitoring` is running and tails kagent/agentgateway pod logs.
- Loki is reachable at the current lab endpoint and reports ready; a Loki `query_range` for `{namespace="kagent"}` returned live kagent log streams.
- agentgateway metrics are available from the live gateway pod; `envoy_cluster_external_upstream_rq*` samples were returned from port `9091`.
- Existing Alloy remote write was pointed at an HTTP app that returns HTML/405 for remote write. Correct that endpoint to a Prometheus remote-write receiver or Mimir push URL before considering metrics delivery proven.

The repo bundle above makes the endpoint choice explicit and repeatable, so the same proof can be replayed without committing private hostnames.

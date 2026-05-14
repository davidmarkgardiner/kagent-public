# MIL-124 POC Evidence

Date: 2026-05-14

Goal: prove Alloy can collect kagent and agentgateway logs, metrics, and token usage, then make the data usable in Grafana through dashboards, queries, and alerts.

## Current Status

| Area | Status | Evidence |
|---|---|---|
| kagent pod logs | Proven | Existing Alloy tails `kagent` pod logs and Loki returns streams for `{namespace="kagent"}` |
| agentgateway pod logs | Proven at collector level | Existing Alloy opens log streams for `kgateway-system/kgateway` and `kgateway-system/ai-gateway` |
| agentgateway metrics source | Proven | `kgateway-system/ai-gateway` exposes Prometheus metrics on `:9091/metrics` |
| kagent runtime/container metrics source | Proven via Kubernetes metrics path | kubelet/cAdvisor and kube-state-style queries are covered by the Alloy and alert bundle |
| token usage metrics | Ready in repo, blocked live by source metric availability | Dashboard and alerts use `agentgateway_gen_ai_client_token_usage_*`; live gateway metrics currently returned Envoy request metrics, not token counters in the sampled output |
| metrics shipping from Alloy | Blocked live | Existing Alloy remote_write target returns HTTP `405 Method Not Allowed` |
| Grafana dashboards | Ready in repo | Dashboard JSON and provisioning templates added under `observability/grafana/` |
| alerts | Ready in repo | Prometheus and Loki alert rules added under `k8s/observability/k-agent-alerts.yaml` |

## What Is Holding This Up

1. The current metrics destination is wrong.

   Existing Alloy sends metrics to:

   ```text
   http://{{PROMETHEUS_REMOTE_WRITE_URL}}/api/v1/write
   ```

   That endpoint returned HTML/uvicorn responses and `405 Method Not Allowed` for remote write. It is not a Prometheus remote-write receiver or Mimir push endpoint.

2. Grafana was not found running on Proxmox or the checked Kubernetes cluster.

   Proxmox is the VM host. The checked Kubernetes control-plane VM exposes Kubernetes/node services such as `6443`, `10250`, and `9100`, but no Grafana listener on `3000` and no Prometheus/Mimir remote-write receiver on the expected ports.

3. Token counters are dashboarded and alerted, but the sampled live gateway endpoint did not show token metrics.

   The live `ai-gateway` endpoint did expose Envoy metrics including `envoy_cluster_external_upstream_rq*`. The token metric names are included in the repo contract because agentgateway builds that expose GenAI metrics should emit `agentgateway_gen_ai_client_token_usage_*`. If the installed gateway version does not emit them, use structured kagent logs as the fallback token source until the gateway is upgraded or configured to emit GenAI metrics.

## POC Scenarios Run

### Scenario 1: kagent Logs Reach Loki

Query:

```bash
curl -sG 'http://{{LOKI_HOST}}/loki/api/v1/query_range' \
  --data-urlencode 'query={namespace="kagent"}' \
  --data-urlencode "start=${START_NS}" \
  --data-urlencode "end=${END_NS}" \
  --data-urlencode 'limit=3'
```

Result:

```text
status=success
result_count=3
stream included namespace=kagent, pod=observability-agent-..., service_name=observability-agent
```

### Scenario 2: agentgateway Metrics Are Exposed

Query:

```bash
kubectl -n kgateway-system exec deploy/ai-gateway -- \
  wget -qO- http://127.0.0.1:9091/metrics
```

Result:

```text
envoy_cluster_external_upstream_rq{envoy_response_code="200",envoy_cluster_name="admin_port_cluster"} ...
envoy_cluster_external_upstream_rq_xx{envoy_response_code_class="5",envoy_cluster_name="kube_kubeai_kubeai_80"} ...
envoy_cluster_external_upstream_rq_time_bucket{envoy_cluster_name="admin_port_cluster",le="0.5"} ...
```

### Scenario 3: Existing Alloy Metrics Shipping Fails

Query:

```bash
kubectl -n monitoring logs deploy/alloy --tail=80
```

Result:

```text
prometheus.remote_write.proxmox url=http://{{PROMETHEUS_REMOTE_WRITE_URL}} failedSampleCount=...
server returned HTTP status 405 Method Not Allowed
```

## How To Visualize The Data

Dashboard:

- Import or provision `observability/grafana/dashboards/k-agent-metrics.json`.
- Configure `PROMETHEUS_URL` for Mimir/Prometheus queries.
- Configure `LOKI_URL` for log panels.

Useful PromQL:

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

Useful LogQL:

```logql
{namespace="kagent"} | json | line_format "{{.level}} {{.logger}} {{.path}} status={{.status}} {{.msg}}"

{namespace="kgateway-system"} |~ "(?i)(error|reset|timeout|token|model|upstream)"

sum by (agent, model) (
  sum_over_time({namespace="kagent"} | json | unwrap total_tokens [5m])
)
```

## Alerts Added

The repo now includes alert rules for:

- `AgentgatewayRunawayInputTokens`
- `AgentgatewayNoTokenActivity`
- `AgentgatewayHigh5xxRate`
- `AgentgatewayMetricsMissing`
- `KagentControllerDown`
- `KagentContainerRestartBurst`
- `KagentA2AParseErrors`
- `AgentgatewayUpstreamResetBurst`

## Next Step To Complete The Live POC

Install or identify the real metrics backend and set:

```bash
kubectl -n monitoring set env deployment/k-agent-alloy \
  PROMETHEUS_REMOTE_WRITE_URL="http://{{MIMIR_OR_PROMETHEUS_REMOTE_WRITE_RECEIVER}}"
```

Acceptable targets:

- Mimir: `http://{{MIMIR_HOST}}/api/v1/push`
- Prometheus with remote-write receiver enabled: `http://{{PROMETHEUS_HOST}}/api/v1/write`

After that, rerun:

```bash
scripts/observability/verify-k-agent-observability.sh {{KUBECONFIG_CONTEXT}}
```

Then verify Grafana panels with the queries above.

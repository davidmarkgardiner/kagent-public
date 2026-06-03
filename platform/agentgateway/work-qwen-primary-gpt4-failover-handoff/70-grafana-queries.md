# Grafana Queries

Use these in Grafana Explore or as panels on the Agent Gateway Traffic Quality
dashboard.

## Route 429s

```promql
sum by (route, backend, status, reason) (
  increase(agentgateway_requests_total{route=~".*llm.*", status="429"}[1h])
)
```

## Model Request Rate

```promql
sum by (gen_ai_request_model, gen_ai_system) (
  rate(agentgateway_gen_ai_client_token_usage_count[5m])
)
```

## Token Usage Per Minute

```promql
sum by (gen_ai_request_model, gen_ai_token_type) (
  rate(agentgateway_gen_ai_client_token_usage_sum[5m]) * 60
)
```

## Route P95 Latency

```promql
histogram_quantile(
  0.95,
  sum by (route, backend, le) (
    rate(agentgateway_request_duration_seconds_bucket{route=~".*llm.*"}[5m])
  )
)
```

## Failed Triage Workflows

```promql
sum by (workflow_template) (
  rate(argo_workflows_count{status="Failed", workflow_template=~".*(k-agent|kagent|triage|alert).*"}[10m])
)
```

## Gateway Rate-Limit Logs

```logql
{namespace=~"agentgateway-system|kgateway-system"} |~ "(?i)(429|too many requests|rate.?limit|quota exceeded)"
```

## Kagent A2A Non-Completion Logs

```logql
{namespace=~"argo|argo-events|kagent"} |~ "(?i)(K-Agent A2A call did not complete|a2a call did not complete|agent invocation did not complete|context deadline exceeded)"
```

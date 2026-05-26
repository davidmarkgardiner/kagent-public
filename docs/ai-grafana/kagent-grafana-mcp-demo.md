# kagent Grafana MCP Demo

This demo shows how the transcript's "agent reads telemetry directly" idea maps
to the kagent and Grafana MCP setup in this repo.

Use placeholders for environment-specific values. Do not commit tokens, private
hostnames, cluster IPs, or internal URLs.

## 1. Verify The Direct MCP Path

Run the smoke test from the repo root:

```bash
scripts/observability/smoke-grafana-mcp.sh --context {{KUBE_CONTEXT}}
```

Expected proof:

- MCP `initialize` returns server info
- `tools/list` includes Grafana read tools
- `list_datasources` returns datasource names, types, and UIDs
- `query_prometheus` returns a non-empty result for `count(up)`

If Loki is available, add a log query:

```bash
scripts/observability/smoke-grafana-mcp.sh \
  --context {{KUBE_CONTEXT}} \
  --loki-datasource-uid {{LOKI_DATASOURCE_UID}} \
  --loki-query '{namespace="kagent"}'
```

This validates the data path without depending on a healthy model backend.

## 2. Confirm kagent Can See The MCP Server

```bash
kubectl --context {{KUBE_CONTEXT}} -n kagent get remotemcpserver kagent-grafana-mcp
```

Then compare the live tool discovery result with any agent manifest before
rollout:

```bash
kubectl --context {{KUBE_CONTEXT}} -n kagent get remotemcpserver kagent-grafana-mcp \
  -o jsonpath='{range .status.discoveredTools[*]}{.name}{"\n"}{end}' | sort
```

Agent manifests should use current tool names from the live cluster, not names
copied from older examples.

## 3. Ask Investigation Questions

Use investigation prompts rather than simple chart prompts. For example:

```text
An alert fired for namespace {{NAMESPACE}} and workload {{WORKLOAD}}.
Use Grafana MCP to inspect recent metrics, logs, dashboards, and alert metadata.
Tell me what is most likely wrong, what evidence supports that, what is still
uncertain, and which Grafana deeplinks an operator should open next.
```

For kagent/agentgateway triage, the workflow should ask for evidence around:

- pod readiness and restart counts
- request volume and error rate
- LLM backend latency and failures
- A2A gateway success/failure rate
- recent logs from `kagent`, `agentgateway-system`, `kgateway-system`, `argo`,
  and `argo-events`
- related dashboard panels and alert rules

## 4. Route Alerts Through Argo

The desired alert route is:

```text
Grafana Alerting or Prometheus Alertmanager
  -> Argo Events EventSource
  -> Argo Sensor
  -> Argo Workflow
  -> kagent observability-agent
  -> Grafana MCP
```

The contact point is a delivery mechanism only. It should send the alert payload
to Argo Events. Argo then creates a workflow, records the run, and asks
`observability-agent` to enrich the alert with Grafana MCP evidence.

Useful alert fields to preserve in the workflow input:

- `labels.alertname`
- `labels.cluster`
- `labels.namespace`
- `labels.pod`
- `labels.gateway`
- `labels.service`
- `annotations.summary`
- `annotations.description`
- `generatorURL`

## 5. Demo Dashboard Generation Safely

The transcript's dynamic-dashboard idea is worth testing, but keep it outside
the default triage agent.

Recommended controlled flow:

1. fetch an existing dashboard JSON or generate a new dashboard into
   `tmp/grafana-dashboards/`
2. format and validate it with `jq`
3. inspect the diff
4. push through a write-capable Grafana MCP service account only after approval
5. record the resulting dashboard UID and deeplink in the workflow output

Example local validation:

```bash
jq -e . tmp/grafana-dashboards/{{DASHBOARD_NAME}}.json >/dev/null
git diff -- tmp/grafana-dashboards/{{DASHBOARD_NAME}}.json
```

Avoid asking an agent to mutate a large dashboard in place. Fetch a clean
baseline, make the smallest possible change, validate, and then push.

## 6. Expected Demo Narrative

When this works end to end, the operator story is:

1. An alert fires for kagent or agentgateway.
2. Argo captures the payload and starts a triage workflow.
3. `observability-agent` uses Grafana MCP to query Prometheus/Mimir and Loki.
4. The agent checks dashboard context and generates Grafana deeplinks.
5. The workflow returns a concise diagnosis and next action.
6. Any fix is routed through GitOps or an approved Argo remediation workflow,
   not through the read-only triage agent.

Current lab limitation: the direct Grafana MCP path is verified, but the full
agent-mediated A2A answer path depends on a healthy model backend. Repair that
route before treating the demo as fully end to end.

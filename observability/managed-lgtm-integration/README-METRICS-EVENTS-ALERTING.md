# Alerting on Metrics & K8s Events via AlertManager

**Path:** PrometheusRule → Prometheus / Mimir → AlertManager → Argo EventSource webhook → Sensor → triage Workflow → kagent
**Status:** in-cluster path **already tested on `{{CLUSTER_NAME}}`**. Managed-Mimir path designed, blocked on platform-team Q1 + Q3 + Q4.

---

## TL;DR

This is the standard "metrics fire alerts" path. We write `PrometheusRule` CRDs in this repo, the Prometheus or Mimir Ruler evaluates them, AlertManager routes the firing alerts to our `argo-events-webhook` receiver, and Argo Events triggers a triage Workflow that hands off to kagent for analysis.

K8s events that show up as **metrics** (e.g. `kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}` from kube-state-metrics) flow through this same path. K8s events that we want to alert on as **log lines** are covered in `README-LOG-ALERTING.md`.

---

## What's already tested

```
                 {{CLUSTER_NAME}} cluster
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  ┌──────────────────┐    PromQL eval    ┌──────────────────────┐   │
│  │ kube-state-metrics│ ─────────────────►│  Prometheus          │   │
│  │ cAdvisor          │ scrape            │  (kube-prom)         │   │
│  │ kubelet           │                   │  evaluates rules     │   │
│  └──────────────────┘                   └──────────┬───────────┘   │
│                                                    │ fires          │
│                                                    ▼                │
│                                         ┌──────────────────────┐   │
│                                         │  AlertManager        │   │
│                                         │  receiver:           │   │
│                                         │  argo-events-webhook │   │
│                                         └──────────┬───────────┘   │
│                                                    │ POST /alerts   │
│                                                    ▼                │
│              ┌─────────────────────────────────────────────────┐   │
│              │  EventSource (webhook :12000/alerts)            │   │
│              │  Sensor (filter status=firing, rate-limit 5/min)│   │
│              │  WorkflowTemplate alertmanager-triage           │   │
│              │    └─► fetch logs → kagent A2A → GitLab/Mattermost│
│              └─────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

**Reusable artefacts** (live, validated, do not rebuild):

| File | Purpose |
|---|---|
| `../prometheus-alerting/01-alertmanager-values.yaml` | AlertManager `argo-events-webhook` receiver + matchers |
| `../prometheus-alerting/02-custom-alerting-rules.yaml` | Reference `PrometheusRule` (OOMKilled, PodHighRestarts, FailedScheduling, CPU/Memory High, PVCNearCapacity) |
| `../prometheus-alerting/03-eventsource-alertmanager.yaml` | `webhook` EventSource on `:12000/alerts` |
| `../prometheus-alerting/05-sensor.yaml` | Filters firing alerts, triggers `alertmanager-triage` template |
| `../prometheus-alerting/04-workflow-template.yaml` | Triage DAG (fetch pod details → GitLab issue → Mattermost) |
| `../prometheus-alerting/test-alerts.sh` | End-to-end test driver |

Real evidence of it working: `KubePodCrashLooping` from the `gitea` namespace was caught and triaged end-to-end (memory).

---

## How to alert on metrics — the rule pattern

A `PrometheusRule` CR has three parts that determine the triage outcome:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: my-platform-rules
  namespace: monitoring
  labels:
    # 1) Discovery label — local Prometheus picks this up
    release: kube-prom
    # 2) Discovery label — Alloy syncs to managed Mimir Ruler (only set when ready)
    shipto.lgtm: "true"
    lgtm.tenant: platform
spec:
  groups:
    - name: my-group
      interval: 30s
      rules:
        - alert: MyAlert
          expr: <PromQL>
          for: 5m
          labels:
            # 3) Routing label — AlertManager sends ONLY rules with route_to=triage
            #    to our argo-events-webhook receiver
            route_to: triage
            severity: critical          # critical | warning | info
            triage: "true"              # convention: opt-in to AI triage
          annotations:
            summary: "..."
            description: "..."
            runbook_url: "https://..."  # surfaced in Mattermost
```

The three labels each do one job:
- `release: kube-prom` → kube-prometheus-stack's PrometheusRule selector (`spec.ruleSelector.matchLabels`)
- `shipto.lgtm: "true"` → Alloy `mimir.rules.kubernetes` selector (`alloy-snippets/04-rule-sync.alloy`)
- `route_to: triage` (in alert labels) → AlertManager routing tree picks the `argo-events-webhook` receiver

---

## What metrics are available for alerting

### From kube-state-metrics (cluster state — most "events as metrics")

| Metric | Triggers alert on |
|---|---|
| `kube_pod_container_status_last_terminated_reason` | OOMKilled, Error, ContainerCannotRun |
| `kube_pod_container_status_restarts_total` | Crash loops |
| `kube_pod_status_unschedulable` | FailedScheduling |
| `kube_pod_container_status_waiting_reason` | ImagePullBackOff, ErrImagePull, CreateContainerConfigError |
| `kube_node_status_condition` | Node Ready/MemoryPressure/DiskPressure |
| `kube_deployment_status_replicas_available` | Deployment availability |
| `kube_job_failed` | Job failures |
| `kube_persistentvolumeclaim_status_phase` | PVC pending |

These are the **canonical "k8s event as metric" path** — they cover ~80% of what `kubectl get events` would tell us, but as time-series data we can alert on directly.

### From cAdvisor / kubelet (resource usage)

- `container_cpu_usage_seconds_total`
- `container_memory_working_set_bytes`
- `kubelet_volume_stats_used_bytes` / `_capacity_bytes`

### From application / agentgateway / kagent

- `http_requests_total{status=~"5.."}` — RED metrics
- `http_request_duration_seconds_bucket` — latency p95/p99
- `agentgateway_gen_ai_client_token_usage_sum` — token burn / runaway agents
- `argo_workflows_count{status="Failed"}` — pipeline self-health

Examples in `alerting/01-prometheusrules-platform.yaml` cover all three categories.

---

## What's new for managed Mimir (vs the in-cluster path)

Three deltas when we move from local Prometheus to the managed LGTM Mimir:

### 1. Push metrics in via Alloy `prometheus.remote_write`

```alloy
// alloy-snippets/01-metrics-to-mimir.alloy already has this
prometheus.remote_write "managed_mimir" {
  endpoint {
    url = sys.env("MIMIR_PUSH_URL")        // platform team gives us this (Q1)
    headers = { "X-Scope-OrgID" = sys.env("MIMIR_TENANT_ID") }
    bearer_token = sys.env("MIMIR_BEARER_TOKEN")
  }
}
```

We keep local Prometheus running so dashboards / kube-prom-stack alerting still works **and** Alloy ships everything onwards to managed Mimir. Belt and braces — the local stack is our outage fallback.

### 2. Sync rules from cluster → managed Mimir Ruler

Alloy `mimir.rules.kubernetes` watches `PrometheusRule` CRs labelled `shipto.lgtm: "true"` and pushes them to the Mimir Ruler API. See `alloy-snippets/04-rule-sync.alloy`. Same rule YAML works for both local Prometheus (via `release: kube-prom` label) and managed Mimir (via `shipto.lgtm: "true"` label) — we just dual-label.

### 3. Managed AlertManager fans out to our webhook

The managed AlertManager applies routes by label. We need them to add:

```yaml
# Goes into the managed AlertManager config (platform team applies)
route:
  routes:
    - receiver: argo-events-webhook
      matchers:
        - route_to = "triage"
      continue: true

receivers:
  - name: argo-events-webhook
    webhook_configs:
      - url: https://alerts.lab.{{INGRESS_DOMAIN}}/alerts
        send_resolved: true
        max_alerts: 10
        http_config:
          authorization:
            type: Bearer
            credentials: <token from alertmanager-webhook-token Secret>
```

This is the **same Ingress and same EventSource** as `OPTION-A-README.md` — once that ingress exists, both local and managed AlertManager point at it.

---

## How the alert payload becomes a triage Workflow

1. **AlertManager POST** arrives at `:12000/alerts` carrying the standard webhook envelope:
   ```json
   {"version":"4","status":"firing","receiver":"argo-events-webhook",
    "alerts":[{"status":"firing",
       "labels":{"alertname":"OOMKilledContainer","severity":"critical","namespace":"foo","pod":"bar-xyz"},
       "annotations":{"summary":"...","description":"...","runbook_url":"..."},
       "startsAt":"2026-04-30T...Z"}]}
   ```
2. **EventSource** (`webhook` type) wraps the body and emits a CloudEvent.
3. **Sensor** filters `body.status == "firing"`, rate-limits to 5/min, then triggers the `alertmanager-triage` WorkflowTemplate, passing the body in as `alert-payload`.
4. **Workflow DAG** (`alertmanager-triage`):
   - `fetch-pod-details` extracts namespace+pod from the alert payload, runs `kubectl logs`, `kubectl get events`, `kubectl describe`
   - `create-gitlab-issue` opens an issue with full context
   - `notify-mattermost` posts a colour-coded card with severity, runbook link, kagent analysis, kubectl quick commands
5. **kagent A2A** is invoked inside the workflow with prompt anchoring (`CRITICAL: use exact namespace "X"`) — the prompt-engineering pattern from memory that fixed Qwen 14B hallucinations.

The richer alert-shape variant (`alerts/workflow-template-alerts.yaml` in this directory) does the same thing but parses the OTLP-wrapped payload that comes via Kafka — only needed if Option C (queue) is chosen.

---

## Adding a new alert (cookbook)

```bash
# 1. Edit the rules file
$EDITOR alerting/01-prometheusrules-platform.yaml

#    Add a new alert under an existing group, or a new group:
#
#    - alert: NodeMemoryPressure
#      expr: kube_node_status_condition{condition="MemoryPressure",status="true"} == 1
#      for: 2m
#      labels:
#        severity: critical
#        route_to: triage
#      annotations:
#        summary: "Node {{ $labels.node }} under memory pressure"
#        runbook_url: "https://runbooks.example.com/NodeMemoryPressure"

# 2. Apply locally
kubectl apply -f alerting/01-prometheusrules-platform.yaml

# 3. Verify Prometheus picked it up
kubectl port-forward -n monitoring svc/kube-prom-kube-prometheus-prometheus 9090:9090
# open http://localhost:9090/alerts → look for NodeMemoryPressure

# 4. Verify Alloy synced it to managed Mimir (when wired up)
#    Alloy logs show: "Successfully synced rules to Mimir for tenant=platform"
kubectl logs -n monitoring -l app.kubernetes.io/name=alloy --tail=50 | grep -i sync

# 5. Trigger the alert and watch the workflow run
./test-alerts.sh --context {{CLUSTER_NAME}} --create-oom    # or whatever scenario fits
./test-alerts.sh --context {{CLUSTER_NAME}} --verify
```

---

## Testing

The `test-alerts.sh` script in `prometheus-alerting/` is the canonical test harness. It already supports both **synthetic webhook injection** (no real metric needed) and **real failure pods** (creates an OOMKill / CrashLoop / ImagePull pod and waits for the rule to fire).

```bash
# Synthetic: post a webhook payload directly to the EventSource (proves
# everything from EventSource onwards works — Sensor, Workflow, kagent, MM, GitLab)
./test-alerts.sh --context {{CLUSTER_NAME}} --webhook-test

# Real: trigger an actual metric breach, prove rule eval + AM routing works too
./test-alerts.sh --context {{CLUSTER_NAME}} --create-oom        # OOMKilledContainer
./test-alerts.sh --context {{CLUSTER_NAME}} --create-crashloop  # PodHighRestarts
./test-alerts.sh --context {{CLUSTER_NAME}} --create-imagepull  # ImagePullBackOff via kube-prom-stack default

# Verify a triage workflow appeared
./test-alerts.sh --context {{CLUSTER_NAME}} --verify
```

For the **managed Mimir** variant, the test changes only at step "post a webhook payload" — we point at the public ingress (see `OPTION-A-README.md` test plan).

---

## Troubleshooting

| Symptom | Where to look |
|---|---|
| Rule doesn't appear in Prometheus | Rule label `release: kube-prom` missing or different release name (`kubectl get prometheus -n monitoring -o yaml \| grep ruleSelector`) |
| Rule pending → never fires | Check `expr` in `/alerts` UI shows the same value as `for:` threshold |
| AlertManager doesn't route to webhook | `kubectl get secret alertmanager-kube-prom-... -n monitoring -o jsonpath='{.data.alertmanager\.yaml}' \| base64 -d` and confirm matcher `route_to = "triage"` is in the routing tree |
| Webhook arrives but no workflow | `kubectl logs -n argo-events -l sensor-name=alertmanager-triage-sensor` — look for `body.status` filter rejection or rate-limit `dropped` |
| Workflow created but kagent step fails | `kubectl logs <wf-pod> -c main` — most common: A2A `parts` missing `kind: text`, or KAGENT_URL ConfigMap wrong |
| Managed Mimir Ruler doesn't see rule | Alloy logs `mimir.rules.kubernetes`, verify `shipto.lgtm: "true"` label, verify Alloy SA has `get/list/watch` on PrometheusRule CRs |

---

## Open questions blocking the managed-Mimir variant

From `OPEN-QUESTIONS.md`:

| # | Question | Impact |
|---|---|---|
| Q1 | Mimir push URL + tenant + auth | Can't ship metrics to managed Mimir |
| Q3 | Rule provisioning model (Alloy-sync vs MR to central repo) | Determines if rules live in this repo or platform's |
| Q4 | Can managed AM call our webhook? | If no, fall back to NATS JetStream queue |

Until Q1 + Q3 + Q4 are answered the managed-Mimir variant is theoretical. The local-Prometheus variant ships today.

---

## See also

- `OPTION-A-README.md` — the network/ingress story for getting AlertManager (local or managed) → our EventSource
- `README-LOG-ALERTING.md` — the LogQL / Loki sibling of this doc (alerts on log content, including k8s events shipped as logs)
- `LGTM-TO-ARGO-EVENTS-RECAP.md` — top-level recap of the four-options decision tree

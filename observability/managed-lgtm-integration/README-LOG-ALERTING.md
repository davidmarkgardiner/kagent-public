# Alerting on Logs (Loki + LogQL) via AlertManager

**Path:** Loki rules → Loki Ruler → AlertManager → Argo EventSource webhook → Sensor → triage Workflow → kagent
**Status:** **not yet wired up** — design only. Depends on the metrics path (`README-METRICS-EVENTS-ALERTING.md`) being live first, since the AlertManager + Argo EventSource layer is shared.

---

## TL;DR

LogQL alert rules live as Kubernetes CRs in this repo, get synced into the managed Loki Ruler by Alloy, and fire alerts to the **same managed AlertManager** as the metric rules. From there it's identical to the metrics path — webhook to `https://alerts.lab.{{INGRESS_DOMAIN}}/alerts`, Sensor, triage Workflow, kagent.

The big payoff is being able to alert on:
- **Application errors** — Go panics, Python tracebacks, Java OOM stack traces
- **K8s events** as log lines (since Alloy ships `loki.source.kubernetes_events` to Loki — full context: kind, reason, message)
- **Security signals** — auth failure bursts, unauthorized access patterns
- **Pipeline self-health** — kagent A2A parse errors, agentgateway upstream resets

…all without needing to invent a custom metric for each pattern.

---

## Architecture

```
                       Worker / mgmt cluster                                Managed LGTM
┌────────────────────────────────────────────────────────────┐    ┌──────────────────────────┐
│                                                            │    │                          │
│  pod logs                                                  │    │  ┌────────────────────┐  │
│  k8s events ──┐                                            │    │  │  Loki              │  │
│               │                                            │    │  │  (logs storage)    │  │
│       ┌───────▼───────┐    push (HTTPS)                    │    │  └─────────┬──────────┘  │
│       │  Alloy        │────────────────────────────────────┼───►│            │ ruler eval │
│       │  loki.write   │                                    │    │  ┌─────────▼──────────┐  │
│       └───────────────┘                                    │    │  │  Loki Ruler        │  │
│                                                            │    │  │  (LogQL rules)     │  │
│  PrometheusRule CRs                                        │    │  └─────────┬──────────┘  │
│  (lgtm.engine: loki) ─┐                                    │    │            │ fires      │
│                       │                                    │    │  ┌─────────▼──────────┐  │
│       ┌───────────────▼──────┐    push rules               │    │  │  AlertManager      │  │
│       │ Alloy                │────────────────────────────┼───►│  │  (managed)         │  │
│       │ loki.rules.kubernetes│                             │    │  └─────────┬──────────┘  │
│       └──────────────────────┘                             │    │            │             │
│                                                            │    │            │             │
└────────────────────────────────────────────────────────────┘    └────────────┼─────────────┘
                                                                               │ webhook (Bearer)
                                                                               ▼
                                              https://alerts.lab.{{INGRESS_DOMAIN}}/alerts
                                                              │
                                                              ▼
                                              EventSource → Sensor → Workflow → kagent
                                              (same as metrics path — see OPTION-A-README.md)
```

The shaded right side is **owned by the platform team**. We don't run Loki, Loki Ruler, or AlertManager — we ship logs into Loki and ship rule CRs into the Ruler, and the platform team's AlertManager fires alerts back at us.

---

## Why use logs for alerts at all (when we have metrics)

Two reasons:

1. **Some failure modes only show up in text.** A Go panic, a Python `KeyError: 'access_token'`, a `connection refused: 502 from upstream` — these are log strings. Inventing a Prometheus metric for each is more work than just writing a LogQL rule.
2. **K8s events are richer as logs.** `kube_pod_container_status_waiting_reason{reason="ImagePullBackOff"}` tells you the reason. The actual event log line tells you the **image name** and the **registry error** (`unauthorized: HTTP Basic: Access denied`). Loki keeps the full event body, so alert annotations can include it.

Trade-off: log-based alerts are heavier for the backend (LogQL evaluation > PromQL on indexed metrics). Use them where the signal genuinely needs the text — not for things kube-state-metrics already exposes.

---

## What gets shipped into Loki

Two `loki.source.*` components in `alloy-snippets/02-logs-to-loki.alloy`:

### 1. Pod logs (`loki.source.kubernetes`)

Discovers all pods, scrapes `/var/log/pods/...`, attaches `namespace`, `pod`, `container`, `service` (from `app.kubernetes.io/name`) labels.

```alloy
discovery.kubernetes "pods" { role = "pod" }
loki.source.kubernetes "pod_logs" { ... }
```

### 2. K8s events as log lines (`loki.source.kubernetes_events`)

Watches the K8s events API, ships every Event object as a JSON log line. This is the **single most valuable** input for log alerting in a triage system.

```alloy
loki.source.kubernetes_events "events" {
  namespaces = []         // empty = all namespaces
  log_format = "json"
}

// Pre-process: pull reason/type/object kind into LABELS for fast LogQL filtering
loki.process "parse_event" {
  stage.json {
    expressions = {
      event_type    = "type",
      event_reason  = "reason",
      obj_kind      = "involvedObject.kind",
      obj_namespace = "involvedObject.namespace",
    }
  }
  stage.labels { values = { event_type="", event_reason="", obj_kind="" } }
}
```

After this, querying for any FailedMount event in the last 5 minutes is one line of LogQL:

```logql
{event_reason="FailedMount"} | json
```

…and an alert on it is just `count_over_time(...) > N`.

### Common labels added before write

```alloy
loki.process "add_common_labels" {
  stage.static_labels {
    values = {
      cluster     = sys.env("CLUSTER_NAME"),
      environment = sys.env("ENVIRONMENT"),
      region      = sys.env("REGION"),
      tenant      = sys.env("TENANT"),
    }
  }
}
```

These let multi-cluster Loki queries scope to a single cluster (`{cluster="{{CLUSTER_NAME}}"}`).

---

## How log alert rules look

Loki uses the same `RuleGroup` shape as Prometheus, but `expr` is LogQL instead of PromQL. We label the CR so Alloy's `loki.rules.kubernetes` syncs to the Loki Ruler (not the Mimir Ruler).

Working examples in `alerting/02-lokirules-platform.yaml`:

### Application panic detection

```yaml
- alert: ApplicationPanicLogged
  expr: |
    sum by (cluster, namespace, pod, container) (
      count_over_time({cluster=~".+"} |~ "(?i)panic:|fatal error:|goroutine \\d+ \\[running\\]" [5m])
    ) > 0
  for: 0m
  labels:
    severity: critical
    route_to: triage          # same routing label as metrics rules
  annotations:
    summary: "Panic in {{ $labels.namespace }}/{{ $labels.pod }}"
    runbook_url: "https://runbooks.example.com/AppPanic"
```

### Auth failure burst (security signal)

```yaml
- alert: AuthFailureBurst
  expr: |
    sum by (cluster, namespace, service) (
      count_over_time({cluster=~".+"} |~ "(?i)(401 unauthorized|403 forbidden|invalid token|authentication failed)" [5m])
    ) > 50
  for: 5m
  labels:
    severity: warning
    route_to: triage
```

### kagent A2A parse errors (pipeline self-health)

```yaml
- alert: KagentA2AParseError
  expr: |
    sum by (cluster) (
      count_over_time({namespace="kagent"} |~ "parse error|JSON-RPC.*invalid" [5m])
    ) > 5
  for: 5m
  labels:
    severity: warning
    route_to: triage
```

This last one is exactly the kind of alert that's awkward as a metric — we'd have to scrape kagent's HTTP request logs into a counter — but trivial as LogQL.

---

## Alerting on K8s events specifically

Because Alloy ships `loki.source.kubernetes_events` as logs with `event_reason` as a label, every K8s event reason becomes a one-line LogQL alert:

```yaml
- alert: PodFailedMount
  expr: |
    sum by (cluster, obj_namespace) (
      count_over_time({event_reason="FailedMount"}[5m])
    ) > 0
  for: 0m
  labels:
    severity: warning
    route_to: triage
  annotations:
    summary: "FailedMount in {{ $labels.obj_namespace }}"
    description: "{{ $value | printf \"%.0f\" }} FailedMount events in 5m"

- alert: PodImagePullBackOff
  expr: |
    sum by (cluster, obj_namespace) (
      count_over_time({event_reason=~"Failed|ErrImagePull|ImagePullBackOff"}[5m])
    ) > 0
  for: 2m
  labels:
    severity: warning
    route_to: triage

- alert: PodEvicted
  expr: |
    sum by (cluster, obj_namespace) (
      count_over_time({event_reason="Evicted"}[5m])
    ) > 0
  for: 0m
  labels:
    severity: critical
    route_to: triage
```

Compared to metrics-based equivalents, the log-based version preserves the **full event message**, which the triage workflow can grep for (e.g. the actual image name in an ImagePull failure) and pass to kagent for richer analysis.

---

## CRD shape — Loki rules

Two patterns the platform team might mandate (open question Q3):

### Pattern A — Reuse `PrometheusRule` with engine label (preferred)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: platform-triage-log-alerts
  namespace: monitoring
  labels:
    shipto.lgtm: "true"
    lgtm.tenant: platform
    lgtm.engine: loki        # ← tells Alloy rule-sync to use Loki Ruler not Mimir
    route_to: triage
    release: kube-prom
spec:
  groups:
    - name: application-error-patterns
      interval: 1m
      rules:
        - alert: ApplicationPanicLogged
          expr: ...
```

This is what `alerting/02-lokirules-platform.yaml` uses. It's the simplest — same CRD, one extra label.

### Pattern B — Dedicated `LokiRule` CRD (if platform mandates it)

```yaml
apiVersion: loki.grafana.com/v1
kind: LokiRule
metadata:
  name: platform-triage-log-alerts
  namespace: monitoring
spec:
  groups:
    - name: ...
      rules:
        - alert: ...
          expr: ...
```

The rule body itself is identical — only `apiVersion` / `kind` change. We support whichever the platform team picks; flagging this as Q3 in `OPEN-QUESTIONS.md`.

---

## How rules sync to managed Loki

`alloy-snippets/04-rule-sync.alloy` already wires this:

```alloy
loki.rules.kubernetes "sync" {
  address = sys.env("LOKI_RULER_URL")           // platform team gives this (Q2)
  tenant_id    = sys.env("LOKI_TENANT_ID")
  bearer_token = sys.env("LOKI_RULER_BEARER_TOKEN")

  rule_selector {
    match_labels = { "shipto.lgtm" = "true" }
  }
  rule_namespace_selector {
    match_labels = { "lgtm.tenant" = sys.env("TENANT") }
  }

  sync_interval = "1m"
}
```

Same shape as `mimir.rules.kubernetes` — just the API endpoint differs.

---

## Local fallback — Loki Ruler in-cluster (if no managed Loki yet)

If we want to **test the LogQL alerting path before the platform team is ready**, we can stand up a single-binary Loki + Loki Ruler in the proxmox cluster:

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack \
  --namespace logging --create-namespace \
  --set loki.config.ruler.alertmanager_url=http://kube-prom-kube-prometheus-alertmanager.monitoring:9093 \
  --set promtail.enabled=false           # we use Alloy, not Promtail

# Point Alloy's loki.write at this local instance
LOKI_PUSH_URL=http://loki.logging.svc.cluster.local:3100/loki/api/v1/push
LOKI_TENANT_ID=local                     # single-tenant in dev
```

The Ruler in this stack natively forwards firing alerts to AlertManager (the same `kube-prom` AlertManager our metrics rules already use). End result: log-based and metric-based alerts arrive at the **same** Argo EventSource, indistinguishable to the Sensor.

This is the recommended path for **proving the design end-to-end on proxmox** before the managed Loki is wired up.

---

## Adding a new log alert (cookbook)

```bash
# 1. Edit the rules file
$EDITOR alerting/02-lokirules-platform.yaml

#    Example — alert when GitLab MCP returns 5xx more than 5/min:
#
#    - alert: GitlabMcpServerErrors
#      expr: |
#        sum by (cluster) (
#          count_over_time({namespace="argo-events", container="gitlab-mcp"} |~ "HTTP/.*5\\d\\d" [5m])
#        ) > 5
#      for: 5m
#      labels:
#        severity: warning
#        route_to: triage
#      annotations:
#        summary: "GitLab MCP 5xx burst"
#        runbook_url: "https://runbooks.example.com/GitlabMcpDown"

# 2. Apply locally
kubectl apply -f alerting/02-lokirules-platform.yaml

# 3. (Local Loki) verify Ruler picked it up
kubectl exec -n logging deploy/loki -- wget -qO- localhost:3100/loki/api/v1/rules
# (Managed Loki) verify Alloy synced
kubectl logs -n monitoring -l app.kubernetes.io/name=alloy --tail=50 | grep loki.rules.kubernetes

# 4. Trigger the log pattern (or wait for it naturally)
#    To force-test, post a fake log line via the Loki push API:
curl -X POST http://localhost:3100/loki/api/v1/push -H 'Content-Type: application/json' -d '{
  "streams": [{"stream":{"namespace":"argo-events","container":"gitlab-mcp","cluster":"{{CLUSTER_NAME}}"},
               "values":[["'"$(date +%s%N)"'","HTTP/1.1 500 Internal Server Error"]]}]
}'

# 5. Verify a triage workflow appeared (same as metrics path)
kubectl get workflows -n argo-events -l event-type=prometheus-alert --sort-by=.metadata.creationTimestamp
```

---

## Testing the full path

Once a Loki Ruler exists (managed or local), the test plan is identical to the metrics path because everything from AlertManager onwards is shared:

```bash
# Synthetic — post an AM-shaped payload that *looks* like it came from a Loki rule
# (proves the EventSource → Sensor → Workflow → kagent chain handles log alerts)
curl -X POST http://localhost:12000/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "version":"4","status":"firing","receiver":"argo-events-webhook",
    "alerts":[{
      "status":"firing",
      "labels":{
        "alertname":"ApplicationPanicLogged",
        "severity":"critical",
        "namespace":"agentgateway-system",
        "pod":"agentgateway-7d9-xyz",
        "service":"agentgateway",
        "cluster":"{{CLUSTER_NAME}}",
        "route_to":"triage"
      },
      "annotations":{
        "summary":"Panic in agentgateway-system/agentgateway-7d9-xyz",
        "description":"Container logged a panic in the last 5m",
        "runbook_url":"https://runbooks.example.com/AppPanic"
      },
      "startsAt":"2026-04-30T00:00:00Z"
    }]
  }'

# Real — produce a log line that matches the rule, watch Loki evaluate it
kubectl run panic-test --image=busybox --restart=Never -n default -- \
  sh -c 'echo "panic: runtime error: index out of range"; sleep 60'

# Verify
kubectl get workflows -n argo-events -l event-type=prometheus-alert --sort-by=.metadata.creationTimestamp | tail -5
```

---

## Cardinality + cost gotchas

LogQL alerts can be expensive if not scoped:

1. **Always pin a stream selector.** `{namespace="x"} |~ "panic"` is fine. `{cluster=~".+"} |~ "panic"` scans every log in the tenant — fine for low-volume patterns but expensive for hot regexes.
2. **Avoid expensive regex on hot streams.** `kube-system` and ingress controllers produce hundreds of MB/min — narrow with a label first.
3. **Use `|~` not `|=` only when needed.** `|=` is a literal substring match (cheap). `|~` is regex (expensive).
4. **Set `interval` to >= 1m for log rules.** The default 30s is fine for metric rules but the Loki Ruler does a real query each evaluation.
5. **Watch the `lgtm.tenant` budget** — Q7 in OPEN-QUESTIONS.md. The platform team will throttle us if log-rule eval blows past their per-tenant query limit.

---

## Troubleshooting

| Symptom | Where to look |
|---|---|
| Rule not in Loki Ruler | Alloy logs `loki.rules.kubernetes` — check `shipto.lgtm: "true"` label, check `lgtm.engine: loki` label is set so it goes to Loki not Mimir |
| Rule loaded but never fires | Run the `expr` in Grafana Explore (Loki datasource) — verify the LogQL returns rows with the same threshold |
| Loki rejecting logs (push 4xx) | Alloy logs `loki.write` — usually X-Scope-OrgID missing or label cardinality limit hit |
| K8s events not in Loki | Verify `loki.source.kubernetes_events` running in Alloy. Check Alloy SA has `get/list/watch` on `events.k8s.io/v1` |
| Alert fires in Ruler but no AlertManager hit | Ruler `alertmanager_url` config (or managed-side routing) — check `kubectl logs -n logging loki-* -c loki \| grep -i alertmanager` |
| Webhook arrives but no workflow | Same as metrics path — check Sensor logs, rate-limits |

---

## Open questions blocking this

From `OPEN-QUESTIONS.md`:

| # | Question | Impact |
|---|---|---|
| Q2 | Loki push URL + tenant + auth | Can't ship logs to managed Loki |
| Q3 | Rule provisioning model + which CRD shape (PrometheusRule with engine label, or dedicated LokiRule) | Determines rule YAML in this repo |
| Q4 | Can managed AM call our webhook? | Same blocker as metrics path — once solved, both work |
| Q7 | Per-tenant query / cardinality limits | Sizing log-alert rule fan-out |

The local-Loki fallback (single-binary in proxmox) lets us ship and validate the LogQL alerting design **today** without waiting on Q2 / Q3 / Q7.

---

## See also

- `README-METRICS-EVENTS-ALERTING.md` — the metrics sibling of this doc; same downstream pipeline, different signal source
- `OPTION-A-README.md` — the network/ingress story for the AlertManager → EventSource webhook (shared by both paths)
- `alerting/02-lokirules-platform.yaml` — the example rule file referenced throughout
- `alloy-snippets/02-logs-to-loki.alloy` — log push config (pod logs + k8s events)
- `alloy-snippets/04-rule-sync.alloy` — `loki.rules.kubernetes` syncer
- `LGTM-TO-ARGO-EVENTS-RECAP.md` — top-level decision tree

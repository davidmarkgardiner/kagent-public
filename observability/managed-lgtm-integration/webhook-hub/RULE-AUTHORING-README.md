# Rule-authoring conventions for the Webhook Hub

How to write a Prometheus / Loki / Grafana alert rule that produces a fully triage-able alert when it fires through the Hub. Following these conventions means the workflow has the labels it needs, kagent has the context it needs for prompt anchoring, and the Mattermost card has all the fields rendered.

This is the contract between rule authors and the Hub. Treat it as a PR-review checklist for any new alert rule.

---

## What "triage-able" means

When the Hub workflow (`06-workflow-template-triage.yaml`) fires, it needs to answer four questions from the alert payload alone:

1. **What broke?** — the alert name
2. **Where is it?** — cluster, namespace, pod (or service)
3. **How serious?** — severity
4. **Who owns it?** — team

Then the triage step enriches with logs, events, and describe output. The enrichment depends on (2). If the alert payload doesn't tell us where the problem is, kagent has nothing to anchor on and Qwen 14B will hallucinate a namespace (memory: this happens — we mitigated it with explicit anchoring).

So the contract: **every alert that should be triaged must carry alertname + cluster + namespace + (pod OR service) + severity + team in its labels, and summary + description + runbook_url in its annotations.**

---

## Required labels

| Label | Required? | Source | Why |
|---|---|---|---|
| `alertname` | ✅ Always | Rule's `alert:` field | Identifies what fired |
| `severity` | ✅ Always | Rule's `labels:` block (`critical` / `warning` / `info`) | Drives Mattermost card colour, Sensor filtering |
| `namespace` | ✅ Always (for k8s alerts) | Metric/log series label, preserved through aggregation | Triage anchor for kubectl |
| `cluster` | ✅ Always | Alloy `external_labels` — auto-attached on every series | Cross-cluster disambiguation |
| `pod` | ✅ When applicable | Metric/log series label, preserved through aggregation | Triage anchor for `kubectl logs` |
| `service` | ✅ For app/RED alerts | App's `app.kubernetes.io/name` label | Routing for service-team alerts |
| `team` | ✅ Always | Rule's `labels:` block — set explicitly | Subscriber Sensor filter |
| `route_to` | ✅ Always | Rule's `labels:` block — set to `triage` | AlertManager / Grafana routing picks Hub receiver |
| `container` | Optional | Series label, when relevant | Improves kubectl logs targeting |

## Required annotations

| Annotation | Required? | Why |
|---|---|---|
| `summary` | ✅ Always | One-line headline shown in Mattermost card title |
| `description` | ✅ Always | Multi-line context shown in card body — include `{{ $value }}` and `{{ $labels.X }}` |
| `runbook_url` | ✅ Always (placeholder OK) | Linked from Mattermost card; future-self thanks you |
| `dashboard_url` | Optional | If you have a Grafana dashboard for this signal, link it |

---

## The `by (...)` discipline

This is the single biggest gotcha. PromQL/LogQL aggregations drop labels not listed in `by (...)`. If you drop a label triage needs, the resulting alert is unanchorable.

### Bad — drops `pod`, `namespace`, `cluster`

```yaml
- alert: TooManyRestarts
  expr: sum (rate(kube_pod_container_status_restarts_total[5m])) > 3
  # The fired alert has no pod, no namespace, no cluster.
  # Mattermost shows "TooManyRestarts in /" — useless.
```

### Good — preserves all triage labels

```yaml
- alert: TooManyRestarts
  expr: |
    sum by (cluster, namespace, pod, container) (
      rate(kube_pod_container_status_restarts_total[5m])
    ) > 3
  for: 5m
  labels:
    severity: warning
    team: platform
    route_to: triage
  annotations:
    summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} restarting"
    description: |
      Container {{ $labels.container }} restarting at {{ $value | printf "%.2f" }} per second
      over the last 5m in cluster {{ $labels.cluster }}.
    runbook_url: "https://runbooks.example.com/TooManyRestarts"
```

**Mental model:** the labels that show up *in the fired alert* are the **intersection** of (labels in the underlying series) AND (labels listed in every `by (...)` clause along the way). Anything dropped at any stage is gone for good.

### Quick test before merging a rule

Run the rule's `expr` in the Prometheus / Grafana / Loki Explore UI. The result rows must show every label you depend on. If a row doesn't have `pod=`, the alert won't either.

---

## Severity vocabulary

| Severity | When to use | Card colour | Default rate-limit |
|---|---|---|---|
| `critical` | Live customer / data impact, immediate action | Red | 5/min |
| `warning` | Degraded but not customer-facing yet | Orange | 5/min |
| `info` | Notable but not actionable; logging only | Grey | (filtered out by AI triage Sensor) |

Stick to these three. The AI triage Sensor in `07-sensor-ai-triage.yaml` filters for `critical` and `warning`. `info` alerts pass through the Hub but only subscribers that explicitly opt in will pick them up.

---

## The `route_to` routing label

`route_to` is the magic word that makes the upstream AlertManager / Grafana routing tree send the alert to the Hub.

```yaml
labels:
  route_to: triage
```

Without it, the alert evaluates and fires but goes nowhere — the upstream router doesn't match it to the Hub receiver. This label is required on every Hub-bound rule. Other values (`route_to: bigpanda`, `route_to: pager`) can coexist if your upstream routing tree is configured for them.

---

## LogQL-specific conventions

Loki rules have an extra cost dimension — query evaluation runs on every interval and scans logs. Two extra rules:

### Always tightly scope the stream selector

```logql
# BAD — scans every log line in the tenant
sum by (cluster, namespace, pod) (
  count_over_time({cluster=~".+"} |~ "(?i)panic" [5m])
)

# GOOD — narrows to namespaces you actually own
sum by (cluster, namespace, pod) (
  count_over_time({cluster=~".+", namespace=~"team-x|team-y"} |~ "(?i)panic" [5m])
)
```

### Use `|=` (literal) over `|~` (regex) when you can

```logql
# Slower
{namespace="x"} |~ "panic:"

# Faster — literal substring match
{namespace="x"} |= "panic:"
```

### Set rule `interval` to ≥ 1 minute

Default 30s is fine for Prometheus rules but expensive for Loki — every interval triggers a real log scan. Bump to `1m` minimum.

```yaml
- name: my-log-alerts
  interval: 1m            # ← this
  rules: [ ... ]
```

---

## Anatomy of a fully-conforming rule (PromQL)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: my-team-rules
  namespace: monitoring
  labels:
    release: kube-prom        # local Prometheus picks it up
    shipto.lgtm: "true"       # Alloy syncs to managed Mimir Ruler
    lgtm.tenant: my-team
spec:
  groups:
    - name: pod-health
      interval: 30s
      rules:
        - alert: ContainerOOMKilled
          expr: |
            kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1
          for: 0m
          labels:
            # severity → card colour, Sensor filter
            severity: critical
            # team → subscriber Sensor filter
            team: my-team
            # route_to → upstream router picks Hub
            route_to: triage
          annotations:
            summary: "{{ $labels.namespace }}/{{ $labels.pod }} OOMKilled"
            description: |
              Container {{ $labels.container }} killed for exceeding memory limit.
              Cluster: {{ $labels.cluster }}
              Pod:     {{ $labels.namespace }}/{{ $labels.pod }}
            runbook_url: "https://runbooks.example.com/OOMKilled"
            dashboard_url: "https://grafana.example.com/d/abc/pod-memory?var-namespace={{ $labels.namespace }}&var-pod={{ $labels.pod }}"
```

## Anatomy of a fully-conforming rule (LogQL)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule        # or LokiRule, depending on platform-team CRD choice
metadata:
  name: my-team-log-rules
  namespace: monitoring
  labels:
    release: kube-prom
    shipto.lgtm: "true"
    lgtm.tenant: my-team
    lgtm.engine: loki       # tells Alloy rule-sync to use Loki Ruler
spec:
  groups:
    - name: error-patterns
      interval: 1m            # ≥1m for Loki rules
      rules:
        - alert: ApplicationPanicLogged
          expr: |
            sum by (cluster, namespace, pod, container) (
              count_over_time(
                {namespace=~"my-team-.*"} |= "panic:" [5m]
              )
            ) > 0
          for: 0m
          labels:
            severity: critical
            team: my-team
            route_to: triage
          annotations:
            summary: "Panic in {{ $labels.namespace }}/{{ $labels.pod }}"
            description: |
              Container {{ $labels.container }} logged a panic in the last 5m.
              Count: {{ $value | printf "%.0f" }}
              Cluster: {{ $labels.cluster }}
            runbook_url: "https://runbooks.example.com/AppPanic"
```

---

## PR review checklist

Use this when reviewing PRs that add or modify alert rules.

### Labels (alert payload triage anchor)
- [ ] `severity` set to `critical`, `warning`, or `info`
- [ ] `team` set to the owning team's identifier
- [ ] `route_to: triage` set if the alert should reach the Hub
- [ ] All `by (...)` clauses preserve `cluster`, `namespace`, and (`pod` or `service`)

### Annotations (Mattermost card content)
- [ ] `summary` is one line, includes `{{ $labels.namespace }}/{{ $labels.pod }}` (or service)
- [ ] `description` includes `{{ $value }}` so the rate/count is visible in chat
- [ ] `runbook_url` is set (placeholder URL acceptable for new alerts)

### Hygiene
- [ ] `for:` is appropriate (`0m` for instant alerts, `5m`+ for noisy signals)
- [ ] LogQL rules use `|=` over `|~` where possible
- [ ] LogQL rules tightly scope the stream selector
- [ ] LogQL rule `interval` is ≥ 1 minute

### Sync labels (managed-LGTM only — skip for local-cluster-only rules)
- [ ] `shipto.lgtm: "true"` if the rule should reach managed Mimir/Loki Ruler
- [ ] `lgtm.tenant` matches the team's tenant
- [ ] `lgtm.engine: loki` set on Loki rules so Alloy routes to the right ruler

### End-to-end smoke
- [ ] Rule's `expr` runs in the Grafana Explore UI and returns rows with all required labels
- [ ] Synthetic webhook test (post a fake AM-shaped payload to the Hub with these labels) produced a triage workflow

---

## Field glossary — what the Hub workflow reads

For reference when authoring or debugging. Every field below is read by `06-workflow-template-triage.yaml` `parse-alerts` step and used in the kagent prompt or Mattermost card.

| Path in payload | Used for |
|---|---|
| `.alerts[].labels.alertname` | Workflow naming, Mattermost title, kagent prompt |
| `.alerts[].labels.severity` | Card colour, Sensor filter |
| `.alerts[].labels.namespace` | kagent prompt anchor, kubectl target |
| `.alerts[].labels.pod` | kagent prompt anchor, kubectl logs target |
| `.alerts[].labels.service` | Optional kagent context |
| `.alerts[].labels.cluster` | kagent prompt anchor for cross-cluster rules |
| `.alerts[].labels.team` | Subscriber Sensor filter |
| `.alerts[].annotations.summary` | Mattermost card summary field |
| `.alerts[].annotations.description` | Mattermost card body |
| `.alerts[].annotations.runbook_url` | Mattermost card runbook link |
| `.alerts[].status` | Workflow filter (firing vs resolved) |
| `.alerts[].startsAt` | Triage time anchor (used for log time-window queries) |
| `.alerts[].generatorURL` | Card link back to firing query in Prometheus / Grafana |
| `.commonLabels.team` | Sensor filter for team-X subscribers |

If you want to add a new field that the workflow uses, the change is two lines in `06-workflow-template-triage.yaml` `parse-alerts` jq expression. Treat new fields as backwards-compatible additions — never remove a field other subscribers might depend on.

---

## See also

- `README.md` — Hub deployment, prereqs, smoke tests
- `UPSTREAM-SENDER-CONFIG.md` — Grafana Contact Point and AlertManager `webhook_configs` snippets
- `06-workflow-template-triage.yaml` — the workflow these conventions feed
- `../alerting/01-prometheusrules-platform.yaml` — example metric rules following this guide
- `../alerting/02-lokirules-platform.yaml` — example log rules following this guide
- `../README-METRICS-EVENTS-ALERTING.md` — broader metrics-alerting story
- `../README-LOG-ALERTING.md` — broader log-alerting story

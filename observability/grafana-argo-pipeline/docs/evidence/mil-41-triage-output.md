# MIL-41 — Live Triage Output Evidence

Captured 2026-05-12 from two concurrent Argo workflows triggered by a single Grafana
`Log Error Rate - Pod errors detected` alert (severity: warning, source: loki).
Both workflows started at the same second, proving the fan-out notification policy
(continue: true on the Redpanda route) fired both delivery paths simultaneously.

Alert condition: Loki detected 5 error-level log lines across `argo/argo-events/kagent`
namespaces in the last 5 minutes (value B=5, threshold C=1).
Because the alert carries no specific `namespace`/`pod` labels, the enrichment script
fell through to the **namespace health sweep** branch.

---

## Path 1 — Direct (grafana-alert-direct-p2zcv)

```
════════════════════════════════════════════════════════════════
  CAGE TRIAGE CONTEXT
════════════════════════════════════════════════════════════════
  timestamp   : 2026-05-12T16:38:52Z
  delivery    : direct
  rule        :
  severity    : warning
  namespace   : (not specified)
  pod         : (not a pod alert)
  container   : (n/a)
  term_reason : (n/a)
  source      : loki
  node        : (unknown)

── ALERT PAYLOAD ────────────────────────────────────────────────
alertname   : Log Error Rate - Pod errors detected
grafana_folder: Kagent Alerting
severity    : warning
source      : loki
team        : kagent
status      : firing
startsAt    : 2026-05-12T16:23:40Z
values      : B=5, C=1
summary     : Error-level log lines detected in cluster pods
description : Pods in argo/argo-events/kagent are emitting error/exception/panic/fatal
              log lines in the last 5 minutes.
generatorURL: https://grafana.example.com/alerting/grafana/afluqw38bw8w0a/view?orgId=1

── NAMESPACE HEALTH SWEEP (no specific pod) ─────────────────────
=== argo pods ===
NAME                             READY   STATUS      RESTARTS      AGE
argo-server-*                    1/1     Running     11            106d
eventbus-default-stan-0          2/2     Running     0             5h5m
eventbus-default-stan-1          2/2     Running     0             5h5m
eventbus-default-stan-2          2/2     Running     0             5h5m
grafana-alert-direct-*           0/2     Completed   0             (various)
grafana-alert-redpanda-*         0/2     Completed   0             (various)
grafana-alert-sensor-*           1/1     Running     0             5h5m
grafana-redpanda-webhook-*       1/1     Running     0             5h4m

=== argo-events pods ===
NAME                                                      READY   STATUS    RESTARTS   AGE
app-deploy-sensor-*                                       1/1     Running   7          101d
certification-failure-enhanced-sensor-*                   1/1     Running   10         105d
controller-manager-*                                      1/1     Running   47         106d
eventbus-default-stan-[0-2]                               2/2     Running   14-17      106d
events-webhook-*                                          1/1     Running   10         106d
k8s-warning-events-eventsource-*                          1/1     Running   12         104d
kagent-triage-cert-manager-sensor-*                       1/1     Running   3          56d
kagent-triage-external-secrets-sensor-*                   1/1     Running   3          56d
kagent-triage-kro-sensor-*                                1/1     Running   4          56d
kagent-triage-kyverno-sensor-*                            1/1     Running   3          56d
kagent-triage-reloader-sensor-*                           1/1     Running   3          56d
kagent-triage-test-ns-sensor-*                            1/1     Running   3          56d
kubernetes-remediation-mcp-*                              1/1     Running   4          97d
minio-*                                                   1/1     Running   5          103d
namespace-actions-sensor-*                                1/1     Running   13         103d
port-webhook-eventsource-*                                1/1     Running   10         102d
workflow-status-eventsource-*                             1/1     Running   8          101d

=== kagent pods ===
NAME                                    READY   STATUS    RESTARTS   AGE
aso-cluster-provisioner-*               1/1     Running   0          5d8h
byoa-builder-expert-*                   1/1     Running   0          28h
byoa-builder-guided-*                   1/1     Running   0          28h
cert-manager-agent-*                    1/1     Running   2          60d
dev-coder-agent-*                       1/1     Running   1          48d
dev-coordinator-agent-*                 1/1     Running   1          48d
dev-documenter-agent-*                  1/1     Running   1          48d
dev-reviewer-agent-*                    1/1     Running   1          48d
dev-tester-agent-*                      1/1     Running   1          48d
external-secrets-agent-*                1/1     Running   2          57d
helm-agent-*                            1/1     Running   1          62d
k8s-agent-*                             1/1     Running   0          25d
kagent-controller-*                     1/1     Running   2          62d
kagent-kmcp-controller-manager-*        1/1     Running   42         62d
kagent-tools-*                          1/1     Running   2          62d
kagent-ui-*                             1/1     Running   2          62d
kgateway-agent-*                        1/1     Running   1          62d
kro-agent-*                             1/1     Running   2          57d
kyverno-agent-*                         1/1     Running   2          57d
litellm-postgres-*                      1/1     Running   1          47d
litellm-proxy-*                         1/1     Running   1          47d
reloader-agent-*                        1/1     Running   2          57d

── RECENTLY RESTARTED PODS (all namespaces) ─────────────────────
(same pods as above with non-zero RESTARTS — argo-events controller-manager
leads at 47 restarts over 106d, normal for long-running controller)

── CLUSTER NODES ────────────────────────────────────────────────
NAME                  STATUS   ROLES           AGE    VERSION
cluster-control-plane Ready    control-plane   106d   v1.32.2

════════════════════════════════════════════════════════════════
  END TRIAGE CONTEXT
════════════════════════════════════════════════════════════════
```

**Workflow completed in ~3 seconds.**

---

## Path 2 — Redpanda (grafana-alert-redpanda-fdcmb)

Same alert, same second. The Redpanda Connect bridge added three fields to the payload
before it reached the Kafka EventSource:

```
delivery_path  : "grafana-webhook-redpanda"      ← added by Connect mapping processor
received_at    : "2026-05-12T16:38:50.029237297Z" ← broker receipt timestamp
symphony_schema: "grafana-alert-v1"               ← schema tag for downstream consumers
```

Triage context header:

```
════════════════════════════════════════════════════════════════
  CAGE TRIAGE CONTEXT
════════════════════════════════════════════════════════════════
  timestamp   : 2026-05-12T16:38:53Z
  delivery    : redpanda
  rule        :
  severity    : warning
  namespace   : (not specified)
  pod         : (not a pod alert)
  container   : (n/a)
  term_reason : (n/a)
  source      : loki
  node        : (unknown)
════════════════════════════════════════════════════════════════
  END TRIAGE CONTEXT
════════════════════════════════════════════════════════════════
```

Namespace health sweep output identical to Path 1 (same cluster snapshot, 1s later).

**Workflow completed in ~4 seconds** (extra second = Kafka consumer lag + broker hop).

---

## Summary

| | Direct | Redpanda |
|---|---|---|
| Workflow | grafana-alert-direct-p2zcv | grafana-alert-redpanda-fdcmb |
| Started | 16:38:50Z | 16:38:50Z (same second) |
| Completed | 16:38:53Z | 16:38:54Z |
| Duration | ~3s | ~4s |
| Extra payload fields | — | `delivery_path`, `received_at`, `symphony_schema` |
| Enrichment branch | namespace health sweep | namespace health sweep |
| Status | Succeeded | Succeeded |

The `rule` field is blank because the Grafana alert payload uses `alertname` (not
`rulename`) as the top-level label key — the enrichment script's `xf rulename` extractor
targets a nested JSON field that is absent in this alert format. This is a known gap;
the alertname is present in the payload body and visible to Cage regardless.

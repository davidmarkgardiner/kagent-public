# Anomaly Detection — Platform Starter Set

Top anomalies worth detecting across the core platform stack, with a short
description and the metrics to build each one on. Scoped as entry points, not
full runbooks — enough to stand up a first Grafana ML forecast/outlier panel or
alert per item.

**Stack in scope:** Node Auto Provisioner (NAP / Karpenter), cert-manager,
external-dns, Kyverno, Alloy (+ sealed/sterile secrets), Istio add-on.

**Detection style key:**
- **Forecast / outlier** — metric has a clean baseline + seasonality; good fit
  for Grafana ML (forecasting, outlier detection). Alert on deviation from
  predicted band.
- **Threshold** — binary or non-seasonal; a static/burn-rate threshold beats ML.

---

## Priority focus (office showcase)

These four are the ones we most want to demo. Node scheduling health plus the
big one: **we reserve far more CPU/memory than we actually use** — right-sizing
that gap is a clear, visual cost win.

### 1. Unschedulable pods stuck pending  ⭐

Pods requesting capacity that never lands — NAP not provisioning fast enough,
hitting a cloud quota/limit, no instance type matches the request, or taints/
affinity make pods unplaceable. Sustained pending is a live degradation: the
workload is down or under-capacity right now.

**Why anomaly, not just alert:** a low baseline of transient pending is normal
(pods wait a few seconds for a node). We want the *outlier* — pending count or
pending *duration* climbing above the normal band, especially when it doesn't
clear.

- `kube_pod_status_phase{phase="Pending"}` — count of pending pods over time
- `kube_pod_status_unschedulable` — pods the scheduler flagged unschedulable
- Pending age: `time() - kube_pod_created` for pods still Pending (alert when
  p95 age crosses ~2–5 min)
- Cross-check the reason: scheduler events / `FailedScheduling`, and
  `karpenter_pods_state{...}` to confirm NAP saw the pod

**Panel idea:** forecast band on pending count per namespace; annotate with NAP
provisioning events so a spike lines up (or doesn't) with a node launch.

### 2. Node provisioning latency drift  ⭐

Time from "pod pending" → "node Ready and pod scheduled" creeping up. Signals
cloud API throttling, wrong/scarce instance types, image pull slowness, or
bootstrap problems. Slow provisioning = slow autoscale = user-visible lag under
load.

- `karpenter_pods_startup_duration_seconds` — end-to-end pod startup (headline
  metric; forecast p50/p99)
- Gap between `karpenter_nodeclaims_launched_total` and
  `karpenter_nodeclaims_registered_total` — launched-but-not-registered = nodes
  slow to join
- `karpenter_nodeclaims_termination_duration_seconds` — drain/terminate side
- Cloud throttle signal: provider API error/throttle logs from the NAP
  controller

**Panel idea:** forecast on p99 startup duration; alert when observed leaves the
predicted band for N minutes.

### 3. Consolidation churn / thrash  ⭐

Nodes created and destroyed too frequently. NAP consolidation is supposed to
save money, but over-aggressive churn causes constant pod eviction/reschedule,
disruption, and (ironically) cost from repeated launches. Learn the normal churn
rate; alert on the outlier.

- `karpenter_nodeclaims_disrupted_total` — disruption actions (consolidation,
  drift, expiration) by reason
- `karpenter_voluntary_disruption_decisions_total` — decision rate
- `rate(karpenter_nodes_created_total)` / `rate(karpenter_nodes_terminated_total)`
  — create/terminate velocity
- Correlate with #1 pending: churn that spikes pending is doubly bad

**Panel idea:** forecast on nodes created+terminated per hour; flag when both
run hot at once (thrash, not net scale-up/down).

### 4. Capacity over-reservation — requested vs actual  ⭐⭐

**The big one.** Pods *request* far more CPU/memory than they *use*, so NAP
provisions nodes to satisfy requests while real utilization sits low. We pay for
reserved-but-idle capacity. Surfacing the gap per namespace/workload makes the
waste obvious and gives right-sizing targets.

**Slack = requested − used.** Track the ratio, not just absolutes.

CPU:
```promql
# Fleet requested vs actually used (cores)
sum(kube_pod_container_resource_requests{resource="cpu"})
sum(rate(container_cpu_usage_seconds_total{container!=""}[5m]))

# Utilization ratio (low = over-reserved)
sum(rate(container_cpu_usage_seconds_total{container!=""}[5m]))
  /
sum(kube_pod_container_resource_requests{resource="cpu"})
```

Memory:
```promql
# Requested vs working-set used (bytes)
sum(kube_pod_container_resource_requests{resource="memory"})
sum(container_memory_working_set_bytes{container!=""})

# Utilization ratio
sum(container_memory_working_set_bytes{container!=""})
  /
sum(kube_pod_container_resource_requests{resource="memory"})
```

Per-namespace breakdown (right-sizing targets) — add `by (namespace)` to each
sum. The namespaces with the lowest ratio and highest absolute request are the
best trim candidates.

Also useful:
- `kube_node_status_allocatable` vs summed pod requests — how much allocatable
  is committed to requests vs free
- `karpenter_nodes_allocatable` vs `karpenter_pods_state` — NAP's own view of
  allocatable vs scheduled

**Detection style:** partly threshold (ratio persistently < ~0.4 = over-reserved)
and partly forecast (utilization has daily/weekly seasonality; anomalous *drops*
mean new waste appeared). Great candidate for a "right-sizing opportunities"
dashboard: a table of worst offenders + a fleet trend line.

**Payoff to showcase:** "X cores / Y GiB reserved, Z% actually used → right-size
these N workloads to reclaim ~$/month."

---

## cert-manager

### 5. Cert expiry approaching / renewal failing

Renewal loop stuck — ACME rate limit, DNS-01 challenge broken, issuer
misconfigured. Classic silent outage precursor: nothing breaks until the cert
lapses, then everything 5xxs.

- `certmanager_certificate_expiration_timestamp_seconds - time()` — time to
  expiry (threshold alert, e.g. < 14d and not renewing)
- `certmanager_certificate_ready_status{condition="False"}` — certs not Ready
- ACME order/challenge failures in controller error logs

**Detection style:** threshold — binary, not seasonal.

---

## external-dns

### 6. DNS record sync failures / drift

Records not reconciling; the DNS registry drifts from cluster state. Traffic
blackhole risk — endpoints resolve to nothing or to stale IPs.

- `external_dns_registry_errors_total`, `external_dns_source_errors_total`
- Divergence: `external_dns_registry_endpoints_total` vs
  `external_dns_source_endpoints_total`
- `external_dns_controller_last_sync_timestamp_seconds` — staleness (now − last
  sync)

**Detection style:** threshold on error rate + staleness; outlier on divergence.

---

## Kyverno

### 7. Policy denial spike

Sudden surge in admission rejections — a bad deploy, or a misconfigured policy
blocking legitimate workloads cluster-wide. Learn the normal fail rate; alert on
the spike.

- `kyverno_admission_requests_total` vs
  `kyverno_policy_results_total{result="fail"}`
- Outlier on fail rate per policy

**Detection style:** forecast / outlier.

### 8. Webhook latency / failure

Kyverno admission webhook slow or erroring → admission timeouts, deploys hang,
and (if failurePolicy=Fail) writes to the API server stall cluster-wide.

- `kyverno_admission_review_duration_seconds` — p99 forecast
- `kyverno_controller_reconcile_total` errors
- `apiserver_admission_webhook_rejection_count` — API-server side view

**Detection style:** forecast on latency; threshold on error rate.

---

## Alloy + sealed / sterile secrets

### 9. Alloy pipeline drop / lag

The collector drops samples or export fails → blind spots in observability
itself. Worst case: every other detector here goes quiet and looks "healthy."

- `up{job=~"alloy.*"}` — scrape gaps
- `prometheus_remote_storage_samples_failed_total`,
  `..._dropped_total` — export losses
- `prometheus_remote_write_wal_samples_appended_total` — throughput baseline

**Detection style:** threshold on failed/dropped; outlier on throughput drop.

### 10. Sealed / sterile secret decrypt failures

Controller can't unseal (key rotation, corrupt payload, wrong key) → app pods
crashloop on a missing secret. Failure shows up downstream, so correlate.

- Unseal error rate from the sealed-secrets controller logs
- Correlate:
  `kube_pod_container_status_waiting_reason{reason="CreateContainerConfigError"}`

**Detection style:** threshold on error rate + correlated pod waiting reason.

---

## Istio add-on

### 11. Error-rate / latency anomaly per service

5xx spike or p99 latency drift on mesh traffic. The core SLO signal and the best
natural fit for anomaly detection — clean seasonality, clear baseline.

- `rate(istio_requests_total{response_code=~"5.."}[5m])` vs forecast
- `istio_request_duration_milliseconds_bucket` — p50/p99 outlier

**Detection style:** forecast / outlier (per service).

### 12. mTLS / connection failures

TLS handshake failures, sidecar not ready, or config push errors → partial mesh
outage that's hard to see from app logs alone.

- `pilot_xds_push_errors_total` — config push failures
- `pilot_proxy_convergence_time` — config propagation drift
- `envoy_cluster_upstream_cx_connect_fail` — upstream connect failures
- `istio_tcp_connections_closed_total` — anomalous close rate

**Detection style:** threshold on push errors; outlier on convergence time.

---

## Bonus (if room on the board)

- **Pod restart / crashloop burst** — `rate(kube_pod_container_status_restarts_total[5m])`
  forecast per namespace.
- **Node NotReady / kubelet flap** —
  `kube_node_status_condition{condition="Ready",status="false"}` anomaly.

---

## Suggested build order

1. **#4 capacity over-reservation** — highest-visibility win, mostly PromQL, no
   ML required to start.
2. **#1 unschedulable pods** — operational pain we feel at the office.
3. **#2 / #3 provisioning latency + churn** — round out NAP health.
4. **#11 Istio error/latency** — best showcase of Grafana ML forecasting.
5. Fill in cert-manager, external-dns, Kyverno, Alloy as threshold alerts.

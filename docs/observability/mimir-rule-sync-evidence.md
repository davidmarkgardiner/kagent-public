# Alloy Mimir Rule Sync: Local Validation Evidence

Date: 2026-05-19

## Executive Finding

`mimir.rules.kubernetes` was **not enabled on the local validation cluster initially**.

The local validation cluster Alloy deployment is healthy and shipping
logs/metrics, but the mounted Alloy config contains only:

- `loki.source.kubernetes`
- `loki.process`
- `loki.write`
- `prometheus.scrape`
- `prometheus.relabel`
- `prometheus.remote_write`

There is no active `mimir.rules.kubernetes` component, no active
`loki.rules.kubernetes` component, and no `mimir_rules_*` or `loki_rules_*`
debug metrics exposed by Alloy.

This means the Prometheus rules that are currently visible in Grafana on
the local validation cluster are coming from the local kube-prometheus-stack
`PrometheusRule -> Prometheus` path, not from Alloy pushing rules into a Mimir
Ruler.

An isolated proof was then enabled on the local validation cluster without
disturbing the existing metrics/logs Alloy instance:

- local Mimir proof target: `monitoring/mimir-rule-sync-proof`
- isolated Alloy rule-sync instance: `monitoring/alloy-rule-sync-proof`
- smoke rule CR: `monitoring/managed-rule-sync-smoke`
- Grafana datasource: `Mimir Rule Sync Proof`, uid `mimir-rule-sync-proof`

That proof **does work**: Alloy discovered the Kubernetes `PrometheusRule`,
pushed it to the local Mimir Ruler API, and Grafana can read the synced rule via
the Mimir datasource proxy.

## What The Component Does

Per the official Grafana Alloy docs, `mimir.rules.kubernetes` discovers
`PrometheusRule` Kubernetes resources and loads them into a Mimir instance. It
is compatible with Grafana Mimir, Grafana Cloud, Grafana Enterprise Metrics, and
the Prometheus Operator `PrometheusRule` CRD.

Important mechanics:

- It runs inside an Alloy pod and reads the Kubernetes API.
- It needs RBAC for `get/list/watch` on `namespaces` and
  `monitoring.coreos.com/prometheusrules`.
- It pushes to the Mimir Ruler API, not the metrics remote-write endpoint.
- `tenant_id` is required when the Mimir target is multi-tenant; without it the
  API commonly returns `401 Unauthorized: no org id`.
- `rule_selector` selects `PrometheusRule` labels.
- `rule_namespace_selector` selects Kubernetes `Namespace` labels.
- Health and debug metrics are exposed through Alloy when the component is
  configured.

Official docs:

- <https://grafana.com/docs/alloy/latest/reference/components/mimir/mimir.rules.kubernetes/>
- <https://grafana.com/docs/alloy/latest/reference/components/loki/loki.rules.kubernetes/>

## Local Validation Evidence

### Alloy Is Running

```text
deployment.apps/k-agent-alloy 1/1
image: grafana/alloy:v1.16.1
service/k-agent-alloy ClusterIP ... 12345/TCP
```

Alloy readiness endpoint:

```text
Alloy is ready.
```

### Active Alloy Config Does Not Include Rule Sync

Current `monitoring/k-agent-alloy-config` includes:

```alloy
loki.write "lgtm" {
  endpoint {
    url = sys.env("LOKI_PUSH_URL")
  }
}

prometheus.remote_write "lgtm" {
  endpoint {
    url = sys.env("PROMETHEUS_REMOTE_WRITE_URL")
  }
}
```

It does not contain:

```alloy
mimir.rules.kubernetes "..."
loki.rules.kubernetes "..."
```

The Alloy `/metrics` endpoint exposes `prometheus_remote_storage_*` metrics for
`prometheus.remote_write.lgtm`, but no `mimir_rules_*` or `loki_rules_*`
metrics.

### RBAC Is Not Sufficient For Rule Sync

The active `k-agent-alloy` service account currently cannot read
`PrometheusRule` CRs:

```text
kubectl auth can-i list prometheusrules.monitoring.coreos.com \
  --as=system:serviceaccount:monitoring:k-agent-alloy -A
no

kubectl auth can-i watch prometheusrules.monitoring.coreos.com \
  --as=system:serviceaccount:monitoring:k-agent-alloy -A
no
```

It can list namespaces:

```text
kubectl auth can-i list namespaces \
  --as=system:serviceaccount:monitoring:k-agent-alloy
yes
```

### The Local Rule Path Works

The labelled K-Agent/Agent Gateway `PrometheusRule` exists:

```text
monitoring/k-agent-agentgateway-alerts
labels:
  shipto.lgtm=true
  lgtm.tenant=platform
  route_to=triage
  release=kube-prom
```

Prometheus loaded the rule groups from the local kube-prometheus-stack rule
file:

```text
k-agent-agentgateway-runtime
k-agent-agentgateway-token-usage
k-agent-controller-and-container-health
```

Representative loaded alert labels:

```text
kagent_path=webhook
route_to=triage
severity=warning
team=ai-platform
```

Grafana is healthy and sees the local datasources:

```text
Grafana version: 12.3.2
Datasources:
  Alertmanager -> http://kube-prom-kube-prometheus-alertmanager.monitoring:9093/
  Prometheus   -> http://kube-prom-kube-prometheus-prometheus.monitoring:9090/
  Loki         -> {{LOKI_URL}}
```

Grafana's own ruler API also has older Grafana-managed rules, but those are
separate from `mimir.rules.kubernetes`.

## Enabled Proof Evidence

The proof manifest is:

```text
k8s/observability/mimir-rule-sync-proof.yaml
```

Server-side dry run passed, then the manifest was applied. Both deployments
rolled out:

```text
deployment "mimir-rule-sync-proof" successfully rolled out
deployment "alloy-rule-sync-proof" successfully rolled out
```

Alloy loaded the rule-sync component:

```text
component_id=mimir.rules.kubernetes.proof
initializing with configuration
```

Alloy then synced the smoke rule:

```text
added rule group
namespace=alloy/monitoring/managed-rule-sync-smoke/5b3a0a81-7c12-40cd-960e-296d599bf894
group=managed.rule.sync.smoke
```

Alloy metrics prove the Ruler write happened:

```text
mimir_rules_events_total{type="sync-mimir"} 1
mimir_rules_mimir_client_request_duration_seconds_count{
  operation="POST /prometheus/config/v1/rules/<namespace>",
  status_code="202"
} 1
```

The local Mimir Ruler config API returns the synced rule:

```text
curl -H 'X-Scope-OrgID: platform' \
  http://127.0.0.1:19009/prometheus/config/v1/rules
```

Output:

```yaml
alloy/monitoring/managed-rule-sync-smoke/5b3a0a81-7c12-40cd-960e-296d599bf894:
  - name: managed.rule.sync.smoke
    interval: 1m
    rules:
      - alert: ManagedRuleSyncSmoke
        expr: vector(1)
        for: 1m
        labels:
          route_to: triage
          severity: info
```

Grafana can also read the rule through the Mimir datasource proxy:

```text
/api/datasources/proxy/uid/mimir-rule-sync-proof/api/v1/rules
```

Output includes:

```json
{
  "name": "ManagedRuleSyncSmoke",
  "query": "vector(1)",
  "state": "pending",
  "labels": {
    "route_to": "triage",
    "severity": "info"
  },
  "health": "ok"
}
```

This proves the lift-and-shift mechanism: a labelled Kubernetes
`PrometheusRule` can be pushed programmatically by Alloy into a Mimir-compatible
Ruler and then read through Grafana.

## How The Managed Rule-Sync Pattern Should Work

The intended managed LGTM flow is:

```text
PrometheusRule CR in Kubernetes
  -> Alloy mimir.rules.kubernetes watches the CR
  -> Alloy authenticates to managed Mimir/Grafana Cloud Ruler
  -> Alloy writes the rule group to the tenant's Ruler API
  -> Managed Grafana UI shows/evaluates the rule from the backend ruler
```

This can work around "UI-only" operator workflows only if we can obtain one of:

- a Grafana Cloud metrics/Ruler endpoint plus service-account token,
- a managed Mimir Ruler URL plus bearer token,
- or a gateway/proxy endpoint that accepts the Ruler API on behalf of our tenant.

It does **not** avoid the need for API credentials entirely. The user does not
need to click rules into the UI, but Alloy still needs write access to the Ruler
API.

## Minimal Managed LGTM Configuration

```alloy
mimir.rules.kubernetes "managed" {
  address   = sys.env("MIMIR_RULER_URL")
  tenant_id = sys.env("MIMIR_TENANT_ID")

  bearer_token = sys.env("MIMIR_RULER_BEARER_TOKEN")

  rule_selector {
    match_labels = {
      "shipto.lgtm" = "true",
      "lgtm.tenant" = sys.env("TENANT"),
    }

    match_expression {
      key      = "lgtm.engine"
      operator = "NotIn"
      values   = ["loki"]
    }
  }

  sync_interval = "1m"
}
```

Use `rule_namespace_selector` only if the Kubernetes Namespace itself is
labelled for tenant isolation. The normal safer selector is on the
`PrometheusRule` labels.

The repo snippet at
`observability/managed-lgtm-integration/alloy-snippets/04-rule-sync.alloy` was
validated with `grafana/alloy:v1.16.1 validate` after moving tenant filtering to
`rule_selector`.

## Minimal RBAC

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: alloy-rule-sync
rules:
  - apiGroups: [""]
    resources: ["namespaces"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["monitoring.coreos.com"]
    resources: ["prometheusrules"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: alloy-rule-sync
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-rule-sync
subjects:
  - kind: ServiceAccount
    name: k-agent-alloy
    namespace: monitoring
```

## Minimal Rule CR

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: managed-rule-sync-smoke
  namespace: monitoring
  labels:
    shipto.lgtm: "true"
    lgtm.tenant: platform
    route_to: triage
spec:
  groups:
    - name: managed.rule.sync.smoke
      interval: 1m
      rules:
        - alert: ManagedRuleSyncSmoke
          expr: vector(1)
          for: 1m
          labels:
            severity: info
            route_to: triage
          annotations:
            summary: Synthetic Alloy rule-sync smoke test
```

## Verification Commands

Check Alloy loaded the rule-sync component:

```bash
kubectl -n monitoring logs deploy/k-agent-alloy --tail=200 | \
  egrep 'mimir.rules.kubernetes|ruler|rule sync|rules.kubernetes'
```

Check Alloy debug metrics:

```bash
kubectl -n monitoring port-forward svc/k-agent-alloy 12345:12345
curl -fsS http://127.0.0.1:12345/metrics | egrep 'mimir_rules_|loki_rules_'
```

Check RBAC:

```bash
kubectl auth can-i list prometheusrules.monitoring.coreos.com \
  --as=system:serviceaccount:monitoring:k-agent-alloy -A
kubectl auth can-i watch prometheusrules.monitoring.coreos.com \
  --as=system:serviceaccount:monitoring:k-agent-alloy -A
```

Check the managed backend:

```bash
curl -fsS -H "Authorization: Bearer ${MIMIR_RULER_BEARER_TOKEN}" \
  -H "X-Scope-OrgID: ${MIMIR_TENANT_ID}" \
  "${MIMIR_RULER_URL}/prometheus/config/v1/rules"
```

For Grafana Cloud, use the exact Ruler endpoint and auth model provided by the
platform team; do not assume the remote-write URL is also the Ruler URL.

## Current Conclusion

local validation cluster originally proved only the local
`PrometheusRule -> Prometheus -> Grafana/Alertmanager` path and the Alloy
metrics/log shipping path. It now also proves the Alloy
`PrometheusRule -> mimir.rules.kubernetes -> Mimir Ruler -> Grafana datasource`
path using an isolated local Mimir proof target.

The remaining target environment blocker is credential and endpoint access for the managed
Ruler API. Once those values are available, the same proof should be repeated
with a small labelled `PrometheusRule` CR, Alloy `mimir_rules_*` metrics
increasing, and the rule visible in the managed Grafana Alerting UI without
manual rule creation.

# Programmatic Alerting — Engineering POC

## Problem

Managed LGTM at work exposes no API for alert configuration. Only path is the UI dashboard. This is unscalable across multiple applications and blocks agentic tooling.

**Options:**
1. Push the managed team to expose an API / GitOps workflow
2. Run our own stack in an eng cluster, prove the pattern, hand them working YAML

This doc covers option 2 — fastest path to verified, version-controlled alerts.

---

## What's Already Built

`observability/prometheus-alertmanager/` contains a working implementation:

| File | Purpose |
|------|---------|
| `01-alertmanager-values.yaml` | AlertManager Helm values — webhook receiver to Argo Events |
| `02-custom-alerting-rules.yaml` | `PrometheusRule` CRDs — OOMKill, restarts, CPU/mem/PVC thresholds |
| `03-eventsource-alertmanager.yaml` | Argo Events webhook listener |
| `04-workflow-template.yaml` | Triage DAG — fetch pod logs → GitLab issue → Mattermost notify |
| `05-sensor.yaml` | Alert filter + workflow trigger (rate-limited 5/min) |
| `06-grafana-dashboard.json` | Alert triage Grafana dashboard |
| `deploy.sh` | Ordered deploy with prerequisite checks |
| `test-alerts.sh` | End-to-end test — webhook injection, failing pods, verify |

These are the templates to extend for new applications.

---

## Engineering Cluster: Quick Start

### Prerequisites

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

### 1. Deploy kube-prometheus-stack

```bash
helm install kube-prom prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  -f observability/prometheus-alertmanager/01-alertmanager-values.yaml
```

### 2. Apply Alert Rules

```bash
kubectl apply -f observability/prometheus-alertmanager/02-custom-alerting-rules.yaml
```

### 3. Verify Rules Loaded

```bash
# Prometheus UI
kubectl port-forward -n monitoring svc/kube-prom-kube-prometheus-prometheus 9090:9090
# http://localhost:9090/alerts
```

### 4. Test Alert Pipeline

```bash
chmod +x observability/prometheus-alertmanager/test-alerts.sh
./observability/prometheus-alertmanager/test-alerts.sh --all
```

---

## Adding Alerts for a New Application

Copy and adapt the `PrometheusRule` CRD pattern:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: <app-name>-alerts
  namespace: monitoring
  labels:
    release: kube-prom          # must match Helm release name
spec:
  groups:
    - name: <app-name>
      rules:
        - alert: <AlertName>
          expr: <promql-expression>
          for: 5m
          labels:
            severity: warning   # critical | warning | info
            triage: "true"      # routes to Argo Events triage pipeline
          annotations:
            summary: "Human-readable summary"
            description: "Detail with {{ $labels.namespace }}/{{ $labels.pod }}"
```

Apply:
```bash
kubectl apply -f <app-name>-alerts.yaml

# Verify picked up
kubectl get prometheusrule <app-name>-alerts -n monitoring
```

---

## cert-manager Example

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cert-manager-alerts
  namespace: monitoring
  labels:
    release: kube-prom
spec:
  groups:
    - name: cert-manager
      rules:
        - alert: CertificateExpiringSoon
          expr: certmanager_certificate_expiration_timestamp_seconds - time() < 604800
          for: 1h
          labels:
            severity: warning
            triage: "true"
          annotations:
            summary: "Certificate expiring within 7 days in {{ $labels.namespace }}"
            description: "Certificate {{ $labels.name }} in {{ $labels.namespace }} expires in < 7 days."

        - alert: CertificateNotReady
          expr: certmanager_certificate_ready_status{condition="False"} == 1
          for: 10m
          labels:
            severity: critical
            triage: "true"
          annotations:
            summary: "Certificate not ready in {{ $labels.namespace }}"
            description: "Certificate {{ $labels.name }} has been in a non-ready state for more than 10 minutes."

        - alert: CertManagerDown
          expr: absent(up{job="cert-manager"}) == 1
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "cert-manager is not running"
            description: "No cert-manager metrics endpoint has been reachable for 5 minutes."
```

---

## GitOps Workflow

```
New alert needed
      │
      ▼
Write PrometheusRule YAML (or AlertmanagerConfig)
      │
      ▼
Test in eng cluster (kubectl apply + test-alerts.sh)
      │
      ▼
PR review
      │
      ▼
Hand YAML to managed team / apply via pipeline
```

Agents can generate and validate the YAML. Humans review the PromQL. Managed team applies to prod.

---

## Notification Endpoints

Current pipeline routes to Mattermost. To wire Teams or PagerDuty, update AlertManager receiver in `01-alertmanager-values.yaml`:

```yaml
# Microsoft Teams (via incoming webhook)
receivers:
  - name: teams-webhook
    webhook_configs:
      - url: "https://your-org.webhook.office.com/webhookb2/..."
        send_resolved: true

# PagerDuty
  - name: pagerduty
    pagerduty_configs:
      - routing_key: "<integration-key>"
        severity: '{{ .CommonLabels.severity }}'
```

---

## Port-Forward Reference

```bash
# Prometheus — query metrics, check alert rules
kubectl port-forward -n monitoring svc/kube-prom-kube-prometheus-prometheus 9090:9090

# AlertManager — check routing, silence alerts
kubectl port-forward -n monitoring svc/kube-prom-kube-prometheus-alertmanager 9093:9093

# Grafana — dashboards (admin / prom-operator)
kubectl port-forward -n monitoring svc/kube-prom-grafana 3000:80

# Argo Workflows — view triage runs
kubectl port-forward -n argo svc/argo-server 2746:2746
```

---

## Escalation: Teams Message Template

Use this to request templates from the observability team and assign ownership of outstanding work:

> I'll reach out to the LGTM team directly about programmatic access — though we may be quicker standing up our own Prometheus stack in the eng cluster, validating alert rules there, and handing them the code when it's ready to promote.
>
> In the meantime, could you share the templates/ screen shots in ticket for whatever targeted monitoring you've already configured? Even a single working example (cert-manager, ingress, anything) gives us the pattern to replicate for ALL the apps with missing coverage.
>
> We can assing to another engineer to pick up the outstanding work? There are apps running in dev right now with no targeted monitoring in place — that gap needs an owner and a timeline, not just a backlog item.

---

## Handing to the Managed Team

Once rules are validated in the eng cluster, the deliverable is:

1. `PrometheusRule` YAML files (one per application)
2. `AlertmanagerConfig` YAML (notification routing)
3. Grafana dashboard `ConfigMap` (auto-imported via sidecar)

These can be applied via `kubectl apply` or wired into their existing pipeline. No UI access required.

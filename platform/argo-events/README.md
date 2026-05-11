# Argo Events — Platform Install & Sources

Event-driven automation layer. Converts K8s events, webhook calls, and EventHub messages into Argo Workflow runs.

## Architecture

```
K8s Events / Azure EventHub / GitLab webhooks
          │
          ▼
    [EventSource]          ← receives raw events, normalises to CloudEvents
          │
          ▼
      [EventBus]           ← NATS native message bus
          │
          ▼
      [Sensor]             ← filters events, applies trigger conditions
          │
          ▼
  [WorkflowTemplate]       ← Argo Workflow execution (kagent-triage, onboarding, etc.)
```

## Directory Layout

| Path | Purpose |
|------|---------|
| `install/rbac/` | ServiceAccount, Role, RoleBinding for Argo Events controller and SA |
| `install/eventbus/` | NATS native EventBus definition |
| `install/helm/` | Helm chart (pinned to v1.9.5 — see below) |
| `sources/auto-healer/` | EventSource + Sensor for automatic pod/deployment healing |
| `sources/gitlab/` | GitLab webhook EventSource |
| `sources/gitlab/byo-kagent/` | Sensor that triggers BYO-kagent onboarding workflow |

## EventHub Version Pin {#eventhub-version-pin}

**Always use Argo Events chart `2.4.14` / appVersion `v1.9.5` when consuming Azure EventHub.**

Starting with v1.9.6, the `azureEventsHub` EventSource crashes with a nil-pointer panic when it receives messages that do not include a `messageId` field (upstream [Issue #3595](https://github.com/argoproj/argo-events/issues/3595)). This is confirmed unfixed through v1.9.7.

The chart in `install/helm/Chart.yaml` is already pinned. Do not upgrade until the upstream fix is released and verified.

Workarounds if you must use a newer version:
- Ensure every EventHub producer sets `messageId` on every message
- Switch to a non-EventHub source (Kafka, webhook, etc.)

## Sensor Safeguards

All sensors should implement rate-limiting and deduplication guards. See `agents/kagent-triage/SENSOR-SAFEGUARDS.md` for the full reference.

## Quick Start

```bash
# 1. Install Argo Events (pinned version)
helm repo add argo https://argoproj.github.io/argo-helm
helm upgrade --install argo-events argo/argo-events \
  --version 2.4.14 \
  --namespace argo-events --create-namespace

# 2. Apply RBAC
kubectl apply -f install/rbac/

# 3. Create EventBus
kubectl apply -f install/eventbus/

# 4. Apply sources
kubectl apply -f sources/auto-healer/
```

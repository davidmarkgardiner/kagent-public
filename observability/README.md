# Observability

## Overview

This area contains the observability patterns for platform and AI SRE workflows:

- Grafana Alloy collection from workload clusters.
- Managed LGTM integration for Mimir, Loki, dashboards, and rules.
- Alertmanager or Grafana Alerting delivery into Argo Events.
- kagent triage workflows for K-Agent, Agent Gateway, and platform alerts.
- Grafana MCP enrichment so agents can query dashboards, Prometheus/Mimir, Loki,
  and alerting metadata during triage.

Start with these documents for the current K-Agent / Agent Gateway path:

| Goal | File |
| --- | --- |
| Install and verify the observability bundle | [`../docs/observability/k-agent-agentgateway-observability.md`](../docs/observability/k-agent-agentgateway-observability.md) |
| Replicate Grafana MCP enrichment on another cluster | [`../docs/observability/grafana-mcp-home-lab.md`](../docs/observability/grafana-mcp-home-lab.md) |
| Understand the AI + Grafana triage pattern | [`../docs/ai-grafana/README.md`](../docs/ai-grafana/README.md) |
| Run the Grafana MCP smoke test | [`../scripts/observability/smoke-grafana-mcp.sh`](../scripts/observability/smoke-grafana-mcp.sh) |
| Maintain managed LGTM rule sync | [`managed-lgtm-integration/rule-sync/README.md`](managed-lgtm-integration/rule-sync/README.md) |
| Route Alertmanager alerts to kagent triage | [`../k8s/observability/k-agent-alert-triage-sensor.yaml`](../k8s/observability/k-agent-alert-triage-sensor.yaml) |

## Grafana MCP Triage Enrichment

The current alert enrichment path is:

```text
Grafana Alerting or Prometheus Alertmanager
  -> Argo Events EventSource
  -> Argo Sensor
  -> Argo Workflow
  -> kagent observability-agent
  -> Grafana MCP
  -> Prometheus/Mimir, Loki, dashboards, alerting metadata
```

The contact point is only the front door. It sends the original alert payload to
Argo Events. The workflow asks `observability-agent` to use Grafana MCP tools
such as `list_datasources`, `query_prometheus`, `query_loki_logs`,
`get_dashboard_summary`, `get_dashboard_panel_queries`, and `generate_deeplink`
before returning an operator verdict.

Keep the default agent read-oriented. Do not add dashboard mutation, plugin
install, annotation write, or incident creation tools unless the workflow has an
explicit human approval path.

## Legacy Event Hub Pattern

The older multi-cluster Kubernetes event triage pattern is still useful for
Event Hub backed ingestion:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WORKLOAD CLUSTERS                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  AKS Cluster 1  │  │  AKS Cluster 2  │  │  AKS Cluster N  │             │
│  │                 │  │                 │  │                 │             │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │             │
│  │  │   Alloy   │  │  │  │   Alloy   │  │  │  │   Alloy   │  │             │
│  │  └─────┬─────┘  │  │  └─────┬─────┘  │  │  └─────┬─────┘  │             │
│  └────────┼────────┘  └────────┼────────┘  └────────┼────────┘             │
│           │                    │                    │                       │
└───────────┼────────────────────┼────────────────────┼───────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AZURE EVENT HUB                                     │
│                    ┌────────────────────┐                                   │
│                    │  k8s-events topic  │                                   │
│                    └──────────┬─────────┘                                   │
└───────────────────────────────┼─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MANAGEMENT CLUSTER                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         argo-events namespace                         │  │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐  │  │
│  │  │  EventSource    │───►│     Sensor      │───►│ Triage Workflow  │  │  │
│  │  │ (Event Hub sub) │    │  (filter/route) │    │ (AI + Telegram)  │  │  │
│  │  └─────────────────┘    └─────────────────┘    └──────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### Workload Clusters
- **Grafana Alloy** - Collects K8s events and forwards to Event Hub
- Replaces existing Fluent Bit implementation
- Minimal footprint, just event collection

### Azure Event Hub
- Central event ingestion point
- Topic: `k8s-events`
- Consumer groups per management cluster

### Management Cluster
- **Argo Events EventSource** - Subscribes to Event Hub
- **Argo Events Sensor** - Filters and routes events
- **Triage Workflow** - AI-assisted triage + Telegram alerts

## Deployment

### 1. Workload Clusters
Deploy Alloy to each workload cluster:
```bash
cd workload-cluster
# Update placeholders
kubectl apply -f .
```

### 2. Management Cluster
Deploy Argo Events + triage workflow:
```bash
cd management-cluster
# Update placeholders
kubectl apply -f .
```

## Configuration

### Placeholders - Workload Clusters

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{CLUSTER_NAME}}` | Workload cluster name | `aks-prod-uksouth-001` |
| `{{ENVIRONMENT}}` | Environment tag | `prod` / `staging` |
| `{{AZURE_REGION}}` | Azure region | `uksouth` |
| `{{EVENTHUB_NAMESPACE}}` | Event Hub namespace | `evh-platform-prod` |
| `{{EVENTHUB_NAME}}` | Event Hub name | `k8s-events` |
| `{{EVENTHUB_CONNECTION_STRING}}` | Shared Access Key connection string | `{{EVENTHUB_CONNECTION_STRING}}` |

### Placeholders - Management Cluster

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{MGMT_CLUSTER_NAME}}` | Management cluster name | `aks-mgmt-uksouth-001` |
| `{{EVENTHUB_NAMESPACE}}` | Event Hub namespace | `evh-platform-prod` |
| `{{EVENTHUB_NAME}}` | Event Hub name | `k8s-events` |
| `{{EVENTHUB_CONSUMER_GROUP}}` | Consumer group for this mgmt cluster | `$Default` or `mgmt-triage` |
| `{{KEY_VAULT_NAME}}` | Azure Key Vault | `kv-platform-mgmt` |
| `{{MANAGED_IDENTITY_CLIENT_ID}}` | Workload Identity client ID | `xxxxxxxx-xxxx-...` |
| `{{TELEGRAM_BOT_TOKEN}}` | Telegram bot token | (from Key Vault) |
| `{{TELEGRAM_CHAT_ID}}` | Telegram chat/channel ID | `-100xxxxxxxxxx` |

## Files

### workload-cluster/
| File | Purpose |
|------|---------|
| `01-namespace.yaml` | Monitoring namespace |
| `02-alloy-config.yaml` | Alloy → Event Hub configuration |
| `03-alloy-deployment.yaml` | Alloy deployment + RBAC |
| `04-alloy-secret.yaml` | Event Hub connection string (template) |

### management-cluster/
| File | Purpose |
|------|---------|
| `01-namespace.yaml` | argo-events namespace |
| `02-argo-events-install.sh` | Argo Events installation script |
| `03-eventbus.yaml` | NATS EventBus |
| `04-external-secrets.yaml` | Key Vault integration for secrets |
| `05-eventsource-eventhub.yaml` | Event Hub subscription |
| `06-workflow-template.yaml` | Triage workflow with Telegram |
| `07-sensor.yaml` | Event → Workflow routing |

## Migration from Fluent Bit

### What changes
- Replace Fluent Bit DaemonSet with Alloy Deployment
- Alloy uses `loki.source.kubernetes_events` (native K8s event watching)
- Same Event Hub destination, different producer

### What stays the same
- Event Hub topic and schema
- Downstream consumers (management cluster)
- Alert routing and triage logic

### Rollout strategy
1. Deploy Alloy alongside Fluent Bit (both producing to Event Hub)
2. Verify events arriving from Alloy
3. Remove Fluent Bit DaemonSet

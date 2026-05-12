# Sensors Catalog

All Argo Events `Sensor` resources in this repository, grouped by purpose.

> **Safeguards:** See `agents/kagent-triage/SENSOR-SAFEGUARDS.md` for rate-limiting and deduplication patterns that should be applied to all sensors.

## kagent-triage Sensors (per-namespace, homelab)

| Sensor Name | Namespace | File | Trigger Purpose |
|-------------|-----------|------|-----------------|
| `kagent-triage-sensor` | `argo-events` | `agents/kagent-triage/03-sensor-kagent-triage.yaml` | kagent-triage-trigger |
| `kagent-triage-cert-manager` | `argo-events` | `agents/kagent-triage/cert-manager-sensor.yaml` | kagent-triage-cert-manager |
| `kagent-triage-external-secrets` | `argo-events` | `agents/kagent-triage/external-secrets-sensor.yaml` | kagent-triage-external-secrets |
| `kagent-triage-kro` | `argo-events` | `agents/kagent-triage/kro-sensor.yaml` | kagent-triage-kro |
| `kagent-triage-kyverno` | `argo-events` | `agents/kagent-triage/kyverno-sensor.yaml` | kagent-triage-kyverno |
| `kagent-triage-reloader` | `argo-events` | `agents/kagent-triage/reloader-sensor.yaml` | kagent-triage-reloader |
| `kagent-triage-test-ns` | `argo-events` | `agents/kagent-triage/test-ns-sensor.yaml` | kagent-triage-test-ns |

## kagent-triage Sensors (per-namespace, AKS worker-cluster-bundle)

| Sensor Name | Namespace | File | Trigger Purpose |
|-------------|-----------|------|-----------------|
| `kagent-triage-sensor` | `argo-events` | `agents/kagent-triage/worker-cluster-bundle/03-sensor-generic.yaml` | kagent-triage-trigger |
| `kagent-triage-cert-manager` | `argo-events` | `agents/kagent-triage/worker-cluster-bundle/sensor-cert-manager.yaml` | kagent-triage-cert-manager |
| `kagent-triage-external-secrets` | `argo-events` | `agents/kagent-triage/worker-cluster-bundle/sensor-external-secrets.yaml` | kagent-triage-external-secrets |
| `kagent-triage-flux-system` | `argo-events` | `agents/kagent-triage/worker-cluster-bundle/sensor-flux-system.yaml` | kagent-triage-flux-system |
| `kagent-triage-gatekeeper-system` | `argo-events` | `agents/kagent-triage/worker-cluster-bundle/sensor-gatekeeper-system.yaml` | kagent-triage-gatekeeper-system |
| `kagent-triage-aks-istio-ingress` | `argo-events` | `agents/kagent-triage/worker-cluster-bundle/sensor-istio-ingress.yaml` | kagent-triage-aks-istio-ingress |
| `kagent-triage-aks-istio-system` | `argo-events` | `agents/kagent-triage/worker-cluster-bundle/sensor-istio-system.yaml` | kagent-triage-aks-istio-system |
| `kagent-triage-kro` | `argo-events` | `agents/kagent-triage/worker-cluster-bundle/sensor-kro.yaml` | kagent-triage-kro |
| `kagent-triage-kube-system` | `argo-events` | `agents/kagent-triage/worker-cluster-bundle/sensor-kube-system.yaml` | kagent-triage-kube-system |
| `kagent-triage-kyverno` | `argo-events` | `agents/kagent-triage/worker-cluster-bundle/sensor-kyverno.yaml` | kagent-triage-kyverno |
| `kagent-triage-reloader` | `argo-events` | `agents/kagent-triage/worker-cluster-bundle/sensor-reloader.yaml` | kagent-triage-reloader |
| `kagent-triage-test-ns` | `argo-events` | `agents/kagent-triage/worker-cluster-bundle/sensor-test-ns.yaml` | kagent-triage-test-ns |

## kagent-triage Sensors (AKS namespaces)

| Sensor Name | Namespace | File | Trigger Purpose |
|-------------|-----------|------|-----------------|
| `kagent-triage-flux-system` | `argo-events` | `agents/kagent-triage/aks/flux-system-sensor.yaml` | kagent-triage-flux-system |
| `kagent-triage-gatekeeper-system` | `argo-events` | `agents/kagent-triage/aks/gatekeeper-system-sensor.yaml` | kagent-triage-gatekeeper-system |
| `kagent-triage-aks-istio-ingress` | `argo-events` | `agents/kagent-triage/aks/istio-ingress-sensor.yaml` | kagent-triage-aks-istio-ingress |
| `kagent-triage-aks-istio-system` | `argo-events` | `agents/kagent-triage/aks/istio-system-sensor.yaml` | kagent-triage-aks-istio-system |
| `kagent-triage-kube-system` | `argo-events` | `agents/kagent-triage/aks/kube-system-sensor.yaml` | kagent-triage-kube-system |

## Observability / EventHub Pipeline Sensors

| Sensor Name | Namespace | File | Trigger Purpose |
|-------------|-----------|------|-----------------|
| `k8s-event-triage` | `argo-events` | `observability/alloy-eventhub-pipeline/03-sensor.yaml` | triage-workflow |
| `k8s-event-triage` | `argo-events` | `observability/alloy-eventhub-pipeline/management-cluster/07-sensor.yaml` | triage-workflow |
| `k8s-triage-critical` | `argo-events` | `observability/alloy-eventhub-pipeline/tier-critical/sensor.yaml` | critical-triage |
| `k8s-triage-infra` | `argo-events` | `observability/alloy-eventhub-pipeline/tier-infra/sensor.yaml` | infra-triage |
| `k8s-triage-warnings` | `argo-events` | `observability/alloy-eventhub-pipeline/tier-warnings/sensor.yaml` | warning-triage |

## Observability / AlertManager + Webhook Hub Sensors

| Sensor Name | Namespace | File | Trigger Purpose |
|-------------|-----------|------|-----------------|
| `alertmanager-triage-sensor` | `argo-events` | `observability/prometheus-alertmanager/05-sensor.yaml` | triage-workflow |
| `alertmanager-triage-sensor` | `argo-events` | `observability/prometheus-alertmanager/enhanced/05-sensor.yaml` | alertmanager-triage-workflow |
| `alertmanager-resolved-sensor` | `argo-events` | `observability/prometheus-alertmanager/enhanced/05-sensor.yaml` | alertmanager-resolved-notification |
| `alloy-poc-sensor` | `argo-events` | `observability/managed-lgtm-integration/alloy-direct-poc/02-sensor.yaml` | alloy-poc-echo-workflow |
| `webhook-hub-ai-triage-sensor` | `argo-events` | `observability/managed-lgtm-integration/webhook-hub/07-sensor-ai-triage.yaml` | trigger-ai-triage |
| `webhook-hub-team-x-slack-sensor` | `argo-events` | `observability/managed-lgtm-integration/webhook-hub/08-sensor-slack-example.yaml` | trigger-slack |

## Platform Sensors (auto-healer, GitLab, app-onboarding, HITL)

| Sensor Name | Namespace | File | Trigger Purpose |
|-------------|-----------|------|-----------------|
| `auto-healer-sensor` | `argo-events` | `platform/argo-events/sources/auto-healer/sensor.yaml` | trigger-healer |
| `demo-autohealer-sensor` | `argo-events` | `platform/argo-events/sources/auto-healer/demos/00-sensor-demo.yaml` | trigger-demo-healer |
| `byo-kagent-sensor` | `argo-events` | `platform/argo-events/sources/gitlab/byo-kagent/byo-kagent-sensor.yaml` | trigger-agent-onboarding, trigger-mcp-onboarding |
| `alertmanager-kafka` | `kagent-poc` | `platform/argo-events/sources/alertmanager-redpanda/sensor.yaml` | alertmanager-kafka-consumer |
| `alertmanager-webhook` | `kagent-poc` | `platform/argo-events/sources/webhook/sensor.yaml` | alertmanager-webhook-consumer |
| `app-onboarding-sensor` | `argo-events` | `platform/argo-workflows/templates/app-onboarding/app-onboarding-sensor.yaml` | app-onboarding-trigger |
| `teams-hitl-sensor` | `argo-events` | `platform/teams-hitl/sensor.yaml` | resume-on-approve, stop-on-reject, stop-on-expire |

---

**Total: 42 sensors**

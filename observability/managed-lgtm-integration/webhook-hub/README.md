# Central Webhook Hub — example build

Self-contained YAML for the Hub design described in `../CENTRAL-WEBHOOK-HUB.md`.

## What's here

```
webhook-hub/
├── README.md                          ← this file
├── 00-namespace.yaml                  ← namespace + label
├── 01-secrets.yaml                    ← bearer token placeholder
├── 02-rbac.yaml                       ← ServiceAccount + RBAC for Sensors/Workflows
├── 03-eventsource.yaml                ← Argo Events webhook (port 12000, /inbound)
├── 04-istio-virtualservice.yaml       ← Istio Gateway → EventSource Service
├── 05-istio-authorization-policy.yaml ← source-IP + bearer header + default DENY
├── 06-workflow-template-triage.yaml   ← kagent triage workflow (subscriber action)
├── 07-sensor-ai-triage.yaml           ← Subscriber 1 — AI triage
├── 08-sensor-slack-example.yaml       ← Subscriber 2 — team-X Slack
└── deploy.sh                          ← ordered apply with prereq checks
```

## Prerequisites

- Argo Events installed in `argo-events` (controller + EventBus). Reuses the existing setup from `../../prometheus-alerting/`.
- Argo Workflows installed in `argo`.
- Istio AKS add-on or upstream Istio with a shared wildcard Gateway (e.g. in `aks-istio-ingress`). Skip Istio files if running on a non-AKS cluster — see `../OPTION-A-README.md` for the nginx-ingress alternative.
- ConfigMaps `kagent-config` and `mattermost-webhook-config` already in `argo-events` from earlier work. Slack subscriber additionally needs `slack-webhook-config-team-x`.

## Quick start

```bash
# 1. Generate the bearer token Grafana will send
TOKEN=$(openssl rand -hex 32)
kubectl create secret generic webhook-hub-token \
  --namespace argo-events \
  --from-literal=token="${TOKEN}"

# 2. Edit istio files — replace placeholders with your wildcard hostname / Gateway
$EDITOR 04-istio-virtualservice.yaml
$EDITOR 05-istio-authorization-policy.yaml

# 3. Deploy
chmod +x deploy.sh
./deploy.sh --context <kube-context>

# 4. Smoke test — should return 200 OK and create a Workflow
curl -X POST https://webhook-hub.<your-domain>/inbound \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d @../../prometheus-alerting/test-payload-firing.json   # any AM-shaped payload

# 5. Verify
kubectl get workflows -n argo-events -l hub-subscriber=ai-triage --sort-by=.metadata.creationTimestamp
```

## Adding a new subscriber

Copy `08-sensor-slack-example.yaml`, rename it, change:
- `metadata.name` — unique Sensor name
- `dependencies[0].filters.data` — your label match (alertname, team, severity, namespace)
- `triggers[0].template` — your action (Workflow ref, HTTP, Slack, etc.)

Apply, done. No changes to the EventSource, ingress, or auth — they're shared infrastructure.

## What this folder is not

This is example code for the PoC, not a production Helm chart. The replication kit (Helm chart / KRO ResourceGraph for new subscribers) is Week 4 of the PoC plan in `../CENTRAL-WEBHOOK-HUB.md`.

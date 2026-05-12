---
name: kagent-namespace-agent
description: Create, deploy, and test kagent AI agents for Kubernetes namespace triage. Use when adding a new namespace to the kagent triage pipeline, creating namespace-specific diagnostic agents, or wiring up Argo Events sensors to route K8s events to kagent agents.
metadata:
  openclaw:
    emoji: "🤖"
    requires:
      anyBins: ["kubectl", "curl"]
---

# kagent Namespace Agent Skill

Create and deploy kagent AI agents for Kubernetes namespace-specific triage.
Each namespace gets its own agent with domain-specific knowledge, wired into the Argo Events pipeline.

## Quick Start

```bash
# Create a new namespace agent (interactive)
~/clawd/skills/kagent-namespace-agent/scripts/create-agent.sh --namespace cert-manager --description "TLS certificate lifecycle management"

# Create + deploy + test in one go
~/clawd/skills/kagent-namespace-agent/scripts/create-agent.sh --namespace cert-manager --description "TLS certificate lifecycle management" --deploy --test
```

## What It Does

1. **Generates a kagent Agent CR** with a namespace-specialised system prompt
2. **Generates an Argo Sensor** that routes K8s warning events from that namespace to the agent
3. **Deploys both** to the Kind cluster
4. **Tests the agent** by sending a diagnostic query via the kagent controller API
5. **Outputs portable YAML** that can be lifted to AKS (just swap EventSource)

## Architecture

```
K8s Warning Event (namespace X)
  → EventSource (k8s-warning-events, cluster-wide)
  → Sensor (filters namespace == X)
  → Argo WorkflowTemplate (kagent-triage)
  → kagent Agent (X-agent) via REST API
  → Diagnosis + Telegram notification
```

## Templates

All templates are in `templates/` directory:
- `agent.yaml.tmpl` — kagent Agent CR template
- `sensor.yaml.tmpl` — Argo Sensor CR template
- `test-error.yaml.tmpl` — Error injection manifest for testing

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--namespace` | Yes | Target K8s namespace to create agent for |
| `--description` | Yes | Domain description (e.g., "TLS certificate management") |
| `--context` | No | kubectl context (default: {{CLUSTER_NAME}}) |
| `--kagent-ns` | No | kagent namespace (default: kagent) |
| `--model-config` | No | ModelConfig name (default: default-model-config) |
| `--deploy` | No | Deploy immediately after generation |
| `--test` | No | Run E2E test after deployment |
| `--output-dir` | No | Output directory (default: current dir) |

## Adding a New Namespace Agent

### Step 1: Generate the manifests
```bash
./scripts/create-agent.sh \
  --namespace cert-manager \
  --description "TLS certificate lifecycle management using cert-manager. Handles Certificate, Issuer, ClusterIssuer, CertificateRequest resources. Common issues: failed ACME challenges, expired certificates, issuer not ready, secret not found."
```

### Step 2: Review and deploy
```bash
kubectl apply -f cert-manager-agent.yaml
kubectl apply -f cert-manager-sensor.yaml
```

### Step 3: Test
```bash
# Inject a test error
kubectl apply -f cert-manager-test-error.yaml

# Watch for the workflow trigger
kubectl get workflows -n argo-events -w

# Check kagent UI for the conversation
```

## Lift-and-Shift to AKS

When moving to AKS, change:
1. **EventSource**: Replace `k8s-warning-events` with Event Hub consumer EventSource
2. **Secrets**: Update Telegram bot token secret reference
3. **ModelConfig**: Point to Azure OpenAI or your preferred provider
4. **IngressRoute**: Replace Traefik with Azure Application Gateway / Ingress

The Agent CRs and Sensors are portable as-is.

## Prerequisites

- kagent installed on the cluster (v0.8.0+)
- Argo Workflows + Argo Events running
- EventBus (NATS) configured
- k8s-warning-events EventSource watching all namespaces
- kagent-triage WorkflowTemplate deployed (see /home/david/repos/argo-workflow/kagent-triage/)

# MIL-126: A2A + HITL + Skills Demo

This bundle is the end-to-end MIL-126 demonstration:

1. `demo-a2a-coordinator-agent` receives the request.
2. It calls `demo-skill-loader-agent` over kagent Agent-as-tool A2A and gets the loaded skill list.
3. It calls `demo-hitl-approval-agent` over A2A to produce a human approval packet.
4. The Argo workflow posts that packet to the mock Teams bot and suspends.
5. A human approval callback resumes the workflow.
6. The workflow calls the coordinator again with `human decision: approved`.

The demo is intentionally safe: the remediation action is a string in the approval request. No cluster-changing command is executed.

## Agents

| Agent | Role | A2A skills exposed |
|---|---|---|
| `demo-a2a-coordinator-agent` | Front door and orchestrator | `a2a-hitl-skills-demo` |
| `demo-skill-loader-agent` | Demonstrates skill loading | `k8s-troubleshooter`, `byoa-agent-builder`, `fleet-health` |
| `demo-hitl-approval-agent` | Converts remediation into an approval request | `human-approval-gate` |

## Run

Prerequisites:

- kagent in the `kagent` namespace with `default-model-config`
- Argo Workflows in the `argo` namespace
- Argo Events in the `argo-events` namespace
- `kubectl`, `argo`, and `jq` locally

```bash
a2a/kagent-hitl-skills-demo/scripts/run-demo.sh
```

The script applies only demo-scoped kagent Agents, the Teams HITL EventSource/Sensor, and a dev-only mock bot in `argo`. It then submits `workflow.yaml`, waits for the suspend node, approves through the mock bot, and verifies the workflow succeeds.

To run against a non-current context or a specific model config:

```bash
KUBE_CONTEXT=proxmox-k8s MODEL_CONFIG=litellm-qwen-14b \
  a2a/kagent-hitl-skills-demo/scripts/run-demo.sh
```

`MODEL_CONFIG` defaults to `default-model-config`. On the Proxmox/home-lab cluster, `litellm-qwen-14b` points at the local Qwen model.

## Manual A2A Check

```bash
kubectl apply -f a2a/kagent-hitl-skills-demo/agents.yaml
kubectl wait --for=condition=Ready -n kagent \
  agent/demo-skill-loader-agent \
  agent/demo-hitl-approval-agent \
  agent/demo-a2a-coordinator-agent \
  --timeout=240s

kubectl port-forward -n kagent svc/demo-a2a-coordinator-agent 19091:8080
```

```bash
curl -sS -X POST http://localhost:19091/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "mil-126-manual",
    "method": "message/send",
    "params": {
      "message": {
        "messageId": "mil-126-manual-1",
        "role": "user",
        "parts": [{
          "kind": "text",
          "text": "Scenario: demo CrashLoopBackOff. Proposed action: kubectl rollout restart deploy/example-api -n demo. Human decision: not approved yet. Load skills and ask for HITL approval."
        }]
      }
    }
  }' | jq .
```

Expected response markers:

- `A2A_CALLS: skill-loader, hitl-approval`
- `SKILLS_LOADED`
- `APPROVAL_REQUIRED: yes`
- `WAITING_ON: human approval callback`

## Cleanup

```bash
kubectl delete -f a2a/kagent-hitl-skills-demo/workflow.yaml --ignore-not-found
kubectl delete -f a2a/kagent-hitl-skills-demo/mock-bot-runtime.yaml --ignore-not-found
kubectl delete -f a2a/kagent-hitl-skills-demo/workflow-rbac.yaml --ignore-not-found
kubectl delete configmap mock-bot-src -n argo --ignore-not-found
kubectl delete -f a2a/kagent-hitl-skills-demo/agents.yaml --ignore-not-found
```

The Teams HITL EventSource and Sensors are shared platform components, so the default cleanup leaves them in place. If this demo installed them only for a throwaway cluster, remove them too:

```bash
kubectl delete -f platform/teams-hitl/sensor.yaml --ignore-not-found
kubectl delete -f platform/teams-hitl/eventsource.yaml --ignore-not-found
```

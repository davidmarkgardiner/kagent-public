# LitmusChaos to Argo Events to kagent Triage

This POC wires LitmusChaos `ChaosResult` updates into the existing `kind-homelab` Argo Events and kagent triage path.

## Components

- `manifests/chaos-target.yaml`: `chaos-demo/chaos-target`, a two-replica HTTP echo workload.
- `manifests/litmus-rbac.yaml`: service account and RBAC used by Litmus runner jobs in `chaos-demo`.
- `manifests/argo-events-litmus-rbac.yaml`: watch permissions for `argo-events/argo-events-sa` on Litmus CRDs.
- `experiments/*.yaml`: ChaosHub Kubernetes experiments plus `ChaosEngine` triggers for `pod-delete`, `pod-network-latency`, and `pod-cpu-hog`.
- `manifests/eventsource-litmus.yaml`: Argo Events resource EventSource watching Litmus `ChaosResult` resources.
- `manifests/sensor-litmus-triage.yaml`: Sensor that invokes `kagent/chaos-triage-agent` and writes an audit/remediation trail.
- `manifests/modelconfig-qwen.yaml` and `manifests/agent-chaos-triage.yaml`: Qwen/OpenRouter model config and chaos triage agent definition.

## Install

```bash
helm repo add litmuschaos https://litmuschaos.github.io/litmus-helm/
helm repo update litmuschaos

helm upgrade --install chaos litmuschaos/litmus \
  --namespace litmus \
  --create-namespace

helm upgrade --install litmus-core litmuschaos/litmus-core \
  --namespace litmus \
  --set policies.monitoring.disabled=true \
  --set resources.requests.cpu=200m \
  --set resources.requests.memory=256Mi \
  --set resources.limits.cpu=500m \
  --set resources.limits.memory=512Mi

helm upgrade --install litmus-kubernetes-chaos litmuschaos/kubernetes-chaos \
  --namespace chaos-demo \
  --create-namespace \
  --set environment.runtime=containerd \
  --set environment.socketPath=/run/containerd/containerd.sock
```

The `litmus` chart installs ChaosCenter. The `litmus-core` chart installs the operator and CRDs. The `kubernetes-chaos` chart installs the ChaosHub Kubernetes experiments used here.

## OpenRouter Secret

The Qwen model config expects this secret in `kagent`:

```bash
kubectl create secret generic openrouter-api-key \
  -n kagent \
  --from-literal=OPENROUTER_API_KEY="$OPENROUTER_API_KEY"
```

The default model is `qwen/qwen3-next-80b-a3b-instruct:free` so the demo does not require paid OpenRouter credits. If that shared free route is rate-limited, set `spec.model` in `manifests/modelconfig-qwen.yaml` to a funded Qwen model before rerunning.

## Run

```bash
./chaos/litmus/run-demo.sh
```

The script applies the target and manifests, runs `pod-delete` and `pod-cpu-hog`, waits for each triage workflow to succeed, tails Argo Events and kagent logs, prints `ChaosResult` state, and starts a ChaosCenter UI port-forward at `http://localhost:9091`. Triage workflows are created in the `argo` namespace.

## Expected Evidence

```bash
kubectl get pods -n litmus
kubectl get chaosresult -n chaos-demo -o wide
kubectl logs -n argo-events -l eventsource-name=litmus-chaos-events --tail=80
kubectl logs -n argo-events -l sensor-name=kagent-triage-litmus --tail=120
kubectl get workflows -n argo -l app.kubernetes.io/name=kagent-triage-litmus
kubectl logs -n kagent -l app.kubernetes.io/name=chaos-triage-agent --tail=120
```

Successful triage workflows annotate `deployment/chaos-target` with the last Litmus result, ensure two replicas, and write an incident entry to `configmap/kagent/chaos-triage-hive-mind`.

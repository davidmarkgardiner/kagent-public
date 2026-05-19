# Ring-Fenced Cluster Install Guide: LitmusChaos to Argo Events to kagent

This guide is the sanitized install handoff for deploying the same chaos engineering path in a ring-fenced cluster.

It covers:

- LitmusChaos Helm charts and versions used in the local validation run.
- Images to mirror or swap to an approved private registry.
- Security contexts and resource limits that must stay in place.
- The kagent, Argo Events, and workflow resources needed to replicate the demo.
- Evidence captured from the local validation run.

## Validated versions

| Component | Chart | Version used |
| --- | --- | --- |
| ChaosCenter | `litmuschaos/litmus` | `3.28.0` |
| Litmus core operator / CRDs | `litmuschaos/litmus-core` | `3.28.1` |
| Kubernetes ChaosHub experiments | `litmuschaos/kubernetes-chaos` | `3.28.1` |
| Litmus app images | upstream app version | `3.28.0` |

## Prerequisites

- Kubernetes cluster with Argo Events, Argo Workflows, kagent, and the kagent CRDs already installed.
- A kagent-compatible OpenAI endpoint or private model endpoint. The local
  validation run used Qwen through KubeAI. For another environment, replace
  `manifests/modelconfig-qwen.yaml` with the approved model endpoint and secret
  reference.
- Private image mirror access for all images listed below.
- A namespace selected for chaos experiments. The examples use `chaos-demo` only.
- Approval from the cluster owner before enabling network or node-level chaos.

## Files added for ring-fenced deployment

```text
chaos/litmus/
|-- WORK-INSTALL.md
|-- evidence/chaos-eval-2026-05-18.md
|-- scripts/chaos-eval-poc.py
`-- values/
    |-- litmus-values-work.yaml
    |-- litmus-core-values-work.yaml
    `-- kubernetes-chaos-values-work.yaml
```

## Images to mirror or swap

Replace `registry.example.invalid/mirror` in the values files with the approved private registry path (`{{INTERNAL_REGISTRY}}`).

### Litmus ChaosCenter

```text
litmuschaos/litmusportal-frontend:3.28.0
litmuschaos/litmusportal-server:3.28.0
litmuschaos/litmusportal-auth-server:3.28.0
litmuschaos/litmusportal-subscriber:3.28.0
litmuschaos/litmusportal-event-tracker:3.28.0
litmuschaos/chaos-operator:3.28.0
litmuschaos/chaos-runner:3.28.0
litmuschaos/chaos-exporter:3.28.0
mongo:6
bitnamilegacy/mongodb:8.0.13-debian-12-r0
bitnamilegacy/os-shell:12-debian-12-r51
argoproj/workflow-controller:v3.3.1
argoproj/argoexec:v3.3.1
```

### Litmus core and experiments

```text
litmuschaos/chaos-operator:3.28.0
litmuschaos/chaos-runner:3.28.0
litmuschaos/chaos-exporter:3.28.0
litmuschaos/go-runner:3.28.0
litmuschaos/ansible-runner:3.28.0
```

### Demo target and Argo workflow scripts

```text
hashicorp/http-echo:1.0.0
python:3.11-slim
bitnami/kubectl:1.30.7
```

## Install commands

Do not run the local validation `run-demo.sh` directly in another cluster until
the image registry, model endpoint, namespaces, RBAC, and experiment scope are
reviewed.

```bash
helm repo add litmuschaos https://litmuschaos.github.io/litmus-helm/
helm repo update litmuschaos

kubectl create namespace litmus --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace chaos-demo --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install chaos litmuschaos/litmus \
  --namespace litmus \
  --version 3.28.0 \
  --values chaos/litmus/values/litmus-values-work.yaml

helm upgrade --install litmus-core litmuschaos/litmus-core \
  --namespace litmus \
  --version 3.28.1 \
  --values chaos/litmus/values/litmus-core-values-work.yaml

helm upgrade --install litmus-kubernetes-chaos litmuschaos/kubernetes-chaos \
  --namespace chaos-demo \
  --version 3.28.1 \
  --values chaos/litmus/values/kubernetes-chaos-values-work.yaml
```

## Apply the kagent and Argo Events integration

Review `manifests/modelconfig-qwen.yaml` first. Replace the endpoint and secret reference with approved environment-specific values.

```bash
kubectl apply -f chaos/litmus/manifests/chaos-target.yaml
kubectl apply -f chaos/litmus/manifests/litmus-rbac.yaml
kubectl apply -f chaos/litmus/manifests/argo-events-litmus-rbac.yaml
kubectl apply -f chaos/litmus/manifests/modelconfig-qwen.yaml
kubectl apply -f chaos/litmus/manifests/agent-chaos-triage.yaml
kubectl apply -f chaos/litmus/manifests/eventsource-litmus.yaml
kubectl apply --server-side --force-conflicts -f chaos/litmus/manifests/sensor-litmus-triage.yaml
```

## Security and resource controls

The ring-fenced values and manifests now include the controls that were missing from the original public repo snapshot:

- Chart resource requests and limits for Litmus frontend, API, auth server, MongoDB wait init container, operator, and exporter.
- Restricted container security contexts where the upstream chart exposes them:
  - `runAsNonRoot: true`
  - `allowPrivilegeEscalation: false`
  - `readOnlyRootFilesystem: true` where compatible
  - `capabilities.drop: ["ALL"]`
  - `seccompProfile.type: RuntimeDefault`
- `automountServiceAccountToken: false` on ChaosCenter frontend/API/auth containers where supported.
- Pinned Argo workflow helper images instead of `latest`.
- Resource requests and limits on Argo workflow script templates.
- Restricted demo target pod security context and no service account token mount.
- Node-level Litmus experiments disabled in `kubernetes-chaos-values-work.yaml` by default.

Important caveat: some Litmus chaos jobs require elevated permissions or runtime access depending on the experiment. Keep them isolated to a dedicated namespace and do not enable node-level experiments on a shared cluster without a formal change window.

## RBAC scope

The example keeps `chaos-demo` as the only target namespace. The kagent chaos triage agent is instructed not to modify resources outside `chaos-demo`.

Before deployment, review:

- `manifests/litmus-rbac.yaml`: Litmus runner permissions for the experiment namespace.
- `manifests/argo-events-litmus-rbac.yaml`: Argo Events watch and bounded remediation permissions.
- `manifests/agent-chaos-triage.yaml`: kagent tools and safety instructions.

## Validation commands

Render the charts before deployment:

```bash
helm template chaos litmuschaos/litmus \
  --namespace litmus \
  --version 3.28.0 \
  --values chaos/litmus/values/litmus-values-work.yaml >/tmp/litmus-rendered.yaml

helm template litmus-core litmuschaos/litmus-core \
  --namespace litmus \
  --version 3.28.1 \
  --values chaos/litmus/values/litmus-core-values-work.yaml >/tmp/litmus-core-rendered.yaml

helm template litmus-kubernetes-chaos litmuschaos/kubernetes-chaos \
  --namespace chaos-demo \
  --version 3.28.1 \
  --values chaos/litmus/values/kubernetes-chaos-values-work.yaml >/tmp/kubernetes-chaos-rendered.yaml
```

Check the integration after deployment:

```bash
kubectl get pods -n litmus
kubectl get pods -n chaos-demo
kubectl get eventsource -n argo-events litmus-chaos-events
kubectl get sensor -n argo-events kagent-triage-litmus
kubectl get agent -n kagent chaos-triage-agent
kubectl get chaosresult -n chaos-demo -o wide
kubectl get workflows -n argo -l app.kubernetes.io/name=kagent-triage-litmus
```

## Test Scenarios And Agent Loop

Start with these scenarios:

1. `pod-delete`: proves the Litmus runner can disrupt the sample workload and
   that kagent receives a `ChaosResult` event.
2. `pod-cpu-hog`: proves sustained pressure signals still flow through Argo
   Events and the triage workflow.
3. `pod-network-latency`: keep disabled until network-chaos scope is approved
   for the target namespace.

The loop to observe is:

```text
Litmus ChaosEngine
  -> ChaosResult
  -> Argo Events EventSource
  -> Sensor-created Argo Workflow
  -> kagent chaos-triage-agent
  -> deployment annotation plus chaos-triage-hive-mind ConfigMap entry
```

For self-learning experiments, keep the first iteration observe-only: write the
agent's hypothesis, commands, and recommended remediation into the hive-mind
ConfigMap or another approved evidence store. Only enable automated remediation
after the recommendations have been reviewed and scoped to the `chaos-demo`
namespace.

## Tomorrow Pickup Checklist

1. Replace `registry.example.invalid/mirror` in `values/*.yaml` with
   `{{INTERNAL_REGISTRY}}`.
2. Replace `manifests/modelconfig-qwen.yaml` with the approved model endpoint
   and secret reference.
3. Render all three Helm charts with the provided values files.
4. Apply Litmus, the sample target, RBAC, EventSource, Sensor, and kagent agent
   manifests.
5. Run `pod-delete`, then `pod-cpu-hog`.
6. Capture `ChaosResult`, Argo workflow phase, kagent logs, deployment
   annotations, and `configmap/kagent/chaos-triage-hive-mind`.

## Local Validation Evidence

The sanitized run report is committed at:

```text
chaos/litmus/evidence/chaos-eval-2026-05-18.md
```

Summary:

- Overall health score: `0.95 / 1.0`
- `pod_restart`: k8s-agent recovered in `151.5s`
- `scale_zero_restore`: chaos-triage-agent restored in `121.2s`
- `clickhouse_outage`: ClickHouse restored in `5.1s`, Langfuse web remained healthy

The evaluation script is committed at:

```text
chaos/litmus/scripts/chaos-eval-poc.py
```

The raw local run log was intentionally not committed to the public repo.

# LitmusChaos to Argo Events to kagent Triage

This POC wires LitmusChaos `ChaosResult` updates into a Kubernetes Argo Events
and kagent triage path.

## Components

- `manifests/chaos-target.yaml`: `chaos-demo/chaos-target`, a two-replica HTTP echo workload.
- `manifests/litmus-rbac.yaml`: service account and RBAC used by Litmus runner jobs in `chaos-demo`.
- `manifests/argo-events-litmus-rbac.yaml`: watch permissions for `argo-events/argo-events-sa` on Litmus CRDs.
- `experiments/*.yaml`: ChaosHub Kubernetes experiments plus `ChaosEngine` triggers for `pod-delete`, `pod-network-latency`, and `pod-cpu-hog`.
- `manifests/eventsource-litmus.yaml`: Argo Events resource EventSource watching Litmus `ChaosResult` resources.
- `manifests/sensor-litmus-triage.yaml`: Sensor that invokes `kagent/chaos-triage-agent` and writes an audit/remediation trail.
- `manifests/modelconfig-qwen.yaml` and `manifests/agent-chaos-triage.yaml`: local Qwen/KubeAI model config and chaos triage agent definition.

## Ring-fenced cluster deployment

For a ring-fenced cluster, use [`WORK-INSTALL.md`](./WORK-INSTALL.md). It
includes the exact Helm chart versions, private-registry image list, values
files to edit, resource limits, security contexts, RBAC review notes, and the
sanitized evidence from the local validation run.

## Image Mirror Scope

For the smallest useful LitmusChaos deployment, mirror only the core operator,
runner, and experiment image:

```text
litmuschaos/chaos-operator:3.28.0
litmuschaos/chaos-runner:3.28.0
litmuschaos/go-runner:3.28.0
```

If you deploy the sample workload from this repo, also mirror:

```text
hashicorp/http-echo:1.0.0
```

If you enable the Argo Events and kagent triage workflow, also mirror the helper
images used by `manifests/sensor-litmus-triage.yaml`:

```text
python:3.11-slim
bitnami/kubectl:1.30.7
```

The larger ChaosCenter image set in `WORK-INSTALL.md` is only needed when you
deploy the Litmus portal/UI. A base command-line or GitOps-run experiment path
can start with `litmus-core`, `kubernetes-chaos`, and one approved experiment.

## Local Validation Install

```bash
helm repo add litmuschaos https://litmuschaos.github.io/litmus-helm/
helm repo update litmuschaos

helm upgrade --install chaos litmuschaos/litmus \
  --namespace litmus \
  --create-namespace \
  --set 'portal.frontend.tolerations[0].key=node-role.kubernetes.io/control-plane' \
  --set 'portal.frontend.tolerations[0].operator=Exists' \
  --set 'portal.frontend.tolerations[0].effect=NoSchedule' \
  --set 'portal.server.tolerations[0].key=node-role.kubernetes.io/control-plane' \
  --set 'portal.server.tolerations[0].operator=Exists' \
  --set 'portal.server.tolerations[0].effect=NoSchedule' \
  --set mongodb.architecture=replicaset \
  --set mongodb.replicaCount=1 \
  --set mongodb.arbiter.enabled=false

helm upgrade --install litmus-core litmuschaos/litmus-core \
  --namespace litmus \
  --set policies.monitoring.disabled=true \
  --set resources.requests.cpu=200m \
  --set resources.requests.memory=256Mi \
  --set resources.limits.cpu=500m \
  --set resources.limits.memory=512Mi \
  --set 'tolerations[0].key=node-role.kubernetes.io/control-plane' \
  --set 'tolerations[0].operator=Exists' \
  --set 'tolerations[0].effect=NoSchedule'

helm upgrade --install litmus-kubernetes-chaos litmuschaos/kubernetes-chaos \
  --namespace chaos-demo \
  --create-namespace \
  --set environment.runtime=containerd \
  --set environment.socketPath=/run/containerd/containerd.sock
```

The `litmus` chart installs ChaosCenter with a one-member MongoDB replica set to
fit a small validation cluster while preserving the chart's expected database
endpoint. The `litmus-core` chart installs the operator and CRDs. The
`kubernetes-chaos` chart installs the ChaosHub Kubernetes experiments used here.

## Local Qwen Model

The Qwen model config is `litellm-qwen-14b` and points at the local KubeAI OpenAI-compatible endpoint:

```yaml
model: qwen3-14b
openAI:
  baseUrl: http://kubeai.kubeai.svc.cluster.local/openai/v1
```

On the validation Kubernetes cluster, verify the model is ready before running:

```bash
kubectl --context {{KUBE_CONTEXT}} get model qwen3-14b -n kubeai
kubectl --context {{KUBE_CONTEXT}} get modelconfig litellm-qwen-14b -n kagent
```

## Run

```bash
./chaos/litmus/run-demo.sh
```

The script uses the current kubectl context unless `KUBECTL_CONTEXT` is set. It
applies the target and manifests, runs `pod-delete` and `pod-cpu-hog`, waits for
each triage workflow to succeed, tails Argo Events and kagent logs, prints
`ChaosResult` state, and starts a ChaosCenter UI port-forward at
`http://localhost:9091`. Triage workflows are created in the `argo` namespace.

If an existing Litmus install was previously created with the default three-member MongoDB replica set, the script automatically resets the Litmus MongoDB workload and PVCs while downsizing it for this POC. Set `RESET_LITMUS_MONGODB=false` to preserve an existing ChaosCenter database.

If one worker is unstable during validation, set
`DEMO_AVOID_NODE={{NODE_NAME}}`; the script cordons that node for the run and
uncordons it on exit.

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

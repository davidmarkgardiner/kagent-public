# Preventing NAP Evictions for Long-Running Jobs

Audience: platform engineers, application teams, and SREs running batch or long-running workloads on AKS clusters with Node Auto-Provisioning.

Last updated: 2026-05-13

## 1. The Problem

AKS Node Auto-Provisioning (NAP) is managed Karpenter. It can remove or replace nodes when it finds a consolidation opportunity.

That is useful for cost and bin-packing, but it can surprise teams running long jobs:

- A pod is still doing work.
- The node looks underutilized.
- NAP decides the node can be consolidated.
- The pod is evicted and the job restarts or fails.

The issue is usually not that NAP is broken. It is that the workload has not told Karpenter it must run to completion, or it is running on a node pool whose disruption policy is too aggressive for batch work.

## 2. Key Point

There is not a global "only evict after all jobs finish" switch for every workload.

The practical control is workload and node-pool policy:

- Mark non-disruptable pods with `karpenter.sh/do-not-disrupt: "true"`.
- Put long-running jobs on a dedicated `NodePool`.
- Configure that pool with `consolidationPolicy: WhenEmpty`.
- Avoid Spot capacity for work that must finish.
- Treat `terminationGracePeriod` as a hard drain deadline that can eventually
  delete protected pods.

## 3. How NAP Disruption Works

NAP uses Karpenter concepts:

- `NodePool`: policy for provisioning and disrupting nodes.
- `AKSNodeClass`: Azure VM and kubelet settings.
- `NodeClaim`: the actual provisioned node claim.
- Pod resource requests: the scheduling signal NAP uses to pick VM capacity.

For voluntary disruption, Karpenter normally:

1. Finds nodes that are candidates for disruption.
2. Checks disruption budgets.
3. Simulates where the pods could go.
4. Starts replacements when needed.
5. Drains the node.
6. Deletes the node claim.

The important part: with `WhenEmptyOrUnderutilized`, a node with running pods can still become a consolidation candidate.

## 4. The Recommended Pattern

Use this combination for long-running jobs:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: long-running-task
spec:
  backoffLimit: 0
  template:
    metadata:
      annotations:
        karpenter.sh/do-not-disrupt: "true"
    spec:
      restartPolicy: Never
      containers:
        - name: worker
          image: example.azurecr.io/worker:latest
          resources:
            requests:
              cpu: "4"
              memory: 16Gi
            limits:
              cpu: "4"
              memory: 16Gi
```

Put the annotation on the pod template, not only the Job metadata.

## 5. Dedicated Batch NodePool

For batch work, prefer a specific pool:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-jobs
spec:
  weight: 60
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    expireAfter: Never
    budgets:
      - nodes: "1"
  template:
    metadata:
      labels:
        workload-type: batch
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values:
            - on-demand
        - key: kubernetes.io/os
          operator: In
          values:
            - linux
      taints:
        - key: workload-type
          value: batch
          effect: NoSchedule
      nodeClassRef:
        group: karpenter.azure.com
        kind: AKSNodeClass
        name: batch-azurelinux
```

Then target jobs to that pool:

```yaml
spec:
  template:
    spec:
      tolerations:
        - key: workload-type
          operator: Equal
          value: batch
          effect: NoSchedule
      nodeSelector:
        workload-type: batch
```

## 6. What This Does and Does Not Protect

Protected:

- Voluntary consolidation.
- Drift in the normal case, unless the NodeClaim has `terminationGracePeriod`
  configured.
- Routine NAP optimization decisions.

Not protected:

- Expiration.
- Node repair.
- VM failure.
- Azure maintenance events.
- Spot eviction.
- Manual `kubectl delete node`.
- Deleting the `NodePool`.
- Force deletion after a configured NodePool `terminationGracePeriod`.

## 7. Work Verification Plan

Use a non-production AKS cluster that already has NAP enabled.

Important: running workload tests against NAP can create or remove Azure VM capacity. Get approval for the test cluster, time window, quota impact, and expected cost before applying workload manifests.

### Phase 1: Read-only Baseline

```bash
kubectl config current-context
kubectl get nodepools -o wide
kubectl get nodes -L karpenter.sh/nodepool,workload-type
kubectl get pods --all-namespaces \
  -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,NODE:.spec.nodeName,DO_NOT_DISRUPT:.metadata.annotations.karpenter\.sh/do-not-disrupt' \
  | grep -v '<none>' || true
```

Expected result:

- You know which `NodePool` the current jobs use.
- You know whether `WhenEmptyOrUnderutilized` is enabled.
- You know whether the Job pod templates already carry `karpenter.sh/do-not-disrupt`.

### Phase 2: Manifest Validation

Validate manifests before applying anything:

```bash
kubectl apply --dry-run=server -f batch-nodepool.yaml
kubectl apply --dry-run=server -f long-running-job.yaml
```

Expected result:

- The API server accepts the manifests.
- No live resources are created by dry-run.

### Phase 3: Controlled Workload Test

After approval, apply a small long-running Job that fits the approved test budget:

```bash
kubectl create namespace nap-disruption-test
kubectl apply -n nap-disruption-test -f long-running-job.yaml
kubectl get pods -n nap-disruption-test -w
```

Expected result:

- The pod starts and shows the `karpenter.sh/do-not-disrupt` annotation.
- The pod remains running during consolidation checks.
- NAP does not voluntarily evict the pod before the job completes.

### Phase 4: Observe NAP

```bash
kubectl get events --all-namespaces --sort-by='.lastTimestamp' \
  | grep -Ei 'karpenter|disrupt|consolidat|drift|nodeclaim' \
  | tail -50

kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter -c controller --tail=200
```

Expected result:

- Karpenter logs show no voluntary disruption of the protected pod.
- Any skipped consolidation is explainable by the protected pod or `WhenEmpty` policy.

### Phase 5: Cleanup

```bash
kubectl delete namespace nap-disruption-test
kubectl get pods --all-namespaces | grep nap-disruption-test || true
```

Expected result:

- Test pods are gone.
- Empty NAP nodes are eligible for cleanup after `consolidateAfter`.

## 8. Decision Table

| Workload Type | Recommended Policy |
|---|---|
| Stateless replicated service | `WhenEmptyOrUnderutilized`, PDBs, multiple replicas |
| Long-running batch job | `WhenEmpty`, `do-not-disrupt`, on-demand nodes |
| ML training or non-idempotent processing | Dedicated batch pool, `expireAfter: Never`, no Spot |
| Cost-sensitive interruptible jobs | Spot pool, checkpointing, retries |
| Critical maintenance window | Temporary disruption budget with `nodes: "0"` |

## 9. Karpenter Cross-Check

Current upstream Karpenter documents these details:

- Default disruption policy is `WhenEmptyOrUnderutilized` with
  `consolidateAfter: 0s` if fields are not set.
- `WhenEmptyOrUnderutilized` can consider a node consolidatable after
  `consolidateAfter` even when it is not empty.
- `karpenter.sh/do-not-disrupt: "true"` is permanent protection for voluntary
  disruption, and duration values such as `"30m"` are supported.
- Protected pods exclude nodes from consolidation and conditionally exclude them
  from drift.
- `terminationGracePeriod` can bypass PDBs and `do-not-disrupt` once the node is
  draining.
- `do-not-disrupt` does not exclude nodes from forceful methods such as
  expiration, interruption, node repair, or manual deletion.

## 10. References

- AKS NAP overview: https://learn.microsoft.com/en-us/azure/aks/node-auto-provisioning
- AKS NAP disruption policies: https://learn.microsoft.com/en-us/azure/aks/node-auto-provisioning-disruption
- Karpenter disruption documentation: https://karpenter.sh/docs/concepts/disruption/

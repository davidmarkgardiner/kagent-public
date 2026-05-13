# NAP Disruption Policy for Long-Running Jobs

AKS Node Auto-Provisioning (NAP) is managed Karpenter. If a node pool uses
`consolidationPolicy: WhenEmptyOrUnderutilized`, NAP can decide that a node is
worth replacing or removing even while workload pods are still running.

For long-running, non-restartable, or expensive batch jobs, use a conservative
policy:

1. Annotate the Job pod template with `karpenter.sh/do-not-disrupt: "true"`.
2. Prefer a dedicated batch `NodePool` with `consolidationPolicy: WhenEmpty`.
3. Avoid Spot capacity for jobs that cannot tolerate interruption.
4. Set `expireAfter: Never` or a value longer than the maximum job runtime.
5. Avoid a NodePool `terminationGracePeriod` that is shorter than the maximum
   job runtime, because it can eventually force-delete protected pods.

This protects against voluntary NAP disruption such as consolidation and drift.
It does not protect against VM failure, Azure maintenance, Spot interruption,
manual `kubectl delete node`, or deleting the `NodePool`.

## Job Annotation

Add the annotation to `spec.template.metadata.annotations`, not just the Job
metadata:

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

With this annotation, Karpenter treats the pod like a blocking disruption budget
for voluntary disruption. The node is not fully terminated until the protected
pod is removed, the annotation is removed or expires, the pod reaches
`Succeeded`/`Failed`, or the NodeClaim termination grace period elapses.

For bounded protection, recent Karpenter versions support a duration. If AKS
does not accept this form in the managed NAP version on the cluster, use the
documented boolean value instead:

```yaml
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "8h"
```

## Dedicated Batch NodePool

For workloads that should only be consolidated after all workload pods have
finished, use `WhenEmpty` rather than `WhenEmptyOrUnderutilized`:

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

Schedule the Job onto the batch pool:

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

## Operational Checks

Inspect the current NAP policies:

```bash
kubectl get nodepools -o wide
kubectl get nodepool default -o yaml
```

Find pods that are protected from NAP voluntary disruption:

```bash
kubectl get pods --all-namespaces \
  -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,NODE:.spec.nodeName,DO_NOT_DISRUPT:.metadata.annotations.karpenter\.sh/do-not-disrupt' \
  | grep -v '<none>'
```

Check recent Karpenter/NAP disruption activity:

```bash
kubectl get events --all-namespaces --sort-by='.lastTimestamp' \
  | grep -Ei 'karpenter|disrupt|consolidat|drift|nodeclaim' \
  | tail -50
```

Check NAP controller logs:

```bash
kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter -c controller --tail=200
```

## Policy Recommendation

Use `WhenEmptyOrUnderutilized` only for stateless, horizontally replicated,
restart-safe workloads.

Use a dedicated `WhenEmpty` NodePool plus `karpenter.sh/do-not-disrupt: "true"`
for long-running batch jobs that must run to completion.

If a whole NodePool must be frozen during a critical processing window, use a
zero-node disruption budget:

```yaml
spec:
  disruption:
    budgets:
      - nodes: "0"
```

Remove or schedule that freeze after the critical window, otherwise the cluster
can retain excess nodes and cost more than expected.

## References

- [AKS NAP overview](https://learn.microsoft.com/en-us/azure/aks/node-auto-provisioning)
- [AKS NAP disruption policies](https://learn.microsoft.com/en-us/azure/aks/node-auto-provisioning-disruption)
- [Karpenter disruption documentation](https://karpenter.sh/v1.12/concepts/disruption/)

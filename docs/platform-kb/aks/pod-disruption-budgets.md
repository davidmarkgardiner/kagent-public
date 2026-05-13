# Pod Disruption Budgets on the Shared AKS Platform

## Summary

Use a `PodDisruptionBudget` when an application needs a minimum number of replicas available during voluntary disruptions such as node upgrades, drain operations, or cluster maintenance.

## Steps

1. Make sure the workload has at least two replicas before adding a budget.
2. Choose either `minAvailable` or `maxUnavailable`; do not set both in the same PDB.
3. Match the selector to the same labels used by the Deployment, StatefulSet, or ReplicaSet.
4. For stateless services, start with `maxUnavailable: 1` so one replica can be evicted at a time.
5. For quorum-based systems, calculate `minAvailable` from the quorum requirement and test a node drain in non-production.
6. Check PDB status before maintenance with `kubectl get pdb -n <namespace>`.

## Example

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: web
```

## Related source links

- Kubernetes disruption budgets: https://kubernetes.io/docs/tasks/run-application/configure-pdb/
- AKS planned maintenance: https://learn.microsoft.com/azure/aks/planned-maintenance


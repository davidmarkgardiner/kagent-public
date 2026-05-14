# Pod Disruption Budgets on the Shared AKS Platform

## Summary

Use a `PodDisruptionBudget` when an application must keep a minimum number of pods available during voluntary disruptions such as node upgrades, drain operations, cluster maintenance, or autoscaler consolidation.

## When to Use a PDB

Create a PDB for production workloads with more than one replica when one unavailable replica is acceptable but full disruption is not. Do not add a PDB to a single-replica workload unless the team understands it can block voluntary node maintenance.

## Steps

1. Make sure the workload has at least two replicas.
2. Choose either `minAvailable` or `maxUnavailable`; do not set both.
3. Match the selector to the labels used by the Deployment, StatefulSet, or ReplicaSet.
4. For stateless services, start with `maxUnavailable: 1`.
5. For quorum-based systems, calculate `minAvailable` from the quorum requirement.
6. Test a node drain in non-production before relying on the budget.
7. Check PDB status before maintenance with `kubectl get pdb -n <namespace>`.

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

## Related References

- Kubernetes disruption budgets: https://kubernetes.io/docs/tasks/run-application/configure-pdb/
- AKS planned maintenance: https://learn.microsoft.com/azure/aks/planned-maintenance


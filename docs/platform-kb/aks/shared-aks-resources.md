# Shared AKS Platform Resources

## Summary

The shared AKS platform exposes a curated set of namespaced Kubernetes resources for application teams. Cluster-scoped resources remain platform-owned unless an exception is approved.

## Namespaced Resources Available to Teams

Application teams can normally create the following resources inside approved namespaces:

- `Deployment`
- `StatefulSet`
- `Job`
- `CronJob`
- `Service`
- `Ingress`
- `HTTPRoute`
- `ConfigMap`
- `Secret`
- `ServiceAccount`
- `Role`
- `RoleBinding`
- `NetworkPolicy`
- `HorizontalPodAutoscaler`
- `PodDisruptionBudget`

## Platform-Owned Resources

The platform team manages cluster-scoped resources such as:

- `Namespace`
- `ClusterRole`
- `ClusterRoleBinding`
- admission policies
- ingress controllers
- external DNS
- cert-manager issuers
- storage classes
- node pools
- kagent control-plane components

## Requesting Exceptions

If a team needs a cluster-scoped resource or a new CRD, raise a platform ticket with the use case, blast radius, owner, rollback plan, and production deadline. The platform team reviews exceptions through the standard change path.

## Related References

- Kubernetes API concepts: https://kubernetes.io/docs/reference/using-api/
- AKS cluster operator best practices: https://learn.microsoft.com/azure/aks/operator-best-practices-cluster-security


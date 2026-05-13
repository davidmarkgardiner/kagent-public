# Shared AKS Platform Resources

## Summary

The shared AKS platform exposes a curated set of Kubernetes resources for application teams. Teams can deploy normal namespaced workload resources and selected platform integrations; cluster-scoped changes remain platform-owned.

## Namespaced resources available to teams

Application teams can create `Deployment`, `StatefulSet`, `Job`, `CronJob`, `Service`, `Ingress`, `HTTPRoute`, `ConfigMap`, `Secret`, `ServiceAccount`, `Role`, `RoleBinding`, `NetworkPolicy`, `HorizontalPodAutoscaler`, and `PodDisruptionBudget` resources inside approved namespaces.

## Platform-managed resources

The platform team manages cluster-scoped resources such as `Namespace`, `ClusterRole`, `ClusterRoleBinding`, admission policies, ingress controllers, external DNS, cert-manager issuers, storage classes, node pools, and kagent control-plane components.

## Requesting exceptions

If a team needs a cluster-scoped resource or a new CRD, raise a platform ticket with the use case, blast radius, owner, rollback plan, and production deadline. The platform team will review it through the standard change path.

## Related source links

- Kubernetes API concepts: https://kubernetes.io/docs/reference/using-api/
- AKS cluster operator best practices: https://learn.microsoft.com/azure/aks/operator-best-practices-cluster-security


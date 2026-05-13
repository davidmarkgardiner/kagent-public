# Secure Pods on the Shared AKS Platform

## Summary

Secure pod workloads by using namespace defaults, Kubernetes securityContext settings, NetworkPolicy, image provenance, resource limits, and secret hygiene. The shared AKS platform expects teams to harden pods before production promotion.

## Steps

1. Run the container as non-root and set `allowPrivilegeEscalation: false` in the pod or container `securityContext`.
2. Drop Linux capabilities by default and add back only the specific capability the workload needs.
3. Set read-only root filesystems where the application can run without writing to the image layer.
4. Add CPU and memory requests and limits so the scheduler and cluster autoscaler can protect shared capacity.
5. Attach a namespace-scoped `NetworkPolicy` that allows only required ingress and egress flows.
6. Store secrets in the platform secret flow and mount them as environment variables or volumes only when the pod needs them.
7. Use signed or trusted images from the approved registry and avoid mutable tags such as `latest`.

## Example manifest fragment

```yaml
securityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
```

## Related source links

- Kubernetes Pod Security Standards: https://kubernetes.io/docs/concepts/security/pod-security-standards/
- AKS security baseline: https://learn.microsoft.com/azure/aks/security-baseline


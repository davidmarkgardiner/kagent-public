# Secure Pods on the Shared AKS Platform

## Summary

Secure pod workloads by using Kubernetes `securityContext` settings, resource controls, network policy, trusted images, and platform secret handling. The shared AKS platform expects teams to harden workloads before production promotion.

## Required Defaults

1. Run containers as non-root with `runAsNonRoot: true`.
2. Set `allowPrivilegeEscalation: false` for application containers.
3. Drop Linux capabilities by default and add back only a capability that is explicitly required.
4. Use the runtime default seccomp profile.
5. Set CPU and memory requests and limits.
6. Avoid mutable tags such as `latest`; use versioned or digest-pinned images.

## Example Fragment

```yaml
securityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
containers:
  - name: app
    image: ghcr.io/example/app:v1.2.3
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
          - ALL
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 512Mi
```

## Network Policy

Application namespaces should define namespace-scoped `NetworkPolicy` resources that allow only required ingress and egress paths. Start with default deny where practical, then add explicit allows for upstream services, DNS, and approved platform dependencies.

## Secrets

Use the approved platform secret path. Do not commit credentials, connection strings, or tokens to Git. Mount secrets only into pods that require them, and prefer workload identity for Azure services.

## Related References

- Kubernetes Pod Security Standards: https://kubernetes.io/docs/concepts/security/pod-security-standards/
- AKS security baseline: https://learn.microsoft.com/azure/aks/security-baseline


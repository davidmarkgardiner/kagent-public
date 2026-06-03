# Application Certificates on the Shared AKS Platform

## Summary

Application certificates should be supplied to workloads at pod runtime, not injected into the AKS node image or mounted from the node filesystem.

The only expected node-level certificate exception is the approved private registry CA, such as the Nexus image-pull CA, when the container runtime needs it to pull images. Application TLS certificates, mTLS client certificates, service CAs, and application trust bundles should be declared in Kubernetes YAML and mounted only into the pods that need them.

## Platform Position

Do not depend on certificates pre-installed on Ubuntu or Azure Linux nodes for application behaviour. That couples the application to node image details, makes rotation harder, increases blast radius, and breaks portability between node pools and operating systems.

Use one of these runtime patterns instead:

- Use a Kubernetes `Secret` for private certificate material, private keys, client certificates, credentials, and TLS secrets.
- Use a Kubernetes `ConfigMap` only for non-confidential CA bundles or public configuration.
- Use Azure Key Vault with the Secrets Store CSI Driver when the source of truth is Key Vault and the workload should mount certificates directly from the vault.
- Mount certificate files read-only into the application container using `volumes` and `volumeMounts`.

## Recommended YAML Pattern

This example keeps the certificate lifecycle with the application deployment rather than the node image. Replace placeholders with approved environment values outside this public repo.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-tls
  namespace: {{APP_NAMESPACE}}
type: kubernetes.io/tls
data:
  tls.crt: {{BASE64_CERTIFICATE}}
  tls.key: {{BASE64_PRIVATE_KEY}}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-ca-bundle
  namespace: {{APP_NAMESPACE}}
data:
  ca.crt: |
    -----BEGIN CERTIFICATE-----
    {{PUBLIC_CA_CERTIFICATE}}
    -----END CERTIFICATE-----
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  namespace: {{APP_NAMESPACE}}
spec:
  template:
    spec:
      containers:
        - name: app
          image: {{REGISTRY_HOST}}/{{IMAGE_NAME}}:{{IMAGE_TAG}}
          volumeMounts:
            - name: app-tls
              mountPath: /etc/app/tls
              readOnly: true
            - name: app-ca-bundle
              mountPath: /etc/app/ca
              readOnly: true
          env:
            - name: APP_TLS_CERT_FILE
              value: /etc/app/tls/tls.crt
            - name: APP_TLS_KEY_FILE
              value: /etc/app/tls/tls.key
            - name: APP_CA_BUNDLE_FILE
              value: /etc/app/ca/ca.crt
      volumes:
        - name: app-tls
          secret:
            secretName: app-tls
        - name: app-ca-bundle
          configMap:
            name: app-ca-bundle
```

## What Not To Do

- Do not use `hostPath` to mount certificates from the AKS node into application pods.
- Do not ask the platform team to bake application certificates into Azure Linux node images.
- Do not put private keys or confidential certificate material in a `ConfigMap`.
- Do not commit real certificates, private keys, tokens, hostnames, tenant IDs, or subscription IDs to Git.
- Do not rely on a certificate being present on every node unless it is a platform-managed node trust certificate for the container runtime.

## Azure Linux Note

Moving from Ubuntu nodes to Azure Linux should not change the application certificate contract. If an application only worked because a certificate happened to exist on the old node image, the workload needs to be updated to mount that certificate at runtime.

AKS custom CA trust is for node trust scenarios, such as enabling the node/container runtime to trust a private registry CA. Microsoft documents that certificates added to AKS node trust this way are not automatically available inside containers. If an application needs a certificate inside the container, supply it through the image or mount it at runtime, with runtime mounting preferred for application-owned certificates.

## Rotation Expectations

Certificate rotation should update the Kubernetes `Secret`, `ConfigMap`, or Key Vault object used by the pod. Applications should either watch the mounted files and reload them, or be restarted through the normal deployment process after certificate rotation.

Avoid mounting a `Secret` or `ConfigMap` through `subPath` when the application expects automatic file updates. Kubernetes and AKS documentation call out that `subPath` mounts do not receive automatic updates when the backing object changes.

## Related References

- AKS custom certificate authority trust for nodes: https://learn.microsoft.com/azure/aks/custom-certificate-authority
- AKS pod security best practices and credential exposure guidance: https://learn.microsoft.com/azure/aks/developer-best-practices-pod-security
- AKS Key Vault provider for Secrets Store CSI Driver: https://learn.microsoft.com/azure/aks/csi-secrets-store-driver
- Kubernetes Secrets: https://kubernetes.io/docs/concepts/configuration/secret/
- Kubernetes ConfigMaps: https://kubernetes.io/docs/concepts/configuration/configmap/
- Kubernetes Volumes and `hostPath`: https://kubernetes.io/docs/concepts/storage/volumes/

# AKS Istio Add-on with Kubernetes Gateway API - TLDR

## TLDR

Do not replace the AKS Istio service mesh add-on. Keep it.

The useful change is to standardize ingress on the Kubernetes Gateway API (`Gateway`, `HTTPRoute`, and related resources) with `gatewayClassName: istio`, backed by the AKS-managed Istio add-on. This gives us a Kubernetes-standard routing API while keeping the managed Istio control plane, sidecar injection, mesh policy, telemetry, and upgrade model we already rely on.

If we already use `gateway.networking.k8s.io` resources with `gatewayClassName: istio`, we may already be using the main feature. In that case, the work is about confirming that the CRDs are AKS-managed, the cluster is on a supported Istio add-on revision, and the ingress operating model is documented and governed.

## Current vs Additional Capability

| Area | What we likely have today | What the AKS Istio Gateway API path adds | Why it matters |
|---|---|---|---|
| Service mesh | AKS Istio service mesh add-on provides the managed Istio control plane, sidecar injection, mesh traffic policy, mTLS, telemetry, and Istio CRDs. | No replacement. The same Istio add-on remains the mesh implementation. | This is not a mesh migration. It is an ingress API and operating-model improvement. |
| Ingress API | We may use Istio-native `Gateway`/`VirtualService`, Kubernetes `Ingress`, or already use Kubernetes Gateway API resources. | Standard Kubernetes Gateway API resources such as `Gateway` and `HTTPRoute` with `gatewayClassName: istio`. | Reduces Istio-specific routing config for common ingress use cases and aligns with the Kubernetes direction for L7 routing. |
| CRD management | Gateway API CRDs may be self-installed, drifted, or absent depending on cluster history. | AKS Managed Gateway API installs and manages standard-channel Gateway API CRDs. | Reduces manual CRD lifecycle work and gives a clearer Microsoft support boundary. |
| Platform/app ownership | Platform and app routing concerns can be mixed together in shared Istio manifests. | Platform owns `Gateway`; app teams can own constrained `HTTPRoute` objects. | Cleaner delegation: shared listener/LB/TLS policy stays with the platform team, per-app host/path routing moves closer to app teams. |
| Gateway infrastructure | We may maintain gateway `Deployment`, `Service`, scaling, and disruption settings directly, or rely on existing Istio ingress gateway patterns. | A `Gateway` can cause Istio to provision the backing `Deployment`, `Service`, `HPA`, and `PDB`. | Less hand-built gateway plumbing and more repeatable GitOps patterns. |
| Private ingress | Internal load balancers and private DNS are likely handled through current Azure service annotations and network standards. | Gateway API supports Azure LB annotations under `spec.infrastructure.annotations`, including internal LB and subnet selection. | Lets the same private-network pattern be expressed from the Gateway object rather than separate service patching. |
| TLS | TLS may be handled by existing Kubernetes secrets, cert-manager, Key Vault CSI, or a platform-specific process. | Microsoft documents TLS termination by syncing Key Vault material into Kubernetes TLS secrets via Secrets Store CSI and referencing them from the `Gateway`. | Gives a supported reference path, but the private Key Vault, managed identity, and private DNS setup still need to be proven in our environment. |
| Upgrades | Istio add-on upgrades are managed through AKS Istio revision behavior. | Gateway API CRD bundle upgrades are managed by AKS based on Kubernetes version when Managed Gateway API is enabled. | Fewer separately managed networking API versions, but we still need upgrade testing in private clusters. |
| GitOps model | Routing may be coupled to app or mesh manifests inconsistently. | Shared `Gateway` can live in platform config; app `HTTPRoute` objects can live with service config. | Better Flux ownership boundaries and easier review of who is changing shared ingress versus app routing. |
| Portability | Istio-native ingress config is tied to Istio. | Gateway API manifests are more portable across conforming implementations, although behavior still depends on the implementation. | Useful if we want common patterns across clusters or future ingress implementations. |

## What This Does Not Add

| Not added | Detail |
|---|---|
| A new mesh data plane | Traffic still flows through Istio/Envoy managed by the AKS Istio add-on. |
| Replacement for Istio policy | Istio authorization, telemetry, destination rules, and other mesh features still come from Istio. |
| Free migration of complex Istio routing | Basic host/path routing maps well to `HTTPRoute`; advanced Istio-specific behavior needs case-by-case validation. |
| Automatic proof for private networks | Internal LB, private DNS, Key Vault private endpoints, firewall rules, and image/control-plane dependencies still need environment testing. |
| Unlimited customization | Generated gateway resources are customizable only through supported/allow-listed fields. |

## Private / Restricted Network Checks

Before adopting this broadly, validate these in a non-production private cluster:

| Check | Why |
|---|---|
| `az aks update --enable-gateway-api` works from the management path used for cluster administration. | Managed Gateway API is enabled through AKS control-plane operations. |
| Gateway API CRDs show AKS-managed annotations and a supported standard-channel bundle. | Confirms we are inside the supported AKS-managed CRD path. |
| Istio add-on revision is `asm-1-26` or higher. | Microsoft documents this as the compatibility baseline for the Istio add-on with Managed Gateway API. |
| `GatewayClass` named `istio` exists and is accepted. | Confirms the Istio add-on implementation is active. |
| An internal-only `Gateway` provisions an internal Azure Load Balancer in the expected subnet. | This is the key private-network ingress requirement. |
| Private DNS resolves the application hostname to the internal load balancer address. | Gateway readiness does not prove users can resolve or reach the service. |
| TLS termination works with the intended certificate source. | Key Vault CSI requires managed identity, RBAC or access policy, private endpoint, DNS, and firewall alignment. |
| Generated `Deployment`, `Service`, `HPA`, and `PDB` meet platform standards. | Defaults may be close, but production clusters often need explicit sizing, scheduling, and disruption settings. |
| Upgrade behavior is tested during AKS and Istio add-on revision changes. | Gateway API ownership and generated resources should be checked before production rollout. |

## Recommended Pilot

1. Pick one low-risk internal HTTP service.
2. Enable Managed Gateway API on a non-production AKS cluster that already uses the Istio add-on.
3. Create one platform-owned internal `Gateway` with `gatewayClassName: istio`.
4. Attach one app-owned `HTTPRoute`.
5. Validate internal LB, DNS, TLS, route ownership, logs, HPA/PDB defaults, and rollback.
6. If successful, document the platform-owned `Gateway` pattern and app-team `HTTPRoute` template.

## Example Shape

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: internal-app-gateway
  namespace: {{PLATFORM_NAMESPACE}}
spec:
  gatewayClassName: istio
  infrastructure:
    annotations:
      service.beta.kubernetes.io/azure-load-balancer-internal: "true"
      service.beta.kubernetes.io/azure-load-balancer-internal-subnet: "{{SUBNET_NAME}}"
  listeners:
    - name: http
      port: 80
      protocol: HTTP
      hostname: "{{APP_HOSTNAME}}"
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              platform.example.com/allow-gateway-routes: "true"
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app-route
  namespace: {{APP_NAMESPACE}}
spec:
  parentRefs:
    - name: internal-app-gateway
      namespace: {{PLATFORM_NAMESPACE}}
  hostnames:
    - "{{APP_HOSTNAME}}"
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: {{SERVICE_NAME}}
          port: 80
```

## Share Message

We should treat AKS Istio Gateway API support as an additive ingress standardization layer, not a replacement for the AKS Istio add-on.

The mesh remains the AKS-managed Istio add-on. The benefit is that ingress can move toward Kubernetes Gateway API resources: platform-owned `Gateway` objects for shared listener/LB/TLS policy, and app-owned `HTTPRoute` objects for host/path routing. That gives us cleaner GitOps ownership, a more portable Kubernetes-native API, and less hand-built gateway infrastructure because Istio can provision the gateway `Deployment`, `Service`, `HPA`, and `PDB`.

The main private-network risks to prove are internal Azure Load Balancer creation, subnet permissions, private DNS, Key Vault CSI access over Private Link if used for TLS, and whether the generated gateway resources meet our sizing and disruption standards. Recommended next step: pilot one low-risk internal HTTP service on a non-production private AKS cluster using `gatewayClassName: istio`.

## References

- Microsoft Learn: Configure Istio ingress with the Kubernetes Gateway API for AKS: <https://learn.microsoft.com/en-us/azure/aks/istio-gateway-api>
- Microsoft Learn: Install Managed Gateway API CRDs on AKS: <https://learn.microsoft.com/en-us/azure/aks/managed-gateway-api>

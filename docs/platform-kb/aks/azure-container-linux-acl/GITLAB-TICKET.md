# GitLab Ticket Draft: Evaluate Azure Container Linux ACL for AKS 1.34

## Title

Evaluate Azure Container Linux ACL node pools for AKS 1.34 platform rollout

## Description

Microsoft has introduced Azure Container Linux (ACL) as a generally available AKS node pool OS option from AKS `1.34`. ACL is an immutable, container-optimized node OS derived from Flatcar Container Linux with Azure Linux packages, servicing, and AKS integration.

We need to determine whether ACL can be used for our AKS `1.34` rollout, either as the default node OS for selected pools or as a hardened node pool option.

The main early concern is private registry trust. Our current platform depends on a Nexus certificate being available on nodes so the container runtime can pull images from Nexus. ACL's immutable host model may not support any process that relies on manual node filesystem mutation or ad hoc certificate mounting. We need to test whether the supported AKS custom CA trust path works with ACL and whether Nexus-backed image pulls survive node creation, scale-out, and node image upgrades.

## Scope

- Deploy a non-production AKS `1.34` cluster with ACL node pools.
- Test Nexus image pulls out of the box.
- Configure the Nexus CA through the supported AKS custom CA trust mechanism and retest image pulls.
- Install the standard platform stack and managed add-ons.
- Deploy representative applications.
- Run node replacement, scale-out, and node image upgrade tests.
- Produce a rollout recommendation for the AKS `1.34` release.

## Key Questions

- Does ACL work with the current Nexus private registry image-pull pattern?
- Does AKS custom CA trust work with ACL for the Nexus CA?
- Are any managed add-ons, extensions, DaemonSets, CSI drivers, ingress components, or monitoring agents incompatible with ACL?
- Do any workloads rely on mutable node filesystem behavior?
- Is ACL suitable for all pools, selected hardened pools, or not yet suitable for this release?

## Initial Test Matrix

| Area | Test | Expected Result |
|---|---|---|
| Cluster | Create AKS `1.34` cluster with ACL node pool | Cluster and nodes become Ready |
| Nexus pull without CA | Pull a representative Nexus-hosted image before custom CA setup | Expected to fail if Nexus CA is private; capture exact error |
| Nexus pull with CA | Configure AKS custom CA trust and pull the same image | Pull succeeds without manual node mutation |
| Scale-out | Add ACL nodes after CA configuration | New nodes can pull Nexus images |
| Node recycle | Replace ACL nodes | Replacement nodes retain Nexus trust |
| Node image upgrade | Apply supported node image update path | Nexus trust and add-ons survive |
| Add-ons | Install standard platform add-ons | Add-ons become healthy |
| Workloads | Deploy representative applications | Pods schedule, pull images, start, restart, and scale |
| Host assumptions | Check privileged DaemonSets and hostPath users | No unsupported writes to immutable host paths |

## Platform Stack To Validate

- Flux
- Workload identity
- Ingress / Gateway API / service mesh components in use
- cert-manager or certificate tooling in use
- Secrets Store CSI Driver / Key Vault integration
- Azure Monitor / Container Insights / managed Prometheus
- Policy and security add-ons
- Storage CSI drivers
- kagent
- agentgateway
- AKS-MCP
- Argo Workflows
- Argo Events
- Representative application deployments

## Known ACL Constraints To Track

- AKS `1.34` or later required.
- Trusted Launch with Secure Boot and vTPM required.
- Only `NodeImage` and `None` are supported OS upgrade channels.
- `SecurityPatch` and `Unmanaged` OS upgrade channels are not compatible.
- Artifact Streaming is not supported.
- Pod Sandboxing is not supported.
- Confidential VMs are not supported.
- Generation 1 VMs are not supported.
- ARM64 requires compatible Cobalt/v6 SKUs.

## Acceptance Criteria

- ACL cluster deployment is proven in a non-production environment.
- Nexus-backed image pulls work through a supported AKS node trust mechanism.
- The standard platform stack installs successfully.
- Representative applications run successfully.
- Node scale-out, replacement, and image upgrade do not break image pulls or add-ons.
- Incompatibilities are documented with owner, severity, workaround, and decision.
- A final recommendation is recorded for the AKS `1.34` release:
  - adopt ACL for selected hardened pools;
  - continue with Azure Linux as default and extend the ACL pilot;
  - defer ACL because of a specific blocker.

## References

- Platform README: `docs/platform-kb/aks/azure-container-linux-acl/README.md`
- AKS custom CA trust KB: `docs/platform-kb/aks/application-certificates.md`
- Microsoft ACL overview: https://learn.microsoft.com/azure/aks/azure-container-linux-overview
- Microsoft Azure Linux overview: https://learn.microsoft.com/azure/azure-linux/azure-linux-aks-overview
- Microsoft AKS custom CA trust: https://learn.microsoft.com/azure/aks/custom-certificate-authority

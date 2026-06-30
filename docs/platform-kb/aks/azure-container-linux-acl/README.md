# Azure Container Linux ACL Evaluation for AKS

## Summary

Azure Container Linux (ACL) is an AKS node pool operating system option. It does not replace application container images. It replaces the Linux host image used by AKS nodes when a node pool is created or migrated to ACL.

ACL is generally available for AKS starting with Kubernetes `1.34`. It is derived from Flatcar Container Linux and combines an immutable, container-focused host model with Azure Linux packages, servicing, and AKS integration.

## Platform Position

Treat ACL as a candidate hardened node pool profile for the AKS `1.34` release, not as an automatic replacement for existing Azure Linux node pools.

The right next step is to deploy a non-production AKS `1.34` cluster with ACL node pools, install the standard platform stack, and run compatibility tests before deciding whether ACL becomes part of the release rollout.

## Azure Linux vs ACL

| Area | Azure Linux Container Host | Azure Container Linux ACL |
|---|---|---|
| Primary use | Standard Microsoft AKS Linux node OS | Hardened, immutable AKS node OS |
| Host model | Conventional Linux node image | Immutable/container-appliance style host |
| Mutability | Normal writable host areas | `/usr` is read-only and protected by `dm-verity` |
| Security controls | Hardened kernel, small package set, Microsoft build/sign/validation, CIS Level 1 | Azure Linux supply chain plus immutable `/usr`, SELinux enforcing, Trusted Launch, Secure Boot, vTPM, signed UKI |
| Updates | Standard AKS node image/security update model | Weekly image-based node updates; full node image updates only |
| Compatibility | Broadest AKS add-on and extension compatibility | Must be validated for add-ons and node-level agents |
| Best fit | Default AKS Linux pools and broad workload compatibility | Security-sensitive or regulated pools where immutable host behavior is valuable |

## Benefits of ACL

- Stronger host integrity: immutable `/usr` protected by `dm-verity`.
- Smaller mutable surface for accidental drift or host-level tampering.
- SELinux enforcing mode by default.
- Trusted Launch, Secure Boot, and vTPM are required.
- Weekly image-based node updates keep node images consistent.
- Supports AMD64 and ARM64 node pools, with ARM64 subject to SKU requirements.
- Supports NVIDIA GPU node pools on AMD64.
- Supports AKS node auto-provisioning.

## Known Limitations

Validate these against the exact AKS version and region before adoption:

- AKS `1.34` or later is required.
- Trusted Launch with Secure Boot and vTPM is required.
- Non-Trusted Launch variants are not available.
- ARM64 requires Cobalt-based v6 SKUs for Trusted Launch compatibility.
- Only `NodeImage` and `None` are supported OS upgrade channels.
- `Unmanaged` and `SecurityPatch` OS upgrade channels are not compatible with ACL.
- Artifact Streaming is not supported.
- Pod Sandboxing is not supported.
- Confidential VMs are not supported.
- Generation 1 VMs are not supported.
- OS Guard preview features such as Integrity Policy Enforcement are not currently supported by ACL.

## Managed Add-on Risk

Microsoft documents the main ACL platform limitations, but there is not a single public matrix that proves every AKS managed add-on and extension against ACL.

Assume add-ons need validation if they:

- run privileged DaemonSets;
- mount host paths;
- install or modify host packages;
- write into host OS paths such as `/usr`;
- depend on custom host certificate placement;
- rely on unsupported features such as Pod Sandboxing, Artifact Streaming, or Confidential VMs;
- depend on specific node image internals.

The evaluation should prove the actual platform stack rather than relying on generic compatibility assumptions.

## Nexus Image-pull CA Test

The first likely compatibility test is the private Nexus registry certificate.

The current platform pattern mounts or installs a Nexus CA on the AKS nodes so that the node container runtime can trust Nexus and pull images. That is a node trust scenario, not an application certificate scenario.

This may still work with ACL if it uses the supported AKS custom CA trust path, but it must be tested. ACL's immutable host model means any process that assumes ad hoc node mutation, package installation, or manual certificate placement could fail or become unsupported.

Evaluation questions:

- Can a fresh ACL node pool pull a test image from Nexus with no custom CA configured?
- If not, does AKS `--custom-ca-trust-certificates` work with ACL for the Nexus CA?
- Does the CA apply correctly during node creation, scale-out, node image upgrade, and node replacement?
- Does `containerd` trust the CA without manual node shell steps?
- Are the certificates visible only to the node/container runtime, not automatically to application containers?
- Does the current GitOps/KRO/ASO cluster definition have a safe place to declare the custom CA input, or does this require a platform design change?

Expected outcome:

- If AKS custom CA trust works on ACL, the Nexus CA should not block ACL adoption.
- If the current process relies on manual node filesystem mutation, treat that as a blocker and redesign it before ACL rollout.

## Test Plan

1. Deploy a non-production AKS `1.34` cluster with ACL node pools.
2. Record the exact AKS version, region, VM SKU, OS SKU, node image version, and upgrade channel.
3. Test image pulls from Nexus without custom CA configuration.
4. Configure the Nexus CA through the supported AKS custom CA trust path and retest image pulls.
5. Install the base platform stack:
   - Flux;
   - workload identity;
   - ingress / Gateway API / service mesh components in use;
   - cert-manager or certificate tooling in use;
   - Secrets Store CSI Driver / Key Vault integration;
   - Azure Monitor / Container Insights / managed Prometheus;
   - policy and security add-ons;
   - storage CSI drivers;
   - kagent, agentgateway, AKS-MCP, Argo Workflows, and Argo Events.
6. Deploy representative applications from the current stack.
7. Run node scale-out, node recycle, and node image upgrade tests.
8. Check privileged DaemonSets, hostPath mounts, and node-level agents.
9. Capture failures, workarounds, and unsupported features.
10. Decide whether ACL is suitable for the AKS `1.34` release rollout.

## Acceptance Criteria

- ACL cluster deploys successfully on AKS `1.34`.
- Nexus-backed image pulls work through a supported node trust mechanism.
- Standard platform add-ons install and become healthy.
- Representative applications deploy, restart, and scale successfully.
- Node replacement and image upgrade do not break Nexus trust or platform add-ons.
- Any incompatible add-on or workload is documented with an owner, severity, workaround, and rollout decision.
- The final recommendation is one of:
  - adopt ACL for selected hardened pools in the `1.34` rollout;
  - keep Azure Linux as default and run a longer ACL pilot;
  - defer ACL because a documented blocker affects the current platform stack.

## References

- Microsoft Learn: Azure Container Linux for AKS overview: https://learn.microsoft.com/azure/aks/azure-container-linux-overview
- Microsoft Learn: Azure Linux Container Host for AKS overview: https://learn.microsoft.com/azure/azure-linux/azure-linux-aks-overview
- Microsoft Learn: AKS custom certificate authorities: https://learn.microsoft.com/azure/aks/custom-certificate-authority
- Existing platform KB: application certificates on AKS: `docs/platform-kb/aks/application-certificates.md`

# kagent and Agent Substrate security-context notes

Updated 3 November 2026. This README supports the [SYS_ADMIN security review](agent-substrate-sys-admin-security-review.md). Substrate is intended for its own **separate engineering cluster**. The request still concerns **two Azure policies only**, with Kyverno restoring enforcement elsewhere.

## Policy scope by namespace

🟧 means **request namespace exclusion**, subject to the existing approval process. 🟩 means **leave other policies unchanged**. These colors describe the request, not deployed state.

| Microsoft Azure policy | Namespaces to add to that policy's exclusions | Setting behind the request |
| --- | --- | --- |
| [Kubernetes cluster containers should only use allowed capabilities](https://github.com/Azure/azure-policy/blob/f096d8de10fb25e71dd7f82b78ded110ec711d73/built-in-policies/policyDefinitions/Kubernetes/ContainerAllowedCapabilities.json) | 🟧 `kagent`, `ate-system` | The worker adds elevated capabilities, including `SYS_ADMIN`; the newer `atelet` adds `DAC_OVERRIDE`. |
| [Kubernetes cluster containers should run with a read only root file system](https://github.com/Azure/azure-policy/blob/f096d8de10fb25e71dd7f82b78ded110ec711d73/built-in-policies/policyDefinitions/Kubernetes/ReadOnlyRootFileSystem.json) | 🟧 `kagent`, `ate-system` | Worker and Substrate infrastructure containers leave `readOnlyRootFilesystem` unset. |

The proposed central assignment change may add `kagent` and `ate-system` to `excludedNamespaces` across multiple clusters. Preserve existing exclusions and limit the change to these two definitions. Verify the Kyverno baseline on every affected cluster before making that central change. The [main review](agent-substrate-sys-admin-security-review.md#cluster-specific-enforcement-with-kyverno) explains the required cluster-specific enforcement.

🟩 All other Azure policies remain unchanged. Privilege escalation and the other security-context controls are outside this exclusion request. If another policy blocks deployment, capture its rejection and address it separately.

## Cluster-specific allowance

| Target | Required behavior for the two controls |
| --- | --- |
| Approved separate engineering cluster, reviewed Substrate containers | 🟧 Allow only the approved runtime capability sets and root-filesystem deviations, matched to protected workload identity and image configuration. |
| Other workloads on engineering | 🟩 Keep the baseline enforced, including ordinary Pods in `kagent` and `ate-system`. |
| Every other cluster affected by the Azure exclusions | 🟥 Deny the Substrate deviations. 🟩 Enforce the baseline even in namespaces named `kagent` or `ate-system`. No engineering allowance is installed there. |

Kyverno is cluster-local. A `ClusterPolicy` is not automatically a fleet policy or a trusted cluster-name check. The proposed design deploys a common baseline everywhere and an allowance only through the protected engineering cluster's GitOps overlay. A workload label or editable namespace/ConfigMap must not turn another cluster into an approved target.

The allowance must retain bounded validation. Simply skipping the baseline for an entire namespace or container name could permit arbitrary additions. Review the workload/container, service account, immutable image digest, exact capability set, and filesystem exception together. Restrict policy/exception/webhook administration and cluster enrollment.

**Do not widen the central Azure exclusions until every affected cluster has verified Kyverno Enforce coverage.** Audit-only policy is not a replacement. Preserve the actual Azure parameters and approved scope, and verify main/init/ephemeral containers, controller-created Pods, updates, webhook filters, availability, and fail-closed behavior. Existing violating resources need explicit review; admission policy does not automatically remove them.

Before onboarding a new inheriting cluster, establish the same baseline. Keep the engineering allowance absent unless that cluster receives its own approval. This is a proposed design, not an installed or tested fleet policy. The [validation](https://kyverno.io/docs/policy-types/cluster-policy/validate/) and [exception](https://kyverno.io/docs/guides/exceptions/) syntax must match the installed Kyverno version.

## Saved settings behind the request

The following settings come from the saved native home-lab Pod inventory collected on **1 November 2026 at approximately 11:35 UTC**, with kagent `1.0.0-alpha17` and Substrate `v0.6.0-alpha3`. They are not fresh workplace observations.

| Namespace and container | Capability settings | `readOnlyRootFilesystem` |
| --- | --- | --- |
| `kagent`, `Deployment/kagent-default`, `worker` | Drops `ALL`, then adds the runtime capability set below. | Unset; defaults to `false`. |
| `ate-system`, `DaemonSet/atelet`, `atelet` | Drops `ALL`, adds `DAC_OVERRIDE`. | Unset; defaults to `false`. |
| `ate-system`, objectstore sidecars in the `atelet` and API-server Pods | Drop `ALL`; no explicit additions. | Unset; defaults to `false`. |
| `ate-system`, main containers in `ate-api-server`, `ate-controller`, `ate-idp-server`, `atenet-router`, and `atenet-egress` | `ate-idp-server` drops `ALL`; the others do not explicitly define capability drops. | Unset; defaults to `false`. |
| `kagent`, controller and UI | Drop `ALL`; no explicit additions. | Explicit `true`. |
| `ate-system`, credential provider | Drops `ALL`; no explicit additions. | Explicit `true`. |

The worker capability additions are `NET_ADMIN`, `SYS_ADMIN`, `SYS_CHROOT`, `SYS_PTRACE`, `SETUID`, `SETGID`, `SETPCAP`, `DAC_OVERRIDE`, `FOWNER`, `CHOWN`, `MKNOD`, `NET_RAW`, and `SETFCAP`.

The saved lab also contained additional workers and database/storage containers in these namespaces. The table explains the principal reasons for the two exclusions; it is not a complete workplace inventory. A namespace exclusion also covers other matching containers in that namespace, including the controller, UI, and credential provider that already satisfy these two settings.

## What the two policies check

The reviewed Microsoft allowed-capabilities definition, version **6.2.0**, has `allowedCapabilities`, `requiredDropCapabilities`, and `excludedNamespaces` parameters. Its [Gatekeeper template](https://store.policy.core.windows.net/kubernetes/container-allowed-capabilities/v3/template.yaml) checks capability additions against the allowlist and verifies required drops. Dropping `ALL` does not cancel the check on capabilities explicitly added back.

The reviewed read-only-root-filesystem definition, version **6.3.0**, also has `excludedNamespaces`. Its [Gatekeeper template](https://store.policy.core.windows.net/kubernetes/read-only-root-filesystem/v3/template.yaml) rejects containers whose `readOnlyRootFilesystem` is not `true`, including an omitted field.

`readOnlyRootFilesystem: true` protects the container root filesystem. A volume mount's `readOnly: true` protects that mount separately. A read-only certificate or device mount does not satisfy the root-filesystem policy. See the [Kubernetes SecurityContext reference](https://kubernetes.io/docs/reference/kubernetes-api/core/pod-v1/#securitycontext).

The requested filesystem exclusion is for deploying the existing manifests. Whether individual containers could later use a read-only root filesystem with explicit writable volumes remains untested and is outside this phase.

## Workplace confirmation and next deployment

Microsoft's [AKS policy reference](https://learn.microsoft.com/en-us/azure/aks/policy-reference) is a catalog, not the workplace assignment inventory. The policy owner must confirm the two actual assignments or initiative members, effective parameters, existing exclusions, and deployed Substrate version. Namespace placement can differ from the lab.

The core delivery team's restricted deployment access and peer-review process remain the operating controls described in the main review. No Azure exclusion or Kyverno policy was applied by this documentation update. Require stakeholder approval and verified fleet coverage before changing the Azure exclusions; then retry deployment only in the approved engineering cluster.

## Evidence for a bounded runtime node pool

The [main review includes breakout analysis, cluster-specific controls, and a draft stakeholder response](agent-substrate-sys-admin-security-review.md#responding-to-the-production-risk-concern). A separate engineering cluster is the intended boundary. Node-pool placement is an additional control within it, not a substitute for cluster separation. The two-policy Azure scope is unchanged.

Before claiming the design is enforced, obtain these workplace checks. None was performed on the workplace fleet for this document.

1. Record all clusters inheriting the two Azure exclusions. Verify Kyverno Enforce coverage and drift monitoring on each, and verify the runtime allowance exists only in the approved engineering overlay.
2. Show approved engineering runtime requests pass, while altered capabilities, images, identities, and filesystem settings outside the allowance fail. Show the same exceptional requests fail on every other affected cluster, including in `kagent` and `ate-system`. Identify the actual denying Kyverno rule; another admission engine's denial is not proof of Kyverno enforcement.
3. Verify worker and `atelet` placement in the engineering cluster after replacement and scale-out. Use required placement and taints for reserved runtime nodes; restrict overrides and inventory platform DaemonSets and their credentials. The reviewed base `atelet` manifest has no node selector.
4. Review engineering node, runtime, controller, gateway, and tool permissions separately. Keep production application workloads and production-changing credentials out of the engineering runtime. Prove prohibited production network paths fail from actor, worker, and node-originated paths.
5. Verify the real tool/API service identities deny production application writes. An incorrect authorized tool call needs no sandbox escape. Any future write approval belongs at a separate executor, independently of model prompts.
6. Record stakeholder decisions, expiry, alert ownership, central-exclusion rollback, credential revocation, and node quarantine/rebuild procedures. Verify new-cluster onboarding cannot create an unprotected inheriting cluster.

The separate-cluster design is confirmed intent from the delivery owner. Cluster/network isolation, fleet admission coverage, and effective production permissions still require evidence. No rollout or stakeholder approval is claimed by this README.

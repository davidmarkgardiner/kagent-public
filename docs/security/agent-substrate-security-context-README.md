# kagent and Agent Substrate security-context notes

Updated 3 November 2026. This README supports the [SYS_ADMIN security review](agent-substrate-sys-admin-security-review.md) and the current request for **two Azure policy exclusions only**.

## Policy scope by namespace

🟧 means **request namespace exclusion**, subject to the existing approval process. 🟩 means **leave other policies unchanged**. These colors describe the request, not deployed state.

| Microsoft Azure policy | Namespaces to add to that policy's exclusions | Setting behind the request |
| --- | --- | --- |
| [Kubernetes cluster containers should only use allowed capabilities](https://github.com/Azure/azure-policy/blob/f096d8de10fb25e71dd7f82b78ded110ec711d73/built-in-policies/policyDefinitions/Kubernetes/ContainerAllowedCapabilities.json) | 🟧 `kagent`, `ate-system` | The worker adds elevated capabilities, including `SYS_ADMIN`; the newer `atelet` adds `DAC_OVERRIDE`. |
| [Kubernetes cluster containers should run with a read only root file system](https://github.com/Azure/azure-policy/blob/f096d8de10fb25e71dd7f82b78ded110ec711d73/built-in-policies/policyDefinitions/Kubernetes/ReadOnlyRootFileSystem.json) | 🟧 `kagent`, `ate-system` | Worker and Substrate infrastructure containers leave `readOnlyRootFilesystem` unset. |

For each policy, merge `kagent` and `ate-system` into `excludedNamespaces`, preserving the existing list. Limit any initiative-level change to these two policy definitions. The [main review](agent-substrate-sys-admin-security-review.md#policy-scope-by-namespace) explains scope and evidence limits.

🟩 All other Azure policies remain unchanged. Privilege escalation and the other security-context controls are outside this exclusion request. If another policy blocks deployment, capture its rejection and address it separately.

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

The core delivery team's restricted deployment access and peer-review process remain the operating controls described in the main review. No Azure exclusion or Kyverno policy was applied by this documentation update. After approved changes to these two policies, retry deployment and use any new denial as the basis for the next narrowly scoped request.

## Evidence for a bounded runtime node pool

The [main review now includes breakout analysis, proposed controls, and a draft stakeholder response](agent-substrate-sys-admin-security-review.md#responding-to-the-production-risk-concern). The two-policy exclusion table above is unchanged.

A Substrate WorkerPool is a pool of worker Pods, not an AKS node pool. The reviewed worker template supports optional node selectors and required affinity. The base `atelet` DaemonSet has no node selector. Dedicated placement is therefore a configuration and verification requirement, not an automatic consequence of using Substrate.

Before describing the deployment as contained, obtain these workplace checks. They are proposed evidence requirements; none was performed on the workplace cluster for this document.

1. Verify rendered WorkerPools, generated worker Pods, `atelet`, and its sidecars use the approved runtime nodes. Check actual placement after replacement and scale-out, including the absence of `atelet` on unrelated nodes.
2. Combine taints with hard placement. Test that unrelated Pods cannot enter the pool and runtime Pods cannot target other pools. Restrict scheduling overrides, direct node binding, node labels, and the use of the namespace exclusions. Inventory platform DaemonSets that still run there.
3. Review node, runtime, controller, gateway, and MCP/tool credentials and effective permissions separately. A workload's hosting node does not restrict its API authorization. Keep production application workloads and production-authorized credentials off runtime nodes.
4. Prove required network paths work and prohibited production paths fail. Cover actor traffic, the outer worker, and node-originated traffic. Pod NetworkPolicies are not a sufficient claim of containment after node compromise.
5. Prove the actual tool/API service identity denies production writes. An incorrect authorized tool call needs no sandbox escape. Enforce any future write approval at a separate executor, independently of the model and its prompts.
6. Record stakeholder decisions, an expiry, monitoring ownership, and a tested stop/revoke/quarantine procedure. Prefer a separate non-production cluster if the shared-cluster risk is unacceptable.

The existing restriction to the core delivery team and peer review helps control deployment. It does not establish the placement, network, or production-authorization checks above. The defensible claim is reduced and verified exposure under an agreed pilot, with shared-cluster residual risk stated explicitly.

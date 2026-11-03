# Agent Substrate SYS_ADMIN security review

Updated 3 November 2026 for security and core application delivery reviewers.

Related [security-context README](agent-substrate-security-context-README.md) records the capability and root-filesystem settings behind this request.

## Summary

The current request is to exclude **`kagent` and `ate-system` from two specific Microsoft Azure policies** so the existing kagent/Substrate manifests can be deployed. The two policies concern allowed capabilities and a read-only root filesystem.

The existing workplace model, as described by the delivery owner, uses namespace exclusions. This document therefore requests namespace exclusions for each policy. Workload details explain why each namespace needs the exclusion; they are not selectors that make the Azure exclusion apply only to those containers.

Other policies remain unchanged. If another policy rejects the next deployment, capture that denial and address that policy separately.

## Policy scope by namespace

The following is the complete exclusion request for this phase. 🟧 means **request namespace exclusion from this policy**. It does not mean the exclusion has already been approved or applied.

| Microsoft Azure policy | `kagent` | `ate-system` | Reason |
| --- | --- | --- | --- |
| [Kubernetes cluster containers should only use allowed capabilities](https://github.com/Azure/azure-policy/blob/f096d8de10fb25e71dd7f82b78ded110ec711d73/built-in-policies/policyDefinitions/Kubernetes/ContainerAllowedCapabilities.json) | 🟧 Exclude | 🟧 Exclude | The Substrate worker in `kagent` adds runtime capabilities including `SYS_ADMIN`. The newer `atelet` container in `ate-system` adds `DAC_OVERRIDE`. These additions conflict with a restrictive capability allowlist. |
| [Kubernetes cluster containers should run with a read only root file system](https://github.com/Azure/azure-policy/blob/f096d8de10fb25e71dd7f82b78ded110ec711d73/built-in-policies/policyDefinitions/Kubernetes/ReadOnlyRootFileSystem.json) | 🟧 Exclude | 🟧 Exclude | The saved worker in `kagent` and `atelet` plus several supporting containers in `ate-system` do not set `readOnlyRootFilesystem: true`. The unchanged configuration fails the read-only requirement. |

For **each of these two policies**, the requested namespace additions are:

```text
kagent
ate-system
```

Both reviewed Microsoft definitions expose `excludedNamespaces`. The policy owner must merge these names into the effective exclusion list, preserving existing exclusions. If assigned through an initiative, scope the change to these two definitions; do not use a shared initiative parameter that would also exempt the namespaces from unrelated policies.

The public definitions reviewed were versions **6.2.0** and **6.3.0**, respectively, from Microsoft's [AKS policy reference](https://learn.microsoft.com/en-us/azure/aks/policy-reference). The source links above pin the reviewed definitions. The catalog is not an inventory of the policies actually assigned at work. Workplace assignment versions, parameter values, and denial records have not been inspected here.

🟩 **All other policy settings stay unchanged for this phase.** This includes any separate capability policies. No additional exclusion is requested unless a subsequent deployment denial identifies it as necessary.

## Which components explain the exclusions?

These identities come from the saved native home-lab inventory collected on **1 November 2026 at approximately 11:35 UTC**, using kagent `1.0.0-alpha17` and Substrate `v0.6.0-alpha3`. They provide a reference for the workplace request, not fresh workplace proof.

| Namespace | Reference workload | Relevant setting |
| --- | --- | --- |
| `kagent` | `Deployment/kagent-default`, container `worker`, produced by `WorkerPool/kagent-default`; service account `kagent-default` | Adds `SYS_ADMIN` and other runtime capabilities after dropping `ALL`. `readOnlyRootFilesystem` is unset. |
| `ate-system` | `DaemonSet/atelet`, container and service account `atelet` | Adds `DAC_OVERRIDE` after dropping `ALL`. `readOnlyRootFilesystem` is unset. |
| `ate-system` | `atelet` and API-server objectstore sidecars, plus supporting Substrate services | Several containers leave `readOnlyRootFilesystem` unset. This contributes to the namespace-level filesystem exclusion. |

The saved worker image was `ghcr.io/kagent-dev/substrate/ateworker-gvisor:v0.6.0-alpha3`. Older releases use different container names and security contexts. Verify the actual workplace version and worker namespace before applying the request.

## What is the runtime doing, and why does it need capabilities?

Agent Substrate is the execution layer used by kagent to start, isolate, suspend, and resume agent workloads. Its gVisor worker constructs a sandbox around agent code inside a Kubernetes container.

The reviewed [worker builder](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/cmd/atecontroller/internal/controllers/workerpool_apply.go#L358-L432) assigns capabilities for sandbox setup, root changes, tracing, networking, and filesystem preparation. The worker also performs [filesystem mounts](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/internal/imagecache/bundle_linux.go) and [cgroup preparation](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/internal/ateworker/cgroup/cgroup.go#L38-L95), including operations requiring `CAP_SYS_ADMIN`.

`SYS_ADMIN` is a broad Linux capability. It does not grant Kubernetes `cluster-admin`, but it increases the consequences of a runtime compromise. Ordinary model requests do not themselves need host `SYS_ADMIN`; the capability belongs to the sandbox infrastructure.

The newer [atelet manifest](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/manifests/ate-install/atelet.yaml) gives `atelet` a different capability, `DAC_OVERRIDE`, to clean up actor-owned directories in writable node state. This is why the allowed-capabilities exclusion includes `ate-system` even though the saved newer `atelet` does not explicitly add `SYS_ADMIN`.

The filesystem request admits the existing configuration without a hardening redesign. An unset `readOnlyRootFilesystem` defaults to `false`. Writable runtime volumes do not by themselves prove that the entire container root filesystem must remain writable. No conversion to read-only root filesystems was tested for this request.

## Existing operating controls and exclusion scope

The delivery owner confirmed on 3 November 2026 that deployment into the relevant namespace is restricted to approximately **four or five people in the core application delivery team**, and that changes pass **peer review** before entering it. Namespace RBAC, automation identities, and repository review rules were not independently inspected for this document.

A namespace exclusion removes that Azure policy's check for all matching workloads in the namespace, including containers that already meet the policy. It does not technically limit the allowance to the worker or `atelet`. The operating controls therefore apply to both excluded namespaces and their deployment automation.

The worker executes agent code through gVisor, which provides an isolation boundary described in the [gVisor security introduction](https://gvisor.dev/docs/architecture_guide/intro/). This does not remove trust in the outer worker or its node access. The [Substrate security document](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/docs/security.md) also records unfinished protections; they are not claimed as workplace controls here.

A separate Kyverno allowlist can be proposed as a compensating control for these namespace-wide exclusions. It could constrain workload identities, image digests, capabilities, filesystem settings, and placement. It has not been deployed or validated here. The containment proposal below changes no Azure exemption scope and deploys no controls.

## Responding to the production-risk concern

The concern is valid. A broad Linux capability increases infrastructure risk, and an agent with production-changing tools can make a damaging request even while its sandbox works correctly. These risks need separate controls.

| Risk | Potential impact | Control that addresses it |
| --- | --- | --- |
| Sandbox or runtime compromise | An attacker may reach worker/node state, co-located workloads, mounted credentials, or shared runtime sockets. Further movement depends on reachable services, identities, and vulnerabilities. | Dedicated runtime nodes, enforced placement, restricted node and workload identities, external network controls, and a separate cluster where stronger isolation is needed. |
| Incorrect production tool operation | A permitted but wrong MCP/tool request can change production without any sandbox escape. | No production write authority in the pilot. Enforce tool permissions at the service/API, and reserve future changes for a separate approved executor. |

`SYS_ADMIN` is a Linux capability used by the runtime. It is not a Kubernetes role or an Azure production-management role. That distinction explains the request; it does not remove the risk of the elevated runtime.

### A WorkerPool does not automatically isolate AKS nodes

A Substrate WorkerPool groups worker Pods. It is different from an AKS node pool, which groups node VMs. In the reviewed version, [node selectors and required node affinity are optional WorkerPool template fields](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/pkg/api/v1alpha1/workerpool_types.go#L29-L102). The [builder starts with no node selector or affinity](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/cmd/atecontroller/internal/controllers/workerpool_apply.go#L546-L575) when a template is absent.

The [atelet DaemonSet](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/manifests/ate-install/atelet.yaml#L109-L153) must cover worker nodes. Its reviewed base manifest has tolerations but no node selector, so it can run beyond the intended runtime pool unless explicitly restricted. Confining workers alone is insufficient.

Hard placement limits where these Pods execute. It does not confine their API permissions or network reach. For example, the reviewed [atelet ClusterRole](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/manifests/ate-install/atelet.yaml#L24-L65) includes cluster-wide Pod reads. That is not production write permission, but it demonstrates why hosting-node placement and authorization are separate boundaries.

Dedicated nodes reduce exposure to other application workloads. They do not guarantee that a compromise stays on those nodes. Kubernetes explicitly identifies [lateral movement through shared services despite node isolation](https://kubernetes.io/docs/concepts/security/multi-tenancy/#node-isolation). The reviewed Substrate security document also marks node-level blast-radius containment as unfinished. Its [shared writable socket implementation](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/internal/nodepath/nodepath.go#L41-L57) records a remaining local-state risk. No exploit was reproduced in this review.

### Proposed containment for stakeholder approval

**These are proposed approval conditions, not verified workplace protections.** The recommended first step is a time-limited non-production evaluation, preferably in a separate cluster without production credentials or production write access. If the evaluation shares a production cluster, stakeholders must explicitly accept the remaining shared-cluster risk.

| Boundary | Proposed protection | Evidence needed before claiming protection |
| --- | --- | --- |
| Runtime node placement | Use a dedicated AKS **user** node pool. Require a hard node selector or required affinity on every worker pool and on `atelet`, including its sidecars. Keep production applications off these nodes. Inventory necessary platform DaemonSets and their credentials. | Rendered settings and actual Pod-to-node inventory, including after worker replacement and scale-out. Confirm no `atelet` remains on unrelated nodes. |
| Scheduling and admission | Combine a dedicated-node taint with required placement. Restrict who can change WorkerPools, scheduling fields, node labels, tolerations, and direct node binding. A proposed admission allowlist must restrict elevated containers and approved images inside both Azure-excluded namespaces. | Negative admission tests for an unauthorized workload using the dedicated pool, an elevated Pod targeting another pool, and an unapproved image or capability addition. Allow required platform controllers without a broad bypass. |
| Kubernetes and Azure identities | Review runtime, node/kubelet, controller, gateway, tool, and workload identities separately. Grant only required resource/action scopes. Avoid production secrets or production-authorized MCP services on runtime nodes. Do not assume a new node pool has isolated cloud permissions. | Effective RBAC and Azure role assignments, credential locations, and authorization tests for actual service accounts. Cluster-scoped platform permissions remain a documented residual risk. |
| Network access | Use default-deny Pod traffic with explicit dependencies. Independently restrict node-originated access to production endpoints and metadata credentials using supported network controls outside the potentially compromised worker. Preserve required AKS/control-plane traffic. | Negative connectivity tests from the actor, outer worker, and representative node-originated path. Verify the actual CNI, routing, firewall, and subnet enforcement. Pod NetworkPolicies alone are not proof against a compromised node. |
| Production operations | Give the pilot only approved read-only tools, backed by read-only service identities. Do not rely on an agent prompt saying it will not write. Future writes require a separate executor and server-enforced approval tied to the exact operation and target. | Tool/API authorization denies writes, including direct calls that bypass the agent's normal UI. Verify the real tool server's identity, not just the agent's Kubernetes service account. Use synthetic targets for destructive-operation denial tests. |
| Node and runtime maintenance | Pin approved runtime images and sandbox assets, maintain node/kernel patches, restrict node administration, and set resource budgets. | Image/asset digests, node-image and patch records, admin access inventory, and observed resource limits. |
| Detection and response | Record runtime lifecycle, API/tool calls, and policy decisions with sensitive data redacted. Provide a tested way to stop invocations, revoke credentials, quarantine nodes, and rebuild the runtime pool after suspected compromise. | Audit samples, alert ownership, expiry/review date, and a shutdown/revocation exercise. Removing an Azure exclusion alone does not terminate existing Pods or revoke credentials. |

The [Kubernetes dedicated-node guidance](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/#example-use-cases) requires affinity in addition to tolerations when workloads must stay on dedicated nodes. Microsoft's [AKS node-pool guidance](https://learn.microsoft.com/en-us/azure/aks/use-system-pools) distinguishes user pools from the critical system pool. [Kubernetes RBAC guidance](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) and [AKS managed-identity guidance](https://learn.microsoft.com/en-us/azure/aks/managed-identity-overview) support separate permission reviews. [NetworkPolicy limitations](https://kubernetes.io/docs/concepts/services-networking/network-policies/#what-you-cant-do-with-network-policies-at-least-not-yet) explain why Pod policy is only one layer.

The shared-cluster residual risk remains. If that risk is unacceptable to the production platform owner, move the evaluation to a separate cluster with separately bounded identities and networking before approval. A separate cluster still needs those identity and network controls to protect other systems.

### Draft response to the approver

> Thank you for raising this. We agree that approval should include the owners of the affected platform and production services, with security, IAM, and network stakeholders as appropriate.
>
> The technical requirement is a Linux capability on the Substrate runtime container that constructs the agent sandbox. It does not itself assign kagent Kubernetes cluster-admin or an Azure production-management role. Our current Azure mechanism is broader, however, because the two policy exclusions cover the named namespaces. We propose restricted admission and deployment ownership to constrain what can use those exclusions.
>
> We propose a time-limited non-production pilot with workers and atelet confined to dedicated nodes, reviewed identities and network paths, and read-only tools with no production write authority. We will provide placement evidence and negative authorization/connectivity tests before treating these as implemented protections. Any future production-changing action would need a separate approved executor.
>
> Dedicated nodes reduce exposure but do not guarantee containment within a shared cluster. If that remaining risk is unacceptable, we propose a separate evaluation cluster. We are seeking agreement on these bounded conditions and the evidence required for approval, rather than asserting that the capability is risk-free.

This is a draft for the delivery owner to share. No stakeholder has been contacted, and no approval is claimed. Record the actual platform, security, IAM/network, and affected service owners' decisions before proceeding. The Azure exemption request remains limited to allowed capabilities and read-only root filesystem for `kagent` and `ate-system`.

## Complete this two-policy request

The policy owner needs the actual assignment or initiative-member reference for each named definition, its current parameters and exclusions, and the matching workplace workload/version evidence. Record the request owner, review date, and approval through the existing process.

After an approved exclusion change, retry the intended deployment and retain its result. A new denial becomes the evidence for a separate follow-up. These two exclusions do not establish that every remaining policy will pass or that the runtime is ready for workplace use.

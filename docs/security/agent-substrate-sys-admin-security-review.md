# Agent Substrate SYS_ADMIN security review

Updated 3 November 2026 for security and core application delivery reviewers.

Related [security-context README](agent-substrate-security-context-README.md) records the capability and root-filesystem settings behind this request.

## Summary

The delivery owner has clarified that Substrate will run in its **own separate engineering cluster**, away from production and unrelated workloads. This is the intended deployment boundary, not a claim that workplace isolation has already been verified. The initial requested target is engineering only; stakeholder approval remains pending.

The current central Azure assignment design uses namespace exclusions that may affect every cluster inheriting the assignment. The proposal is to exclude `kagent` and `ate-system` from **two Azure policies only**, while Kyverno restores the corresponding restrictions on every affected cluster. Only the engineering cluster receives reviewed Substrate allowances. Broad Azure assignment scope is a characteristic of this proposed operating model, not an inherent requirement of Azure Policy.

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

Both reviewed Microsoft definitions expose `excludedNamespaces`. After the Kyverno protection below is verified on every affected cluster, the policy owner can merge these names into the effective exclusion lists, preserving existing exclusions. If assigned through an initiative, scope the change to these two definitions; do not use a shared initiative parameter that would also exempt the namespaces from unrelated policies.

The public definitions reviewed were versions **6.2.0** and **6.3.0**, respectively, from Microsoft's [AKS policy reference](https://learn.microsoft.com/en-us/azure/aks/policy-reference). The source links above pin the reviewed definitions. The catalog is not an inventory of the policies actually assigned at work. Workplace assignment versions, parameter values, and denial records have not been inspected here.

🟩 **All other policy settings stay unchanged for this phase.** This includes any separate capability policies. No additional exclusion is requested unless a subsequent deployment denial identifies it as necessary.

## Cluster-specific enforcement with Kyverno

The Azure namespace exclusion removes a check; it does not grant a Kubernetes or Azure role. The effective permission must be narrowed again through protected, cluster-local admission policy.

| Cluster and workload | Central Azure treatment for these two policies | Required Kyverno outcome |
| --- | --- | --- |
| Approved separate engineering cluster, reviewed Substrate workloads in `kagent` and `ate-system` | 🟧 Namespace exclusions may apply. | 🟧 Permit only the reviewed runtime identities, images, capability sets, and filesystem deviations. |
| Approved engineering cluster, all other workloads | Preserve applicable Azure controls; the two excluded namespaces have the documented Azure gap. | 🟩 Enforce the baseline. An engineering cluster is not a blanket allowance for every Pod. |
| Production and every other affected cluster, including any namespaces also named `kagent` or `ate-system` | 🟧 The same namespace exclusions may be inherited. | 🟥 Deny the Substrate capability/filesystem deviations. 🟩 Keep the baseline in Enforce; install no engineering allowance. |

Here, red means deny the exceptional request. It does not mean deny ordinary compliant kagent workloads. The exact Azure assignment scope and cluster inventory still need confirmation.

### How to make the cluster restriction reliable

A Kyverno `ClusterPolicy` governs the cluster where it is installed; it is not a fleet-wide controller. Deploy a common baseline through the protected GitOps configuration for **every cluster whose Azure coverage changes**. Render the Substrate allowance only into the explicitly approved engineering cluster's configuration, identified by the platform's managed cluster inventory. Do not decide approval from a Pod/namespace label or a ConfigMap that workload deployers can edit.

The baseline must reproduce the two actual Azure controls, including configured allowed capabilities and required capability drops, the read-only root-filesystem check, and existing approved scope. It must cover the Azure-excluded namespaces, main/init/ephemeral containers, controller-created Pods, and relevant update paths. Confirm Kyverno filters, webhook selectors, and existing-violation behavior do not create bypasses.

On engineering, a narrowly matched allowance must retain bounded validation. A generic namespace exemption or a PolicyException that skips a capability rule without a replacement check could allow arbitrary capabilities. Require the approved workload/container, service account, immutable image digest, and exact allowed additions. Scope filesystem deviations to reviewed runtime containers. Other Pods in both namespaces keep the baseline.

[Kyverno validation](https://kyverno.io/docs/policy-types/cluster-policy/validate/) distinguishes blocking Enforce mode from reporting-only Audit mode. [Policy exceptions](https://kyverno.io/docs/guides/exceptions/) need separate scope and ownership controls. Use the syntax supported by the installed version. This document supplies the design; it does not claim a tested policy bundle or Azure-equivalence proof.

Policy administrators must restrict changes to cluster enrollment, GitOps overlays, Kyverno policies/exceptions, webhook configuration, namespace filters, and the identities that can alter them. Peer review by the core delivery team remains part of the operating model. Neither that process nor a workload label substitutes for admission enforcement.

### Roll out without a fleet-wide protection gap

1. Inventory every cluster affected by the central assignment, the two effective definitions/parameters, and existing approved exclusions. Unknown or unprotected clusters are unresolved rollout gaps.
2. Deliver and verify the Kyverno baseline in **Enforce** on each affected cluster. Configure and verify fail-closed webhook behavior for the covered requests, compatible availability settings, and ongoing drift reporting. A Kyverno installation or an Audit report alone is insufficient.
3. Deliver the bounded engineering-only allowance through its protected cluster overlay. Test both permitted runtime shapes and rejected deviations. Prove negative results originate from Kyverno; an Azure or PSA rejection alone does not prove the replacement control works.
4. Obtain stakeholder approval, then make the two central Azure exclusion changes. Re-test the permitted engineering workloads and denied requests elsewhere after the Azure checks are removed from those namespaces. If coverage fails, restore the Azure exclusion settings rather than leave an affected cluster unprotected.
5. Require the same baseline before onboarding new clusters that inherit these exclusions. Do not copy the engineering allowance to another cluster without a separate approval. Retain evidence and alerts for missing, weakened, stale, or bypassed enforcement.

The current lab results are not this fleet proof. Workplace Kyverno versions, policies, failure behavior, cluster enrollment, engineering exceptions, and runtime isolation remain unverified. No cluster or Azure assignment was changed by this document.

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

Kyverno is the proposed compensating enforcement layer for the central exclusions. The engineering-only allowance and baseline on every other affected cluster are required parts of this design. They have not been deployed or validated here. The Azure request remains limited to the two named policies.

## Responding to the production-risk concern

The proposed boundary is a **separate engineering cluster**, not a node pool sharing production's Kubernetes control plane. A runtime compromise could still expose that engineering cluster's nodes, workloads, runtime state, snapshots, and credentials. Cross-system impact then depends on reachable services, identities, or additional vulnerabilities. Separate clusters reduce the shared-cluster exposure; they do not automatically remove production network paths or production-authorized tool credentials.

`SYS_ADMIN` is a Linux runtime capability, not a Kubernetes role or an Azure production-management role. An agent can also make a damaging authorized tool call without escaping its sandbox. Runtime containment and tool authorization therefore need separate evidence.

| Boundary | Proposed protection in the engineering rollout | Evidence needed before claiming protection |
| --- | --- | --- |
| Cluster separation | Run Substrate only in the approved separate engineering cluster. Keep production and unrelated workloads out of it. Install no Substrate allowance on other clusters. | Managed cluster inventory, GitOps enrollment and rendered policy differences, workload inventory, and negative admission tests on other affected clusters. |
| Runtime placement | Restrict workers and `atelet` to the engineering runtime nodes. A Substrate WorkerPool groups worker Pods; it does not itself create an AKS node-pool boundary. Use hard placement and taints where nodes are reserved within engineering. | Actual worker and `atelet` placement after replacement/scale-out; inventory remaining platform DaemonSets and their credentials. |
| Identities and production operations | Review runtime, node/kubelet, controller, gateway, and tool identities separately. Give pilot tools only approved read-only access. Do not put production-changing credentials in the engineering runtime. Future writes require a separate approved executor. | Effective Kubernetes/Azure permissions and tool-server authorization tests, including synthetic denied write requests that bypass the normal agent UI. |
| Network access | Restrict both Pod and node-originated traffic to approved dependencies. Independently block unapproved production and metadata-credential paths, preserving required platform traffic. | Positive dependency tests and negative connectivity tests covering actor, outer worker, and node paths using the actual CNI, routing, and external network controls. |
| Maintenance and response | Pin approved runtime images/assets, patch nodes, restrict administration, bound resources, monitor policy drift and API/tool activity, and provide stop/revoke/quarantine procedures. | Digests, patch/access records, redacted audit samples, an expiry/review date, and a tested incident-response procedure. |

The reviewed [WorkerPool template](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/pkg/api/v1alpha1/workerpool_types.go#L29-L102) supports optional selectors and affinity. The [atelet base manifest](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/manifests/ate-install/atelet.yaml#L109-L153) has no node selector. Its [ClusterRole](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/manifests/ate-install/atelet.yaml#L24-L65) includes cluster-wide Pod reads. These source facts require placement and identity verification; they are not evidence of the workplace configuration.

[Kubernetes node-isolation guidance](https://kubernetes.io/docs/concepts/security/multi-tenancy/#node-isolation) explains the residual shared-cluster risk avoided by choosing a separate cluster. [NetworkPolicy limitations](https://kubernetes.io/docs/concepts/services-networking/network-policies/#what-you-cant-do-with-network-policies-at-least-not-yet) explain why Pod policy alone does not establish containment after node compromise. The reviewed Substrate security document marks node-level containment as unfinished, and its [shared socket implementation](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/internal/nodepath/nodepath.go#L41-L57) records a local-state risk. No exploit was reproduced here.

### Draft response to the approver

> We agree that the relevant stakeholders should approve the deployment boundary and controls. Substrate is intended to run in its own separate engineering cluster, away from production and unrelated workloads. The requested Linux capability belongs to its sandbox runtime; it does not itself assign kagent Kubernetes cluster-admin or an Azure production-management role.
>
> Our central Azure assignment design may apply the two namespace exclusions across multiple clusters. We propose to restore both restrictions through Kyverno in Enforce mode on every affected cluster, with a bounded runtime allowance deployed only to the approved engineering cluster. Production and other clusters would receive no Substrate allowance, even if they contain namespaces with the same names. The Kyverno baseline must be verified before the central exclusions change.
>
> We will provide fleet coverage, engineering-only configuration, admission-denial evidence, runtime placement, identity and network tests, monitoring, and rollback arrangements for stakeholder review. Engineering tools will have no production application write authority in the initial rollout; any future production changes require separate authorization and execution controls.
>
> This is a proposal for a bounded engineering deployment with evidence, expiry, and accountable owners. It is not a claim that broad capabilities are risk-free, or that cluster separation alone protects every connected production system.

This is a draft for the delivery owner to share. No stakeholder has been contacted and no approval is claimed. Record the actual platform, security, IAM/network, and affected service owners' decisions. The Azure exemption request remains limited to allowed capabilities and read-only root filesystem for `kagent` and `ate-system`.

## Complete this two-policy request

The policy owner needs the actual assignment or initiative-member reference for each named definition, its current parameters and exclusions, and the matching workplace workload/version evidence. Record the request owner, review date, and approval through the existing process.

Require verified Kyverno coverage across the affected fleet before the central change, and verify engineering-only runtime admission afterwards. Retry the intended engineering deployment and retain its result. A new denial becomes evidence for a separate follow-up. These two exclusions do not establish that every remaining policy will pass or that the runtime is ready for workplace use.

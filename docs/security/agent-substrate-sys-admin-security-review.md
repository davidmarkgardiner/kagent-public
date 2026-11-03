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

A separate Kyverno allowlist could later constrain workload identities, image digests, capabilities, and filesystem settings inside these namespaces. That remains a proposal. This phase changes documentation only and requests no Kyverno deployment or changes to other Azure policies.

## Complete this two-policy request

The policy owner needs the actual assignment or initiative-member reference for each named definition, its current parameters and exclusions, and the matching workplace workload/version evidence. Record the request owner, review date, and approval through the existing process.

After an approved exclusion change, retry the intended deployment and retain its result. A new denial becomes the evidence for a separate follow-up. These two exclusions do not establish that every remaining policy will pass or that the runtime is ready for workplace use.

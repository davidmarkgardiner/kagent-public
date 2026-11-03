# Agent Substrate SYS_ADMIN security review

Prepared 3 November 2026 for security and core application delivery reviewers.

Related [security-context README](agent-substrate-security-context-README.md) records read-only filesystem, privilege escalation, root user, profile, sidecar, and host-mount findings. Baseline restrictions apply to both `kagent` and `ate-system`, with exceptions limited to approved runtime containers.

## Summary

Agent Substrate is the execution layer used by kagent to start, isolate, suspend, and resume agent workloads. Its gVisor worker runs a sandbox runtime inside a Kubernetes container. The runtime needs elevated Linux permissions to construct that sandbox and manage its filesystems and resource groups.

`SYS_ADMIN` is a Linux capability, written `CAP_SYS_ADMIN` in kernel documentation. It is broad and security-sensitive. It does not grant Kubernetes `cluster-admin`, but it increases the consequences of a runtime compromise.

The capability belongs to the **sandbox infrastructure container**. A model request or ordinary MCP tool call does not itself need host `SYS_ADMIN`. Agent code executes behind the gVisor boundary. The runtime remains trusted infrastructure with access to node resources.

The proposed security position is a bounded runtime exception, supported by restricted deployment access, peer review, and an additional Kyverno allowlist. Approval must identify the actual installed version and workload. A blanket namespace exemption would permit more than this requirement.

## Policy scope by namespace

This is the **proposed policy target for the reviewed Substrate `v0.6.0-alpha3` configuration**, using the saved lab identities. It is not a workplace deployment or an approved exception list. Confirm workplace versions, identities, and image digests before applying it.

The colors describe the proposed decision, not current compliance or deployed enforcement.

| Color and label | Meaning |
| --- | --- |
| 🟩 Baseline | Apply the restriction in both namespaces. |
| 🟧 Runtime allowance | Keep the policy and permit only the named runtime container's reviewed deviation. Approval is still required. |
| 🟨 Review needed | A saved setting is unset or compatibility is unproven. Harden it or justify a specific exception before Enforce. |
| 🟥 Deny | Reject the broader permission or namespace-wide exemption. |

| Policy required in both namespaces | Baseline behavior | `kagent` scope | `ate-system` scope |
| --- | --- | --- | --- |
| `require-drop-all` | Every container explicitly sets `capabilities.drop: [ALL]`. | 🟩 Baseline, including the Substrate worker. | 🟩 Baseline, including `atelet` and objectstore sidecars. |
| `allow-capability-additions` | Only `NET_BIND_SERVICE` may be added under the supplied baseline. | 🟧 Only `Deployment/kagent-default`, container `worker`, may use the reviewed worker capability allowlist below. Ordinary containers retain the baseline. | 🟧 Only `DaemonSet/atelet`, container `atelet`, may add `DAC_OVERRIDE`. Its objectstore sidecar adds no capabilities. No `SYS_ADMIN` allowance is established here for this version. |
| `deny-escalation` | Every container sets `allowPrivilegeEscalation: false`. | 🟧 The approved `worker` needs an escalation allowance because it holds `SYS_ADMIN`. Controller, UI, and ordinary containers retain `false`. | 🟨 `atelet`, objectstore sidecars, and several control-plane containers leave it unset. Target `false`; compatibility or a specific exception must be established. Do not allow escalation across the namespace. |
| `deny-privileged` | Require `privileged: false`, or its default. | 🟩 Keep `privileged: false` on the newer worker. 🟥 Deny `privileged: true`. | 🟩 No full-privileged requirement in the saved newer `atelet` configuration. 🟥 Deny `privileged: true`. |
| `deny-host-namespaces` | Deny `hostNetwork`, `hostPID`, and `hostIPC`. | 🟩 Baseline. No exception evidenced. | 🟩 Baseline. No exception evidenced. |
| `deny-hostpath` | Deny hostPath except exact reviewed runtime volumes and mounts. | 🟧 The approved worker Pod may declare and mount `/var/lib/ate`, writable with `HostToContainer` propagation. | 🟧 The `atelet` Pod needs exact node volumes. The main container mounts `/var/lib/ate`, `/var/lib/kubelet/plugins`, and `/var/lib/kubelet/device-plugins` writable, and `/dev` read-only at `/host/dev`. Its objectstore sidecar mounts only `/var/lib/ate` from those host paths. |
| Read-only root filesystem, additional control | Require `readOnlyRootFilesystem: true`, with separately approved writable volumes. | 🟩 Controller and UI already request it. 🟨 Worker leaves it unset; test compatibility or justify an exception. | 🟩 Credential provider already requests it. 🟨 `atelet`, sidecars, and several other components leave it unset; review each container. |
| Non-root execution, additional control | Require `runAsNonRoot: true`. | 🟧 The approved worker runs as UID/GID 0. Ordinary containers retain the non-root target. | 🟧 `atelet` and its objectstore sidecar run as UID/GID 0. 🟨 Other unset non-root settings need their own review. |
| Seccomp and AppArmor, additional controls | Require approved restrictive profiles; use `RuntimeDefault` where supported and compatible. | 🟧 Only the approved worker uses the reviewed `Unconfined` profiles. Ordinary containers retain restrictive profiles. | 🟨 `atelet` and several control-plane components leave profiles unset. Verify defaults and compatibility; no namespace-wide `Unconfined` allowance. |
| Sysctl allowlist, additional control | Permit only approved sysctls and values. | 🟩 No worker-specific sysctl allowance evidenced. | 🟨 Review `atenet-egress` with `net.ipv4.ip_unprivileged_port_start=0` against the actual policy. This is a separate gateway setting, not a worker exception. |

The six named rules above exist in the lab policy [`lab-runtime-permissions`](../../work-agent-bundles/kyverno-runtime-permissions-lab/policies/audit.json). Read-only root filesystem, non-root, profile, and sysctl controls are **additional proposed controls**, not rules already supplied by that policy. The lab kept both namespaces in **Audit**. The target is reviewed Enforce coverage with tested runtime allowances; no such rollout is claimed here.

The worker capability allowlist is `NET_ADMIN`, `SYS_ADMIN`, `SYS_CHROOT`, `SYS_PTRACE`, `SETUID`, `SETGID`, `SETPCAP`, `DAC_OVERRIDE`, `FOWNER`, `CHOWN`, `MKNOD`, `NET_RAW`, and `SETFCAP`, with `drop: [ALL]`. It applies only to the approved worker container, not every Pod in `kagent`. Additional worker pools need separate scope approval. Runtime allowances must also match the reviewed service account and immutable image digest.

**Privilege escalation and full privileged mode are different settings.** In the newer worker, `SYS_ADMIN` requires an escalation allowance while `privileged: false` stays enforced. In the older `v0.0.9` path, both the worker and `atelet` requested `privileged: true`; that needs a separate version-specific decision for both namespaces. Do not apply the newer matrix to that older installation unchanged. See the [Kubernetes escalation semantics](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/).

🟥 Do not exclude all of `kagent` or `ate-system`, permit arbitrary capability additions, or treat a shared service account or caller-supplied label as sufficient authorization. The operating controls remain restricted core-team deployment and peer review. The policy, its exceptions, and namespace security labels also need restricted ownership.

## Which component and namespace require it?

The following identities were recovered from the saved Kubernetes Pod and Deployment inventory collected on **1 November 2026 at approximately 11:35 UTC**. This is historical native home-lab evidence, using kagent `1.0.0-alpha17` and Substrate `v0.6.0-alpha3`. It is not an inspection of the workplace cluster.

| Component | Kubernetes identity in the saved lab | Namespace | Permission observed |
| --- | --- | --- | --- |
| gVisor sandbox worker | `WorkerPool/kagent-default` produces `Deployment/kagent-default`; container `worker`; service account `kagent-default`; label `ate.dev/worker-pool=kagent-default` | `kagent` | Explicit `SYS_ADMIN` and other capabilities, root UID/GID, `privileged: false` |
| Additional lab worker pools | Deployments `agentshield-poc` and `graph-context-lab`; container `worker`; service account `kagent-default` | `kagent` | The same elevated worker security context. These lab pools are not automatically part of a workplace exception. |
| Node supervisor | `DaemonSet/atelet`; container and service account `atelet` | `ate-system` | Root UID/GID; drops `ALL`, adds `DAC_OVERRIDE`. No explicit `SYS_ADMIN` or full privileged mode in this saved version. |
| Substrate controller and API server | `Deployment/ate-controller` and `Deployment/ate-api-server` | `ate-system` | Neither container explicitly requests `SYS_ADMIN` or privileged mode in the saved inventory. |

The worker image was `ghcr.io/kagent-dev/substrate/ateworker-gvisor:v0.6.0-alpha3`. Its Pod name is generated and changes with rollout. The exception must use the reviewed workload identity and image digest, not one transient Pod name.

The complete saved worker capability addition set was `NET_ADMIN`, `SYS_ADMIN`, `SYS_CHROOT`, `SYS_PTRACE`, `SETUID`, `SETGID`, `SETPCAP`, `DAC_OVERRIDE`, `FOWNER`, `CHOWN`, `MKNOD`, `NET_RAW`, and `SETFCAP`, after `drop: [ALL]`. Approval therefore needs to assess the complete runtime context.

**`ate-system` and the worker namespace are different scopes.** The worker runs in its WorkerPool's namespace, which was `kagent` in this lab. Workplace naming and placement may differ. A Kubernetes Service routes traffic; the capability is requested by a Pod's container security context.

### Older installations have broader permissions

The earlier AKS work used Substrate `v0.0.9`. That version's controller creates the worker container named `ateom`, running as root with `privileged: true`. Its upstream `atelet` DaemonSet also requests `privileged: true` in `ate-system`. A request for full privileged mode is broader than an explicit `SYS_ADMIN` addition.

These differences are verified against the [v0.0.9 worker builder](https://github.com/kagent-dev/substrate/blob/v0.0.9/cmd/atecontroller/internal/controllers/workerpool_apply.go) and [v0.0.9 atelet manifest](https://github.com/kagent-dev/substrate/blob/v0.0.9/manifests/ate-install/atelet.yaml). The newer context is defined in the [v0.6.0-alpha3 worker builder](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/cmd/atecontroller/internal/controllers/workerpool_apply.go#L358-L432).

The exact workplace release, rejected Pod, namespace, image digest, and denying policy have not been supplied for this review. The identities above are a concrete reference, not a claim that the workplace uses the same names or permissions.

## What does SYS_ADMIN do here, and why is it needed?

The worker creates the execution environment around an agent. The reviewed implementation uses elevated operations for the following work.

| Runtime operation | Reason for elevated permissions | Source evidence |
| --- | --- | --- |
| Construct the sandbox filesystem and execution boundary | Mount operations and root changes require permissions unavailable to an ordinary restricted application Pod. The worker builder associates `SYS_ADMIN`, `SYS_CHROOT`, and `SYS_PTRACE` with sandbox setup and application tracing. | [Worker capability definition](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/cmd/atecontroller/internal/controllers/workerpool_apply.go#L358-L432) |
| Compose actor root filesystems from cached OCI layers | The worker performs filesystem mounts and finalizes image layers, including operations requiring `CAP_SYS_ADMIN`. | [Image bundle implementation](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/internal/imagecache/bundle_linux.go) |
| Prepare per-actor resource accounting | The worker can remount its cgroup filesystem writable and create child cgroups for actor resource accounting. That remount requires `CAP_SYS_ADMIN`. | [Cgroup delegation implementation](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/internal/ateworker/cgroup/cgroup.go#L38-L95) |
| Suspend and resume actors | The worker invokes gVisor checkpoint and restore and reconstructs the surrounding runtime environment. The permission requirement covers runtime setup as well as this lifecycle. | [gVisor worker lifecycle](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/cmd/ateworker-gvisor/main.go) |

This is an implementation requirement of the reviewed Substrate runtime. It is not proof that every possible sandbox implementation needs this exact capability set. Removing permissions requires a supported runtime change and successful cold-start, checkpoint, restore, cleanup, and isolation tests. No reduced-capability configuration was tested for this review.

## Existing protections and their limits

### Deployment access and peer review

The delivery owner confirmed on 3 November 2026 that deployment into the relevant namespace is restricted to approximately **four or five people in the core application delivery team**, and that changes must pass peer review before entering it.

These operating controls reduce who can introduce or change elevated workloads. The approval record can substantiate them with namespace RoleBindings, relevant ClusterRoleBindings, deployment automation identities, and repository branch/review rules. Those access records were not independently inspected for this document. The same restrictions need to cover the worker namespace as well as `ate-system` where applicable.

### Controls visible in the saved lab and reviewed source

| Protection | Evidence and limitation |
| --- | --- |
| gVisor separates agent code from the host kernel | The worker hosts agent execution through `runsc`. gVisor provides an application-kernel boundary and its own defense mechanisms. This does not remove trust in the outer worker. See the [gVisor security introduction](https://gvisor.dev/docs/architecture_guide/intro/). |
| Explicit worker capability set in the newer version | The saved worker drops `ALL` before adding the runtime set and has `privileged: false`. This reduces permissions relative to full privileged mode, but retains substantial authority. |
| Separate Pod host namespaces | The saved workers have no enabled `hostNetwork`, `hostPID`, or `hostIPC`. Their node storage access still requires review. |
| Agent permissions are configured separately | The actor OCI specification takes capabilities from the actor's own container specification. The worker's host capabilities are not a blanket actor grant. See the [actor OCI specification builder](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/internal/ocispec/ocispec.go#L79-L104). |
| Admission controls and reporting were exercised in the lab | The published [Kyverno lab results](../../work-agent-bundles/kyverno-runtime-permissions-lab/LAB-RESULTS.md) record 34 successful admission cases covering capabilities and other Pod permissions. Existing Substrate workers remained in **Audit**, where their elevated settings appeared as findings. An enforced Substrate exception was not tested. |

The newer worker also uses **unconfined seccomp and AppArmor**, runs as root, and has a writable hostPath mounted at `/var/lib/ate` with `HostToContainer` propagation. The hostPath contains shared runtime state and sockets. The [upstream node-path implementation](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/internal/nodepath/nodepath.go#L41-L57) explicitly records socket replacement as a remaining risk of this shared writable mount. Namespace membership does not contain that node access.

The reviewed [Substrate security document](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/docs/security.md) describes sandboxing, identity, mTLS, and gateway controls, but also identifies unfinished authorization, storage encryption, network filtering, and node containment work. These cannot all be claimed as deployed protections. Dedicated, tainted runtime nodes, verified network restrictions, and approved snapshot storage are proposed compensating controls until workplace evidence establishes their actual configuration.

## Proposed additional Kyverno protection

A namespace-specific allowlist can strengthen the request by turning the reviewed runtime specification into an admission rule. It supplements restricted deployment access and peer review. **This policy is proposed; it has not been implemented or deployed by this document.** Its syntax must match the installed Kyverno version.

The intended admission behavior is as follows.

| Rule | Required outcome |
| --- | --- |
| Approved workloads and images only | Permit the identified runtime controllers and their generated Pods, using approved service accounts and immutable image digests. Reject unrelated workloads, unexpected sidecars, and altered commands or mounts. Restrict who can create WorkerPools or change their templates. A caller-supplied label or owner reference alone is insufficient. |
| Exact permission allowance | Permit only the capability set and security context reviewed for that component and version. For the newer worker, retain `privileged: false` and `drop: [ALL]`. Reject additional capabilities or broader host access. Any older full-privileged requirement needs a separate explicit decision. |
| Bounded node access | Permit only reviewed hostPath paths, mount modes, propagation settings, and node placement. Reject host networking, host PID, and host IPC unless separately justified. |
| Complete admission coverage | Cover direct Pods, controller templates, init containers, and ephemeral-container updates. Allow the actual Substrate, Deployment, ReplicaSet, and GitOps controller identities needed for reconciliation without exempting all their requests. |
| Protected policy ownership | Restrict changes to Kyverno policies, PolicyExceptions, webhook settings, namespace security labels, RBAC, and the allowlist itself. Keep the allowlist in the peer-reviewed delivery process. Limit Pod exec, attach, debug, and ephemeral-container access separately. |
| Enforcement and evidence | Validate existing workloads in Audit first. After approval, use Enforce for the bounded scope, verify fail-closed admission behavior, and retain current policy reports and API audit records. Reports alone do not block deployment. |

[Kyverno validation rules](https://kyverno.io/docs/policy-types/cluster-policy/validate/) support blocking requests that do not match approved properties. An allowlist makes an exception more specific; it does not make `SYS_ADMIN` harmless or prevent compromise of an already admitted runtime.

Kyverno cannot override a denial from Azure Policy/Gatekeeper or built-in Pod Security Admission. The control owner must approve any change to the actual denying assignment or constraint. [Pod Security Admission exemptions](https://kubernetes.io/docs/concepts/security/pod-security-admission/) also need separate consideration. A namespace-wide permissive PSA setting removes that PSA layer for other Pods, so complementary admission enforcement and restricted namespace access matter.

## Information required to close the workplace review

The approval record still needs the following target-specific evidence.

- The rejected admission message, exact Azure Policy definition/assignment or other denying rule, and affected fields.
- The installed Substrate version, controller/DaemonSet name, container name, namespace, WorkerPool, service account, and approved image digest.
- The actual Pod and controller security contexts, host mounts, namespace labels, and runtime node placement.
- The namespace deployment and debug access inventory, automation identities, and peer-review rules that support the stated operating controls.
- The reviewed Kyverno allowlist and tests that allow the genuine runtime while denying an altered image, extra capability, extra mount, injected container, or unauthorized workload.
- A named exception owner, expiry/review date, and rollback that stops affected workers through the approved delivery flow and restores enforcement. Removing an exception alone does not terminate existing Pods.
- A successful target cold-start and suspend/resume test, plus checks of network isolation and snapshot protection. A running Pod alone does not prove these properties.

The existing [workplace Audit-pilot guide](../../work-agent-bundles/kyverno-runtime-permissions-lab/WORKPLACE-START-HERE.md#keep-the-substrate-rollout-as-a-separate-acceptance-step) keeps this runtime exception as a separate acceptance step. This document provides its technical rationale and proposed safeguards. It does not grant an exception or change cluster policy.

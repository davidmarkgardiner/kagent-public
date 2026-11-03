# kagent and Agent Substrate security-context notes

Prepared 3 November 2026. Read alongside the [SYS_ADMIN security review](agent-substrate-sys-admin-security-review.md), which explains runtime permissions, ownership, and proposed safeguards.

## What else needs security review?

The saved Substrate workers have more security-context exceptions than `SYS_ADMIN`. Their root filesystem is not configured read-only, privilege escalation is not disabled, they run as root, and seccomp and AppArmor are explicitly unconfined. They also mount writable node storage.

The kagent controller and UI have different settings. Both explicitly use a read-only root filesystem, disable privilege escalation, and drop all capabilities. Permission exceptions must therefore identify individual runtime containers rather than cover every Pod in a namespace.

The capability restrictions and other baseline controls must cover **both `kagent` and `ate-system`**. Any relaxation needs a reviewed component-specific exception. A missing hardening setting is a finding to assess, not evidence that the component requires an exception.

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

## Evidence scope

The observations below come from the saved native home-lab Pod inventory collected on **1 November 2026 at approximately 11:35 UTC**, with kagent `1.0.0-alpha17` and Substrate `v0.6.0-alpha3`. The review includes normal containers and init containers, including restartable init containers used as sidecars. No ephemeral containers were present in these two namespaces in that inventory.

These are stored API settings interpreted using Kubernetes semantics. They are not a fresh workplace inspection or a measurement of each running process's effective privileges. An absent field is recorded as **unset**, even where Kubernetes defines a default.

## Read-only filesystems and privilege escalation are separate controls

| Setting | Meaning |
| --- | --- |
| `readOnlyRootFilesystem: true` | Makes the container root filesystem read-only. Unset defaults to `false`. |
| `volumeMounts[].readOnly: true` | Marks that volume mount read-only. This is separate from the root filesystem setting. A container can have a read-only root filesystem and writable mounted storage. |
| `allowPrivilegeEscalation: false` | Uses `no_new_privs` to prevent a process gaining privileges through execution. Unset defaults to `true`. |
| `privileged: true` | Enables full privileged-container mode. This is broader than permitting escalation or adding one capability. |

Kubernetes does not permit combining `allowPrivilegeEscalation: false` with full privileged mode or `CAP_SYS_ADMIN`. Therefore, a worker with `privileged: false` and `SYS_ADMIN` still cannot claim escalation is disabled. See the [Kubernetes security-context guide](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) and [SecurityContext API reference](https://kubernetes.io/docs/reference/kubernetes-api/core/pod-v1/#securitycontext).

Permitting escalation describes the security setting. It does not prove that a process escalated privileges or that a vulnerability was exploited. A read-only root filesystem also does not remove elevated capabilities or protect a writable hostPath.

## Component settings in the saved inventory

The `privileged` column reports explicit settings or the Kubernetes default. Pod-level `runAsNonRoot` and seccomp settings are included where containers inherit them.

| Namespace and workload/container | `readOnlyRootFilesystem` | `allowPrivilegeEscalation` | `privileged` | Other observed settings |
| --- | --- | --- | --- | --- |
| `kagent`, `Deployment/kagent-default`, `worker` | Unset; default `false` | Unset; default `true`, also tied to `SYS_ADMIN` | Explicit `false` | UID/GID 0; `drop: [ALL]` plus the runtime capability set; seccomp and AppArmor `Unconfined`; writable `/var/lib/ate` hostPath. |
| `kagent`, workers in `agentshield-poc` and `graph-context-lab` | Unset; default `false` | Unset; default `true`, also tied to `SYS_ADMIN` | Explicit `false` | Same worker settings. These additional lab pools are not automatically in scope for a workplace exception. |
| `ate-system`, `DaemonSet/atelet`, `atelet` | Unset; default `false` | Unset; default `true` | Unset; default `false` | UID/GID 0; drops `ALL`, adds `DAC_OVERRIDE`; seccomp and AppArmor unset; writable node mounts. |
| `ate-system`, `atelet` restartable init container `objectstore-plugin` | Unset; default `false` | Unset; default `true` | Unset; default `false` | UID/GID 0; drops `ALL`; writable `/var/lib/ate` and plugin storage. This sidecar needs its own assessment. |
| `kagent`, `Deployment/kagent-controller`, `controller` | Explicit `true` | Explicit `false` | Unset; default `false` | Drops `ALL`; Pod requires non-root and uses seccomp `RuntimeDefault`. |
| `kagent`, `Deployment/kagent-ui`, `ui` | Explicit `true` | Explicit `false` | Unset; default `false` | Drops `ALL`; Pod requires non-root and uses seccomp `RuntimeDefault`; writable `/tmp` volume. |
| `ate-system`, `Deployment/k8s-credential-provider`, `k8s-credential-provider` | Explicit `true` | Explicit `false` | Unset; default `false` | Drops `ALL`; Pod requires non-root and specifies UID/GID 65532. |
| `ate-system`, main containers in `ate-api-server`, `ate-controller`, `ate-idp-server`, `atenet-router`, and `atenet-egress` | Unset; default `false` | Unset; default `true` | Unset; default `false` | Non-root enforcement and seccomp/AppArmor unset. `ate-idp-server` drops `ALL`; the other listed main containers do not explicitly define capability drops. Actual image UID and runtime-default capabilities were not measured. |

The API server's restartable init container `objectstore-plugin` also drops `ALL`, but leaves read-only root filesystem, escalation, and non-root enforcement unset. This is separate from the identically named sidecar in the `atelet` Pod.

The saved `kagent-postgresql` main container and its `tls-reloader` sidecar also leave read-only root filesystem and escalation unset. They inherit seccomp `RuntimeDefault`; the sidecar specifies UID 70. The `ate-system` RustFS container specifies UID/GID 10001 but leaves both of those hardening fields unset. Its bucket-initialization Job also leaves both unset. These are separate hardening findings, not consequences of the worker's `SYS_ADMIN` requirement.

## Node mounts and other settings

The worker mounts host `/var/lib/ate` writable at the same container path, with `HostToContainer` propagation. This exposes runtime state and sockets. The [connected review](agent-substrate-sys-admin-security-review.md#existing-protections-and-their-limits) describes the remaining shared-state risk.

The saved `atelet` container has these host mounts.

| Host path | Container path | Mount setting |
| --- | --- | --- |
| `/var/lib/ate` | `/var/lib/ate` | Writable |
| `/var/lib/kubelet/plugins` | `/var/lib/kubelet/plugins` | Writable |
| `/var/lib/kubelet/device-plugins` | `/var/lib/kubelet/device-plugins` | Writable |
| `/dev` | `/host/dev` | Explicitly read-only |

The objectstore sidecar in the `atelet` Pod mounts `/var/lib/ate` writable. It does not mount every hostPath declared by the Pod. The exception inventory must distinguish a Pod's declared volumes from the volumes each container actually mounts.

No Pod in these two namespaces had enabled `hostNetwork`, `hostPID`, or `hostIPC` in the saved inventory. The `atenet-egress` Pod did set `net.ipv4.ip_unprivileged_port_start=0`, which allows low-port binding within that Pod's network namespace. Any sysctl review belongs to that gateway workload, separately from the sandbox worker capability exception.

## Required behavior versus hardening opportunities

The pinned [worker security-context builder](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/cmd/atecontroller/internal/controllers/workerpool_apply.go#L358-L432) explicitly requests root, capabilities, and unconfined seccomp/AppArmor for the runtime's mount and sandbox operations. The [atelet manifest](https://github.com/kagent-dev/substrate/blob/e2fc0fa9f77ab5fc09eb01b43ccd74bd84c67c71/manifests/ate-install/atelet.yaml) describes its writable node state and `DAC_OVERRIDE` use for cleanup.

Those sources do not establish that every unset hardening field is essential. In particular, writable runtime volumes do not by themselves prove that the container's entire root filesystem must be writable. Testing a read-only root filesystem with explicit writable volumes is a possible hardening investigation. It has not been performed here. Similarly, `atelet` has no `SYS_ADMIN` in the saved newer configuration, so whether escalation can be disabled is a separate compatibility question.

The earlier Substrate `v0.0.9` worker and `atelet` both requested full privileged mode. Their read-only root filesystem and escalation fields were also unset in the reviewed builders/manifests. Those older settings need a broader review than the newer explicit capability set. The first review links the [older source and version differences](agent-substrate-sys-admin-security-review.md#older-installations-have-broader-permissions).

## Implications for the proposed Kyverno allowlist

Both namespaces retain the baseline. Each permitted deviation must name the workload, container, service account, approved image digest, field, reason, owner, and review date.

- Ordinary components should explicitly disable escalation, drop capabilities, require non-root execution, and use a reviewed seccomp profile. A read-only root filesystem can retain specifically approved writable volumes.
- The Substrate worker exception must assess root execution, the complete capability set, escalation, unconfined profiles, root-filesystem writes, and host mounts together. Allowing `SYS_ADMIN` alone does not address the other rules that can reject the Pod.
- Unset hardening fields on controllers, gateways, databases, and sidecars need separate compatibility checks. They must not inherit the worker's exception just because they share its namespace.
- Policies must inspect init containers, restartable init sidecars, and ephemeral-container updates as well as main containers. Pod-level defaults and container overrides both matter.
- Deployment restrictions and peer review remain the operating controls described in the first review. The Kyverno allowlist remains proposed. This README changes documentation only.

Fresh workplace Pod and controller specifications, together with the actual admission rejection, are needed before requesting exceptions or claiming these settings match the workplace installation.

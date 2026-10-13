# Cross-check the passing AKS lab against the blocked workplace canary

Use this before another controller fix proposal. The closest passing home
result was a **disposable AKS 1.35.8, Linux AMD64, Azure Linux 3.0** run of
Substrate 0.0.9 and kagent 0.10.1. It is separate from an older **ARM64 kind
on LinuxKit** public run and from the AKS 1.37 preview run with Substrate
0.4.0-alpha1. The 1.35.8 lab cluster was deleted after receipts were saved.

The home AKS result reached golden Ready and completed golden restore, Full
pause/restore and Data commit/restore with matching HTTP 200 agent cards;
three further fresh actors repeated the lifecycle. It did **not** make a real
model/MCP/chat request or prove the three-scene A2A demo. The workplace run
failed earlier: `CreateActor(A)` succeeded, status held B, and
`ResumeActor(B)` returned `NotFound` before any A2A call.

## Known comparison inputs

| Dimension | Passing home AKS 0.0.9 baseline | Workplace evidence supplied so far |
| --- | --- | --- |
| Kubernetes and node | AKS 1.35.8; `Standard_D8s_v3`; AMD64; Microsoft Azure Linux 3.0; kernel `6.6.150.1-1.azl3` | AKS and AMD64 reported; Kubernetes version, node OS image/version, kernel, VM SKU, kubelet and container runtime **UNKNOWN** in the sanitized handoff. |
| Releases | Substrate charts/CRDs 0.0.9; kagent charts/CRDs 0.10.1 | Substrate 0.0.9 snapshot and kagent 0.10.1 snapshot reported; exact chart archives, CRD schemas and source revisions **UNKNOWN**. |
| Golden controller | Public Substrate 0.0.9 ate-controller in the stock path; image index `sha256:dc29e79987fe4177b92c8b30a4fa4f36f3cf1a80937b03a7a8cd3411f98693e5` | Supplied ate-controller index and AMD64 manifest match the public registry objects. Verify the running Pod `imageID` and whether the mirrored reference preserves those bytes. |
| kagent controller | Public kagent 0.10.1 in the stock path; public index `sha256:878a55478c1727e048d38154158aae41aa701149c6660f78696fe682c7495146` | Supplied index matches public kagent controller; running AMD64 leaf and configuration **UNKNOWN**. |
| Worker and `runsc` | gVisor WorkerPool, one replica; AMD64 `runsc release-20260622.0`, SHA-256 `f18a948bf9c8bbb54eb998549a3a8d719a1c7de2efbe8fdd2ff0ee5fecd06f19` | gVisor path reported; actual pool spec/replicas/placement and live `runsc` file hash/path **UNKNOWN** in this handoff. |
| Asset delivery | A lab-only patched `atelet` fetched the binary from an internal object store into the content-addressed node cache after a forced miss. Stock canary also passed. | Work has described a seeded ATELET shared runtime volume; verify its actual bytes, permissions, mount and `runsc_path`. This is a known delivery-method difference. |
| Control-plane topology | Disposable lab topology and its receipts need checking before claiming equality; no workplace-like replica/store layout is established here. | ATE API/controller replica counts, Valkey topology, restarts, status-write audit, snapshot store and CA/trust path **UNKNOWN**. |
| Agent and template | Fresh Go `SandboxAgent`; generated immutable `ActorTemplate`, `onPause: Full`, `onCommit: Data`, durable `/data`, agent-card readiness probe. | Exact failing SandboxAgent/ActorTemplate spec, generated workload image and owner UID mapping **UNKNOWN**. |
| Result | Golden Ready and repeated runtime lifecycle; no A/B mismatch observed. | Golden blocked at A/B identity mismatch; no A2A scene ran. |

The home inputs and limits are recorded in the copied
[AKS evaluation handoff](AKS-EVAL-WORK-AGENT-HANDOFF.md),
[0.0.9 parity handoff](WORK-AGENT-RUNSC-EQUIVALENCE-HANDOFF.md), and
[home proof examples](HOME-LAB-SUBSTRATE-PROOF-EXAMPLES.md). The public image
digest list is in [IMAGES.md](https://github.com/davidmarkgardiner/kagent-public/blob/docs/substrate-workplace-proof-20261009/work-agent-bundles/agent-substrate/IMAGES.md).
These documents are historical receipts and summaries, not a live cluster.

## Copy this request to the work agent

```text
Please compare the failed workplace canary against the attached passing
AKS 1.35.8 / Linux AMD64 / Azure Linux 3.0 / Substrate 0.0.9 / kagent
0.10.1 home baseline. Do read-only discovery on the explicitly selected
non-production work cluster first. Keep all raw outputs in the approved
private evidence store; return only sanitized values and receipt links.

Return one table with Home value | Work observed value | MATCH, DIFFERENT or
UNKNOWN | private receipt for each of these:
1. AKS/Kubernetes and kubelet versions; selected worker and controller node
   architectures, Azure Linux or other OS image/version, kernel, VM SKU,
   container runtime, node pool labels/taints, and pod placement.
2. Substrate/kagent chart and CRD versions; actual running imageID digests
   (index versus AMD64 manifest) for ate-controller, ate-api, atelet,
   ateom-gvisor, kagent controller and generated Go ADK workload.
3. ATE API and ate-controller replica counts, Valkey/store topology and
   restart/failover history around the failure; snapshot store and CA path.
4. WorkerPool class/replicas/placement; SandboxConfig; actual AMD64 runsc
   version, SHA-256, size, mode, cache/seed/fetch path and worker runsc_path.
5. The exact failing SandboxAgent and generated ActorTemplate kind/API,
   owner UID, image, command, mounts, readiness probe, snapshot modes and
   durable directory. Compare with the home Go canary, not just labels.
6. For one ActorTemplate UID, every CreateActor attempt across ATE API
   replicas, every status write of GoldenActorID and Phase, and the first
   ResumeActor request. Give UTC times, resourceVersions and receipt IDs.

Do not call the environments the same because both say AMD64, AKS, or 0.0.9.
State the first material difference and whether it can plausibly affect the
A/B identity mismatch. Node kernel, runsc and WorkerPool differences matter
for later execution, but A/B diverged before the actor was resumed; examine
controller/status/store topology and receipt correlation first.

After the table, propose the smallest isolated reproduction, without running
it yet: exact version and image pins, target AKS/node shape, controller/API
replica and store layout, synthetic ActorTemplate, structured lifecycle and
Kubernetes status-write receipts, pass/fail gate, cleanup and cost boundary.
Start with the known passing configuration, then vary one work-only input at
a time. If the work node OS/kernel/AKS version differs, specify a disposable
AKS reproduction with that exact shape. If the control-plane difference can
be tested locally first, say what local test proves and what still requires
AKS. Preserve the workplace failure receipt. Do not deploy, evict, restart,
or alter shared cluster resources as part of this comparison.

Return COMPARED / MATERIAL DIFFERENCE FOUND / STILL UNKNOWN, with the
smallest next step. Keep the team demo BLOCKED until golden Ready and the
three A2A continuity scenes pass on a fresh approved canary.
```

The historical lab was deleted. Recreating an AKS test environment is a
separate execution step after the work-side comparison identifies the exact
target shape and bounds.

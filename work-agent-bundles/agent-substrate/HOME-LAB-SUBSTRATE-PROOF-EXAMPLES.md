# Public lab proof examples for the workplace Markdown package

This is a **reference for evidence shape**, not a workplace receipt. Use the exact installed workplace version, source and node. Copy the table structure into the private `SUBSTRATE-KAGENT-EVIDENCE.md`, replace example values with workplace observations, and link each row to a raw private artifact. Use the [ticket template](WORKPLACE-SUBSTRATE-GITLAB-TICKET-TEMPLATE.md) for the short GitLab summary and the [redeploy template](WORKPLACE-SUBSTRATE-REDEPLOY-WALKTHROUGH-TEMPLATE.md) for the complete reproduction steps.

## The closest public baseline: disposable AKS, 7 October 2026

The [AKS evaluation handoff](AKS-EVAL-WORK-AGENT-HANDOFF.md) and [0.0.9 parity handoff](WORK-AGENT-RUNSC-EQUIVALENCE-HANDOFF.md) record a **Substrate 0.0.9 + kagent 0.10 (patch 1)** gVisor run on an AKS 1.35.8 AMD64 Azure Linux 3.0 node. Do not combine its facts with the separate 1.37 preview / Substrate 0.4.0-alpha1 / kagent 1.0.0-alpha8 run.

| Baseline ID | What the public run observed | What the workplace agent must attach |
| --- | --- | --- |
| H01 | Four pinned charts/CRDs, running control/data plane, one ready gVisor WorkerPool and pinned generated workload image. | Flux commit/reconcile; chart archive hashes; CRD/schema versions; running imageIDs; node OS/kernel/architecture and pod placement. |
| H02 | `SandboxAgent` Ready with generated immutable ActorTemplate and golden snapshot. | Agent conditions, owner-linked template UID/spec, golden ID/status and timestamps. |
| H03 | AMD64 `runsc release-20260622.0`, SHA-256 `f18a948bf9c8bbb54eb998549a3a8d719a1c7de2efbe8fdd2ff0ee5fecd06f19`; lab cache was repopulated from an internal object store after eviction. | Workplace configured hash plus **actual file hash**, size, permissions, path and worker `runsc_path`. If the work design seeds ATELET's shared volume, show the seed on a fresh node; record this intentional difference from the lab fetch path. |
| H04 | Fresh actor restored from golden and returned an HTTP 200 agent card. | Actor/session ID, golden ID, restore RPC/status, timestamped agent-card response and body hash. |
| H05 | `onPause: Full` checkpoint and restore returned a matching HTTP 200 agent card. | Full scope in template/RPC, snapshot object/version, pause/restore transitions and before/after card hashes. |
| H06 | `onCommit: Data` commit and restore returned a matching HTTP 200 agent card. | Data scope in template/RPC, snapshot object/version, commit/restore transitions and before/after card hashes; resume before commit if required by installed release. |
| H07 | Three further **fresh actors** repeated golden → Full → Data lifecycle without exit 128. | Three distinct actor IDs; each ordered transition, result, snapshot and response receipt; first fatal stderr if any fails. |

For the home-lab-parity verdict, H01–H07 must each show `PASS` with raw workplace receipts. A seeded cache can satisfy H03 when the binary and actual worker path are proved; a different delivery method should be recorded, not hidden. Matching the public version number or returning a final Ready status does not substitute for the transition receipts.

## Example Markdown excerpt to emulate

The older [real-cluster run](evidence/RUN-RED-2026-07-16.md) shows the concise, reviewer-friendly shape below. It used **Substrate 0.0.6 / kagent 0.9.10**, so these values are **not** the 0.0.9 AKS or workplace result:

```text
SandboxAgent: Accepted=True, Ready=True (WorkloadReady)
WorkerPool: desired=1, ready=1
Actor: ResumeActor -> Running; SuspendActor -> Suspended
Snapshot: gs://ate-snapshots/.../<actor>/<snapshot>
```

A completed private evidence row should add IDs, time, source and a receipt link, for example:

```markdown
| H05 | PASS | Run <run-id>, actor <actor-id>, Full pause at <UTC> -> snapshot
<object/version>; restore at <UTC> -> HTTP 200; before/after card SHA-256
<hash> | [E-17](<private-receipt-link>) |
```

The private receipt `E-17` should contain the actual command or API request, output, actor/template/session IDs, UTC timestamp and file SHA-256. For H03, include a fresh-node seed completion log, `sha256sum` of the actual executable, file mode, and the `runsc_path` used by the worker. Do not call an illustrative excerpt a receipt.

## What the public AKS run did **not** prove

The 0.0.9 AKS handoff explicitly says there was **no real model/MCP/chat request**, **no changed `/data` survival assertion**, and **no strict air-gap/packet-level egress test**. Matching agent cards after restore do not establish those claims. The earlier real-cluster 0.9.10 run also recorded a 404 from the normal controller A2A REST route for its sandbox agent, while the Substrate runtime lifecycle passed. Therefore, test the exact intended workplace kagent front door separately and report its version-specific result.

Use the [proof template](WORKPLACE-SUBSTRATE-KAGENT-PROOF-TEMPLATE.md) P01–P13 rows to prove additional claims. Keep the ticket wording scoped: `H01–H07 workplace parity passed` if that is all the evidence supports; say `real kagent request`, `state retained`, `air-gapped`, `fast restore`, or `capacity saving` only for their own passing rows.

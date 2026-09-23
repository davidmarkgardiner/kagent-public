> Packaged from the private video project. It records what the published
> video claims and the evidence behind each claim, so the work team can see
> exactly which statements are supported. The run it cites is
> [`../evidence/LIVE-RUN-2026-09-14.md`](../evidence/LIVE-RUN-2026-09-14.md).

# Claim-to-evidence map

## Evidence policy

This project narrows the earlier evidence map to the nine-frame reference-led story. Every factual claim inherits the original source boundary. The demonstration is a sanitized reconstruction of one dated synthetic run; it is not a customer environment, a live production recording or a current-version claim.

| ID | Script claim | Evidence source | Public-safe wording | Boundary carried into the frame |
|---|---|---|---|---|
| R01 | A normal kagent `Agent` and a `SandboxAgent` use different execution models. | the earlier private video claim map, C01 | “A normal kagent Agent uses a shared Kubernetes Deployment. A SandboxAgent runs as a Substrate actor on reusable workers.” | Never depict a dedicated pod for every normal-agent chat. |
| R02 | `SandboxAgent` reconciles through `ActorTemplate` to a logical actor using a `WorkerPool`. | the earlier private video claim map, C02; [`../evidence/LIVE-RUN-2026-09-14.md`](../evidence/LIVE-RUN-2026-09-14.md), Reconciliation receipt | “A SandboxAgent describes the runtime; kagent generates an ActorTemplate; sessions map to logical actors on reusable workers.” | Runtime-specific architecture, not a compatibility promise for other versions or clusters. |
| R03 | The dated setup was ready and used a three-replica WorkerPool. | [`../evidence/LIVE-RUN-2026-09-14.md`](../evidence/LIVE-RUN-2026-09-14.md), Pinned runtime and Reconciliation receipt | “The SandboxAgent and generated ActorTemplate were Ready; the WorkerPool was configured with three replicas.” | Historical synthetic test on 14 September 2026. Do not present versions as current latest. |
| R04 | Session one stored `ORANGE-FALCON-17`. | [`../evidence/LIVE-RUN-2026-09-14.md`](../evidence/LIVE-RUN-2026-09-14.md), Session one steps 1–2 | “Session one stored `ORANGE-FALCON-17` and returned `MARKER STORED`.” | Synthetic data only. |
| R05 | The same actor was sampled as Resuming, Running and Suspended on both requests. | [`../evidence/LIVE-RUN-2026-09-14.md`](../evidence/LIVE-RUN-2026-09-14.md), Session one steps 3–6 | “The same logical actor moved through Resuming, Running and Suspended on both requests.” | Lifecycle samples are not a byte-for-byte storage trace or a capacity measurement. |
| R06 | The later request in the same session returned the marker. | [`../evidence/LIVE-RUN-2026-09-14.md`](../evidence/LIVE-RUN-2026-09-14.md), Session one steps 4–6 | “A later request reused the same session and actor and returned `ORANGE-FALCON-17`.” | Functional continuity in this synthetic test only. |
| R07 | Session two created a different actor and did not inherit session one's marker. | [`../evidence/LIVE-RUN-2026-09-14.md`](../evidence/LIVE-RUN-2026-09-14.md), Session two | “A second session created a different actor and returned `NO MARKER IN THIS SESSION`.” | Functional separation between two synthetic sessions; not tenant-isolation or security proof. |
| R08 | Substrate separates logical session state from dedicated idle compute. | the earlier private video claim map, C09; R04–R07 above | “Substrate separates the logical session from dedicated idle compute and restores it onto reusable workers when work arrives.” | Architectural conclusion. No measured density, utilization, latency, cost or scale-to-zero claim. |
| R09 | Suspension is not deletion. | [`../evidence/LIVE-RUN-2026-09-14.md`](../evidence/LIVE-RUN-2026-09-14.md), Boundaries; the earlier private video claim map, C10 | “Retained session data and snapshots need separate retention and erasure controls.” | No physical-erasure, retention-policy or external-copy deletion claim. |
| R10 | No performance or production-scale outcome was measured. | [`../evidence/LIVE-RUN-2026-09-14.md`](../evidence/LIVE-RUN-2026-09-14.md), Boundaries | “This run measured no density gain, latency improvement, cost saving or production-scale result.” | Keep the statement on screen and in narration. |
| R11 | The public-facing episode is reconstructed and sanitized. | the earlier private video claim map, C12 | “Sanitized reconstruction using synthetic data in an authorized private test environment.” | No employer, customer, private endpoint, repository, cluster, subscription, task ID or full actor identifier. |

## Excluded evidence and claims

- The separate `GREEN-COMET-21` UI lane is not used.
- The raw task IDs, full actor IDs, endpoint names, storage URI and local paths stay in the private receipt only.
- The run did not inspect raw snapshot bytes, record a before-and-after worker-capacity sample, execute an end-to-end deletion test, or measure performance, density, utilization or cost.
- The three configured worker replicas remain visible; the video must not imply that the WorkerPool or control plane scales to zero.
- “Sandboxed” describes the execution model here. It must not be presented as proof of tenant isolation or a completed security assessment.

## Composition check

Before any production build, compare every spoken factual sentence and on-screen claim against R01–R11. If a sentence requires a stronger claim, change the sentence or obtain new evidence before changing the visual.


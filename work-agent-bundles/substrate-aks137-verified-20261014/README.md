# Verified AKS 1.37 Substrate redeployment bundle

**Evidence status:** the personal AKS and isolated Kind demonstration clusters
were deleted after the recorded 14 October run. The receipts below are
historical captures from before deletion. This handoff update performs local
artifact/script checks only; it gathers no new cluster evidence and runs no
live cluster smoke test. The work agent must run the supplied smoke test
after reinstalling in the bank.

On 14 October 2026, the stock newer gVisor installation passed on a fresh
personal AKS cluster and an isolated local Kind cluster. Each ran three
kagent-generated Go ADK actors, ten Full-state counter actors and ten
Data-state counter actors through creation, read-back, golden restore,
pause/restore and suspend/restore. All 46 passing actors retained their
identity and finished Suspended. No runtime/controller source patch was used.

The AKS target was **1.37.0, `osSku: AzureLinux`, `Standard_D8s_v3`, one
AMD64 node**, with Microsoft Azure Linux 3.0. The exact node image, kernel,
container runtime, images, asset hashes and benchmark results are in
[`EVIDENCE.md`](EVIDENCE.md). Both disposable clusters were removed after
receipt capture; see the cleanup receipts under [`evidence/`](evidence/).

## Start with these files

1. Import the images and complete [`PREREQUISITES.md`](PREREQUISITES.md),
   including the attached offline prerequisites payload and its checksums.
2. Give [`WORK-AGENT-PROMPT.md`](WORK-AGENT-PROMPT.md) and this whole folder
   to the work agent. Follow [`BANK-REINSTALL.md`](BANK-REINSTALL.md) for the
   authorized, scoped removal and fresh installation.
3. Run [`SMOKE-TEST.md`](SMOKE-TEST.md): the five-actor runtime check first,
   then disconnected-delivery and real-model checks, then benchmarks.
4. Compare the locks, values and [`evidence/aks/platform.json`](evidence/aks/platform.json).
   [`REDEPLOY.md`](REDEPLOY.md) retains the original connected lab walkthrough.

Copy this entire folder. Keep the filenames. Check `CHECKSUMS.sha256` after
transfer with `shasum -a 256 -c CHECKSUMS.sha256` or
`sha256sum -c CHECKSUMS.sha256`.

## Which installation this proves

| Input | Tested pairing |
| --- | --- |
| Substrate and CRDs | 0.4.0-alpha1, stock released images pinned by OCI digest |
| kagent and CRDs | 1.0.0-alpha8, stock controller/UI/Go ADK pinned by OCI digest |
| Agent API | `api.kagent.dev/v1alpha3 Agent` with an inline Harness |
| Actor runtime | gVisor, with the 2 September 2026 `gvisor.tar.zstd` archive |
| Actor routing | `ate-target-actor: <atespace>/<actor>` |
| State backend / snapshot store | Chart-provided PostgreSQL / RustFS |
| WorkerPool | One `gvisor` worker, reused serially |

`runsc` is still the executable inside the gVisor archive. This is the newer
packaged gVisor installation, not a microVM/Kata test. The separate microVM
backend was not exercised.

This pairing replaces the older Substrate 0.0.9 / kagent 0.10.x API and
backend. It is a coordinated version change, not a drop-in image replacement
for `SandboxAgent`. A pass here does not disprove an old-version controller
bug or explain yesterday's workplace failure. If the workplace must remain
on the older pairing, stop before applying these manifests.

## What the demonstration proves

- Stock kagent reconciliation produced usable golden snapshots.
- Fresh actors could be created, read and resumed with matching identities.
- Full snapshots preserved the synthetic process-memory and file counters.
- Data snapshots restarted process memory and preserved the file counter.
- Three public Go ADK actors per cluster served unchanged agent cards after
  both Full pause and Data commit restoration.
- The passing actors released their worker assignments after pause/suspend.

No real LLM, MCP or chat requests were made. The bundled Ollama ModelConfig
is an explicitly unreachable fixture used for runtime reconciliation only.
The latency measurements are small serial operator-path benchmarks, not
production throughput, capacity, isolation or air-gap certification.

## Fixture transfer

The test fixture source is under [`fixture/`](fixture/). The exact tested
multi-architecture OCI archive is distributed as `fixture.oci.tar` on the
GitHub release `substrate-aks137-proof-20261014`; binaries are not committed
to this repository. Its archive SHA-256 is in
[`fixture-archive-lock.json`](fixture-archive-lock.json), and its OCI index
and AMD64/ARM64 image digests are in
[`fixture-image-lock.json`](fixture-image-lock.json).

The folder supplies configuration, tests and sanitized receipts. Runtime
images, operator dependencies, credentials and Kubernetes access remain
separate deployment inputs. The new bank handoff release includes the pinned
charts, gVisor archive, fixture, source directory and operator helpers in
`substrate-prerequisites.tar.gz`; see `PREREQUISITES.md`. The installed chart defaults download the pinned
gVisor archive from public Google Storage. An isolated workplace must supply
the same bytes through its approved delivery path and prove that path there.

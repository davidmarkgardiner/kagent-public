# Observed evidence and benchmarks

**Evidence status:** the personal AKS and isolated Kind demonstration clusters
were deleted after the recorded 14 October run. The receipts below are
historical captures from before deletion. This handoff update performs local
artifact/script checks only; it gathers no new cluster evidence and runs no
live cluster smoke test. The work agent must run the supplied smoke test
after reinstalling in the bank.

Run date: 14 October 2026. These are fresh personal-lab receipts. All runtime
images were stock public images. The checkout used to build the operator and
bootstrap helpers was unchanged `kagent-dev/substrate` commit
`c2e2e130606db615a553421b6352e47f49860870`. The runtime image config labels did
not expose a source revision; image provenance is the published OCI digest,
not an independently established image-to-source commit mapping.

## Exact platforms

| Fact | Local Kind | Personal AKS |
| --- | --- | --- |
| Kubernetes | 1.37.0 | 1.37.0 |
| Architecture | ARM64 | AMD64 |
| VM / node capacity | Docker VM, 10 CPUs, approximately 15.6 GiB | `Standard_D8s_v3`, 8 vCPUs, nominal 32 GiB |
| OS SKU | Not an AKS OS SKU | `AzureLinux` |
| Node OS | Debian GNU/Linux 13, inside Docker Desktop | Microsoft Azure Linux 3.0 |
| Kernel | `6.10.14-linuxkit` | `6.6.157.1-1.azl3` |
| Container runtime | containerd 2.3.4 | containerd 2.2.4 |
| AKS node image | Not applicable | `AKSAzureLinux-V3gen2-202610.08.0` |
| Region / tier | Local Mac | UK South / Free control-plane tier |
| Node count / OS disk | One Kind node | One node, 64 GiB Ephemeral OS disk |

The local machine is not AzureLinux. The full node facts are in
[`evidence/home/platform.json`](evidence/home/platform.json) and
[`evidence/aks/platform.json`](evidence/aks/platform.json). The personal AKS
run is the AMD64/AzureLinux evidence for the workplace comparison. The AKS
node advertised `ate.dev/kvm` capacity, but no microVM test was performed.

## Versions, configuration and assets

- Substrate/CRDs 0.4.0-alpha1; kagent/CRDs 1.0.0-alpha8.
- The four freshly downloaded chart archives were byte-identical to the
  7 October archives. [`chart-lock.json`](chart-lock.json) records their hashes.
- [`image-lock.json`](image-lock.json) contains OCI indexes and AMD64/ARM64
  manifests. Observed container imageIDs are in each platform's
  `image-inventory.json`. Supporting PostgreSQL and fixture-registry tags
  resolved to the same observed content in both runs; the bundle locks them
  by digest for subsequent installations.
- The same Agent YAML, Go ADK image index, model fixture, pool, values and
  fixture OCI index were used in both environments. Generated ActorTemplate
  workload specifications matched after excluding metadata/status. Generated
  names and UIDs differed and were discovered independently.
- The WorkerPool had one desired/Ready gVisor worker. Counter templates had
  limits of 1 CPU and 512 MiB per actor. The two API replicas, one controller
  and relevant worker/container logs were captured privately.
- Stock atelet fetched the gVisor archive from public Google Storage; there
  was no internal-fetch patch, seeded-cache substitute or deny-egress test.

| Runtime asset | Local ARM64 | AKS AMD64 |
| --- | --- | --- |
| Archive date | 2026-09-02 | 2026-09-02 |
| Archive SHA-256 | `a64916f9813ce7e4841a30480a599337f7dda07b421c6bf0123db2212aa7d1df` | `d547d81401461fd1c679c5c4fa0a6c2b8ef7dc3c22ce23c9e25dcc4c69cfd06f` |
| Independently hashed extracted runsc binary | `29c8327f4572dd52cc102a2bd10235a38ccce5404c26f5b13d9598a7aba642e8` | `1a3982cb91714f9c0c7148668d2c40143ee97e238f8a8e7452e410770d34fbe3` |
| Binary size / mode | 102,340,738 bytes / 755 | 109,183,527 bytes / 755 |

Both worker-visible binaries reported
`release-20260824.0-120-g727c8c389c36-dirty`, spec 1.2.1. This is the string
in the upstream nightly archive; the archive hashes pin the tested bytes.
The archive hash and executable hash are different measurements. Cold fetch
and extraction events plus direct worker execution receipts are under
[`evidence/home/runtime-assets.json`](evidence/home/runtime-assets.json) and
[`evidence/aks/runtime-assets.json`](evidence/aks/runtime-assets.json).

## Lifecycle and state assertions

| Test per cluster | Fresh actors | Required observations | Local / AKS |
| --- | --- | --- | --- |
| kagent-generated Go ADK | 3 | Golden restore, Full pause/restore, Data commit/restore, stable actor UID and agent card | PASS / PASS |
| Synthetic counter, Full/Full | 10 | Memory/file counts `1/1, 2/2, 3/3`, stable actor UID and marker | PASS / PASS |
| Synthetic counter, Data/Data | 10 | Memory/file counts `1/1, 1/2, 1/3`, stable actor UID and marker | PASS / PASS |

All passing sequences checked create/read identity, worker assignment while
Running, a local snapshot while Paused, a new external snapshot after commit,
no assignment after release, and an unchanged template/golden. Each suite
has `result.json`, `assertions.json` and `benchmark.json` under the platform
evidence directory. The 23 passing actors per cluster finished Suspended
on one reused worker. This is serial reuse and idle actor inventory, not a
concurrency or maximum-density measurement. Two extra AKS diagnostic actors
are retained in the final pre-cleanup inventory and excluded from the pass
count and benchmark.

## Benchmark measurements

The following numbers are milliseconds of Mac operator CLI wall time. They
include process startup, service-account token acquisition, automatic
port-forwarding and network round trips. Assets were already cached; these
are not fresh-node cold-start timings or pure server-side restore latency.
Each row has ten serial samples. P50 is the median; P95 is nearest rank,
which is the maximum for N=10. Raw samples are retained in `benchmark.json`.

| Environment / fixture mode | Restore after pause p50 / p95 | Restore after commit p50 / p95 |
| --- | --- | --- |
| Local / Full | 377.7 / 665.4 | 374.7 / 605.5 |
| Local / Data | 252.1 / 1253.7 | 416.8 / 1604.2 |
| AKS / Full | 905.6 / 963.2 | 923.1 / 987.6 |
| AKS / Data | 837.9 / 921.5 | 834.5 / 929.1 |

AKS resource samples showed the single worker at 26m CPU / 11 MiB during
the sampled benchmark window and the control plane/storage had their own
usage. These are point samples, not peak/RSS limits or per-actor cost.
The local metrics API was unavailable. There is no like-for-like resource
comparison, throughput load test or always-running-pod control benchmark.

## Failed preparation and excluded test attempts

Failures were retained rather than counted as passing benchmark samples:

1. The initially installed Kind binary produced a kubeadm v1beta3 configuration
   rejected by Kubernetes 1.37. The pinned Kind 0.33.0 helper created the
   isolated cluster successfully.
2. The bootstrap helper required its source-directory working directory.
   Helm then refused the namespace created by that bootstrap until the new
   lab namespace had release ownership metadata. The final installers
   express both steps. No runtime source fix was involved.
3. A local installer was edited while its shell was waiting for Helm, which
   caused a trailing parse error after Helm had installed successfully.
   The final script passes `bash -n`; the healthy deployment and subsequent
   configuration upgrade were verified separately. The combined wrapper
   was not replayed from a third completely empty cluster.
4. The first AKS checker incorrectly required a new external URI after pause.
   This version stores a **localSnapshot** on pause and retains the prior
   external snapshot until commit. The raw paused status established the
   correct contract. The checker was corrected, the failure kept under
   `excluded-first-attempt.json`, and fresh actors passed the corrected test.
5. The first local ADK invocation used the AKS-generated template name and
   failed before actor creation. The local template name was discovered;
   the excluded failure and the fresh passing sequence are both retained.

Startup database/DNS and certificate-mount retries also appear in the private
logs. The passing claim concerns the final tested deployment and complete
actor sequences, not an error-free installation history.

## Proof boundaries and receipt trail

This is a verified newer stock deployment. It does not reproduce or explain
an old 0.0.9 GoldenActorID mismatch. No real model/MCP/chat call, tenant
isolation test, strict air-gap proof, multi-node snapshot portability test or
production capacity benchmark was performed.

[`evidence/receipt-index.json`](evidence/receipt-index.json) records hashes of
the original private receipts and sanitized public copies. Generated IDs
and private node/IP values are consistently replaced with placeholders.
Raw kubeconfigs, credentials, complete templates and logs remain private.
Cleanup is recorded separately in `evidence/cleanup.json`.

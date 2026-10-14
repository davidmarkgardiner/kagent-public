# Work-agent request: reproduce the verified deployment before changing source

Copy the request below with this entire bundle into the approved private
work project.

```text
Please stop the proposed ATE controller idempotency/source fix for this
exercise. Reproduce the attached verified stock deployment first. Do not
patch the ATE controller, API, atelet, kagent controller or Go ADK, and do not
add runtime-source regression tests as a prerequisite to this deployment.

The fresh personal AKS evidence from 14 October 2026 used AKS 1.37.0,
osSku AzureLinux, Microsoft Azure Linux 3.0, Standard_D8s_v3, AMD64 and one
node. Substrate/CRDs were 0.4.0-alpha1; kagent/CRDs were 1.0.0-alpha8.
It used the newer gVisor archive path, stock digest-pinned images, PostgreSQL,
RustFS and one gVisor worker. It did not use microVM/Kata or a local runtime
source patch. Read README.md and EVIDENCE.md before using the installers.

First inventory the actual work environment and preserve the old failure
receipts. Produce a private parity table against image-lock.json,
chart-lock.json, the values files and evidence/aks/platform.json. Record the
actual AKS and kubelet versions, osSku, node image, VM SKU, architecture,
kernel, containerd, namespaces, replica counts, configured image references,
running imageIDs, runtime asset delivery/checksums, storage backend and
generated template. Resolve image indexes to the correct AMD64 manifests;
do not substitute the ARM64 leaves from the local Kind lab.

This is a coordinated upgrade to Agent/Harness and the newer Substrate
backend. It is not compatible with simply replaying old SandboxAgent YAML.
If the approved work scope requires Substrate 0.0.9/kagent 0.10.x, say so and
stop the migration. Do not call a different pairing identical to this one.

Prepare an exact cleanup/redeployment plan for the existing disposable
evaluation installation. List each release, object and data owner. Preserve
needed agent/model configuration, credentials and the old failed evidence.
Remove only the agreed disposable evaluation resources. Do not remove shared
databases, snapshot stores, CRDs or other agents, or force-clear finalizers.
If the existing installation shares resources with workloads outside this
exercise, use a separate approved evaluation target instead.

Redeploy the compatible version set using REDEPLOY.md, the pinned chart/image
inputs and reviewed desired configuration. Start with fresh generated goldens
and a new snapshot prefix. Do not reuse old golden actors, Redis state or
snapshots across this backend/version change. Adapt actual context, names,
namespaces, CA/issuer, registry/storage and model references in a private
copy, and document every difference from the verified configuration.

For an isolated work network, mirror the exact index/AMD64 image contents,
chart archives and AMD64 gvisor.tar.zstd bytes. Validate the approved seeded
or internal delivery path with independent hash, executable mode, shared
mount and the worker-visible runsc version. A cache directory name alone is
insufficient. Do not reintroduce a source patch to mimic this public-fetch
lab, or call the lab an air-gap pass.

Run the generated Go ADK lifecycle and both counter modes. Discover the
generated template name; it differs across environments even when the
generated workload specification matches. Capture every created actor's
name/atespace/UID, exact status transitions, local pause snapshot, external
commit snapshot, worker assignment, HTTP response, UTC time and command exit.
Capture the logs from every API/controller replica and relevant worker.
Stop each sequence on its first failure and retain the failure. Do not retry
until green or rename UNKNOWN to PASS.

Repeat the benchmark with ten fresh counter actors per snapshot mode, one
worker and the same fixture image. Report raw samples, N, p50 and p95, node
resources and the client location. The supplied CLI timings include token
acquisition, port-forwarding and network RTT; do not label them pure restore
latency. Report unmeasured CPU/peak/load/throughput comparisons as UNKNOWN.

Return private SUBSTRATE-WORK-REDEPLOY.md with the real copyable commands and
cleanup scope, SUBSTRATE-WORK-PARITY.md with every match/difference, and
SUBSTRATE-WORK-RESULTS.md with the complete outcomes, benchmarks and receipt
index. Keep workplace identifiers, credentials and raw receipts private.
Bind an approved real ModelConfig and run the three-turn session demonstration
separately before claiming model-backed chat or session continuity. This
bundle's ADK agent-card test and synthetic counter test do not make that claim.

If a matching deployment still fails, identify its earliest failing gate
and return the correlated CreateActor/read/status/ResumeActor or underlying
runsc error receipts. Do not apply a source repair during this exercise.
The conclusion should state what works now and what remains unexplained.
```

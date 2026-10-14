# Work-agent request: clean reinstall and prove the stock pairing

Copy this request and the entire bundle into the approved private work project.
Import the images and complete the prerequisites before deleting the old stack.

```text
Reproduce the attached verified stock deployment. David authorizes removal
and fresh installation of this dedicated evaluation stack. Follow
PREREQUISITES.md, BANK-REINSTALL.md and SMOKE-TEST.md. Do not patch the ATE
controller, API, atelet, kagent controller or Go ADK, or make source regression
tests a prerequisite to this exercise. Preserve the previous failed receipts.

The tested personal AKS baseline is Kubernetes/kubelet 1.37.0, osSku
AzureLinux, Microsoft Azure Linux 3.0, Standard_D8s_v3, AMD64, one node and
one gVisor worker. Use Substrate/CRDs 0.4.0-alpha1 and kagent/CRDs
1.0.0-alpha8, stock digest-pinned images, PostgreSQL and RustFS. This still
uses runsc from the full pinned 2026-09-02 gVisor archive; it is not a
microVM/Kata installation. Agent/Harness replaces the older SandboxAgent API.

Inventory the actual installation. Update the work-through template in
BANK-REINSTALL.md with its real kubeconfig, namespaces, releases, agent,
worker pool, template names, registry, issuer/CA, storage and model route.
Keep this adaptation and receipts private. Compare every input with the
bundle locks, values and evidence/aks/platform.json. Record node image,
kernel, containerd, configured images and running imageIDs as well as version
labels. Preserve OCI index contents or record the exact AMD64 leaf mapping.

Verify all transferred prerequisites before cleanup. Use the offline
payload and prepare.sh --offline; do not fetch public dependencies inside
the bank. Prove ordinary pod pulls AND atelet actor-image pulls from the
approved registry. Seed the entire locked gVisor tree atomically through the
approved node-delivery mechanism and verify hashes, executable modes, shared
mount and worker-visible runsc. Directory presence alone is not proof.
Verify actual service-account issuer discovery/JWKS, certificate APIs/CA,
snapshot storage and fresh PostgreSQL state under the bank network controls.

List the exact owned resources and backups, stop only their recreating
GitOps/callers, and execute the scoped clean removal in BANK-REINSTALL.md.
Keep the old controller running while its owned agents/actors finalize.
Do not delete the cluster/node pool, shared data, unrelated workloads,
shared CRDs or shared certificate infrastructure; do not force finalizers.
Resolve shared ownership before deleting anything outside the dedicated
stack. Once prerequisites and ownership are established, carry out the
already-authorized reinstall without another blanket permission request.

Install the pinned stock charts using the private mirror/auth/storage values.
Use fresh state, generated goldens and snapshot prefixes. Do not reuse old
Valkey/Redis state, SandboxAgent YAML or snapshots across this version change.
Record all environment-specific differences and retain rendered manifests.

Run smoke-test.sh using actual names. It gates the reference node/pairing
and runs three generated Go ADK actors plus one Full and one Data counter.
Retain identity, state transitions, golden/local/external snapshots, worker
assignment/release, HTTP responses, UTC times, exits and correlated logs.
Stop at the first failure; retain it and report its earliest failing gate.
Do not silently retry until green or change source during this exercise.

Runtime smoke does not prove chat or an air gap. Complete the separate
fresh-node disconnected-delivery checks and approved real-model three-turn
session canary in SMOKE-TEST.md. The bundled dummy Ollama ModelConfig is
unreachable and suitable only for runtime reconciliation. Use an approved
real ModelConfig for the model-backed canary. Do not infer memory restoration
from an LLM response or call missing evidence PASS.

After smoke passes, benchmark ten fresh actors per counter mode with the
same fixture and one worker. Retain raw samples, N, p50/p95, selected node,
client location and resource samples. CLI timings include token acquisition,
port-forwarding and network RTT; they are not pure restore latency.

Return private SUBSTRATE-WORK-REDEPLOY.md with real copyable commands and
cleanup scope, SUBSTRATE-WORK-PARITY.md with every match/difference, and
SUBSTRATE-WORK-RESULTS.md with each smoke gate, benchmarks and receipt index.
Use PASS/FAIL/UNKNOWN accurately. If prerequisites prevent installation,
return the concrete blocker without altering source or weakening controls.
Explain what works and what remains unproved; matching labels alone are not
bank proof. Keep identifiers, credentials and raw logs out of public GitHub.
```

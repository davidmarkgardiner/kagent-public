# Prerequisites before the bank reinstall

Complete this inventory before removing the old evaluation stack. The
reference is the **personal AMD64 AKS** receipt, not the ARM64 Kind host.
Use [`evidence/aks/platform.json`](evidence/aks/platform.json) and
[`EVIDENCE.md`](EVIDENCE.md) for the actual measured baseline.

| Requirement | Reference / acceptance check |
| --- | --- |
| VM SKU / architecture | `Standard_D8s_v3`, AMD64, one selected gVisor worker |
| Kubernetes / kubelet | 1.37.0 / v1.37.0 |
| AKS OS SKU / node OS | `AzureLinux` / Microsoft Azure Linux 3.0 |
| Node image | `AKSAzureLinux-V3gen2-202610.08.0`; record any difference |
| Kernel / containerd | `6.6.157.1-1.azl3` / 2.2.4; record any difference |
| Substrate / CRD charts | 0.4.0-alpha1, archive hashes in `chart-lock.json` |
| kagent / CRD charts | 1.0.0-alpha8, archive hashes in `chart-lock.json` |
| Image contents | Correct OCI index or AMD64 manifest digest from `image-lock.json` |
| Agent API | `api.kagent.dev/v1alpha3 Agent` with Harness; replace old SandboxAgent manifests |
| Certificate APIs | Served ClusterTrustBundle and PodCertificateRequest APIs with working projection/signing |
| Runtime asset | Entire Linux AMD64 nightly 2026-09-02 `gvisor.tar.zstd`, including `gvisor-bin/` |
| Snapshot storage / state | Reachable approved object storage and fresh compatible PostgreSQL state |
| Operator access | Named private kubeconfig, required namespace/CRD/RBAC access and approved port-forward path |
| Operator tools | Bash, kubectl, Helm, Python 3.12+ and PyYAML 6.0.3; prepared operator binaries |
| Real model | Approved reachable ModelConfig, credentials and CA trust for the application smoke |

Matching AKS version and VM SKU does not guarantee the same node image,
kernel or network/authentication/storage setup. Compare and retain those
facts before describing a workplace run as equivalent.

## Transfer payload

Container images are a separate import. The prepared non-image prerequisites
are attached as `substrate-prerequisites.tar.gz` to release
`substrate-aks137-bank-handoff-20261014`. The payload contains:

- Four pinned chart archives.
- The exact AMD64 gVisor archive used by the successful AKS test.
- The exact synthetic fixture OCI archive.
- Unmodified source archive at commit
  `c2e2e130606db615a553421b6352e47f49860870` for the bootstrap helper's working directory.
- Stock-source operator helpers for Linux AMD64 and macOS ARM64. Linux
  helpers were cross-built with Go 1.27.0, vendored dependencies and CGO off.

[`prerequisites-lock.json`](prerequisites-lock.json) records every transferred
file's size and SHA-256. No kubeconfig, bank credentials or generated CA
private keys are included. Linux helper startup is checked without a network;
their target-cluster calls still need the bank smoke test. The operator
workstation architecture is separate from the cluster's AMD64 architecture.

On an internet-connected transfer workstation:

```bash
gh release download substrate-aks137-bank-handoff-20261014 \
  --repo davidmarkgardiner/kagent-public --pattern substrate-prerequisites.tar.gz
```

After copying the bundle and payload into the bank through the approved route:

```bash
cd '{{BUNDLE_DIR}}'
export PROOF_PREREQUISITES='{{TRANSFER_DIR}}/substrate-prerequisites.tar.gz'
python3 - <<'PYVERIFY'
import hashlib, json, os
from pathlib import Path
lock = json.loads(Path('prerequisites-archive-lock.json').read_text())
file = Path(os.environ['PROOF_PREREQUISITES'])
assert file.stat().st_size == lock['bytes']
hash = hashlib.sha256()
with file.open('rb') as stream:
    for block in iter(lambda: stream.read(1048576), b''):
        hash.update(block)
assert hash.hexdigest() == lock['sha256']
print('Prerequisites transfer archive verified')
PYVERIFY
tar -xzf "$PROOF_PREREQUISITES"
bash ./prepare.sh --offline
python3 -c 'import yaml; print(yaml.__version__)'
kubectl version --client
helm version
```

Expect `OFFLINE_PREREQUISITES=PASS` and PyYAML 6.0.3. The offline path checks
the files, extracts/verifies the pinned source and copies the matching helper
binaries. It does not fetch from GitHub, Google or a Go module proxy, compile
runtime images, or mutate Kubernetes. Other operator platforms need matching
approved helpers before proceeding. The older connected `prepare.sh` path
is a lab convenience; do not run it inside a disconnected bank environment.

## Images and registry authentication

Import every used image from the lock and chart renders, including controller,
UI, Go ADK workload, gVisor worker, atenet/agentgateway, certificate controller,
credential provider, pause image, PostgreSQL, RustFS, bucket-init utility and
the synthetic fixture. Preserve immutable content. Recreated mirror tags
alone do not establish equivalence. If importing only AMD64 manifests, use
the corresponding AMD64 digest and record the source-index mapping.

Make a private copy of `image-lock.json` with mirror references in each row's
`aliases` and the actual private digest-pinned `pinned` reference. Export
`PROOF_IMAGE_LOCK` to that private file. `pin-images.py` fails if a rendered
image remains mutable; it will not silently accept an unmapped mirror tag.
Supply private desired values via `PROOF_SUBSTRATE_VALUES` and
`PROOF_KAGENT_VALUES` and retain the rendered manifest/image inventory.

Normal pod image pulls and **atelet's actor-image pulls** are different paths.
The stock atelet image cache pulls anonymously unless its kubelet exec
credential-provider configuration and executable directory are supplied.
The chart exposes `atelet.imageCredentialProviderConfig` and
`atelet.imageCredentialProviderBinDir`. Discover the real host paths and
prove an actor-image pull from the bank registry; ordinary pod
`imagePullSecrets` alone are not evidence that this second path works.

If the disposable HTTP fixture registry is disallowed, import the fixture
into the approved private registry and adapt only the fixture image references
and delivery configuration. Keep the fixture contents/digests and state
assertions. Record that difference rather than weakening admission controls.

## Runtime asset delivery

Use the same **archive** SHA-256 as the verified AMD64 run:

```text
d547d81401461fd1c679c5c4fa0a6c2b8ef7dc3c22ce23c9e25dcc4c69cfd06f
```

The full per-file hash/mode inventory is in
[`gvisor-files-amd64.json`](gvisor-files-amd64.json). The extracted `runsc`
binary SHA-256 is
`1a3982cb91714f9c0c7148668d2c40143ee97e238f8a8e7452e410770d34fbe3`.
Do not compare the archive hash with the executable hash.

For a seeded delivery, the stock content-addressed directory is
`/var/lib/ate/static-files/gvisor-<ARCHIVE_SHA256>/`. Stage the whole archive
tree into that directory atomically through the approved per-node delivery
mechanism. Keep `runsc` and `gvisor-bin/` together. Verify the complete tree's
hashes and modes before exposing the final directory, including on a fresh
worker node. The stock cache-hit path checks directory presence; that alone
does not validate a partial or incorrectly seeded tree.

Check the same binary from the actual selected worker's shared mount, retain
its hash/version and correlate it with the canary actor's worker assignment.
The reference version string was
`release-20260824.0-120-g727c8c389c36-dirty`, spec 1.2.1. The archive checksum
pins the bytes more precisely than the version string.

The tested lab used public Google Storage. The pinned stock `openAsset`
implementation tries anonymous Google Storage before its configured store.
Changing a URL alone therefore does not establish zero public attempts.
The bank must prove its approved seed/internal delivery under its actual
network controls. Do not introduce a runtime-source patch during this run.

## Authentication, storage and policy

Validate in-cluster DNS, issuing CAs, certificate projections and bootstrap
pool ownership. The helper discovers the actual service-account issuer;
do not copy the personal AKS issuer or generated CA material.

The pinned API verifies JWTs using OIDC discovery. Prove that the issuer's
discovery document and JWKS are reachable and trusted from the API pods
through the bank's approved path. This stock build does not expose an
arbitrary `jwksUrl` or inline-JWKS field in its authentication configuration.
Changing the issuer string cannot change the `iss` claim in real tokens.
If discovery is blocked, return that prerequisite blocker rather than
disabling verification or inventing a configuration field.

Validate the approved storage credentials, endpoints, writable snapshot
prefix, PostgreSQL schema/backend and the rendered worker/atelet admission
requirements. Keep shared resources and real credentials outside the cleanup
scope. A successful public lab is a working baseline, not a bank air-gap,
registry-authentication or real-model result.

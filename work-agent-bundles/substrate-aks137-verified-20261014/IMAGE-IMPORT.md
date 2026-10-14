# Images to import for tomorrow

Use Linux AMD64 for the `Standard_D8s_v3` AKS node. Import these **18 public
images**, plus the synthetic fixture from the attached OCI archive. This
is the complete reference gVisor installation and runtime-smoke image set.
It includes both PostgreSQL versions and the chart's support images.

The earlier 13-row JSON lock omitted five already digest-pinned chart
support images. This revision adds those indexes and their platform digests;
it does not change the images used by the recorded lab run. Completeness was
checked against the pinned chart renders, fixture registry manifest and
Go ADK workload lock. No live cluster was queried or tested.

| # | Source image / version | Used for |
| --- | --- | --- |
| 1 | `ghcr.io/kagent-dev/substrate/ateapi:v0.4.0-alpha1` | Substrate API |
| 2 | `ghcr.io/kagent-dev/substrate/atecontroller:v0.4.0-alpha1` | Substrate controller |
| 3 | `ghcr.io/kagent-dev/substrate/atelet:v0.4.0-alpha1` | Node atelet |
| 4 | `ghcr.io/kagent-dev/substrate/atenet:v0.4.0-alpha1` | Atenet routing / ext-proc |
| 5 | `ghcr.io/kagent-dev/substrate/kubernetes-secrets:v0.4.0-alpha1` | Kubernetes Secrets provider |
| 6 | `ghcr.io/kagent-dev/substrate/podcertcontroller:v0.4.0-alpha1` | Pod certificate controller |
| 7 | `ghcr.io/kagent-dev/substrate/ateom-gvisor:v0.4.0-alpha1` | gVisor worker |
| 8 | `ghcr.io/kagent-dev/kagent/controller:1.0.0-alpha8` | kagent controller |
| 9 | `ghcr.io/kagent-dev/kagent/ui:1.0.0-alpha8` | kagent UI |
| 10 | `ghcr.io/kagent-dev/kagent/golang-adk:1.0.0-alpha8` | Go ADK actor workload |
| 11 | `docker.io/library/postgres:18.6-alpine3.23` | kagent PostgreSQL |
| 12 | `registry:3` | Reference fixture registry |
| 13 | `busybox:1.36` | Read-only asset-audit helper |
| 14 | `amazon/aws-cli:2.17.0` | Snapshot bucket initialization |
| 15 | `ghcr.io/kagent-dev/substrate/agentgateway:50999825cb55` | Atenet agentgateway dataplane |
| 16 | `postgres:18-alpine` | Substrate PostgreSQL / TLS reloader |
| 17 | `registry.k8s.io/pause:3.10.2` | Actor pause container |
| 18 | `rustfs/rustfs:1.0.0-beta.3` | Snapshot object storage |

## Pull the exact AMD64 images

On your internet-connected import workstation, in this bundle directory:

```bash
set -euo pipefail
while IFS= read -r image; do
  docker pull --platform linux/amd64 "$image"
done < images-linux-amd64.txt
```

[`images-linux-amd64.txt`](images-linux-amd64.txt) contains all 18 exact
AMD64 digest references, ready to copy into your approved import process.
Tags in the table are readable labels; the digest in the pull list fixes the
actual content. `docker pull` downloads to that workstation. You still need
to transfer/import the images into the bank registry using its approved flow.
Keep a source-to-private-reference/digest mapping for tomorrow's agent.

If your import flow preserves complete multi-architecture indexes, use
[`images-index.txt`](images-index.txt) instead. Copy all referenced manifests
and blobs while preserving the digest. [`image-lock.json`](image-lock.json)
records source indexes and platform-specific leaves. An AMD64-only import
should use its AMD64 leaf digest in the private deployment configuration.
Do not select ARM64 from the Mac lab.

`registry:3` is used by the reference disposable fixture registry. If your
bank will host the fixture in its approved registry, that temporary registry
is optional. `busybox:1.36` is the reference read-only runtime-asset audit
helper. Pulling all 18 avoids deciding those small helper substitutions now.

## Import the nineteenth image from the fixture archive

The synthetic counter fixture has no public registry pull URL. Its exact
bytes are in `artifacts/fixture.oci.tar` inside the prerequisites release
asset. Do not try to pull the example `localhost:15014/fixture` reference.
Import this OCI archive through your approved registry importer, or have
tomorrow's agent load it with `push-fixture.py` into the reference registry.

- OCI index: `sha256:14de92f1e72157f4e4322702a08020ca193c20471ae2021b2e76a806d5a96a67`
- Linux AMD64 manifest: `sha256:8590af269aac93de813e1f64df625f10572f1b18693541d39d80e6e071877729`
- Archive SHA-256: `863c844033d984ed7e3198e90a022a59ecc65f457baa5660c25affec96975f72`

See [`fixture-image-lock.json`](fixture-image-lock.json) and
[`fixture-archive-lock.json`](fixture-archive-lock.json) for the transfer checks.

## Also transfer the runtime archive and prerequisites

`runsc` and its gVisor helpers are separate runtime assets. Pulling the worker
image does not include them. Download the unchanged
`substrate-prerequisites.tar.gz` release asset, verify its checksum and bring
it through the approved transfer route:

https://github.com/davidmarkgardiner/kagent-public/releases/tag/substrate-aks137-bank-handoff-20261014

It supplies the full tested AMD64 gVisor archive, four chart archives,
fixture OCI archive, source working directory and operator helpers.
Follow [`PREREQUISITES.md`](PREREQUISITES.md) for Python/PyYAML, kubectl/Helm,
registry credentials, certificate discovery and storage requirements.

This image list covers the reference stack and runtime smoke. Any existing
bank-specific MCP server, model-serving container or image-pull credential
provider executable needs its separately approved dependency set; those were
not part of the recorded runtime-only demonstration. Both model-backed chat
and workplace smoke remain to be tested after reinstalling.

# The pinned runsc asset: making it reachable without gs:// or AWS

atelet fetches the gVisor `runsc` binary pinned in the `SandboxConfig`, by
default from `gs://gvisor/releases/...`. On a cluster with no egress to Google
storage the actor never boots, which is the failure the work team hit.

**There is a way that needs no object storage and no egress at all**, and it
was proven on 2026-09-23. Read the next section before anything else.

## First, clearing up two things

**The chart's "S3" is not AWS.** The Substrate chart deploys **RustFS**, an
S3-compatible object store, as a Deployment inside your own cluster, backed by
an ordinary PVC — on AKS that is an Azure managed disk. Nothing contacts AWS,
and no AWS account is involved. The `aws-cli` image in the chart is only a
client that speaks the S3 protocol to that in-cluster Service, and it runs one
Job to create a bucket. Any S3-compatible client would do.

**Azure Blob cannot be the backend directly.** Substrate 0.0.9 selects storage
with `ATE_STORAGE_BACKEND`, and the only values are `s3` and GCS (the default).
Azure Blob exposes no S3-compatible endpoint, so it cannot be plugged in as-is.
On Azure the practical answer is the bundled RustFS on Azure disks, or an
S3-compatible appliance if your platform already runs one.

## Recommended: pre-seed the node cache

`atelet` computes a content-addressed path for the asset,
`/var/lib/ateom-gvisor/static-files/runsc-<sha256>`, and **returns immediately
if that file already exists** — before any fetch is attempted. That directory
is on the hostPath atelet already mounts. Put the binary there and the asset
URL is never used.

[`preseed-daemonset.yaml`](preseed-daemonset.yaml) does this: an init container
from an image that carries the binary, verifying the digest and installing it
with mode 0755, then a pause container to hold the DaemonSet. It needs no
network.

**For the step-by-step — fetch the binary, build the image, push it, fill in
the DaemonSet, verify on the node — follow
[`PACKAGE-AND-PRESEED.md`](PACKAGE-AND-PRESEED.md).** The image is built from
[`Dockerfile.runsc`](Dockerfile.runsc).

**Proven, end to end.** On a two-node kind cluster with the hardened Substrate
install:

1. The DaemonSet seeded `runsc-62eee121...` on the Substrate node.
2. The `SandboxConfig` asset URL was then deliberately repointed to
   `gs://unreachable-internal-mirror/runsc`.
3. A `SandboxAgent` still reached `Accepted=True Ready=True`, and its
   ActorTemplate reached `Ready` **with a golden snapshot**.

So the actor booted with an unreachable asset URL, which is only possible via
the cache. For an air-gapped AKS cluster this is the cheapest route: one
DaemonSet, one mirrored image, no storage decisions.

Practical notes:

- **Architecture matters.** AKS node pools are normally amd64, so mirror the
  `x86_64` binary and its digest. Both digests are in the DaemonSet comments
  and were verified against the chart's `SandboxConfig` on 2026-09-23.
- **Cover every node** that can host a Substrate worker, and keep the DaemonSet
  in place so new or replaced nodes are seeded before their first actor.
- **The digest must match the `SandboxConfig`.** atelet only checks the file's
  presence at the digest-derived path, so a mismatch silently falls through to
  a fetch, which then fails. If boots still fail, check the exact filename on
  the node first.
- The hash check in Substrate is a format check, not an allowlist, so a
  correctly mirrored binary is accepted.

## Alternative: serve it from the cluster's own object store

The asset URL is parsed for a bucket and a key only — the scheme is ignored,
and the fetcher falls back from the anonymous public client to the cluster's
main object-store client, which is RustFS when `ATE_STORAGE_BACKEND=s3`. So a
`gs://<bucket>/<key>` URL pointing at the in-cluster bucket resolves
internally:

```sh
# upload (any S3 client; the bundle already ships aws-cli for its bucket Job)
aws --endpoint-url http://rustfs.ate-system.svc:9000 \
  s3 cp runsc s3://ate-snapshots/gvisor/20260622/x86_64/runsc

# then repoint the SandboxConfig, keeping the digest
kubectl patch sandboxconfig gvisor-default --type=json -p \
  '[{"op":"replace","path":"/spec/assets/amd64/runsc/url",
     "value":"gs://ate-snapshots/gvisor/20260622/x86_64/runsc"}]'
```

The upload was proven on 2026-09-23 (120 MB object, digest intact). **Booting
an actor from that URL was not exercised** — the pre-seed route was verified
instead, so treat this as code-backed but untested. Note the fetcher always
tries the anonymous public client first, so expect a logged failure for that
attempt before the internal one succeeds.

## Third option: allow the egress

Permit HTTPS to `storage.googleapis.com` and the stock configuration works
unchanged. That is a firewall exception for a public bucket, which an
air-gapped cluster will usually refuse.

## What to tell the platform team

The ask is not "an S3 bucket". It is either:

- **one mirrored image** carrying a 130 MB binary, plus a DaemonSet (preferred,
  proven); or
- an egress exception for `storage.googleapis.com` (probably refused).

The bundled RustFS covers snapshot storage either way, and lives on Azure
disks like any other PVC.

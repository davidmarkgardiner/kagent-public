# Work-agent walkthrough: mirror the gVisor asset for air-gapped AKS

Copy-ready procedure for the workplace agent. Goal: Substrate actors can
**suspend / resume / isolate** without egress to `gs://gvisor` or
`storage.googleapis.com`.

Read [`README.md`](README.md) first for the proven pre-seed design. This file is
the step-by-step replication script, including how to take a GitHub release
tarball and land the binary where atelet will find it.

Public-safe: replace every `{{PLACEHOLDER}}`. Never commit storage keys or tokens.

---

## Critical facts (do not skip)

1. **`ateom-gvisor` does not contain `runsc`.** atelet fetches the asset named
   in cluster-scoped `SandboxConfig` `gvisor-default`.
2. **Match the cluster pin.** Digests in this walkthrough for Substrate
   **0.0.9** were verified on 2026-09-23. Do **not** swap in a newer GitHub
   tag (for example `release-20260914.0`) unless you also update
   `SandboxConfig` and accept snapshot incompatibility risk.
3. **Native Azure Blob HTTPS is not a `SandboxConfig` URL.** Substrate storage
   is `s3` or GCS only. On AKS, use **in-cluster RustFS** (chart-bundled,
   PVC on Azure disks) and/or the **node pre-seed** path. Blob can hold
   courier artifacts offline; atelet still needs `s3://`/`gs://` via the
   cluster client, or a pre-seeded hostPath file.
4. **Preferred path (proven):** pre-seed
   `/var/lib/ateom-gvisor/static-files/runsc-<sha256>` via
   [`preseed-daemonset.yaml`](preseed-daemonset.yaml). No object-store fetch
   on actor boot.

---

## Step 0 — Read the live pin

```bash
kubectl get sandboxconfig gvisor-default -o yaml
```

Record:

| Field | What to copy |
|-------|----------------|
| Asset key under `amd64` | `runsc` (bare binary) **or** `gvisor` (archive) |
| `url` | Stock is usually `gs://gvisor/releases/...` |
| `sha256` | 64-char lowercase hex — **this is the source of truth** |

### Substrate 0.0.9 pins (verified 2026-09-23)

Use these unless `kubectl` shows different digests:

| Arch | Binary | sha256 |
|------|--------|--------|
| amd64 / x86_64 (typical AKS) | `runsc` | `f18a948bf9c8bbb54eb998549a3a8d719a1c7de2efbe8fdd2ff0ee5fecd06f19` |
| arm64 / aarch64 | `runsc` | `62eee121f8c188e347c428acc96f111568ede3be37b906046b6f28bbe2cc40c0` |

Release line associated with that pin in the DaemonSet comments: **20260622**
(not `release-20260914.0`).

---

## Step 1 — Download the matching artifact (connected jump box)

### 1a. Preferred: GCS HTTPS for the **pinned** release

```bash
# amd64 example for the 0.0.9 pin — adjust path if SandboxConfig differs
EXPECTED_SHA256="f18a948bf9c8bbb54eb998549a3a8d719a1c7de2efbe8fdd2ff0ee5fecd06f19"

curl -fL -o runsc \
  "https://storage.googleapis.com/gvisor/releases/release/20260622/x86_64/runsc"

echo "${EXPECTED_SHA256}  runsc" | shasum -a 256 -c -
chmod 0755 runsc
```

If the CR names a **tarball** asset (`gvisor` key), download that object instead
and keep it whole (see §1c).

### 1b. GitHub Releases (same bytes when the tag matches the pin)

GitHub point releases publish arch tarballs, for example:

```text
https://github.com/google/gvisor/releases/download/release-20260914.0/gvisor-x86_64.tar.bz2
```

**Only use a GitHub tag whose extracted `runsc` (or whole archive) sha256 equals
`SandboxConfig`.** For Substrate 0.0.9, prefer the 20260622 artifact above — not
`20260914.0` — unless you are deliberately changing the pin.

Generic download + inspect pattern:

```bash
TAG="release-20260622.0"   # example shape; confirm tag exists for your pin
ARCH="x86_64"              # or aarch64
ASSET="gvisor-${ARCH}.tar.bz2"

curl -fL -o "${ASSET}" \
  "https://github.com/google/gvisor/releases/download/${TAG}/${ASSET}"

# Optional: also fetch SHA256SUMS from the release and verify the tarball
shasum -a 256 "${ASSET}"

# List contents (modern releases include runsc + gvisor-bin/ sidecars)
tar -tjf "${ASSET}" | head -50
```

### 1c. Extract `runsc` from the tarball (only if the CR wants a bare binary)

```bash
mkdir -p /tmp/gvisor-extract
tar -xjf gvisor-x86_64.tar.bz2 -C /tmp/gvisor-extract
find /tmp/gvisor-extract -type f -name runsc

# Typical layout: ./runsc at archive root (confirm with find)
cp /tmp/gvisor-extract/runsc ./runsc
chmod 0755 ./runsc
echo "${EXPECTED_SHA256}  runsc" | shasum -a 256 -c -
```

If `SandboxConfig` asset key is **`gvisor`** (full archive), **do not extract for
upload** — atelet extracts. Upload the `.tar.bz2` / `.tar.zstd` as-is and keep
the archive digest from the CR.

Modern archives also ship `gvisor-bin/` next to `runsc`. For the **pre-seed
bare-`runsc`** path used with Substrate 0.0.9, the proven approach seeds only
the `runsc` binary at the digest path; stick to that unless upstream changes
the asset key to a full archive.

---

## Step 2 — Choose how the air-gap cluster obtains the bytes

### Option A — Pre-seed hostPath (recommended, proven 2026-09-23)

Build a tiny image that contains `/runsc`, mirror it, apply the DaemonSet.

```bash
# On the connected builder (Dockerfile is in this directory)
cp runsc ./runsc   # verified binary from Step 1
docker build -t "{{INTERNAL_REGISTRY}}/gvisor/runsc:20260622" -f Dockerfile.runsc .
docker push "{{INTERNAL_REGISTRY}}/gvisor/runsc:20260622"
```

Render and apply [`preseed-daemonset.yaml`](preseed-daemonset.yaml):

```bash
export INTERNAL_REGISTRY="{{INTERNAL_REGISTRY}}"
export RUNSC_SHA256="f18a948bf9c8bbb54eb998549a3a8d719a1c7de2efbe8fdd2ff0ee5fecd06f19"

sed \
  -e "s|{{INTERNAL_REGISTRY}}|${INTERNAL_REGISTRY}|g" \
  -e "s|{{RUNSC_SHA256}}|${RUNSC_SHA256}|g" \
  preseed-daemonset.yaml | kubectl apply -f -

kubectl -n ate-system rollout status ds/runsc-preseed --timeout=5m

# On a substrate node (debug pod / ssh): confirm cache file exists
#   ls -l /var/lib/ateom-gvisor/static-files/runsc-${RUNSC_SHA256}
```

Optional proof: temporarily point `SandboxConfig` URL at an unreachable bucket;
actor golden snapshot should still succeed (see README).

### Option B — Upload into in-cluster RustFS (S3 protocol, Azure disks)

The Substrate chart’s “S3” is **RustFS** on a PVC — not AWS. Upload with any
S3 client:

```bash
# Port-forward or run from a pod that can reach rustfs
aws --endpoint-url "http://rustfs.ate-system.svc:9000" \
  s3 cp runsc "s3://ate-snapshots/gvisor/20260622/x86_64/runsc"

# Scheme in SandboxConfig is ignored for routing; fetcher uses cluster S3 client.
# Keep the digest identical to Step 0.
kubectl patch sandboxconfig gvisor-default --type=json -p \
  '[{"op":"replace","path":"/spec/assets/amd64/runsc/url",
     "value":"gs://ate-snapshots/gvisor/20260622/x86_64/runsc"}]'
```

Prefer GitOps over a live patch when Flux owns the object. Upload was proven;
boot-from-URL was not — prefer Option A for air-gap certainty.

### Option C — Azure Blob as a **courier** only

Use Blob to move the file into the air-gap (azcopy), then still do A or B:

```bash
# Connected → Blob (approved account)
azcopy copy ./runsc \
  "https://{{STORAGE_ACCOUNT}}.blob.core.windows.net/{{CONTAINER}}/gvisor/runsc-20260622"

# Inside air-gap → download to jump box / build agent, then Option A or B
azcopy copy \
  "https://{{STORAGE_ACCOUNT}}.blob.core.windows.net/{{CONTAINER}}/gvisor/runsc-20260622" \
  ./runsc
echo "${EXPECTED_SHA256}  runsc" | shasum -a 256 -c -
```

Do **not** set:

```text
url: https://{{account}}.blob.core.windows.net/...
```

in `SandboxConfig`. That is unsupported.

### Option D — S3 gateway in front of Blob (only if platform mandates Blob as store)

If policy requires Azure Blob as the durable object store, front it with an
approved S3-compatible gateway (for example S3Proxy), point Substrate
`ATE_STORAGE_BACKEND=s3` + `AWS_ENDPOINT_URL` at the **gateway**, upload with
`aws --endpoint-url https://{{GATEWAY}} s3 cp ...`, and use an `s3://` or
`gs://bucket/key` URL in `SandboxConfig`. Extra moving parts — avoid unless
required.

---

## Step 3 — Also mirror `pauseImage`

`SandboxConfig.spec.pauseImage` is a separate OCI image. Mirror its digest into
`{{INTERNAL_REGISTRY}}` and rewrite if the cluster cannot pull
`registry.k8s.io`.

---

## Step 4 — Acceptance checks

```bash
# Read-only structural check
bash ../scripts/verify-aks-substrate.sh \
  --context {{KUBE_CONTEXT}} \
  --sandboxagent hello-substrate

# Functional: harmless prompt → idle → Suspended → resume with state
# Capture ateom / actor evidence. Deny egress to storage.googleapis.com.
```

Checklist for the work agent:

- [ ] `SandboxConfig` sha256 recorded from the live cluster (or 0.0.9 table above)
- [ ] Downloaded bytes verify with `shasum -a 256 -c`
- [ ] Pre-seed DaemonSet Ready on every substrate-capable node **or** RustFS object present
- [ ] No reliance on native Blob HTTPS in `SandboxConfig`
- [ ] `pauseImage` mirrored
- [ ] Actor Ready + golden snapshot without public gVisor egress
- [ ] Evidence: tag/path, sha256, Substrate/kagent versions, node cache `ls` or S3 `ls`

---

## Example: why not blindly use `release-20260914.0`?

```bash
# This is a valid GitHub artifact shape — but wrong for Substrate 0.0.9 unless
# the CR digests match after extract:
curl -fL -o gvisor-x86_64.tar.bz2 \
  "https://github.com/google/gvisor/releases/download/release-20260914.0/gvisor-x86_64.tar.bz2"
tar -xjf gvisor-x86_64.tar.bz2
shasum -a 256 runsc
# Compare to SandboxConfig. If different → do not use for 0.0.9 pre-seed.
```

Use `20260914.0` only when deliberately upgrading the pin together with
`SandboxConfig` and a fresh golden-snapshot plan.

---

## Related

- [`README.md`](README.md) — design, RustFS vs AWS, proven pre-seed story
- [`preseed-daemonset.yaml`](preseed-daemonset.yaml) — DaemonSet template
- [`Dockerfile.runsc`](Dockerfile.runsc) — minimal image packing `/runsc`
- [`../AIRGAPPED-AKS-README.md`](../AIRGAPPED-AKS-README.md) — full AKS air-gap install
- Upstream: [Sandboxing](https://kagent.dev/docs/kagent/1.x/substrate-runtime/sandboxing/),
  [Tune Agent Substrate](https://kagent.dev/docs/kagent/1.x/operations/tune-agent-substrate/),
  [gVisor releases](https://github.com/google/gvisor/releases)

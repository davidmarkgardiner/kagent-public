# Package runsc into an image and pre-seed it on the nodes

The explicit procedure: take the pinned gVisor `runsc` binary, put it in an
image in your own registry, and have a DaemonSet copy it onto every Substrate
node. After this, actors boot with no egress and no object storage, because
atelet finds the binary in its on-node cache and never uses the asset URL.

Every step below was run on 2026-09-23 and 2026-09-24, except the registry
round trip, which is noted where it appears. For why this works, see
[`README.md`](README.md).

## What you are building

```
gVisor release (HTTPS, fetched once on a connected machine)
   │
   ▼  docker build
your-registry/gvisor/runsc:20260622        an image whose only job is to carry /runsc
   │
   ▼  DaemonSet init container: install -m 0755
/var/lib/ateom-gvisor/static-files/runsc-<sha256>     on every Substrate node
   │
   ▼  atelet finds it by digest, skips the fetch
actor boots in a gVisor sandbox
```

The image is a delivery vehicle. Nothing mounts it into a sandbox: the init
container **copies** the binary onto the node, and the file stays there after
the pod is gone.

## Step 1 — Read the pin from the live cluster

The digest is the lookup key, so take it from the cluster rather than trusting
any document, this one included:

```sh
kubectl get sandboxconfig gvisor-default -o jsonpath='{.spec.assets}' | jq .
```

For Substrate `0.0.9` this was, verified 2026-09-23:

| Node architecture | Release line | Binary | sha256 |
|---|---|---|---|
| **amd64** (normal AKS) | 20260622 | `runsc` | `f18a948bf9c8bbb54eb998549a3a8d719a1c7de2efbe8fdd2ff0ee5fecd06f19` |
| arm64 | 20260622 | `runsc` | `62eee121f8c188e347c428acc96f111568ede3be37b906046b6f28bbe2cc40c0` |

**Use the architecture of the node pool, not of your laptop.**

## Step 2 — Fetch the binary on a connected machine

The pinned object is served over ordinary HTTPS, so the `gs://` scheme in the
`SandboxConfig` is not needed to obtain it:

```sh
ARCH=x86_64      # aarch64 for arm64 pools
curl -fL -o runsc \
  "https://storage.googleapis.com/gvisor/releases/release/20260622/${ARCH}/runsc"
shasum -a 256 runsc     # must equal the digest from step 1
```

Stop if the digest does not match. gVisor also publishes tarballs as GitHub
release assets (`gvisor-x86_64.tar.zstd` plus `SHA256SUMS`); if you take that
route, extract `runsc` and check it against the same pin, because the pin
refers to the bare binary.

## Step 3 — Build the image

[`Dockerfile.runsc`](Dockerfile.runsc) is three lines: a base image, a `COPY`
and a `chmod`. Build it with the binary in the context:

```sh
docker build --platform linux/amd64 \
  -t "$REGISTRY/gvisor/runsc:20260622" -f Dockerfile.runsc .
```

**`--platform` matters** when you build on an arm64 laptop for amd64 nodes.
Replace the base image with an approved one if your policy requires it; it
only needs a shell, `sha256sum` and `install`.

Confirm the binary survived the build:

```sh
docker run --rm --entrypoint sh "$REGISTRY/gvisor/runsc:20260622" \
  -c 'ls -l /runsc && sha256sum /runsc'
```

Tested: image built, `/runsc` present, 120710090 bytes, digest intact.

## Step 4 — Push it to your registry

```sh
az acr login -n "$ACR_NAME"
docker push "$REGISTRY/gvisor/runsc:20260622"
```

Or build inside the registry instead, which avoids pushing a 120 MB layer from
a laptop:

```sh
az acr build -r "$ACR_NAME" -t gvisor/runsc:20260622 \
  --platform linux/amd64 -f Dockerfile.runsc .
```

**Not tested here** — there was no registry available. Everything either side
of this step was.

## Step 5 — Fill in the DaemonSet

[`preseed-daemonset.yaml`](preseed-daemonset.yaml) has **three** placeholders:

| Placeholder | Appears | Value |
|---|---|---|
| `{{INTERNAL_REGISTRY}}` | **twice** — the runsc image and the pause image | your registry |
| `{{RUNSC_SHA256}}` | once, in the seed script | the digest from step 1 |

Substituting only the first occurrence leaves the pause container pulling from
a placeholder and the Pod stuck in `ImagePullBackOff`. Check before applying:

```sh
grep -n '{{' preseed-daemonset.yaml     # must print nothing
```

Also set the `nodeSelector` and tolerations to match **where your WorkerPool
runs**. A node that can host a worker but is not covered here will fail to
boot actors.

## Step 6 — Apply and verify

```sh
kubectl apply -f preseed-daemonset.yaml
kubectl -n ate-system rollout status daemonset/runsc-preseed
kubectl -n ate-system logs -l app=runsc-preseed -c seed
```

Expect `seeded /host/static-files/runsc-<sha256>`, or `already seeded` on a
restart. Then confirm on a node:

```sh
kubectl debug node/<substrate-node> -it --image=busybox:1.36 \
  -- ls -l /host/var/lib/ateom-gvisor/static-files/
```

You want exactly `runsc-<sha256>`, about 120 MB, mode `0755`. Tested: the
DaemonSet built from this Dockerfile placed the file with the digest and mode
intact.

## Step 7 — Prove the asset URL is no longer used

Optional but worth doing once, because it converts "it seems to work" into
evidence. Point the asset at a location that cannot resolve, then boot an
agent:

```sh
kubectl patch sandboxconfig gvisor-default --type=json -p \
  '[{"op":"replace","path":"/spec/assets/amd64/runsc/url",
     "value":"gs://unreachable-internal-mirror/runsc"}]'
```

A `SandboxAgent` should still reach `Ready` with a golden snapshot, which is
only possible from the cache. That is exactly the test run on 2026-09-23.
Restore the real URL afterwards so a node without the seed fails loudly rather
than silently.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Pod `ImagePullBackOff` on the `pause` container | The second `{{INTERNAL_REGISTRY}}` was not substituted |
| Seed logs `sha256sum: WARNING` | The binary does not match `{{RUNSC_SHA256}}`; wrong architecture or wrong release line |
| Actor boot still fails with a fetch error | Filename digest does not match the `SandboxConfig` pin, so the cache misses and the URL is used. Compare `ls` output with the CR |
| Works on some nodes only | The DaemonSet does not cover every node that hosts workers; check the `nodeSelector` against the WorkerPool |
| Boots today, fails after a node upgrade | The DaemonSet was removed; it must stay resident so repaved nodes are re-seeded |
| `exec format error` | amd64 binary on arm64 nodes, or the reverse |

## Related

`WORK-AGENT-MIRROR-WALKTHROUGH.md` on the `docs/airgap-gvisor-asset-walkthrough`
branch (PR #100) covers the same ground and adds the RustFS bucket alternative.
It is not on `main` yet. This file is the tested end-to-end packaging path;
when that PR merges, keep the two in step or fold one into the other.

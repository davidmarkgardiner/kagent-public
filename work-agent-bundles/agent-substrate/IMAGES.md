# Agent Substrate with kagent: minimal image list

The images you need to mirror to run kagent `SandboxAgent`s on Agent
Substrate, split into what is required and what you can drop.

Scope:

- kagent chart `0.10.1` and the kagent Substrate fork charts
  (`substrate-crds` and `substrate` `0.0.9`). kagent installs its own fork,
  `ghcr.io/kagent-dev/substrate`, not the upstream
  [`agent-substrate/substrate`](https://github.com/agent-substrate/substrate)
  images.
- Substrate `auth.mode: jwt` (the default), gVisor sandbox class, Go ADK
  runtime.
- Checked on 2026-09-21 with `helm template` against the published OCI charts
  and against the kagent `v0.10.1` controller source. The digests below were
  resolved on 2026-09-21, except postgres and valkey, which use the digests
  from the 2026-09-15 canary because their tags have moved since.

Neither CRD chart (`kagent-crds`, `substrate-crds`) contains any images.

## Summary

| Set | Count | When |
|-----|------:|------|
| Always required | 11 | Every install |
| Always rendered | 1 | kagent UI. Chart 0.10.1 has no flag to turn it off. |
| Required unless external | 4 | postgres, valkey, rustfs and aws-cli. Each can be replaced by a service outside the cluster. |
| Not needed | 8+ | Bundled agents, tools, kmcp, grafana-mcp, skills-init, podcertcontroller |

The smallest install is **12 images** (with external Postgres, Redis Cluster and
S3). A self-contained install is **16 images**.

## 1. Always required (11)

| # | Component | Image | Digest | Used by |
|---|-----------|-------|--------|---------|
| 1 | kagent controller | `ghcr.io/kagent-dev/kagent/controller:0.10.1` | `sha256:878a55478c1727e048d38154158aae41aa701149c6660f78696fe682c7495146` | kagent chart |
| 2 | Go ADK agent runtime | `ghcr.io/kagent-dev/kagent/golang-adk:0.10.1` | `sha256:120353200c0226b322e2830de2844eaf02ae4a4c06e778ee60014e5f6ed4a6d0` | Generated `ActorTemplate` (see note A) |
| 3 | ate-api | `ghcr.io/kagent-dev/substrate/ateapi:v0.0.9` | `sha256:3c50661b4e7d9e697ada97a97b2a8df563057a2cab5b9e7b0b09060ff80d9e85` | substrate chart |
| 4 | ate-controller | `ghcr.io/kagent-dev/substrate/atecontroller:v0.0.9` | `sha256:dc29e79987fe4177b92c8b30a4fa4f36f3cf1a80937b03a7a8cd3411f98693e5` | substrate chart |
| 5 | atelet (node DaemonSet) | `ghcr.io/kagent-dev/substrate/atelet:v0.0.9` | `sha256:ec3e842a1a0a060192710c34be83354d0b45e8d0e40342384d3b836413c3c8e1` | substrate chart |
| 6 | atenet (router and DNS) | `ghcr.io/kagent-dev/substrate/atenet:v0.0.9` | `sha256:15892218c70e736bca06bd9f1134425897f8b9c265428f932de5d6d779e9452a` | substrate chart |
| 7 | gVisor worker | `ghcr.io/kagent-dev/substrate/ateom-gvisor:v0.0.9` | `sha256:4aa5631a7e42e247660c12bef21d50c0a6a717fb717752748cc56a1b849a1fbc` | `substrateWorkerPool.ateomImage` |
| 8 | atenet-router sidecar | `cr.agentgateway.dev/agentgateway:v1.3.0-alpha.1` | `sha256:95e8d849c44ba31399daf504367ecfcfe2d3d3e59ffd96b1098234353afc3ef7` | substrate `images.agentgateway` |
| 9 | atenet DNS | `docker.io/coredns/coredns:1.11.1` | `sha256:1eeb4c7316bacb1d4c8ead65571cd92dd21e27359f0d4917f1a5822a73b75db1` | substrate `images.coredns` |
| 10 | init containers | `docker.io/library/busybox:1.36` | `sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662` | substrate `images.busybox` (ate-api JWT init and atenet-dns init) |
| 11 | sandbox pause | `registry.k8s.io/pause:3.10.2` | `sha256:f548e0e8e3dc1896ca956272154dde3314e8cc4fde0a57577ee9fa1c63f5baf4` | `controller.substrate.pauseImage` (see note B) |

**Note A: golang-adk is not in the Helm render.** The controller writes it
into each generated `ActorTemplate` when a `SandboxAgent` reconciles. From
0.10.x it is set by the chart value `controller.goAgentImage`
(`registry`/`repository`/`tag`), which the chart passes to the controller as
`GO_IMAGE_*` env vars. Point it at the internal registry. On 0.9.x it was
hard-coded to `cr.kagent.dev`; see the registry issue in [`README.md`](README.md).

**Note B: the pause image is not in the Helm render either.** The controller
default is `gcr.io/gke-release/pause@sha256:bcbd57ba5653580ec647b16d8163cdd1112df3609129b01f912a8032e48265da`
(the `--substrate-pause-image` flag). Upstream suggests
`registry.k8s.io/pause:3.10.2` when running outside GCP. Mirror one of them and
set `controller.substrate.pauseImage` to the full `repo@sha256:...` reference.
The ActorTemplate CRD rejects a pause image with no digest.

## 2. Always rendered: kagent UI (1)

| Component | Image | Digest | How to skip |
|-----------|-------|--------|-------------|
| kagent UI | `ghcr.io/kagent-dev/kagent/ui:0.10.1` | `sha256:2c4de55d3ffea5b960a41d667e3cd6b59d64d8da4d6d3ccf528fcd17e6fec4a0` | Chart 0.10.1 has no `ui.enabled`. Set `ui.replicas: 0` and no pod pulls the image. The Deployment still names it, so admission policies that check registries will still see it. Mirroring it is usually easier. |

## 3. Required unless replaced by an external service (4)

This is where the AWS-looking image comes from. `amazon/aws-cli` has nothing to
do with AWS the cloud. It runs one Job, `rustfs-bucket-init`, which creates the
snapshot bucket in the in-cluster RustFS store over the S3 API. If RustFS is
disabled, the Job is not rendered.

| Component | Image | Digest | Drop it with |
|-----------|-------|--------|--------------|
| kagent database | `docker.io/library/postgres:18.6-alpine3.23` | `sha256:697c180dbf244d3ce4a8f4cbc0156cde840af055c1bf8b76aebe422a4822086f` | `database.postgres.bundled.enabled: false` and `database.postgres.url` (or `urlFile`) pointing to an external Postgres |
| Substrate session store (StatefulSet with 6 replicas, plus a cluster-init Job) | `docker.io/valkey/valkey:8.0` | `sha256:dbb2de90cb7a60c4f3f7e8d73fcaab69a94c557bb08a064108fa5d5b1814086e` | `valkey.enabled: false` and `redis.clusterAddress: <host:6379>`. The replacement must be a Redis **Cluster**-mode endpoint. |
| Snapshot object store | `docker.io/rustfs/rustfs:1.0.0-beta.3` | `sha256:378642b05b7dcb4849fb77ebe6aca4ced1c3f66e7e504247df95a5c9018d3358` | `rustfs.enabled: false`, plus an external **S3-compatible** bucket (created beforehand) wired in through `atelet.extraEnv` (`AWS_ENDPOINT_URL`, `AWS_REGION`, `AWS_S3_USE_PATH_STYLE`, credentials) |
| Bucket-init Job | `docker.io/amazon/aws-cli:2.17.0` | `sha256:643507c10ada7964ca6157b3d799f030b90577643da9955d319a77399ed80d73` | Removed automatically when `rustfs.enabled: false` |

On AKS, Azure Blob Storage does not speak S3. Substrate 0.0.9 supports only
`s3` and GCS as storage backends, so unless you already run an S3-compatible
store, keep RustFS **and** aws-cli.

> **Security:** the chart's default RustFS credentials are
> `rustfsadmin`/`rustfsadmin`. Override `rustfs.accessKey` and
> `rustfs.secretKey` on any cluster that is not throwaway.

## 4. Not needed for Substrate

Disable these, or leave them out of the mirror:

| Image | Why it appears | Turn off with |
|-------|----------------|---------------|
| `ghcr.io/kagent-dev/kagent/app` | Python ADK runtime for ordinary Deployment `Agent`s and the 10 bundled agents. `SandboxAgent` is Go only. | `k8s-agent`, `kgateway-agent`, `istio-agent`, `promql-agent`, `observability-agent`, `argo-rollouts-agent`, `helm-agent`, `cilium-policy-agent`, `cilium-manager-agent`, `cilium-debug-agent` all set to `enabled: false` |
| `ghcr.io/kagent-dev/kagent/tools:0.2.1` | Built-in kagent tool server | `kagent-tools.enabled: false`, unless your agents call it |
| `ghcr.io/kagent-dev/kmcp/controller:0.3.0` | kmcp (`MCPServer`) controller | `kmcp.enabled: false` |
| `mcp/grafana:latest` | Grafana MCP server | `grafana-mcp.enabled: false` |
| `ghcr.io/kagent-dev/kagent/skills-init` | Init container, added only to agents that declare skills | Don't use skills, or mirror it |
| `ghcr.io/kagent-dev/substrate/podcertcontroller` | Used only in `auth.mode: mtls` | Keep `auth.mode: jwt` |
| oauth2-proxy | Already off by default | `oauth2-proxy.enabled: false` |
| `argoproj/rollouts-demo:blue` | Appears in the render, but only as text in an agent prompt. It is never pulled. | Not applicable |

## Not an image: the gVisor `runsc` binary

atelet downloads `runsc` at runtime from the `gvisor-default` `SandboxConfig`:
`gs://gvisor/releases/release/20260622/{x86_64,aarch64}/runsc`, pinned by
sha256. It is not an OCI image, so image mirroring does not cover it. An
air-gapped cluster needs that URL reachable, or the asset moved into a
location atelet can read. Upstream atelet falls back to the cluster's own
snapshot bucket, but that has not been tested here on the 0.0.9 fork.

## Copy-paste mirror list

The smallest install, with external Postgres, Redis Cluster and S3:

```text
ghcr.io/kagent-dev/kagent/controller@sha256:878a55478c1727e048d38154158aae41aa701149c6660f78696fe682c7495146
ghcr.io/kagent-dev/kagent/golang-adk@sha256:120353200c0226b322e2830de2844eaf02ae4a4c06e778ee60014e5f6ed4a6d0
ghcr.io/kagent-dev/kagent/ui@sha256:2c4de55d3ffea5b960a41d667e3cd6b59d64d8da4d6d3ccf528fcd17e6fec4a0
ghcr.io/kagent-dev/substrate/ateapi@sha256:3c50661b4e7d9e697ada97a97b2a8df563057a2cab5b9e7b0b09060ff80d9e85
ghcr.io/kagent-dev/substrate/atecontroller@sha256:dc29e79987fe4177b92c8b30a4fa4f36f3cf1a80937b03a7a8cd3411f98693e5
ghcr.io/kagent-dev/substrate/atelet@sha256:ec3e842a1a0a060192710c34be83354d0b45e8d0e40342384d3b836413c3c8e1
ghcr.io/kagent-dev/substrate/atenet@sha256:15892218c70e736bca06bd9f1134425897f8b9c265428f932de5d6d779e9452a
ghcr.io/kagent-dev/substrate/ateom-gvisor@sha256:4aa5631a7e42e247660c12bef21d50c0a6a717fb717752748cc56a1b849a1fbc
cr.agentgateway.dev/agentgateway@sha256:95e8d849c44ba31399daf504367ecfcfe2d3d3e59ffd96b1098234353afc3ef7
docker.io/coredns/coredns@sha256:1eeb4c7316bacb1d4c8ead65571cd92dd21e27359f0d4917f1a5822a73b75db1
docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
registry.k8s.io/pause@sha256:f548e0e8e3dc1896ca956272154dde3314e8cc4fde0a57577ee9fa1c63f5baf4
```

Add these for a self-contained install (bundled Postgres, Valkey and RustFS):

```text
docker.io/library/postgres@sha256:697c180dbf244d3ce4a8f4cbc0156cde840af055c1bf8b76aebe422a4822086f
docker.io/valkey/valkey@sha256:dbb2de90cb7a60c4f3f7e8d73fcaab69a94c557bb08a064108fa5d5b1814086e
docker.io/rustfs/rustfs@sha256:378642b05b7dcb4849fb77ebe6aca4ced1c3f66e7e504247df95a5c9018d3358
docker.io/amazon/aws-cli@sha256:643507c10ada7964ca6157b3d799f030b90577643da9955d319a77399ed80d73
```

## Minimal kagent values for this image set

```yaml
kmcp: {enabled: false}
kagent-tools: {enabled: false}
grafana-mcp: {enabled: false}
k8s-agent: {enabled: false}
kgateway-agent: {enabled: false}
istio-agent: {enabled: false}
promql-agent: {enabled: false}
observability-agent: {enabled: false}
argo-rollouts-agent: {enabled: false}
helm-agent: {enabled: false}
cilium-policy-agent: {enabled: false}
cilium-manager-agent: {enabled: false}
cilium-debug-agent: {enabled: false}
controller:
  goAgentImage:
    registry: "{{INTERNAL_REGISTRY}}"
  substrate:
    enabled: true
    ateApiEndpoint: dns:///api.ate-system.svc:443
    atenetRouterURL: http://atenet-router.ate-system.svc:80
    pauseImage: "{{INTERNAL_REGISTRY}}/pause@sha256:f548e0e8e3dc1896ca956272154dde3314e8cc4fde0a57577ee9fa1c63f5baf4"
    defaultWorkerPool: {name: kagent-default}
substrateWorkerPool:
  create: true
  name: kagent-default
  ateomImage: "{{INTERNAL_REGISTRY}}/kagent-dev/substrate/ateom-gvisor@sha256:4aa5631a7e42e247660c12bef21d50c0a6a717fb717752748cc56a1b849a1fbc"
```

Rendering the kagent chart with these values gives only `controller`, `ui`,
`postgres` and the `ateomImage`. golang-adk and pause are applied later, at
reconcile time. Rewrite the Substrate chart's `image.registry` and `images.*`
values to the internal registry in the same way. For the full pinned set,
including digests for every image, see
[`images.lock.tsv`](../kagent-agentgateway-tenant-isolation/platform/substrate/images.lock.tsv).

## Re-check after a version bump

```sh
helm template kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent --version <v> -f values.yaml | grep -E '^\s*image:' | sort -u
helm template substrate oci://ghcr.io/kagent-dev/substrate/helm/substrate --version <v> -f substrate-values.yaml | grep -E '^\s*image:' | sort -u
```

Then add golang-adk (`GO_IMAGE_*` in the controller ConfigMap), the pause image
(`SUBSTRATE_PAUSE_IMAGE`) and `ateomImage`. None of these show up as `image:`
lines in the render.

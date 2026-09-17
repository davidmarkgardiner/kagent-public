# Agent Substrate on Air-Gapped AKS

This is the **non-production AKS evaluation path** for running a kagent
`SandboxAgent` on Agent Substrate. It does not use kind. A normal read-only
kagent `Agent` does not require Agent Substrate.

```text
SandboxAgent -> kagent controller -> Agent Substrate WorkerPool -> gVisor actor
```

Do not apply the kind demo installer to AKS. It creates a local cluster, uses
demo model configuration, and contains a version-specific demo workaround.

## Required charts

Mirror these OCI charts into the approved internal Helm/OCI registry, pinned to
a tested **compatible** version pair. Do not use an unreviewed `latest` tag.

```text
oci://ghcr.io/kagent-dev/substrate/helm/substrate-crds
oci://ghcr.io/kagent-dev/substrate/helm/substrate
oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds
oci://ghcr.io/kagent-dev/kagent/helm/kagent
```

Install in this order:

```text
1. substrate-crds
2. substrate control and data plane (ate-system)
3. kagent-crds
4. kagent controller with Substrate integration and a WorkerPool
5. SandboxAgent
```

The current lift-and-shift target verified in this repository is kagent
`0.10.1` with Agent Substrate `0.0.9`. Those versions are a pair selected by
the kagent chart, not a recommendation to select the newest independent tag
from each project. On 2026-09-15, the renamed standalone project had released
Substrate `v0.1.0`; do not combine it with kagent `0.10.1` without upstream
compatibility evidence and a full golden-snapshot plus A2A run.

The kagent CRD allows Kubernetes to accept a `SandboxAgent`; the Agent
Substrate charts provide the WorkerPool and runtime that make it run.

## Air-gap preparation

Before changing AKS, retain a versioned deployment manifest containing:

1. The four chart archives and their checksums.
2. Every image rendered by those charts and the chosen values, mirrored by
   digest to `{{INTERNAL_REGISTRY}}`. Include Substrate control/data-plane,
   worker/gVisor, Valkey/object-storage, kagent controller/UI/tool/agent, and
   model-provider images.

   > **Critical — the Go ADK agent-runtime image is NOT in the Helm render.**
   > `helm template` does not surface it: the kagent controller injects it at
   > runtime into the generated `ActorTemplate.spec.containers[].image`. The
   > target profile uses
   > `ghcr.io/kagent-dev/kagent/golang-adk@sha256:120353200c0226b322e2830de2844eaf02ae4a4c06e778ee60014e5f6ed4a6d0`.
   > Mirror that exact source digest, set the kagent global `registry` to the
   > approved internal mirror, and verify the generated ActorTemplate before a
   > chat call. Older charts could emit an unresolved `cr.kagent.dev` path; a
   > cluster-wide rewrite is only the fallback when the installed chart cannot
   > select the mirror declaratively. Never hand-patch the generated
   > ActorTemplate because the controller owns and rewrites it. See
   > [`evidence/RUN-2026-07-16.md`](evidence/RUN-2026-07-16.md).
3. Internal registry CA trust and image-pull credentials, where required.
4. An approved internal model endpoint and a Secret reference for its
   credential. Never put model API keys in Git, Helm values, shell history or
   command arguments.
5. Rendered Flux `HelmRepository`/`HelmRelease` values and image-rewrite policy.
   Production-like AKS installation must reconcile from Git; the commands below
   are render/validation references only.

Render with the exact values that Flux will reconcile, then inspect every image
reference before mirroring:

```bash
helm template substrate-crds {{INTERNAL_REGISTRY}}/substrate/helm/substrate-crds \
  --version {{SUBSTRATE_VERSION}} --namespace ate-system > substrate-crds.rendered.yaml

helm template substrate {{INTERNAL_REGISTRY}}/substrate/helm/substrate \
  --version {{SUBSTRATE_VERSION}} --namespace ate-system \
  -f substrate-values.yaml > substrate.rendered.yaml

helm template kagent-crds {{INTERNAL_REGISTRY}}/kagent/helm/kagent-crds \
  --version {{KAGENT_VERSION}} --namespace kagent > kagent-crds.rendered.yaml

helm template kagent {{INTERNAL_REGISTRY}}/kagent/helm/kagent \
  --version {{KAGENT_VERSION}} --namespace kagent \
  -f kagent-substrate-values.yaml > kagent.rendered.yaml

rg '^\s*image:' *.rendered.yaml
```

## Required kagent values

The required shape is below. Environment values remain placeholders.

```yaml
controller:
  substrate:
    enabled: true
    ateApiEndpoint: "dns:///api.ate-system.svc:443"
    ateApiInsecure: false          # Keep TLS verification on; true is a lab shortcut.
    defaultWorkerPool:
      namespace: kagent
      name: kagent-default
  volumes:
    - name: substrate-ate-api-ca
      configMap:
        name: kagent-substrate-ca
  volumeMounts:
    - name: substrate-ate-api-ca
      mountPath: /etc/substrate-ca
      readOnly: true
  env:
    - name: SSL_CERT_FILE
      value: /etc/substrate-ca/ca.crt

# kagent 0.10.1 supports sandboxClass plus WorkerPool scheduling through template.
substrateWorkerPool:
  create: true
  name: kagent-default
  replicas: 3
  ateomImage: "{{INTERNAL_REGISTRY}}/kagent-dev/substrate/ateom-gvisor@{{SUBSTRATE_WORKER_MIRROR_DIGEST}}"
  sandboxClass: gvisor
  template:
    nodeSelector:
      agent-substrate.platform.example/enabled: "true"
    tolerations:
      - key: agent-substrate.platform.example/dedicated
        operator: Equal
        value: "true"
        effect: NoSchedule
```

The kagent 0.10.1 chart passes `substrateWorkerPool.template` into the WorkerPool CR,
so use it for the dedicated tainted node pool rather than patching the generated
resource. Replace the example label and taint with the approved work values and
verify the worker pods actually land on that pool before proceeding.

`controller.substrate.enabled` only configures kagent to use an already
installed `ate-system` runtime; it does not install Substrate itself.

For JWT mode, set the exact AKS service-account issuer and establish CA trust
before installing kagent. kagent `0.10.1` does not expose a dedicated ate-api
CA-file value; the canary-tested secure path mounts the approved public CA and
sets `SSL_CERT_FILE`. Do not use `ateApiInsecure=true` outside a disposable lab.

## AKS gates before deployment

- Dedicated, tainted AKS node pool for substrate workers.
- Scoped approval for privileged/gVisor checkpoint-restore workloads in
  `ate-system` and the WorkerPool namespace.
- Pod Security Admission labels approved for those namespaces.
- Exact service-account issuer reachable from ate-api, plus explicit ate-api CA
  trust in the kagent controller.
- Node-kernel checkpoint/restore proof on the selected pool.
- Internal registry reachability and image-pull proof from that pool.
- Approved object/snapshot storage, retention and encryption decision.
- Approved internal model/provider endpoint reachable from an actor.

## Quick validation

After Flux has reconciled the four releases and a test `SandboxAgent`, run:

```bash
bash scripts/verify-aks-substrate.sh \
  --context {{KUBE_CONTEXT}} \
  --sandboxagent hello-substrate
```

It verifies CRDs, `ate-system` rollouts, WorkerPool, kagent controller,
SandboxAgent Ready condition and generated ActorTemplate. It does **not** prove
a chat request, snapshot or restore.

For final acceptance, send a harmless prompt to the test agent, wait for it to
become idle, then capture actor/worker and `ateom` evidence that it suspended
and restored. Do not use a platform or production agent as the first test.

## Decision boundary

This is an experimental runtime evaluation, not a prerequisite for the
evidence-first triage pilot. Continue with a normal read-only kagent `Agent`
unless gVisor isolation, suspend/resume state, or high idle-agent density is an
accepted requirement.

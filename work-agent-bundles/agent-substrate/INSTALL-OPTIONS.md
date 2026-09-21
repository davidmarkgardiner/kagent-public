# Agent Substrate install options

Agent Substrate is **not** a setting on an individual Agent. A cluster needs:

1. the Substrate CRDs and Substrate control/data plane installed;
2. the kagent controller switched into Substrate mode; and
3. each Substrate agent declared as `kind: SandboxAgent` instead of `Agent`.

The kagent chart supports **two** ways to get step 1 onto the cluster. Steps 2
and 3 are identical for both.

Checked on 2026-09-21 against upstream kagent `v0.10.1`
(`helm/kagent/Chart-template.yaml`, `helm/kagent-crds/Chart-template.yaml`) and
the published charts (`helm show chart oci://ghcr.io/kagent-dev/kagent/helm/kagent --version 0.10.1`).

## Common to both options

kagent controller values:

```yaml
controller:
  substrate:
    enabled: true
    ateApiEndpoint: dns:///api.ate-system.svc:443
    atenetRouterURL: http://atenet-router.ate-system.svc:80
substrateWorkerPool:
  create: true               # creates the kagent-default WorkerPool
  name: kagent-default
  replicas: 3
  sandboxClass: gvisor
  ateomImage: "{{INTERNAL_REGISTRY}}/kagent-dev/substrate/ateom-gvisor@{{SUBSTRATE_WORKER_MIRROR_DIGEST}}"
```

Agent manifest shape (Go runtime only):

```yaml
apiVersion: kagent.dev/v1alpha2
kind: SandboxAgent
spec:
  type: Declarative
  declarative:
    runtime: go
  substrate:
    workerPoolRef:
      name: kagent-default
```

Ordinary `Agent` resources are unaffected and keep running as Deployments.

Full workplace value templates:
[`kagent-values.work.example.yaml`](../kagent-agentgateway-tenant-isolation/platform/substrate/kagent-values.work.example.yaml),
[`substrate-values.work.example.yaml`](../kagent-agentgateway-tenant-isolation/platform/substrate/substrate-values.work.example.yaml).
Pinned chart and image digests:
[`versions.lock`](../kagent-agentgateway-tenant-isolation/platform/versions.lock).

## Option A: separate Substrate releases (recommended, proven)

Substrate is installed as its own Helm releases in `ate-system`; the kagent
release keeps `substrate.enabled: false`.

```sh
helm upgrade --install substrate-crds oci://ghcr.io/kagent-dev/substrate/helm/substrate-crds \
  --version 0.0.9 --namespace ate-system --create-namespace

helm upgrade --install substrate oci://ghcr.io/kagent-dev/substrate/helm/substrate \
  --version 0.0.9 --namespace ate-system -f substrate-values.yaml

helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent \
  --version 0.10.1 --namespace kagent -f kagent-values.yaml   # substrate.enabled: false
```

This is the path used by this bundle and by
[`kagent-agentgateway-tenant-isolation`](../kagent-agentgateway-tenant-isolation/AKS-SUBSTRATE-PROMOTION.md),
and it has been run live on `red`
([`evidence/RUN-RED-2026-07-16.md`](evidence/RUN-RED-2026-07-16.md)).

## Option B: Substrate as a kagent subchart (supported upstream, not yet tested here)

Set `substrate.enabled: true` on **both** kagent charts. They then pull
`substrate-crds` 0.0.9 and `substrate` 0.0.9 as chart dependencies. Substrate
chart values move under a `substrate:` key (for example
`substrate.atelet.extraArgs`).

```sh
helm upgrade --install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds \
  --version 0.10.1 --namespace kagent --set substrate.enabled=true

helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent \
  --version 0.10.1 --namespace kagent -f kagent-values.yaml --set substrate.enabled=true
```

Open questions before relying on it:

- **Namespace.** Subchart resources may render into the kagent release
  namespace rather than `ate-system`. The controller endpoints above assume
  `ate-system`. Check with `helm template` before installing.
- **No in-place switch from A.** Helm refuses to take over objects already
  owned by the separate `substrate` and `substrate-crds` releases, so a cluster
  on option A cannot simply flip `substrate.enabled`.
- **Experimental.** The kagent chart's install notes mark Substrate as
  experimental and state that kagent uses its own Substrate fork.

## Which to use

Use **option A** for work clusters: Substrate can be upgraded or rolled back
without touching kagent, it stays in its own namespace, and it matches the
tested values and verification scripts. Option B means fewer releases with the
Substrate version locked to the kagent chart, which suits fresh throwaway
clusters.

## Verify

- Read-only cluster verifier: [`scripts/verify-aks-substrate.sh`](scripts/verify-aks-substrate.sh)
- Live gates (agent Ready, one golden ActorTemplate, WorkerPool replicas,
  authenticated call, suspend-to-snapshot):
  [`TEST-MATRIX.md`](../kagent-agentgateway-tenant-isolation/TEST-MATRIX.md) rows S04, S05 and P04.

# Agent Substrate on air-gapped AKS: hardened install

How to install kagent `0.10.1` with the kagent Substrate fork `0.0.9` on an
air-gapped AKS cluster whose admission safeguards reject any pod without a
read-only root filesystem, a hardened securityContext, or CPU/memory limits.
It assumes the four charts are already unpacked in the environment and every
image in [`../IMAGES.md`](../IMAGES.md) is mirrored.

The Substrate chart ships almost no hardening (no resources, and no
securityContext except on atelet). This bundle adds it with a Kustomize
post-renderer, so the unpacked charts stay untouched.

## Proof-of-concept path (start here)

**This is a non-production proof of concept.** The goal is to get it up and
running and tested, not to productionise it. Use the out-of-the-box defaults,
and skip everything this section doesn't list.

**Keep:**
- **The hardening post-render patches.** The cluster safeguards block pods
  without a read-only root filesystem and resource limits, so this is the
  only hardening that is required. It is just the `--post-renderer` flag on
  the `helm` commands in [Install](#install).
- **The existing AKS `substrate` node pool.** atelet and the gVisor workers
  select it by the label AKS already puts on every node,
  `kubernetes.azure.com/agentpool=substrate`. They tolerate any NoSchedule
  taint on it, so no custom label or taint needs approval. Check the pool name:
  ```sh
  kubectl get nodes -L kubernetes.azure.com/agentpool
  ```
  If it isn't `substrate`, change it in `substrate-postrender-patches.yaml`
  (atelet) and `workerpool.yaml`. If no node carries the label, atelet and the
  workers stay Pending.
- **A time-boxed policy exception in `ate-system`**, for atelet and the
  WorkerPool pods only (see
  [What still needs a policy exception](#what-still-needs-a-policy-exception)).

**Use the defaults:**
- **Certificates:** let the chart generate them (already the default in
  `substrate-values.yaml`). Don't pre-create `ateapi-tls` or `ateapi-ca`, and
  don't use Key Vault or External Secrets. After Substrate is installed, copy
  its CA into the kagent namespace once (Install step 6).
- **Valkey and RustFS:** use the bundled ones, not external Redis or S3. Put
  random RustFS credentials in `substrate-values.yaml` rather than the chart
  default `rustfsadmin`.
- **Install tool:** the Helm CLI, as in [Install](#install). Flux is optional.

**Skip:** Key Vault, bring-your-own certificates, external Redis/S3, a new
dedicated node pool, custom node labels or taints, session-key pre-creation
and Flux.

**Do not skip:** the pinned gVisor `runsc` asset. atelet fetches it from
`gs://gvisor/...` by default, and an actor cannot boot without it. Pre-seed it
on the node pool first — [`../runsc-asset/README.md`](../runsc-asset/README.md).

**Success:**
1. A `SandboxAgent` reaches Ready with a golden snapshot (see [Agents](#agents)).
2. Then one model call succeeds through the approved model endpoint.

**Stop and report if:**
- admission rejects anything other than atelet or the worker pods; or
- ate-api cannot reach the token issuer (see [Token issuer](#token-issuer)).

## What was tested

**Tested:** boot-tested on 2026-09-21 on a 3-node kind cluster (Kubernetes
1.35, containerd 2.2). One worker node was labelled and tainted as the
Substrate pool.

- `kagent` namespace enforced Pod Security `restricted`. The controller, UI
  and bundled PostgreSQL were all admitted.
- `ate-system` warned on Pod Security `restricted`. Only atelet was flagged,
  which is expected.
- Every hardened pod started and reached Ready: ate-api, ate-controller,
  atenet router and DNS, the 6 Valkey pods, RustFS and both Jobs.
- atelet and the gVisor worker landed on the tainted Substrate node.
- A `SandboxAgent` reached Ready. Its gVisor actor booted, was checkpointed,
  and the golden snapshot was uploaded to the in-cluster RustFS bucket.
- The certificate rotation runbook below was run end to end, followed by a
  second `SandboxAgent`.
- `verify-render.sh` with `VERIFY_SERVER=1` passed. The Flux HelmReleases
  passed a server-side dry-run against the helm-controller CRDs.

**Not tested:**
- AKS itself: your Deployment Safeguards or Kyverno policies, the AKS node
  image, and an external (AKS OIDC) token issuer.
- An actual Flux reconcile.
- Placement by the AKS pool label `kubernetes.azure.com/agentpool`. The kind
  run used a custom label and taint; the switch to the AKS label was only
  checked at render time.
- A model call from the agent. The test used a dummy key, and boot and
  snapshot do not call the model.

## The work agent's asks: required or not

| Ask | Required? | In this bundle |
|-----|-----------|----------------|
| External Redis cluster | **No** | Bundled Valkey, hardened (6 pods minimum, 1 GiB PVC each). |
| External S3 store | **No** | Bundled RustFS plus the `aws-cli` bucket Job, hardened. The bucket must stay `ate-snapshots`, because kagent's default snapshot location uses that name. |
| Substrate node placement | Use the existing `substrate` pool | The patches pin atelet and the WorkerPool to it. The chart has no placement values for atelet. |
| Approved node label and taint | **No** | Placement uses AKS's built-in `kubernetes.azure.com/agentpool` label and tolerates any NoSchedule taint on that pool. |
| Security approval | **Yes** | Two workloads are privileged by design (see below). |
| Policy exceptions | **Yes, for two workloads only** | Everything else passes the hardening checks and Pod Security `restricted`. |
| Chart availability | Done | Point the installs at the unpacked charts. |
| JWT and CA inputs | Mostly no | The chart generates the CA, server certificate and session keys. You supply the issuer (one command) and copy the CA once. |

## What still needs a policy exception

These two workloads cannot be hardened, because gVisor checkpoint/restore
needs them to be privileged:

| Workload | Why | What can still be set |
|----------|-----|-----------------------|
| `DaemonSet/atelet` (`ate-system`, label `app=atelet`) | `privileged: true`, hostPath `/var/lib/ateom-gvisor`, hostPorts 8085 and 9090 | Read-only root, resources, node placement: all patched |
| WorkerPool pods (`ate-system`, label `ate.dev/worker-pool=kagent-default`) | atecontroller generates the worker Deployment with `privileged: true`, `runAsUser: 0` and a hostPath. The WorkerPool API does not expose securityContext. | Resources and placement, set in `workerpool.yaml`. Read-only root cannot be set. |

The WorkerPool is created in `ate-system`, not `kagent`, so **every privileged
pod is in one namespace**. The `kagent` namespace can stay fully `restricted`.
Scope the exception to those two label selectors in `ate-system`:

- **Kyverno:** a `PolicyException` in `ate-system` naming the privileged,
  host-path, host-port, run-as-non-root, read-only-root and
  capabilities/seccomp rules for those two selectors.
- **AKS Deployment Safeguards:** exclusions are per namespace. Excluding
  `ate-system` exempts the whole namespace, including the hardened pods; check
  `az aks update --help` for the safeguards excluded-namespaces option on your
  CLI version.
- **Pod Security admission labels:** `ate-system` must be
  `pod-security.kubernetes.io/enforce: privileged`, and `kagent` can be
  `restricted`. Pin these labels if platform automation manages them.

## What the hardening adds

Every non-privileged container gets:

- `readOnlyRootFilesystem: true`
- `allowPrivilegeEscalation: false`
- `capabilities.drop: [ALL]`
- a pod-level `runAsNonRoot` and a RuntimeDefault seccomp profile
- CPU and memory requests and limits
- an emptyDir for each path it writes to

| Workload | User | Writable mounts | Notes |
|----------|------|-----------------|-------|
| ate-api | 65532 | `/tmp` and the chart's emptyDir for the cert bundle | Listens on 443 as non-root through the safe, namespaced sysctl `net.ipv4.ip_unprivileged_port_start=0` |
| ate-controller | 65532 | `/tmp` | |
| atenet DNS (coredns + dns-controller) | 65532 | `/tmp` and the chart's Corefile emptyDir | coredns keeps `NET_BIND_SERVICE`. Tested: without it, the container fails with `exec /coredns: operation not permitted`. |
| atenet router + agentgateway | 65532 | `/tmp` | |
| RustFS | 10001 | `/tmp`, `/logs` and the PVC | Tested: without `/logs` it exits with `Read-only file system (os error 30)` |
| Valkey (StatefulSet) and its init Job | 999 | `/tmp` and the PVC | `fsGroup: 999` makes the PVC writable |
| rustfs-bucket-init (aws-cli) | 1000 | `/tmp` | `HOME=/tmp` |
| atelet | root, privileged | `/tmp` and the hostPath | Read-only root works (tested); needs the exception |
| kagent controller and UI | chart defaults | chart defaults | The kagent chart is already hardened |
| kagent PostgreSQL (bundled) | 999 | `/var/run/postgresql`, `/tmp` and the PVC | `kagent-postrender-patches.yaml`. Not needed with an external database. |
| gVisor workers | root, privileged | set by atecontroller | `workerpool.yaml` sets the resources: 250m/512Mi requests, 2 CPU/2Gi limits |

**Resource figures are starting points.** Tune them from observed usage. CPU
limits on ate-api, atenet and coredns can throttle under load; if your
safeguards allow memory-only limits for those, prefer that.

If an older Kyverno sysctl policy rejects `net.ipv4.ip_unprivileged_port_start`,
the fallback is to move ate-api off port 443. That needs an args patch and a
Service `targetPort` patch, and is not included here.

## Files

| File | Purpose |
|------|---------|
| `substrate-values.yaml` | Substrate values: internal registry, issuer, bundled Valkey and RustFS |
| `kagent-values.yaml` | kagent values: Substrate mode, default WorkerPool in `ate-system`, CA trust, internal images, extras disabled |
| `substrate-postrender-patches.yaml` | Hardening patches for the Substrate release (the single source of truth) |
| `kagent-postrender-patches.yaml` | Hardening patch for the bundled PostgreSQL |
| `workerpool.yaml` | The gVisor WorkerPool in `ate-system`, with resources and placement |
| `post-render.sh` | Helm 3 `--post-renderer` that applies a patch file (bash and kubectl only) |
| `flux-helmreleases.sh` | Prints Flux HelmReleases with the same patches inlined |
| `check-hardening.py` | Offline checker for rendered manifests (python3 + PyYAML) |
| `verify-render.sh` | Pre-flight gate: render both releases, check them, and optionally run a server-side dry-run |

## Install

**Before you start**, replace every `{{PLACEHOLDER}}` in the values files and
`workerpool.yaml`:
- the registry
- the issuer
- the RustFS keys
- the pool name, only if it isn't `substrate`: in `workerpool.yaml` and
  `substrate-postrender-patches.yaml`

**Releases:** Substrate is its own release, `substrate` in `ate-system`
(the "separate releases" option in [`../INSTALL-OPTIONS.md`](../INSTALL-OPTIONS.md)).
kagent is the release `kagent` in `kagent`. The patches target the object
names produced by those release names.

```sh
# 0. Namespaces and Pod Security labels.
kubectl create namespace ate-system
kubectl label namespace ate-system pod-security.kubernetes.io/enforce=privileged
kubectl create namespace kagent
kubectl label namespace kagent pod-security.kubernetes.io/enforce=restricted

# 1. Token issuer for substrate-values.yaml (see "Token issuer").
kubectl get --raw /.well-known/openid-configuration | jq -r .issuer

# 2. Offline pre-flight: render both releases with the hardening and check them.
./verify-render.sh <charts>/substrate <charts>/kagent

# 3. Both CRD charts (they contain no pods).
helm upgrade --install substrate-crds <charts>/substrate-crds -n ate-system
helm upgrade --install kagent-crds <charts>/kagent-crds -n kagent

# 4. Let the cluster's own admission policies (Kyverno, Deployment Safeguards,
#    Pod Security) judge a server-side dry run of everything. Only the atelet
#    and WorkerPool exceptions should be reported.
VERIFY_SERVER=1 ./verify-render.sh <charts>/substrate <charts>/kagent

# 5. Substrate with the hardening post-renderer.
helm upgrade --install substrate <charts>/substrate -n ate-system \
  -f substrate-values.yaml --post-renderer ./post-render.sh

# 6. CA trust: copy the chart-generated CA into the kagent namespace.
kubectl -n ate-system get configmap ateapi-ca -o jsonpath='{.data.ca\.crt}' > ateapi-ca.crt
kubectl -n kagent create configmap kagent-substrate-ca --from-file=ca.crt=ateapi-ca.crt

# 7. The gVisor WorkerPool in ate-system.
kubectl apply -f workerpool.yaml

# 8. kagent with the PostgreSQL patch.
helm upgrade --install kagent <charts>/kagent -n kagent -f kagent-values.yaml \
  --post-renderer ./post-render.sh --post-renderer-args kagent-postrender-patches.yaml
```

**Use `helm upgrade --install` or Flux, never `helm template | kubectl apply`.**
The Substrate chart uses Helm `lookup` to keep its generated certificates.
Plain templating produces new ones on every render. The same applies to
Argo CD.

### With Flux

`./flux-helmreleases.sh > helmreleases.yaml` prints the four HelmReleases,
with `dependsOn` ordering and the patches inlined as `postRenderers`. Then:

- Set `{{CHART_SOURCE_KIND}}` and `{{CHART_SOURCE_NAME}}` to the Flux source
  (GitRepository or Bucket) holding the unpacked charts, and set the four
  chart paths.
- Create the values ConfigMaps:
  - `kubectl -n ate-system create configmap substrate-values --from-file=values.yaml=substrate-values.yaml`
  - `kubectl -n kagent create configmap kagent-values --from-file=values.yaml=kagent-values.yaml`
- The kagent HelmRelease depends on `substrate` across namespaces. That is
  blocked if Flux runs with `--no-cross-namespace-refs`.
- Steps 0, 6 and 7 still run outside Flux. Step 6 needs the CA that Substrate
  generates on first install.

### Agents

Declare agents as `SandboxAgent` with `runtime: go`, and **leave out
`spec.substrate.workerPoolRef`**. An explicit reference is looked up in the
agent's own namespace. Without one, the controller uses the default pool in
`ate-system`.

```yaml
apiVersion: kagent.dev/v1alpha2
kind: SandboxAgent
metadata:
  name: hello-substrate
  namespace: kagent
spec:
  type: Declarative
  declarative:
    runtime: go
    modelConfig: default-model-config   # an approved in-cluster model endpoint
    systemMessage: You are a test agent.
```

## Token issuer

ate-api checks the kagent controller's ServiceAccount token against the issuer
in `substrate-values.yaml`. It must match the `iss` claim exactly, so use the
output of step 1.

| Issuer | What ate-api needs |
|--------|--------------------|
| `https://kubernetes.default.svc.cluster.local` or `https://kubernetes.default.svc` | Nothing. ate-api reads the keys from the API server using the in-cluster CA (tested on kind). |
| Anything else, such as the AKS OIDC issuer `https://<region>.oic.prod-aks.azure.com/...` | HTTPS egress to that host. ate-api fetches the discovery document and signing keys from it directly with system trust roots, and the fork has no in-cluster fallback. In an air-gapped cluster that means a firewall allowance, or an egress proxy set as `HTTPS_PROXY`/`NO_PROXY` on the `ate-api-server` container through one more patch (untested). |

AKS clusters with the OIDC issuer enabled (for example for workload identity)
are in the second row.

## CA trust and rotation

The chart's CA is valid for 10 years, but **the ate-api server certificate is
valid for 365 days**. The CA private key is not stored, so rotating means
regenerating both. Run this before the certificate expires. It was tested on
kind:

```sh
kubectl -n ate-system delete secret ateapi-tls
kubectl -n ate-system delete configmap ateapi-ca
helm upgrade substrate <charts>/substrate -n ate-system -f substrate-values.yaml \
  --post-renderer ./post-render.sh                    # or let Flux reconcile
kubectl -n ate-system get configmap ateapi-ca -o jsonpath='{.data.ca\.crt}' > ateapi-ca.crt
kubectl -n kagent create configmap kagent-substrate-ca --from-file=ca.crt=ateapi-ca.crt \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n ate-system rollout restart deployment ate-api-server-deployment ate-controller atenet-router dns rustfs
kubectl -n kagent rollout restart deployment kagent-controller
```

Expect a short interruption while the Deployments restart.

**Bring your own certificate instead** if you have internal PKI or
cert-manager:

1. Set `auth.jwt.bootstrap.serverCert.enabled: false`.
2. Create, before installing:
   - the `ateapi-tls` Secret (`kubernetes.io/tls`), with SANs
     `api.ate-system.svc`, `api.ate-system.svc.cluster.local` and
     `atenet-router.ate-system.svc`;
   - the `ateapi-ca` ConfigMap, with key `ca.crt`.

ate-api builds its certificate bundle at pod start, so restart it after each
renewal.

## Upgrades

Run `verify-render.sh` against every new chart version before rolling it
out. If a new version adds a workload that no patch covers, the checker fails
it by name, instead of the release being rejected at admission.

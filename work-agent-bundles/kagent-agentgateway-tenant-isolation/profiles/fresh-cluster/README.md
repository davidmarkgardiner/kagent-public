# Fresh cluster bootstrap profile

This profile creates the control-plane baseline required to replay the tenant
isolation, Bring Your Own Agent, and Agent Substrate demonstrations on a new,
empty cluster. It is deliberately separate from `scripts/install-control-planes.sh`,
which is an existing-cluster canary/upgrade path.

## Exact version contract

| Component | Version | OCI chart digest |
| --- | --- | --- |
| Gateway API | `v1.6.2` experimental | release asset; record its downloaded SHA-256 in run evidence |
| agentgateway CRDs | `v1.5.0` | `sha256:3a6cf44559c612ac8afb7f867aace69bbd4cdba765f1def6377b7a3186c603e3` |
| agentgateway | `v1.5.0` | `sha256:9216ce83965ad2ce0888014d14aac5e71333fd9d4057cd167da92b37630fbee1` |
| Agent Substrate CRDs | `0.0.9` | `sha256:8a9e7ad008194eb7677b11bce9039b950b363e62d4b9ec9e3ec9f24854f3c25a` |
| Agent Substrate | `0.0.9` | `sha256:8063aa18e277c899e57f6cdf5086e5dcceb552668f30af4943054d2b98a1deda` |
| kagent CRDs | `0.10.1` | `sha256:0b8eacbdc85e21ccad6c008e69ef623428db0be8e45c59492b40f3faff6dcf67` |
| kagent | `0.10.1` | `sha256:dc7fc61090725fd9f860d630a0ca66a1bd2a86d15e3fe267c0467c11cb198403` |

The upstream latest releases checked on 17 September 2026 are kagent `v0.10.1`
and agentgateway `v1.5.0`. Substrate has newer standalone releases, but this
profile intentionally retains `0.0.9`, the compatibility pair selected and
canaried with kagent `0.10.1`. Do not independently bump it.

The minimum tested Kubernetes minor is `1.31`; this lab profile uses `1.32.2`.
The complete source-image inventory is in
`../../platform/substrate/images.lock.tsv`.

## Topology

The cluster is both the management and worker cluster. It runs:

- `tenant-agentgateway` in `tenant-gateway-system`;
- `tenant-kagent` in `tenant-kagent-system`, watching only the two ordinary
  application-agent namespaces; and
- `kagent` in `kagent`, watching only `kagent` and owning Agent Substrate.

The split preserves the already-tested route/service names. The watch sets do
not overlap, so the controllers cannot race over one `Agent` or `SandboxAgent`.

## Installation order

Cluster provisioning and Helm installation belong to one workflow, but not one
simultaneous operation: Helm starts only after the Kubernetes API and nodes are
ready.

### 1. Create the disposable home-lab cluster

```sh
kind create cluster --config kind-cluster.yaml
export KAGENT_CONTEXT=kind-kagent-fresh
kubectl --context "$KAGENT_CONTEXT" wait --for=condition=Ready nodes --all --timeout=5m
kubectl --context "$KAGENT_CONTEXT" apply -f namespaces.yaml
```

The Substrate stack needs roughly 8 vCPU and 16 GiB available to the container
runtime for a reliable demonstration. Do not taint the only kind node.

### 2. Install Gateway API

```sh
curl -fL --proto '=https' --tlsv1.2 \
  -o gateway-api-v1.6.2-experimental.yaml \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.2/experimental-install.yaml
sha256sum gateway-api-v1.6.2-experimental.yaml | tee gateway-api-v1.6.2-experimental.sha256
kubectl --context "$KAGENT_CONTEXT" apply --server-side \
  -f gateway-api-v1.6.2-experimental.yaml
kubectl --context "$KAGENT_CONTEXT" wait --for=condition=Established \
  crd/gateways.gateway.networking.k8s.io \
  crd/httproutes.gateway.networking.k8s.io \
  crd/referencegrants.gateway.networking.k8s.io --timeout=5m
```

Retain the SHA-256 receipt. Gateway API experimental CRDs are required by the
Entra MCP CORS overlay; standard-only CRDs are insufficient for that test.

### 3. Pull and verify every chart

Pull the six OCI charts into an evidence directory. Compare the `Digest:` line
from each `helm pull` with the table above and `../../platform/versions.lock`.
Stop on any mismatch.

```sh
helm pull oci://cr.agentgateway.dev/charts/agentgateway-crds --version v1.5.0
helm pull oci://cr.agentgateway.dev/charts/agentgateway --version v1.5.0
helm pull oci://ghcr.io/kagent-dev/substrate/helm/substrate-crds --version 0.0.9
helm pull oci://ghcr.io/kagent-dev/substrate/helm/substrate --version 0.0.9
helm pull oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds --version 0.10.1
helm pull oci://ghcr.io/kagent-dev/kagent/helm/kagent --version 0.10.1
```

Render the exact archives before installation and retain the output. Run the
repository public-safety scan before moving receipts into Git.

### 4. Install cluster-scoped APIs

Use the verified local chart archives, not a second network pull:

```sh
helm --kube-context "$KAGENT_CONTEXT" upgrade --install agentgateway-crds \
  ./agentgateway-crds-v1.5.0.tgz -n agentgateway-system --wait --timeout 5m
helm --kube-context "$KAGENT_CONTEXT" upgrade --install substrate-crds \
  ./substrate-crds-0.0.9.tgz -n ate-system --wait --timeout 5m
helm --kube-context "$KAGENT_CONTEXT" upgrade --install kagent-crds \
  ./kagent-crds-0.10.1.tgz -n kagent --wait --timeout 5m
```

### 5. Install agentgateway

Create and validate the data-plane parameters before the controller creates its
GatewayClass:

```sh
kubectl --context "$KAGENT_CONTEXT" apply --server-side --dry-run=server \
  -f agentgateway-parameters.yaml
kubectl --context "$KAGENT_CONTEXT" apply -f agentgateway-parameters.yaml
helm --kube-context "$KAGENT_CONTEXT" upgrade --install tenant-agentgateway \
  ./agentgateway-v1.5.0.tgz -n tenant-gateway-system \
  -f agentgateway-values.yaml --wait --timeout 10m
```

`AgentgatewayParameters` governs the generated proxy Deployment; the controller
Helm security context does not automatically harden proxy pods.

### 6. Install Substrate and both kagent owners

```sh
helm --kube-context "$KAGENT_CONTEXT" upgrade --install substrate \
  ./substrate-0.0.9.tgz -n ate-system \
  -f substrate-values.lab.yaml --wait --timeout 15m

helm --kube-context "$KAGENT_CONTEXT" upgrade --install kagent \
  ./kagent-0.10.1.tgz -n kagent \
  -f substrate-kagent-values.lab.yaml --wait --timeout 15m

helm --kube-context "$KAGENT_CONTEXT" upgrade --install tenant-kagent \
  ./kagent-0.10.1.tgz -n tenant-kagent-system \
  -f ordinary-kagent-values.yaml --wait --timeout 15m
```

The lab uses bundled PostgreSQL and `ateApiInsecure: true`. Both are explicitly
disallowed for workplace promotion.

## Provider and authentication boundary

Do not put a provider key in Helm values or Git. After the charts are healthy,
create the provider Secret out of band and apply a reviewed `ModelConfig` that
references the Secret and the approved agentgateway LLM route. The existing red
`deploy.sh` copies a credential from a pre-existing cluster and therefore must
not be used as the fresh-cluster credential workflow.

`modelconfigs.example.yaml` contains the three required CR shapes. Substitute
the model and OpenAI-compatible base URL outside Git, server-dry-run the result,
and apply it only after `model-provider-key`/`tenant-model-key` have been
delivered to the matching namespaces. In the final work design, point the base
URL at the approved agentgateway LLM listener rather than directly at a model
provider.

The UI is disabled. The lab Gateway remains `ClusterIP`; use port-forwarding.
Do not expose an HTTP listener publicly. The work overlay must add organization
TLS, an internal load balancer or approved ingress, Entra policies, and token
refresh evidence.

## Mandatory verification

Before applying the demo agents:

```sh
kubectl --context "$KAGENT_CONTEXT" get crd | grep -E 'gateway|agentgateway|kagent|ate'
kubectl --context "$KAGENT_CONTEXT" -n tenant-gateway-system rollout status \
  deployment/tenant-agentgateway --timeout=5m
kubectl --context "$KAGENT_CONTEXT" -n tenant-kagent-system rollout status \
  deployment/tenant-kagent-controller --timeout=5m
kubectl --context "$KAGENT_CONTEXT" -n kagent rollout status \
  deployment/kagent-controller --timeout=5m
kubectl --context "$KAGENT_CONTEXT" wait --for=condition=Accepted \
  gatewayclass/tenant-agentgateway --timeout=3m
```

Also prove:

- GatewayClass parametersRef is the expected `AgentgatewayParameters`;
- generated proxy and both controllers have the expected images, resources and
  security contexts;
- `tenant-kagent` watches exactly `tenant-kagent-system,team-event,team-chat`;
- `kagent` watches exactly `kagent`;
- WorkerPool desired replicas equal ready replicas;
- a `SandboxAgent` produces exactly one Ready ActorTemplate and a non-empty
  golden snapshot; and
- real A2A calls pass through agentgateway while wrong-token, wrong-role,
  forbidden-tool and direct-Service tests fail without backend activity.

Use `../../scripts/verify-substrate-target.sh`,
`../../scripts/verify-substrate-images.sh`, and
`../../../agent-substrate/scripts/verify-aks-substrate.sh` as supporting gates.
Readiness alone is not functional proof.

## Work/AKS promotion changes

For AKS, keep the same chart versions but replace the lab values with the
reviewed examples under `../../platform/substrate/`:

- internal registry and every locked image digest;
- resolved and mirrored digests for the platform agentgateway `v1.5.0`
  controller and proxy images (the current bundle locks their charts and tags,
  but does not yet record those two runtime digests);
- external PostgreSQL through a Secret/file reference;
- `ateApiInsecure: false` with the approved CA mounted into kagent;
- a dedicated labelled and tainted Substrate node pool;
- three WorkerPool replicas;
- approved privileged/hostPath policy exceptions for `ate-system` and the
  WorkerPool namespace; and
- Entra, TLS, workload-token refresh and external-network verification.

The current Substrate 0.0.9 chart fragment does not yet prove resource limits
and security contexts for every ate-api, controller, atelet, atenet, Valkey and
RustFS container. Before AKS promotion, vendor `helm show values` and the exact
rendered manifests, review every chart-supported override, and fail the policy
gate for missing resources except explicitly approved privileged components.
Do not invent unsupported Helm keys or claim restricted Pod Security for atelet.

## Do not use

- `scripts/install-control-planes.sh` for this fresh install: it is the
  shared-CRD existing-cluster path.
- `work-agent-bundles/agent-substrate/scripts/install-substrate.sh`: it is an
  older kind-only `0.9.9`/`0.0.6` path.
- standalone Substrate `latest`: current upstream latest is newer than the
  compatibility pair proven for kagent `0.10.1`.

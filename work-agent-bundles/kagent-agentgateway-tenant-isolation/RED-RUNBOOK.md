# Red cluster runbook

Red is shared. The canary uses new namespaces, release names, controller name, GatewayClass, and Gateway. It does not alter the existing `ai-gateway` or enable Substrate on the parallel kagent controller. Agentgateway and kagent CRDs are cluster-scoped, so the existing CRD Helm releases must be upgraded in place.

The integrated demo expects the existing platform-owned `kagent/machinist-security-review` SandboxAgent, its one Ready golden ActorTemplate, and the 3/3 `kagent-default` WorkerPool. `scripts/preflight.sh` fails closed if that historical lane is absent. Do not apply `platform/substrate/security-review-sandboxagent.yaml` on red; it is the workplace target manifest.

## Before mutation

```sh
./scripts/preflight.sh red
```

The command prints its raw evidence directory. By default it is outside the repository under the operating-system temporary directory. Set `TENANT_EVIDENCE_DIR` to an approved external location if the work item needs durable raw evidence. Confirm the expected current baseline before continuing.

Render both charts and inspect cluster-scoped names:

```sh
helm template tenant-agentgateway oci://cr.agentgateway.dev/charts/agentgateway \
  --version v1.5.0 --namespace tenant-gateway-system \
  -f platform/helm/agentgateway-values.yaml

helm template tenant-kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent \
  --version 0.10.1 --namespace tenant-kagent-system \
  -f platform/helm/kagent-values.yaml
```

## Install

```sh
export ALLOW_CLUSTER_SCOPED_UPGRADE=yes
./scripts/install-control-planes.sh red
./scripts/render.py --profile red
./scripts/deploy.sh red
./scripts/verify.sh red
```

The verifier also prints its raw evidence directory. Do not copy the raw inventory into this public bundle. Curate only placeholder-safe results into `evidence/red/`.

The `ALLOW_CLUSTER_SCOPED_UPGRADE` gate acknowledges the shared CRD change. It is not a substitute for change approval in a workplace cluster.

## Stop conditions

Stop if an existing Gateway or HTTPRoute loses Accepted status, a CRD has a stored-version conversion error, either canary controller watches the rogue namespace, the Substrate specialist loses Ready/golden-snapshot state, or a required negative case reaches a backend.

Do not enable Substrate reconciliation in `tenant-kagent-system` while red's shared all-namespaces kagent controller exists. Two controllers will race over the same SandboxAgent, and kagent 0.10.1 is not a supported client for red's installed Substrate 0.0.8 API. The workplace target must upgrade the owning controller and Substrate together to the locked 0.10.1/0.0.9 pair.

Do not downgrade CRDs as cleanup. Remove only the exact canary workload objects and controller releases after retaining evidence. Keep the upgraded additive CRDs unless the vendor supplies and the platform owner approves a rollback procedure.

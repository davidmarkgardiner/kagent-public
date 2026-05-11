# App Onboarding — Review Backlog

Consolidated findings from 7 specialist agent reviews (2026-03-24).

## Already Fixed

| Issue | Fix |
|-------|-----|
| Template injection (RCE) — `'''{{param}}'''` | `os.environ[]` in all Python templates |
| Shell injection — unquoted Argo params in bash | Env vars + Python subprocess |
| RBAC `bind`/`escalate` privilege escalation | Removed; restricted to `rolebindings` only |
| DAG skip cascades — skipped tasks skip dependents | `depends:` with `.Skipped` handling |
| `python:3.9-slim` has no kubectl | Switched to `bitnami/kubectl` + `python3` |
| Namespace validation too weak | Added RFC 1123 regex |
| ConfigMap YAML interpolation injection | Rewrote to `kubectl create --from-literal` |
| GitOps config stored too early | Moved deps to wait for deployment + RBAC |

## P0 — Security (before any deployment)

- [ ] **Azure allowlist** — validate `subscriptionId`, `resourceGroup`, OIDC `issuer` against known values
- [ ] **ClusterRole allowlist** — restrict `rbac.clusterRole` to `{view, edit}` only
- [ ] **Service type restriction** — only allow `ClusterIP` (LoadBalancer exposes externally)
- [ ] **System namespace blocklist** — reject `kube-system`, `argo`, `istio-system` etc.
- [ ] **Label key allowlist** — block `pod-security.kubernetes.io/`, `istio-injection` prefixes
- [ ] **Remove `secrets` from ClusterRole** — workflow doesn't need cluster-wide secrets access
- [ ] **Pin image tags** — `bitnami/kubectl:1.31.0`, `python:3.12-slim`, custom toolbox image

## P1 — Correctness

- [ ] **Service requires application** — cross-field validation (`has-service` implies `has-application`)
- [ ] **Add `retryStrategy`** to all kubectl tasks (limit: 2, backoff: 10s)
- [ ] **Concurrency semaphore** — `synchronization.semaphore` with max 10 concurrent workflows
- [ ] **Add `schemaVersion: "v1"`** to payload — JSON Schema (Draft 2020-12) shipped at `schemas/golden-path-payload.schema.json`; `schemaVersion` field not yet added to payload or schema
- [ ] **KAgent failure is silent** — decide: advisory (document) or blocking (add `exit 1`)
- [ ] **Missing `createIfNotExists: false` sample payload**
- [ ] **Add `defaultDeny: false` sample payload**

## P2 — Operational

- [ ] **Extract defaults to ConfigMap** (15+ hard-coded values in parse-payload)
- [ ] **Enrich exit handler** — include `workflow.failures`, namespace, duration in notification
- [ ] **Add Prometheus metrics** — `app_onboarding_total`, `_duration_seconds` via Argo metrics block
- [ ] **Create operational runbooks** (failed onboarding, partial cleanup, ASO stuck, replay, sensor down, schema migration, RBAC escalation, capacity planning)
- [ ] **Implement `allowEgress` netpol** or remove from sample payloads
- [ ] **Strip sensitive fields** (azure section) before storing payload in ConfigMap
- [ ] **Add LimitRange** alongside ResourceQuota (pods without resource specs get rejected otherwise)
- [ ] **Resource quota upper bounds** — enforce max CPU/memory/pods in validation

## P3 — Architecture Evolution

- [ ] **ASO identity block → KRO RGD (`uk8s-app-identity`)** — eliminates 4 templates + 10-min polling loop, adds drift correction. Follows `uk8scluster-public.yaml` pattern.
- [ ] **Consolidate kubectl-apply boilerplate** — use Argo native `resource` templates for simple manifests (quota, service, RBAC)
- [ ] **Single toolbox image** — `python3` + `kubectl` + `jq` + `curl` in one pinned image
- [ ] **Actual GitOps** — push config to Git repo, not just ConfigMap storage
- [ ] **Multi-cluster support** — `targetCluster` parameter + kubeconfig mounting (defer until needed)
- [ ] **Grafana dashboard** — onboarding throughput, success rate, duration distribution
- [ ] **PrometheusRule alerting** — failure rate, duration SLO, KAgent unhealthy, ASO timeout
- [ ] **OpenTelemetry tracing** — distributed traces across DAG steps
- [ ] **Tenant-level quota enforcement** — max resources per SWC across all namespaces
- [ ] **Namespace naming convention** — enforce `{swc}-{project}-{environment}` pattern
- [ ] **Idempotency mutex** — `synchronization.mutex` on `metadata.name` to prevent duplicate workflows

## Review Sources

| Agent | Focus |
|-------|-------|
| Code Reviewer | Initial sweep — injection, DAG bugs, RBAC |
| Security Reviewer | Attack surface — Azure takeover, label injection, system namespaces |
| Architecture | DAG correctness, concurrency, GitOps timing, multi-cluster |
| Planner | Production readiness — schema versioning, observability, runbooks |
| Refactoring | Code quality — boilerplate, defaults extraction, image consolidation |
| TDD | Test coverage — missing payloads, edge cases, KAgent silent failure |
| KRO Specialist | Pattern fit — ASO identity block as RGD, boundary between Argo and KRO |

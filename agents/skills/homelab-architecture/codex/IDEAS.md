# Ideas (Apps + Showcases)

Updated: 2026-02-08

## Showcase Apps Worth Adding

- **Argo CD (or Flux)**: best “wow factor” for reproducibility. Pair it with a repo layout that defines namespaces, Helm releases, and app values.
- **Backstage (Developer Portal)**: creates a real “platform” vibe; link services, docs, runbooks, and dashboards. Great with SSO.
- **External Secrets Operator**: demo secrets flowing from Google Secret Manager (or another store) into K8s safely.
- **MetalLB**: lets you expose services as true LoadBalancers in your LAN; simplifies getting off NodePorts.
- **Keycloak (optional)**: if Authentik stays primary, skip; otherwise Keycloak is a common reference point for SSO demos.

## Practical Homelab Apps (Useful + Demo-able)

- **Vaultwarden** (Bitwarden-compatible) for passwords.
- **Paperless-ngx** for document OCR + automation workflows (pairs well with Home Assistant).
- **Immich** for photo backup/management.
- **Mealie** for recipe management.
- **MinIO** as internal S3 target (enables Velero/Longhorn backups, app object storage).

## AI/Agent “Dave” Demos (Fit Your Existing Stack)

- **LLM Gateway service**: a small API that routes requests to KubeAI models, logs to Langfuse, and enforces auth via Authentik.
- **RAG playground**: ingest docs from Gitea/Ghost, store embeddings (pgvector or Qdrant), and expose a UI via Open WebUI or a tiny Next.js app.
- **Home Assistant Copilot**: agent that reads HA states/events (read-only first), summarizes anomalies, suggests automations, and writes “draft YAML” PRs to Gitea.
- **Ops Copilot**: agent that reads Prometheus alerts, correlates logs in Loki, and files an incident/task into Vikunja with links to Grafana panels.

## Platform Engineering “Polish”

- Add Renovate (or Dependabot) for Helm charts/manifests repos.
- Add CI for YAML lint + kubeconform against your cluster version.
- Add a “golden app template” (Helm chart or Kustomize base) with:
  - resources/limits, liveness/readiness, PDB, service account, networkpolicy, ingress


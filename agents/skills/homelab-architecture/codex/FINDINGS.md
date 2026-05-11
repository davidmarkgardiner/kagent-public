# Findings (Homelab Architecture)

Updated: 2026-02-08

## High Impact Improvements

- Add a real ingress layer inside Kubernetes (Ingress + `cert-manager` + `external-dns`) and stop relying on NodePorts as the primary exposure mechanism. Keep NPM only as an edge reverse-proxy if you want, but route to ClusterIP/Ingress rather than NodePort.
- Add GitOps for the {{CLUSTER_NAME}} cluster (Argo CD or Flux) so services, namespaces, and configs are reproducible and drift is visible.
- Add a backup story that is explicit and tested:
  - Cluster-level: Velero (with restic) for manifests + PVC snapshots/backups.
  - Longhorn: scheduled backups to an S3-compatible target (MinIO, Backblaze B2, etc).
  - Databases: logical dumps for PostgreSQL where recovery-time matters.
- Standardize secrets delivery into Kubernetes:
  - If you want to keep Google Secret Manager, use External Secrets Operator (ESO) and document the pattern.
  - Otherwise switch to something local (Vault, SOPS + age, sealed-secrets).

## Medium Impact Improvements

- Auth: Authentik is present; document a “default SSO pattern” (OIDC/SAML) and which services are already integrated (Grafana, Gitea, Vikunja, etc). Add a checklist for onboarding new apps.
- Observability: You have Grafana/Loki/Prometheus. Add:
  - `kube-state-metrics`, `metrics-server` (if not already), node-exporter
  - alert routing expectations (where Alertmanager sends alerts)
- Security hardening:
  - Define Pod Security Standards / PSA level per namespace (baseline/restricted).
  - Add NetworkPolicies (at least default-deny in “sensitive” namespaces).
  - Add image scanning (Trivy) and optional runtime detection (Falco) if you want to demo security.
- Reliability:
  - Make Longhorn replica count and node constraints explicit (what happens if a node fails).
  - Document resource requests/limits conventions for “default app deployments”.

## Documentation Consistency Notes

- The diagram in `SKILL.md` uses `192.168.6.4` for both Kind host and `k8s-cp1`. If that’s intentional (same machine running both), call it out explicitly to avoid confusion.
- `references/services.json` lists `"Flarum"` in `"namespace": "discourse"` which is surprising (not wrong, but it reads like a rename). Consider aligning namespace name with the app or documenting why.

## Automation To Add (Lightweight)

- A validator for `references/services.json` (added at `codex/scripts/validate_services_json.py`).
- Optional: a generator to render the service inventory as a Markdown table for `README.md` or `SKILL.md` to avoid manual drift.


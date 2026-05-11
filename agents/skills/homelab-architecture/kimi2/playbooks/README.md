# Homelab Improvement Playbooks

Step-by-step guides for deploying recommended services.

---

## Phase 1: Critical Infrastructure

| Playbook | Priority | Time | Description |
|----------|----------|------|-------------|
| [01-deploy-vaultwarden.md](./01-deploy-vaultwarden.md) | HIGH | 30m | Password manager |
| [02-deploy-volback.md](./02-deploy-volback.md) | CRITICAL | 45m | Backup solution |

## Phase 2: Productivity

| Playbook | Priority | Time | Description |
|----------|----------|------|-------------|
| 03-deploy-outline.md | MEDIUM | 1h | Wiki/knowledge base |
| 04-deploy-paperless.md | MEDIUM | 45m | Document management |
| 05-deploy-infisical.md | MEDIUM | 1h | Secret management |

## Phase 3: Developer Experience

| Playbook | Priority | Time | Description |
|----------|----------|------|-------------|
| 06-deploy-codeserver.md | LOW | 30m | Browser-based VS Code |
| 07-deploy-harbor.md | LOW | 2h | Container registry |
| 08-deploy-n8n.md | MEDIUM | 45m | Workflow automation |

---

## Quick Commands

```bash
# Deploy all Phase 1
kubectl apply -f phase1/

# Check all services
kubectl get pods --all-namespaces

# Update services.json after each deployment
./scripts/update-service-registry.sh
```

---

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues.

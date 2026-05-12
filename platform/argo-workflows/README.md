# Argo Workflows — Platform WorkflowTemplates

Argo Workflows WorkflowTemplates for namespace onboarding, ASO cluster provisioning, app/MCP/BYO-kagent onboarding, and canary deployments. Each subdirectory contains ready-to-apply Kubernetes manifests.

## Template Directories

| Directory | Purpose |
|-----------|---------|
| `templates/namespace-onboarding/` | Provision a new namespace with ResourceQuota, NetworkPolicy, and GitOps config |
| `templates/mcp-onboarding/` | Register a new MCP (Model Context Protocol) server into the agent platform |
| `templates/byo-kagent/` | Onboard a Bring-Your-Own-KAgent deployment into the platform |
| `templates/app-onboarding/` | Full app onboarding pipeline — namespace + RBAC + ArgoCD App creation |
| `templates/aso-provisioning/` | ASO-backed AKS cluster provisioning (parameterized + deployment templates) |
| `templates/canary/` | Canary and blue/green deployment workflows using Argo Rollouts + podinfo |
| `templates/vpa/` | Vertical Pod Autoscaler recommendation workflows |
| `rbac/` | ServiceAccount, Role, RoleBinding, ClusterRole, ClusterRoleBinding for workflow execution |
| `install/` | Helm chart values and deployment scripts for Argo Workflows itself |

## Quick Start

See `ARGO_SETUP_README.md` for full installation and port-forward instructions.

```bash
# Apply RBAC first
kubectl apply -f rbac/

# Apply WorkflowTemplates
kubectl apply -f templates/namespace-onboarding/
kubectl apply -f templates/app-onboarding/
```

## Authentication

Argo Workflows server uses JWT tokens. Configure authentication via the values in `install/`.

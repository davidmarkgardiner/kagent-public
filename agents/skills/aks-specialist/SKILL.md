---
name: aks-specialist
description: Azure Kubernetes Service specialist for enterprise AKS clusters. Systematic troubleshooting, incident response, GitLab integration, and automated remediation workflows.
---

# AKS Specialist

Expert Azure Kubernetes Service specialist for diagnosing, troubleshooting, and automating incident response across enterprise AKS clusters.

## When to Use This Skill

- Troubleshooting AKS-specific issues (node pools, Azure CNI, managed identity)
- Responding to production incidents on AKS clusters
- Creating automated triage workflows
- Generating GitLab issues from cluster failures
- Certification and health check automation

## AKS-Specific Diagnostics

### Cluster Health Check
```bash
# Get AKS cluster status
az aks show -g <resource-group> -n <cluster-name> --query "powerState"

# Check node pool status
az aks nodepool list -g <resource-group> --cluster-name <cluster-name> -o table

# Get AKS diagnostics
az aks get-credentials -g <resource-group> -n <cluster-name>
kubectl get nodes -o wide
kubectl get pods -A | grep -v Running
```

### Common AKS Issues

#### Node Pool Issues
**Symptoms:** Nodes NotReady, scaling failures, VM allocation errors

**Diagnostics:**
```bash
# Check node pool status
az aks nodepool show -g <rg> --cluster-name <cluster> -n <nodepool>

# Check VM scale set
az vmss list-instances -g MC_<rg>_<cluster>_<region> -n <vmss-name> -o table

# Check for Azure capacity issues
az vm list-skus -l <region> --query "[?name=='Standard_D4s_v3'].restrictions"
```

**Common Causes:**
- Azure region capacity constraints
- Subnet IP exhaustion (Azure CNI)
- Quota limits exceeded
- Node pool scaling limits

#### Azure CNI Networking
**Symptoms:** Pod scheduling failures, IP exhaustion, connectivity issues

**Diagnostics:**
```bash
# Check subnet IP availability
az network vnet subnet show -g <rg> --vnet-name <vnet> -n <subnet> \
  --query "{available: addressPrefix, used: ipConfigurations | length(@)}"

# Check CNI config
kubectl get pods -n kube-system -l k8s-app=azure-cni -o wide

# Network policy check
kubectl get networkpolicies -A
```

#### Managed Identity Issues
**Symptoms:** Permission denied, Azure resource access failures

**Diagnostics:**
```bash
# Check managed identity
az aks show -g <rg> -n <cluster> --query "identity"

# Check pod identity (if using AAD Pod Identity)
kubectl get azureidentity,azureidentitybinding -A

# Check workload identity
kubectl get serviceaccounts -A -o json | jq '.items[] | select(.metadata.annotations["azure.workload.identity/client-id"])'
```

## Incident Response Workflow

### Severity Levels (AKS)

| Level | Impact | Response Time | Examples |
|-------|--------|---------------|----------|
| SEV-1 | Cluster down | Immediate | API server unreachable, control plane failure |
| SEV-2 | Major degradation | 15 min | Node pool unhealthy, ingress down |
| SEV-3 | Service impaired | 1 hour | Single app failing, pod crashes |
| SEV-4 | Minor issue | Business hours | Warning alerts, non-critical |

### Automated Triage → GitLab Flow

```
K8s Event (Warning)
    ↓
Argo Events Sensor
    ↓
AI Triage Workflow
    ↓
[Analyze with Claude/Grok]
    ↓
Create GitLab Issue
    • What failed
    • Possible causes
    • Remediation steps
    • Verification checklist
```

### GitLab Issue Template

When creating issues for AKS failures:

```markdown
## 🚨 [Severity] Alert - [Cluster] - [Issue Type]

| Field | Value |
|-------|-------|
| **Cluster** | `<cluster-name>` |
| **Namespace** | `<namespace>` |
| **Resource** | `<resource-type>/<name>` |
| **Timestamp** | <ISO timestamp> |

---

## ❌ What Failed
<error message / symptom>

## 🔍 Possible Causes
- Cause 1
- Cause 2
- Cause 3

## 🛠️ Remediation Steps
1. Step with command
2. Step with command

## ✅ Verification Checklist
- [ ] Issue resolved
- [ ] Monitoring stable for 15 min
- [ ] Root cause documented
```

## Health Check Scripts

### Full Cluster Certification

Run the shipped script instead of retyping the checks:

```bash
# From the repo root (script ships inside this skill directory)
agents/skills/aks-specialist/scripts/aks-cert-check.sh [--context CTX] [--json]
```

It runs the sectioned health sweep (API server, nodes, system pods, problem
pods, recent events, PVC status, resource quotas) and exits non-zero when it
detects problem pods or unbound PVCs, so it can gate automation. Interpret the
findings with the diagnostics sections above.

For the full Argo-based certification workflow, use
`infra/kro-stack/certification/` (`deploy-certification.sh`, `example-run.sh`).

## Integration with Existing Workflows

This skill integrates with:
- **argo-events**: Triggers on K8s warning events
- **certification workflow**: Automated health checks
- **GitLab**: Issue creation for failures
- **Telegram**: Real-time alerts

## References

- `scripts/aks-cert-check.sh` - full cluster certification health check (in this skill)
- `agents/skills/k8s-troubleshooter/` - general K8s diagnostic scripts and issue patterns
- `agents/kagent-triage/PLAYBOOK-WORKLOAD-CLUSTER.md` and `PLAYBOOK-MANAGEMENT-CLUSTER.md` - incident playbooks
- `agents/kagent-triage/LIFT-AND-SHIFT-AKS.md` - Azure-specific migration and configuration issues
- `infra/kro-stack/certification/` - Argo-based cluster certification workflows

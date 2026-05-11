# Homelab Architecture Analysis & Recommendations

**Analysis Date:** 2026-02-08  
**Analyst:** Kimi 🧠  
**Scope:** Proxmox K8s Cluster (3 nodes) + Kind Development Cluster

---

## Executive Summary

David's homelab is a **well-architected, production-ready environment** with solid foundations:
- ✅ 3-node K8s cluster with Longhorn distributed storage
- ✅ GitOps-friendly with Gitea, monitoring with Grafana/Prometheus/Loki
- ✅ AI/LLM stack (KubeAI, Open WebUI, Langfuse)
- ✅ Identity management (Authentik SSO)
- ✅ Multiple agent VMs (Gem, Kimi, Codex, Data)

**Overall Grade: A-** (Excellent foundation with room for strategic additions)

---

## Current Architecture Assessment

### Strengths
| Area | Implementation | Score |
|------|---------------|-------|
| **Storage** | Longhorn with 2 replicas | A |
| **Networking** | Cloudflare Tunnel + NPM wildcard certs | A |
| **Monitoring** | Grafana + Prometheus + Loki + Alertmanager | A- |
| **Secrets** | GCloud Secret Manager | B+ |
| **AI Stack** | KubeAI + Open WebUI + Langfuse | A- |
| **Dev Experience** | Gitea + {{CLUSTER_NAME}} dev cluster | A |
| **Documentation** | SKILL.md + services.json | B+ |

### Identified Gaps

| # | Gap | Impact | Priority |
|---|-----|--------|----------|
| 1 | **No Secret Manager (self-hosted)** | Dependency on GCloud | Medium |
| 2 | **No Password Manager** | Security/team sharing | High |
| 3 | **No Document Management** | Paperless workflow missing | Medium |
| 4 | **No Wiki/Knowledge Base** | Team documentation | Medium |
| 5 | **No CI/CD Runner** | Manual deployments | High |
| 6 | **No Backup Solution** | Disaster recovery | Critical |
| 7 | **No Code Server/IDE** | Remote development | Medium |
| 8 | **No Image Registry** | Docker image management | Low |
| 9 | **No Message Queue** | Async job processing | Low |
| 10 | **No Feature Flags** | Progressive rollouts | Low |

---

## Recommended Improvements

### Phase 1: Critical Infrastructure (Immediate)

#### 1.1 Add CI/CD with Gitea Actions
**Why:** Currently no automated build/deploy pipeline
```yaml
# Add to Gitea namespace
gitea-runner:
  replicas: 2
  resources:
    cpu: 500m
    memory: 1Gi
```

#### 1.2 Deploy Vaultwarden (Password Manager)
**Why:** Team password sharing, secure credential management
- **URL:** `vault.lab.{{INGRESS_DOMAIN}}`
- **NodePort:** 30095
- **Storage:** 5Gi
- **Integrates with:** Authentik SSO

#### 1.3 Implement Backup Solution (VolBack or K8up)
**Why:** No disaster recovery strategy currently
```yaml
backup:
  schedule: "0 2 * * *"  # Daily at 2am
  retention: 30d
  destinations:
    - s3://homelab-backups
    - local-nas
```

### Phase 2: Productivity & Documentation (Short-term)

#### 2.1 Deploy Outline Wiki
**Why:** Team knowledge base, AI agent documentation
- **URL:** `wiki.lab.{{INGRESS_DOMAIN}}`
- **Features:** Markdown, collaborative editing, Slack-like UI
- **Storage:** 10Gi for attachments

#### 2.2 Add Paperless-ngx
**Why:** Document digitization and OCR
- **URL:** `docs.lab.{{INGRESS_DOMAIN}}`
- **NodePort:** 30096
- **Use case:** Receipt tracking, contract storage, invoice processing

#### 2.3 Deploy Infisical (or HashiCorp Vault)
**Why:** Self-hosted secret management reduces GCloud dependency
- **URL:** `secrets.lab.{{INGRESS_DOMAIN}}`
- **NodePort:** 30097
- **Migration path:** Gradually migrate from GCloud Secret Manager

### Phase 3: Developer Experience (Medium-term)

#### 3.1 Code Server (VS Code in Browser)
**Why:** Remote development from any device
- **URL:** `code.lab.{{INGRESS_DOMAIN}}`
- **NodePort:** 30098
- **Pre-installed:** kubectl, helm, docker CLI

#### 3.2 Harbor Container Registry
**Why:** Private Docker image storage, vulnerability scanning
- **URL:** `registry.lab.{{INGRESS_DOMAIN}}`
- **NodePort:** 30099
- **Features:** Image signing, replication, retention policies

#### 3.3 Add n8n Workflow Automation
**Why:** Connect services, automate tasks (complements Motia)
- **URL:** `n8n.lab.{{INGRESS_DOMAIN}}`
- **NodePort:** 30100
- **Use cases:** GitHub → Slack notifications, scheduled reports, data sync

### Phase 4: Advanced Capabilities (Long-term)

#### 4.1 Feature Flags (Flagsmith or Unleash)
**Why:** A/B testing, progressive rollouts
- **URL:** `flags.lab.{{INGRESS_DOMAIN}}`

#### 4.2 Message Queue (RabbitMQ or NATS)
**Why:** Async job processing, service decoupling
- **URL:** `queue.lab.{{INGRESS_DOMAIN}}`

#### 4.3 Distributed Tracing (Jaeger or Tempo)
**Why:** Complete observability alongside metrics/logs
- **URL:** `trace.lab.{{INGRESS_DOMAIN}}`

---

## Architecture Comparison

### Current State
```
┌─────────────────────────────────────────────────────────────┐
│                     Cloudflare (DNS)                        │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    ┌──────────────────┐          ┌──────────────────┐
    │   Kind (Dev)     │          │  Proxmox K8s     │
    │   192.168.6.4    │          │  (3 nodes)       │
    └──────────────────┘          └──────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
            ┌───────────┐        ┌───────────┐        ┌───────────┐
            │Worker 1   │        │Worker 2   │        │ Control   │
            │• KubeAI   │        │• Langfuse │        │   Plane   │
            │• Ghost    │        │• Vikunja  │        │           │
            │• OpenWebUI│        │• Authentik│        │           │
            └───────────┘        └───────────┘        └───────────┘
```

### Recommended Target State
```
┌─────────────────────────────────────────────────────────────┐
│                     Cloudflare (DNS)                        │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    ┌──────────────────┐          ┌──────────────────────────┐
    │   Kind (Dev)     │          │     Proxmox K8s          │
    │   192.168.6.4    │          │     (3 nodes + 1 new)    │
    └──────────────────┘          └──────────────────────────┘
                                             │
              ┌──────────────────────────────┼────────────────────┐
              │              │               │                    │
              ▼              ▼               ▼                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    NEW SERVICES LAYER                            │
    ├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
    │Vaultwarden│ Outline │ Paperless│ Infisical│  n8n     │  Code    │
    │Passwords │  Wiki   │  Docs    │ Secrets  │Workflows │  Server  │
    └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
           ┌─────────────┐      ┌─────────────┐
           │   Backup    │      │   Harbor    │
           │  (VolBack)  │      │  Registry   │
           └─────────────┘      └─────────────┘
```

---

## Resource Planning

### Current Resource Utilization (Estimated)
| Node | CPU | RAM | Usage |
|------|-----|-----|-------|
| k8s-cp1 | 4 cores | 8GB | ~60% |
| k8s-worker1 | 4 cores | 16GB | ~70% |
| k8s-worker2 | 4 cores | 16GB | ~70% |

### Post-Additions (Recommended 4th Node)

| Service | CPU | RAM | Storage |
|---------|-----|-----|---------|
| Vaultwarden | 250m | 512Mi | 5Gi |
| Outline | 500m | 1Gi | 10Gi |
| Paperless | 1 | 2Gi | 50Gi |
| Infisical | 500m | 1Gi | 5Gi |
| n8n | 500m | 1Gi | 5Gi |
| Code Server | 1 | 2Gi | 10Gi |
| Harbor | 1 | 2Gi | 100Gi |
| Backup | 500m | 1Gi | - |
| **TOTAL** | **~5 cores** | **~10GB** | **~185GB** |

**Recommendation:** Add 4th node (k8s-worker3) with 4 cores / 16GB RAM

---

## Security Enhancements

### Current: Good
- Authentik SSO
- Cloudflare Tunnel for external access
- Wildcard SSL certificates

### Recommended Additions:
1. **Vaultwarden** - Centralized password management
2. **Infisical** - Self-hosted secrets (reduce cloud dependency)
3. **Falco** - Runtime threat detection
4. **Trivy** - Container vulnerability scanning
5. **Network Policies** - Inter-namespace traffic control

---

## Monitoring Improvements

### Add to Existing Stack:

```yaml
# Additional dashboards needed:
dashboards:
  - homelab-overview:
      - Node resource usage
      - Service health grid
      - SSL cert expiry
      - Backup status
      
  - cost-optimization:
      - Storage utilization
      - Idle resources
      - Right-sizing recommendations
      
  - security:
      - Failed login attempts
      - Certificate expiry
      - Vulnerability scan results
```

---

## Next Steps

| Week | Action | Owner |
|------|--------|-------|
| 1 | Deploy Vaultwarden | Scotty |
| 1 | Set up VolBack backups | Scotty |
| 2 | Deploy Outline Wiki | Kimi |
| 2 | Add Gitea Actions runner | Scotty |
| 3 | Deploy Paperless-ngx | Kimi |
| 3 | Add Code Server | Kimi |
| 4 | Deploy n8n | Scotty |
| 5 | Evaluate 4th node | Team |
| 6 | Deploy Harbor | Scotty |
| 8 | Migrate to Infisical | Team |

---

## Related Documents

- [New Apps Showcase](./SHOWCASE.md) - Demo applications to build
- [Implementation Playbooks](./playbooks/) - Step-by-step deployment guides
- [Architecture Diagrams](./diagrams/) - Visual representations

---

*Analysis complete. Awaiting team review.*

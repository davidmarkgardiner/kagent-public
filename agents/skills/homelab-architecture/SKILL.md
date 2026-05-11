---
name: homelab-architecture
description: Complete architecture reference for David's homelab environment. Use when working with any homelab service, deploying new workloads, troubleshooting connectivity, or understanding the infrastructure. Covers Proxmox K8s cluster, Kind cluster, networking, storage, and all deployed services.
---

# Homelab Architecture Skill

Complete infrastructure reference for David's homelab. Updated 2026-03-12.

## Quick Reference

### Key URLs
| Service | URL | Purpose |
|---------|-----|---------|
| **Dashboard** | https://lab.{{INGRESS_DOMAIN}} | Main Glance dashboard |
| **Grafana** | https://{{INGRESS_DOMAIN}} | Monitoring dashboards |
| **Gitea** | https://gitea.lab.{{INGRESS_DOMAIN}} | Git server |
| **NPM** | https://npm.lab.{{INGRESS_DOMAIN}} | Reverse proxy admin |
| **Longhorn** | https://longhorn.lab.{{INGRESS_DOMAIN}} | Storage management |
| **Uptime Kuma** | https://uptime.lab.{{INGRESS_DOMAIN}} | Service monitoring |

### Cluster Access
```bash
# Proxmox K8s (production)
kubectl --context={{CLUSTER_NAME}} get pods -A

# Kind cluster (development)
kubectl --context={{CLUSTER_NAME}} get pods -A
```

## Infrastructure Overview

```
                    ┌─────────────────────────────────────────────┐
                    │           Cloudflare (DNS + Tunnel)         │
                    └─────────────────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    │                                         │
              *.{{INGRESS_DOMAIN}}                         *.lab.{{INGRESS_DOMAIN}}
              (public, Kind)                         (internal, Proxmox)
                    │                                         │
                    ▼                                         ▼
    ┌───────────────────────────┐         ┌───────────────────────────┐
    │     Mini PC (Kind)        │         │  Nginx Proxy Manager      │
    │     192.168.6.4           │         │  (Proxmox K8s)            │
    │     ─────────────────     │         │  ─────────────────        │
    │  • Traefik Ingress        │         │  • SSL termination        │
    │  • Cloudflare Tunnel      │         │  • Wildcard cert          │
    │  • Dev workloads          │         │  • Route to NodePorts     │
    └───────────────────────────┘         └───────────────────────────┘
                                                     │
                    ┌────────────────────────────────┴───────────────┐
                    │                                                │
                    ▼                                                ▼
    ┌───────────────────────────┐         ┌───────────────────────────┐
    │   k8s-worker1             │         │   k8s-worker2             │
    │   192.168.6.5             │         │   192.168.6.6             │
    │   ─────────────────       │         │   ─────────────────       │
    │  • KubeAI (LLM)           │         │  • Langfuse               │
    │  • Ghost (blog)           │         │  • Vikunja                │
    │  • Ghostfolio             │         │  • Authentik              │
    │  • Open WebUI             │         │  • Motia demo             │
    └───────────────────────────┘         └───────────────────────────┘
```

## Proxmox K8s Cluster

**Nodes:**
| Node | IP | Role | Resources |
|------|-----|------|-----------|
| k8s-cp1 | 192.168.6.4 | Control Plane | 4 CPU, 8GB RAM |
| k8s-worker1 | 192.168.6.5 | Worker | 4 CPU, 16GB RAM |
| k8s-worker2 | 192.168.6.6 | Worker | 4 CPU, 16GB RAM |

**Key Namespaces:**
| Namespace | Services |
|-----------|----------|
| `default` | KubeAI, Open WebUI |
| `monitoring` | Prometheus, Grafana, Loki, Alertmanager |
| `gitea` | Gitea, PostgreSQL, Valkey |
| `ghost` | Ghost CMS |
| `ghostfolio` | Ghostfolio, PostgreSQL, Redis |
| `authentik` | Authentik SSO |
| `langfuse` | Langfuse LLM observability |
| `vikunja` | Vikunja task management |
| `video-automation` | VidAuto dashboard |
| `discourse` | Flarum forum |
| `longhorn-system` | Longhorn storage |
| `proxy` | Nginx Proxy Manager |

## Service Inventory

### Core Infrastructure
| Service | URL | NodePort | Purpose |
|---------|-----|----------|---------|
| NPM | npm.lab.{{INGRESS_DOMAIN}} | 30033 | Reverse proxy |
| Glance | lab.{{INGRESS_DOMAIN}} | 30000 | Dashboard |
| Uptime Kuma | uptime.lab.{{INGRESS_DOMAIN}} | 30031 | Monitoring |
| Longhorn | longhorn.lab.{{INGRESS_DOMAIN}} | 30081 | Storage UI |

### Development Tools
| Service | URL | NodePort | Purpose |
|---------|-----|----------|---------|
| Gitea | gitea.lab.{{INGRESS_DOMAIN}} | 30032 | Git server |
| Grafana | {{INGRESS_DOMAIN}} | 30030 | Metrics |
| Langfuse | langfuse.lab.{{INGRESS_DOMAIN}} | 32401 | LLM observability |
| Vikunja | tasks.lab.{{INGRESS_DOMAIN}} | 32402 | Task management |

### AI/LLM Platform
| Service | URL | NodePort | Namespace | Purpose |
|---------|-----|----------|-----------|---------|
| KubeAI | ai.lab.{{INGRESS_DOMAIN}} | 30091 | kubeai | Local LLM serving (GPU) |
| Open WebUI | chat.lab.{{INGRESS_DOMAIN}} | 30090 | kubeai | Chat interface |
| LiteLLM | litellm.lab.{{INGRESS_DOMAIN}}/ui/ | — | litellm | OpenAI-compatible proxy (key: sk-poc-homelab-1234) |
| KAgent | kagent.lab.{{INGRESS_DOMAIN}} | — | kagent | AI agent framework |
| AKS-MCP | — | — | aks-mcp | kubectl access for AI agents |
| HolmesGPT | — | — | holmesgpt | AI-powered K8s triage (optional) |

**KubeAI models:** qwen2.5-3b (running), qwen3-14b (degraded — GPU nodeSelector mismatch, RTX 3060 is Turing not Ampere)

### Applications
| Service | URL | NodePort | Purpose |
|---------|-----|----------|---------|
| Ghost | blog.lab.{{INGRESS_DOMAIN}} | 30092 | Blog CMS |
| Ghostfolio | stocks.lab.{{INGRESS_DOMAIN}} | 32333 | Portfolio tracker |
| Flarum | forum.lab.{{INGRESS_DOMAIN}} | 30093 | Agent forum |
| VidAuto | vidauto.lab.{{INGRESS_DOMAIN}} | 30034 | Video automation |
| Motia | motia.lab.{{INGRESS_DOMAIN}} | 32080 | Motia demo |
| Authentik | authentik.lab.{{INGRESS_DOMAIN}} | 30094 | SSO |

### Home Automation
| Service | URL | Purpose |
|---------|-----|---------|
| Home Assistant | ha.lab.{{INGRESS_DOMAIN}} | Smart home |
| Proxmox VE | proxmox.lab.{{INGRESS_DOMAIN}} | Hypervisor |

## Storage

**Longhorn** provides distributed block storage:
- Default StorageClass: `longhorn`
- Replica count: 2
- UI: https://longhorn.lab.{{INGRESS_DOMAIN}}

**Common PVC sizes:**
- Databases: 5-10Gi
- Apps: 2-5Gi
- Prometheus/Loki: 10Gi

**Gotcha:** PostgreSQL needs `PGDATA` subdirectory:
```yaml
env:
  - name: PGDATA
    value: "/var/lib/postgresql/data/pgdata"
```

## Networking

### DNS
- **External:** Cloudflare ({{INGRESS_DOMAIN}})
- **Internal:** Pi-hole at 192.168.6.1
- **Wildcard:** `*.lab.{{INGRESS_DOMAIN}}` → NPM

### IP Ranges
| Range | Purpose |
|-------|---------|
| 192.168.5.x | Main LAN |
| 192.168.6.x | K8s/Server VLAN |
| 10.244.x.x | Pod network (Calico) |
| 10.96.x.x | Service network |

### Key IPs
| IP | Host |
|----|------|
| 192.168.5.38 | Proxmox VE |
| 192.168.5.95 | Red Mac (Data agent) |
| 192.168.6.4 | k8s-cp1 / Kind host |
| 192.168.6.5 | k8s-worker1 |
| 192.168.6.6 | k8s-worker2 |
| 192.168.6.10 | Gemini VM |
| 192.168.6.11 | Home Assistant |

## Secrets Management

**All secrets in GCloud Secret Manager:**
```bash
# List secrets
gcloud secrets list

# Get a secret
gcloud secrets versions access latest --secret=<name>

# Common secrets:
# - gitea-api-token
# - npm-credentials
# - langfuse-secret-key / langfuse-public-key
# - vikunja-api-token
# - home-assistant-api-token
# - proxmox-api-token
```

## Deploying New Services

### Standard Pattern
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-namespace
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    spec:
      containers:
        - name: my-app
          image: myimage:latest
          ports:
            - containerPort: 3000
---
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: my-namespace
spec:
  type: NodePort
  selector:
    app: my-app
  ports:
    - port: 3000
      nodePort: 32XXX  # Pick unused port 32000-32767
```

### Add to NPM
```bash
# Get token
NPM_TOKEN=$(curl -s -X POST "https://npm.lab.{{INGRESS_DOMAIN}}/api/tokens" \
  -H "Content-Type: application/json" \
  -d '{"identity":"USER","secret":"PASS"}' | jq -r '.token')

# Create proxy host
curl -X POST "https://npm.lab.{{INGRESS_DOMAIN}}/api/nginx/proxy-hosts" \
  -H "Authorization: Bearer $NPM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain_names": ["myapp.lab.{{INGRESS_DOMAIN}}"],
    "forward_scheme": "http",
    "forward_host": "192.168.6.6",
    "forward_port": 32XXX,
    "certificate_id": 1,
    "ssl_forced": true
  }'
```

## Troubleshooting

### Pod not starting
```bash
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace>
```

### Storage issues
```bash
# Check PVC status
kubectl get pvc -n <namespace>

# Check Longhorn volumes
kubectl get volumes.longhorn.io -n longhorn-system
```

### Network issues
```bash
# Test DNS
nslookup myapp.lab.{{INGRESS_DOMAIN}}

# Test from pod
kubectl run -it --rm debug --image=busybox -- wget -qO- http://service:port
```

### NPM issues
```bash
# Check NPM logs
kubectl logs -n proxy deployment/nginx-proxy-manager

# Verify certificate
curl -vI https://myapp.lab.{{INGRESS_DOMAIN}}
```

## Agent VMs

| VM ID | Name | IP | Agent | Model |
|-------|------|-----|-------|-------|
| 103 | clawdbot-gemini | 192.168.6.10 | Gem 💎 | Gemini 3 Pro |
| 104 | clawdbot-kimi | 192.168.6.104 | Kimi 🧠 | Kimi For Coding |
| 105 | clawdbot-codex | 192.168.6.105 | Codex 🤖 | GPT-4 Turbo |
| 106 | haos | 192.168.6.11 | - | Home Assistant |

## Argo Platform

### Argo Workflows + Events
| Component | Version | Namespace | Purpose |
|-----------|---------|-----------|---------|
| Argo Workflows | v3.6.4 | argo | Workflow execution engine |
| Argo Events | v1.9.10 | argo-events | Event-driven triggers |
| NATS EventBus | native, 3 replicas | argo-events | Event transport (token auth) |

**Key resources:**
```bash
# Workflows
kubectl get workflowtemplate -n argo
# kagent-sre-workflow, local-llm-analysis-only

# Events
kubectl get eventbus,eventsource,sensor -n argo-events
# EventBus: default (NATS)
# EventSources: alertmanager-eventsource (232 restarts — monitor)
# Sensors: prometheus-alert-sensor
```

**Argo UI:** `kubectl port-forward -n argo svc/argo-server 2746:2746` → https://localhost:2746

## Mission Control Instances

Three OpenClaw Mission Control instances deployed:
| Name | URL | VMID | IP |
|------|-----|------|----|
| Main | http://192.168.5.101:4000 | — | 192.168.5.101 (mini PC) |
| Stockbridge | http://192.168.6.131:4000 | VM 131 | 192.168.6.131 |
| Homelab | http://192.168.6.132:4000 | VM 132 | 192.168.6.132 |

## Agents Central Repo

**GitHub:** https://github.com/davidmarkgardiner/agents-central

Contains shared skills, deployment manifests, and agent configurations:
```
agents-central/
├── skills/                  # Agent skills (k8s-event-triage, k8s-troubleshooting, etc.)
├── localhost-stack/         # Full K8s event triage stack deployment
│   ├── deploy.sh            # One-command deploy
│   ├── manifests/           # Exported live manifests per namespace
│   └── DEPLOYMENT-STATUS.md # Current deployment state
├── prometheus-alerting/     # Alerting pipeline
└── ai-platform/config/      # KubeAI, LiteLLM, KAgent Helm values
```

## Related Skills

- `vidauto-project` - Video automation pipeline
- `multi-agent-workflow` - LCARS task tracking
- `claude-mem` - Persistent memory

## Quick Commands

```bash
# Switch context
kubectl config use-context {{CLUSTER_NAME}}

# Watch pods
kubectl get pods -A -w

# Port forward for debugging
kubectl port-forward svc/my-service 8080:80 -n namespace

# Restart deployment
kubectl rollout restart deployment/my-app -n namespace

# Scale
kubectl scale deployment/my-app --replicas=2 -n namespace
```

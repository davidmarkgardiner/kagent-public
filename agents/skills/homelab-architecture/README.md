# Homelab Architecture Skill

Complete infrastructure reference for David's homelab environment.

## What's Included

- **SKILL.md** - Full architecture documentation for AI agents
- **references/services.json** - Machine-readable service inventory
- **codex/** - Findings + backlog + ideas to improve/extend the lab (human-readable)

## Usage

This skill is designed for AI agents working in the homelab environment. Load it when:
- Deploying new services to Proxmox K8s
- Troubleshooting connectivity issues
- Understanding the infrastructure layout
- Looking up service URLs or ports

## Quick Links

| Service | URL |
|---------|-----|
| Dashboard | https://lab.{{INGRESS_DOMAIN}} |
| Grafana | https://{{INGRESS_DOMAIN}} |
| Gitea | https://gitea.lab.{{INGRESS_DOMAIN}} |
| Tasks | https://tasks.lab.{{INGRESS_DOMAIN}} |

## Clusters

- **{{CLUSTER_NAME}}** - Production (3 nodes, Longhorn storage)
- **{{CLUSTER_NAME}}** - Development (single node)

## Updated

2026-02-07 by Scotty 🔧

# AKS MCP — Deployment Manifests

Deployment manifests only. Upstream source code: https://github.com/Azure/aks-mcp

This directory contains the Helm chart for deploying the AKS MCP (Model Context Protocol) server, which provides `call_kubectl` and other AKS management tools to kagent agents.

## Quick Start

```bash
helm upgrade --install aks-mcp ./chart \
  --namespace aks-mcp --create-namespace \
  -f chart/values.yaml
```

## Notes

- The default chart posture is read-only and does not grant Secret reads unless
  `rbac.includeSecrets=true` is explicitly set for an approved specialist.
- Used by kagent agents via the `RemoteMCPServer` resource type
- When specifying `toolNames` in `RemoteMCPServer`, always list tools explicitly — `None` causes a ValidationError

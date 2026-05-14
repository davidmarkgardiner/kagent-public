# Official Upstreams

This repository is a public/sanitized working replica. It vendors patterns and manifests around several active upstream projects, but it is not itself an upstream fork. When behavior is unclear, verify against the official source before changing manifests or docs.

| Area | Official source | Local sibling clone |
|---|---|---|
| Azure Kubernetes Service issue/docs repo | https://github.com/Azure/AKS | `../AKS` |
| AKS-MCP | https://github.com/Azure/aks-mcp | `../aks-mcp` |
| Azure Service Operator | https://github.com/Azure/azure-service-operator | `../azure-service-operator` |
| KRO | https://github.com/kubernetes-sigs/kro | `../kro` |
| kagent | https://github.com/kagent-dev/kagent | `../kagent` |
| agentgateway | https://github.com/agentgateway/agentgateway | `../agentgateway` |

The local sibling clones are reference checkouts for agents working in this repo. They should not be edited as part of normal `kagent-public` tasks unless the task explicitly targets that upstream repository.

If a sibling clone is missing, create a shallow checkout:

```bash
git clone --depth 1 https://github.com/Azure/AKS.git ../AKS
git clone --depth 1 https://github.com/Azure/aks-mcp.git ../aks-mcp
git clone --depth 1 https://github.com/Azure/azure-service-operator.git ../azure-service-operator
git clone --depth 1 https://github.com/kubernetes-sigs/kro.git ../kro
git clone --depth 1 https://github.com/kagent-dev/kagent.git ../kagent
git clone --depth 1 https://github.com/agentgateway/agentgateway.git ../agentgateway
```

Notes:

- KRO is the Kube Resource Orchestrator project under Kubernetes SIGs. Older docs or local notes may mention `kro-run/kro`; prefer `kubernetes-sigs/kro`.
- agentgateway is now tracked at `agentgateway/agentgateway`. Do not confuse it with Envoy AI Gateway or kgateway unless the task specifically names those projects.
- AKS-MCP is separate from the broader Azure MCP server. This repo's AKS operational tool bridge is `Azure/aks-mcp`.


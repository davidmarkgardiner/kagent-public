# Mount all AKS MCP tools on one kagent Agent

[`agent-all-tools.yaml`](agent-all-tools.yaml) is a public-safe **lab/admin
example** of the complete wiring:

```text
Agent -> RemoteMCPServer/aks-mcp -> AKS MCP service
```

Apply it only after deploying AKS MCP and confirming its tool discovery:

```bash
kubectl apply --dry-run=server -f platform/aks-mcp/examples/agent-all-tools.yaml
kubectl apply -f platform/aks-mcp/examples/agent-all-tools.yaml
kubectl -n kagent get remotemcpserver aks-mcp -o yaml
kubectl -n kagent get agent aks-mcp-all-tools-lab-agent
```

The Agent mounts every tool expected from the AKS MCP chart's default component
catalog:

```text
call_az                     call_kubectl
helm                        cilium                       hubble
az_monitoring               az_fleet                     az_network_resources
get_aks_vmss_info           list_detectors               run_detector
run_detectors_by_category   az_advisor_recommendation    inspektor_gadget_observability
```

`toolNames` is intentionally explicit. In this kagent version, setting it to
`None` is invalid, and a requested name not discovered by the RemoteMCPServer
will prevent a correct binding. The live server's
`.status.discoveredTools` is therefore the source of truth; trim the list to
match that status if components are disabled.

## Access is two layers

Mounting a tool makes it available to the agent, but does not grant it
permission. The effective capability is the intersection of:

1. the Agent's explicit `toolNames` allowlist;
2. AKS MCP access level (`readonly`, `readwrite`, or `admin`);
3. its Kubernetes ServiceAccount RBAC and Azure identity roles; and
4. any Agent Gateway and network policies in front of the MCP endpoint.

The chart defaults to `readonly`; even this all-tool example should remain
read-only unless a separate, approval-gated remediation design is in place.

## Do not use this unchanged in production

Create purpose-specific agents instead. For example, a triage agent might
mount only `call_kubectl`, `az_monitoring`, `az_network_resources`, and
`hubble`. Keep `call_az`, `helm`, and `inspektor_gadget_observability` out of
an ordinary read-only incident agent unless their operational need is explicit.

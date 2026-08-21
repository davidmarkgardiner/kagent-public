# Cross-cluster AKS MCP validation: five tools

This runbook validates that one kagent Agent, running on a management cluster,
can reach a target AKS cluster through AKS MCP. It uses only read-only checks:

1. `call_az` — Azure identity/UAMI path
2. `call_kubectl` — target Kubernetes API path
3. `helm` — target Helm release discovery
4. `cilium` — target Cilium control-plane status
5. `hubble` — target Hubble observability status

Do not begin with a broad all-tools mount. This five-tool Agent is a bounded
connectivity proof. It neither creates resources nor deploys workloads.

## Preconditions

- AKS MCP runs on the management cluster using its own Kubernetes ServiceAccount.
- The management cluster's OIDC issuer has a federated credential for the UAMI
  subject `system:serviceaccount:aks-mcp:aks-mcp`.
- The UAMI has the required read permissions on the target AKS resource and is
  authorized by the target cluster's Azure Kubernetes RBAC/Kubernetes RBAC.
- AKS MCP has a target-cluster connection path. The packaged chart supports a
  mounted kubeconfig Secret; federation alone does **not** create a remote API
  connection or select its context.
- The target cluster runs Cilium and Hubble if checks 4 and 5 are expected to
  pass. Otherwise those two checks should return an explicit unavailable result.

No credentials, subscription IDs, cluster names, or kubeconfig contents belong
in this repository.

## 1. Mount the five tools

Apply this only after replacing placeholders in your private environment:

```yaml
apiVersion: kagent.dev/v1alpha2
kind: RemoteMCPServer
metadata:
  name: aks-mcp-cross-cluster
  namespace: kagent
spec:
  description: Read-only AKS MCP endpoint for cross-cluster connectivity checks.
  protocol: STREAMABLE_HTTP
  url: http://aks-mcp.aks-mcp.svc.cluster.local:8000/mcp
  timeout: 120s
  sseReadTimeout: 10m0s
---
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: aks-cross-cluster-five-tool-validator
  namespace: kagent
spec:
  type: Declarative
  description: Read-only AKS MCP validator for one target cluster.
  declarative:
    runtime: go
    modelConfig: {{APPROVED_MODEL_CONFIG}}
    systemMessage: |
      Validate cross-cluster read connectivity only. Run the five requested
      AKS MCP checks against {{TARGET_KUBECONFIG_CONTEXT}}. Do not create,
      apply, delete, patch, upgrade, install, or modify anything. Return a
      PASS/BLOCKED result per tool with the target context and concise evidence.
    tools:
      - type: McpServer
        mcpServer:
          apiGroup: kagent.dev
          kind: RemoteMCPServer
          name: aks-mcp-cross-cluster
          namespace: kagent
          toolNames:
            - call_az
            - call_kubectl
            - helm
            - cilium
            - hubble
```

The exact advertised schema is authoritative. Before creating the Agent,
confirm that all five names appear under:

```bash
kubectl -n kagent get remotemcpserver aks-mcp-cross-cluster -o yaml
```

## 2. Safe validation calls

The Agent should make one call at a time and report each result. The following
are read-only candidate commands; use the discovered tool schema for the exact
argument property names in the installed AKS MCP version.

| Tool | Read-only candidate | What a PASS proves |
| --- | --- | --- |
| `call_az` | `az account show --output json` | The AKS MCP workload can obtain an Azure token as the intended UAMI. |
| `call_kubectl` | `--context {{TARGET_KUBECONFIG_CONTEXT}} get --raw=/readyz` | AKS MCP can reach and authenticate to the target Kubernetes API. |
| `helm` | `--kube-context {{TARGET_KUBECONFIG_CONTEXT}} list --all-namespaces` | Helm can use the target context with read access. |
| `cilium` | `--context {{TARGET_KUBECONFIG_CONTEXT}} status` | Cilium CLI can reach the target and Cilium is available. |
| `hubble` | `--context {{TARGET_KUBECONFIG_CONTEXT}} status` | Hubble can reach the target observability endpoint. |

`call_az` validates Azure identity, not remote Kubernetes connectivity. The
other four validate the selected target cluster context. A Cilium or Hubble
failure is diagnostic evidence; do not work around it by broadening RBAC or
installing components during this read-only test.

## 3. Invoke the Agent

Use the repository helper so the correct kagent A2A envelope and trailing slash
are used:

```bash
scripts/kagent-a2a-invoke.sh \
  --context {{MANAGEMENT_KUBECTL_CONTEXT}} \
  --agent aks-cross-cluster-five-tool-validator \
  --timeout 180 \
  --text 'Validate {{TARGET_KUBECONFIG_CONTEXT}}. Use call_az, call_kubectl, helm, cilium, and hubble exactly once each with read-only checks. Return one PASS or BLOCKED line per tool, including the target context and concise evidence. Do not mutate anything.'
```

## 4. Evidence contract

Call the proof passed only when all of the following are retained with the
request or Kanban card:

- `RemoteMCPServer` status is `Accepted=True` and lists all five tools.
- Agent status is `Accepted=True`, `Ready=True`.
- A2A response reports a result for all five tools.
- AKS MCP logs show five tool invocations with no secret material.
- Each result identifies the intended target context; `call_az` identifies the
  expected Azure subscription/tenant only through approved redacted evidence.
- No mutation occurred: no `apply`, `create`, `delete`, `patch`, Helm upgrade,
  Cilium change, or Hubble deployment.

## Failure classification

| Symptom | Likely boundary | Safe next action |
| --- | --- | --- |
| `call_az` unauthorised | UAMI Azure role/federation | Verify UAMI federation subject and least-privilege Azure role assignment. |
| `call_kubectl` unauthorised | Target Kubernetes RBAC | Verify the identity recognized by the target API, then add a minimal read binding. |
| API timeout | Network or remote kubeconfig path | Verify private DNS, routing, API reachability, and selected kubeconfig context. |
| `cilium`/`hubble` unavailable | CNI/observability prerequisite | Record blocked; verify target Cilium/Hubble installation separately. |
| Tool absent from discovery | AKS MCP component configuration | Enable only the required component and re-check discovery before mounting it. |

This produces a focused cross-cluster connectivity proof before any remediation
agent receives write-capable tools.

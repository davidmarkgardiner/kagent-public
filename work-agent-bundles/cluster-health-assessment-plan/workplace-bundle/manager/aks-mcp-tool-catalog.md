# AKS-MCP tool catalog for this bundle

This catalog is only for mechanical Agent-CR validation. Runtime discovery of
the selected `RemoteMCPServer` remains mandatory.

## Read-Only Tools (safe for triage agents)

| Tool Name | Description |
|-----------|-------------|
| `call_kubectl` | Kubectl diagnostic operations constrained by target Kubernetes read-only authorization |

`call_az` is deliberately excluded. The MCP Azure identity must not be able to
retrieve cluster user/admin credentials because doing so would bypass the
namespace-scoped Kubernetes identity and RoleBindings.

## Write Tools (remediation agents only)

| Tool Name | Description | Risk |
|-----------|-------------|------|
| `none` | This bundle exposes no write tool | High |

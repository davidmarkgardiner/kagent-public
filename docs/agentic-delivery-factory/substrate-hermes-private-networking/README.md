# Agent Substrate, Hermes, and Private Networking

**Purpose:** Describe a private, stateful runtime option for a Hermes-style Kubernetes delivery agent. This is a design guide, not an installation runbook.

## What is supported upstream

| Statement | Classification |
| --- | --- |
| kagent documents `AgentHarness` as a Kubernetes custom resource that provisions a long-running execution environment for a Hermes or OpenClaw coding agent. | **Verified current capability** — [Agent Harness](https://kagent.dev/docs/kagent/concepts/agent-harness) |
| AgentHarness uses Agent Substrate. The runtime uses workers/actors and snapshots idle state to object storage for restoration. | **Verified current capability** — [Agent Substrate](https://kagent.dev/docs/kagent/concepts/agent-substrate) |
| kagent exposes A2A through the controller service; exposing it outside the cluster is optional and normally requires a gateway. | **Verified current capability** — [A2A agents](https://kagent.dev/docs/kagent/examples/a2a-agents) |
| Agent Gateway can sit between kagent agents and model providers to provide policy, access control, rate limiting, audit logs, and observability. | **Verified current capability** — [Agent Gateway integration](https://kagent.dev/docs/kagent/examples/agentgateway) |
| The currently selected AKS environment has the required Substrate control plane, worker pool, snapshot store, Hermes-compatible image, or private model/MCP connectivity. | **Unknown / requires validation** |

## Proposed private topology

```text
Approved user or delivery coordinator
  -> private ingress / private gateway
  -> kagent controller and UI
  -> Hermes AgentHarness on Agent Substrate
  -> Agent Gateway policy boundary
  -> approved private or allow-listed model and MCP services

Snapshots: Agent Substrate <-> approved object storage
```

| Boundary | Required design rule | Classification |
| --- | --- | --- |
| User ingress | Keep the UI/API/A2A service cluster-internal unless a named private ingress route is approved. Authenticate the user before forwarding. | **Proposed design** |
| Agent to model | Route via Agent Gateway where policy, audit, rate, and provider controls are required. Do not give every agent a provider credential. | **Proposed design** |
| Agent to MCP | Allow only named, read-only MCP services by default. Add a write-capable tool only with `requireApproval`, least-privilege RBAC, and a scoped target. | **Proposed design** |
| Snapshot storage | Treat actor snapshots as sensitive workload state. Use an approved private storage path, restricted identity, encryption, retention, and deletion policy. | **Proposed design** |
| Egress | Default-deny egress, then explicitly allow only the required private DNS names or approved provider endpoints. | **Proposed design** |
| Network controls | Use the platform's approved private AKS, private DNS, NetworkPolicy/service-mesh, and private-endpoint patterns. kagent is not an Azure Private Endpoint provisioner. | **Proposed design** |

## Important distinction: stateful does not mean autonomous

An AgentHarness can preserve an agent workspace/session across idle periods, but it should not receive broad cluster-admin access or permission to self-approve changes.

| Capability | Safe default | Classification |
| --- | --- | --- |
| Read cluster evidence | Namespace-scoped read-only service account and read-only MCP tools | **Proposed design** |
| Generate a change | Produce a diff, rendered manifest, and test plan in an isolated worktree | **Proposed design** |
| Apply, patch, delete, Helm upgrade, or external publish | Stop at an approval gate; bind any approval to one exact action and target | **Proposed design** |
| Resume after idle | Restore only from the approved runtime/snapshot path; recheck identity and approval expiry before a state-changing tool runs | **Proposed design** |

## Minimum proof before using it for delivery work

**Proposed design:** Run a non-production proof in a namespace supplied by the platform owner. It passes only when evidence shows all of the following:

1. The installed kagent and Substrate versions are compatible, required CRDs reconcile, and a Hermes AgentHarness reports its documented readiness conditions.
2. The actor can process a benign request, become idle, and resume while retaining the expected non-sensitive session/workspace state.
3. A2A/UI access is reachable only through the approved private route.
4. Agent-to-model and agent-to-MCP traffic follows the intended policy path.
5. A deliberately gated write-capable test action stops for human approval; denial, expiry, and duplicate callbacks do not execute it.
6. Snapshot retention and cleanup evidence is retained without exposing workload data.

## Do not assume

- **Unknown / requires validation:** A generic kagent upgrade enables Substrate. Agent Substrate is a separate runtime integration with its own control plane, worker, and snapshot dependencies.
- **Unknown / requires validation:** A locally documented AgentHarness schema matches the installed CRD. Inspect the installed version before writing manifests.
- **Unknown / requires validation:** A private endpoint exists merely because cluster services use private DNS. Verify DNS, network flow, identity, and policy from the actual workload.

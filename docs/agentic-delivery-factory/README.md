# Agentic Delivery Factory — Runtime and Approval Guides

These planning guides accompany the [Hermes/Kanban Kubernetes workflow contract](HERMES-KANBAN-KUBERNETES-WORKFLOW-CONTRACT.md). They explain the runtime choices that affect a stateful, approval-gated Kubernetes delivery factory. They do not deploy or authorize anything.

| Guide | Question answered | Status |
| --- | --- | --- |
| [Substrate, Hermes, and private networking](substrate-hermes-private-networking/README.md) | Can a stateful Hermes agent run privately on Agent Substrate? | Architecture guide; environment proof required. |
| [Teams approval and session resume](teams-approval-session-resume/README.md) | Can an Approve/Deny card safely resume the correct agent session? | Proposed integration; native kagent UI approval is verified. |
| [LangGraph versus kagent](langgraph-vs-kagent/README.md) | Which layer should own durable delivery workflow state and Kubernetes agent operations? | Decision guide. |

## Evidence rule

**Verified current capability** means the linked upstream or checked-in material documents the capability. It does not prove that a particular cluster, model route, Teams application, or Agent Substrate installation is available.

**Proposed design** means an implementation recommendation. It needs owner approval, version-specific validation, and an evidence-producing proof of concept before production use.

**Unknown / requires validation** must remain a block, rather than being filled in with guessed credentials, endpoints, namespaces, or runtime results.

## Related checked-in material

- [Teams/Argo workflow approval gate](../../platform/teams-hitl/README.md) — existing workflow-level Teams callback design.
- [AgentHarness Hermes next steps](../platform-kb/agents/agentharness-hermes-next-steps.md) — a historical lab handoff; revalidate its version-specific statements before use.
- [Agent Substrate AKS bundle](../../work-agent-bundles/agent-substrate/README.md) — AKS evaluation material and read-only verifier.

# LangGraph versus kagent for the Kubernetes Delivery Factory

**Purpose:** Choose the right control plane for durable workflow state, agent execution, and Kubernetes operations. They are complementary, not direct replacements.

## Short answer

**Proposed design:** Use a durable workflow coordinator such as LangGraph or the existing Hermes/Kanban plus Argo model to own the delivery DAG, evidence gates, and Teams decisions. Use kagent, Agent Gateway, MCP/A2A, and optionally Agent Substrate to run and govern Kubernetes-aware agents.

## Comparison

| Concern | LangGraph | kagent | Implication for this factory |
| --- | --- | --- | --- |
| Core abstraction | Low-level graph/runtime for long-running, stateful application workflows | Kubernetes-native agent control plane built around CRDs, tools, A2A/MCP, and Kubernetes deployment | **Verified current capability** — do not expect one to replace the other automatically. |
| Durable pause/resume | `interrupt()` persists graph state and resumes by a chosen thread ID | Tool approval pauses a gated tool; Substrate can snapshot/restore sandbox actors and AgentHarness environments | **Verified current capability** — select based on whether the durable unit is a workflow graph or an agent runtime. |
| Human approval | Can interrupt at any graph node with an arbitrary JSON payload and external callback | Built-in `requireApproval` and `ask_user` for agent tools | **Verified current capability** — LangGraph offers finer workflow control; kagent offers simpler tool-level governance. |
| Kubernetes and AI controls | Must be integrated by the application team | Native agent/tool configuration, Agent Gateway patterns, MCP/A2A, and Kubernetes focus | **Verified current capability** — kagent reduces platform plumbing. |
| Stateful coding environment | Build it from application/runtime components | AgentHarness provides a managed Hermes/OpenClaw environment on Agent Substrate | **Verified current capability** — version and runtime availability still need local proof. |
| Observability/evaluation | LangGraph ecosystem integrates with LangSmith, or use your own tracing/evaluation stack | kagent/Agent Gateway and the surrounding Kubernetes observability stack provide platform-facing signals | **Proposed design** — retain the factory evidence contract independently of either product's telemetry. |

Sources: [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview), [LangGraph interrupts](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/breakpoints/), [kagent agents](https://kagent.dev/docs/kagent/concepts/agents), [kagent Agent Substrate](https://kagent.dev/docs/kagent/concepts/agent-substrate).

## Pros and constraints

| Option | Advantages | Constraints |
| --- | --- | --- |
| LangGraph-led | Explicit state machine; arbitrary branches, compensation, retries, and approval checkpoints; durable thread state is a first-class concern | You must build the Kubernetes identity, RBAC, private ingress, MCP/tool policy, deployment lifecycle, and evidence integrations carefully. |
| kagent-led | Kubernetes CRDs and agent tooling; A2A/MCP; Agent Gateway governance; tool approvals; Substrate/Hermes option | Less suited to being the sole general-purpose business-process engine; exact runtime/schema behaviour is version-dependent and must be verified. |
| Hybrid | Clear separation: workflow layer owns intent/approval/evidence; kagent layer owns agent/tool execution and policy | Requires explicit correlation IDs and a contract so two systems do not both retry, approve, or claim success. |

## Recommended division of responsibility

```text
Hermes/Kanban, Argo, or LangGraph
  - request intake and worktree lock
  - delivery DAG, retries, timeout, compensation
  - Teams approval record and evidence contract
  - PR-ready handoff

kagent, Agent Gateway, MCP/A2A, and optional Agent Substrate
  - execute scoped agent work
  - discover/read Kubernetes evidence
  - gate sensitive tools with requireApproval
  - route models and tools through policy controls
  - host stateful Hermes harnesses when required
```

## Integration rules

| Rule | Classification |
| --- | --- |
| Assign one durable-workflow owner per delivery. Do not let both LangGraph and Argo retry or compensate the same deployment action. | **Proposed design** |
| Carry the delivery ID, approval ID, artifact hash, target context/namespace, and attempt number across every LangGraph/Hermes/Argo/kagent handoff. | **Proposed design** |
| Treat a kagent tool approval and a workflow approval as separate gates unless an explicit, version-tested bridge correlates them. | **Proposed design** |
| Keep Kubernetes mutations behind a restricted workflow service account or another separately approved executor; read-only agents should not receive apply/delete privileges. | **Proposed design** |
| Prove a minimal end-to-end path before adding multi-agent, cross-system retries or production targets. | **Proposed design** |

## Decision heuristic

Choose **LangGraph-led orchestration** when the difficult part is a bespoke long-running business/delivery process with many conditional paths and externally supplied approvals.

Choose **kagent-led execution** when the difficult part is safely operating Kubernetes-aware agents with controlled MCP/A2A tools, model routing, and Kubernetes-native configuration.

Choose the **hybrid** for the proposed factory: it preserves the evidence-first Kanban workflow while avoiding a bespoke rebuild of the Kubernetes agent platform.

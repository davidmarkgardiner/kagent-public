# Platform Memory Architecture for kagent on AKS

This guide describes how to give kagent agents durable, useful memory across
workflow suspends, A2A handoffs, and separate chat sessions.

The target audience is a platform team running kagent, Argo Workflows, Flux,
agentgateway, AKS-MCP, and shared MCP tools on AKS. The design assumes public
repository examples only. Replace environment-specific values with
`{{PLACEHOLDER}}` values.

## Goal

Agents should be able to answer these questions before they investigate from
scratch:

- Have we seen this issue before?
- Was it a real incident, a known false positive, or an already-triaged
  recurring condition?
- What evidence was used last time?
- What action was approved, rejected, or deferred?
- Which workflow, PR, issue, or human approval recorded the decision?

Memory should improve triage quality without becoming an uncontrolled source of
truth. Procedures stay in Git. Platform documentation stays in Git-backed RAG.
Shared operational lessons live in an explicit, auditable memory service.
Native kagent memory is used only for agent-local recall.

## Memory Types

| Type | What it stores | Recommended implementation | Lifetime |
|---|---|---|---|
| Working memory | Active workflow parameters, approval IDs, current evidence, active A2A `contextId` | Argo Workflow parameters/artifacts, status ConfigMaps, A2A `contextId` | One workflow run |
| Thread memory | Conversation history for one chat or A2A thread | kagent session storage keyed by A2A `contextId` | One conversation thread |
| Native long-term memory | Per-agent/per-user facts and preferences | `spec.declarative.memory` with durable Postgres + pgvector and embedding `ModelConfig` | TTL-based |
| Shared episodic memory | Incidents, false positives, recurring issue records, remediation outcomes | `memory-mcp` or successor shared MCP service backed by a durable database | Months or years, policy driven |
| Semantic memory | Concepts, service ownership, architecture facts, known issue classes | Shared memory for operational concepts; Git-backed RAG for documentation | Policy driven |
| Procedural memory | Skills, playbooks, runbooks, WorkflowTemplates, remediation steps | Git, Flux, Argo WorkflowTemplates, kagent skills, querydoc/RAG | Versioned in Git |

## Recommended Architecture

```text
Alert / request / chat
  -> Argo Workflow or kagent A2A session
  -> Agent preflight:
       1. restore workflow state
       2. continue A2A context when available
       3. search shared memory for incident fingerprints
       4. query docs/runbooks through querydoc/RAG when procedure is needed
  -> Agent investigates current state with read-only tools
  -> Agent writes a structured observation proposal
  -> Memory curator workflow validates, deduplicates, and writes shared memory
  -> If remediation is needed, agent submits workflow or PR; human approves
```

Use four stores, each with a narrow responsibility:

| Store | Role | Notes |
|---|---|---|
| kagent controller database | Sessions and native memory | Production should use external PostgreSQL with vector support. |
| Shared memory MCP database | Cross-agent operational lessons | Should support structured fields, semantic search, audit, and write serialization. |
| Git | Procedures and durable platform contracts | Skills, runbooks, WorkflowTemplates, policy, and agent prompts are reviewed here. |
| RAG index | Search over Git-backed docs | Use querydoc for repo-local POC or Azure AI Search for enterprise retrieval. |

## Microsoft-Aligned AKS Deployment

For a Microsoft estate, prefer managed Azure control points:

| Capability | Recommended Azure shape | Reason |
|---|---|---|
| Durable kagent database | Azure Database for PostgreSQL Flexible Server with `vector` extension | Native kagent memory expects vector-capable Postgres for production. |
| Shared memory database | Azure Database for PostgreSQL Flexible Server | Keeps structured metadata, audit tables, and vector indexes close to kagent. |
| Documentation RAG | Azure AI Search or querydoc, depending on scope | Azure AI Search gives hybrid search, RBAC, and document-level access patterns for enterprise content. |
| Identity | Microsoft Entra Workload ID for AKS | Avoids static Azure credentials in agent pods and MCP servers. |
| Secrets | Azure Key Vault plus External Secrets or CSI driver | Keeps database URLs and provider keys out of Git. |
| Network access | Private endpoints plus AKS NetworkPolicy | Memory and RAG stores should not be public by default. |
| Delivery | Flux and Argo Workflows | Permanent changes are reconciled from Git; agents submit workflows or PRs. |

Relevant Microsoft references:

- [Use Microsoft Entra Workload ID with AKS](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)
- [Enable and use pgvector in Azure Database for PostgreSQL Flexible Server](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/how-to-use-pgvector)
- [Hybrid search in Azure AI Search](https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview)
- [Document-level access control in Azure AI Search](https://learn.microsoft.com/en-us/azure/search/search-document-level-access-overview)

## kagent Native Memory

Native memory is useful, but it is not the shared platform memory plane.

Use it for:

- User preferences.
- Agent-local remembered facts.
- Short-form recall that should be isolated by agent and user.

Do not use it for:

- Cross-agent incident history.
- Compliance-grade audit.
- Canonical documentation.
- Runbooks or remediation procedures.

Enablement shape:

```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: {{AGENT_NAME}}
  namespace: kagent
spec:
  type: Declarative
  declarative:
    modelConfig: {{CHAT_MODEL_CONFIG}}
    memory:
      modelConfig: {{EMBEDDING_MODEL_CONFIG}}
      ttlDays: 30
    systemMessage: |
      You may use native memory for user preferences and agent-local facts.
      Do not treat native memory as authoritative platform documentation.
```

Controller/database requirements:

- Use durable PostgreSQL for production, not in-memory SQLite.
- Set the kagent chart values so vector support is enabled.
- Confirm the PostgreSQL `vector` extension exists.
- Use a stable embedding model; changing embedding providers mid-life can make
  old memories hard to retrieve.

Validation:

```bash
kubectl get cm -n kagent kagent-controller \
  -o jsonpath='{.data.DATABASE_VECTOR_ENABLED}'

kubectl exec -n kagent {{POSTGRES_POD}} -- \
  psql -U {{DB_USER}} -d {{DB_NAME}} \
  -c "SELECT extname FROM pg_extension WHERE extname='vector';"
```

## Shared Episodic Memory

The shared memory service is where agents learn from prior incidents and
handoffs.

Use `memory-mcp` or a successor MCP server with a durable backend. The current
repo pattern already exposes tools such as `search_nodes`, `open_nodes`,
`read_graph`, `add_observations`, `create_entities`, and `create_relations`.
For production, harden that service before high-concurrency use:

- Store data in PostgreSQL, not a read-modify-write file.
- Add a write queue or database transaction boundary.
- Record every write with actor, source workflow, source session, timestamp,
  evidence links, and confidence.
- Separate read-only, observe+read, and full read/write agent tiers.
- Prefer curator-mediated writes for incident memories.

### Suggested Entity Types

| Entity | Name pattern | Purpose |
|---|---|---|
| Incident | `incident/{{DATE}}-{{SLUG}}` | A real event or alert investigation. |
| Issue fingerprint | `fingerprint/{{SYSTEM}}/{{HASH_OR_SLUG}}` | Stable recurring symptom signature. |
| Lesson | `lesson/{{DOMAIN}}/{{SLUG}}` | Reusable operational learning. |
| Decision | `decision/{{DATE}}-{{SLUG}}` | Human or platform decision with rationale. |
| Workflow run | `workflow/{{NAMESPACE}}/{{WORKFLOW_NAME}}` | Links memory to Argo execution. |
| Remediation | `remediation/{{DOMAIN}}/{{SLUG}}` | What was done, proposed, or rejected. |

### Minimum Memory Record

Every shared memory write should have enough structure for agents to decide
whether it applies:

```yaml
kind: IncidentMemory
apiVersion: platform.kagent.dev/v1alpha1
metadata:
  name: incident/{{DATE}}-{{SLUG}}
spec:
  status: active | mitigated | known-benign | superseded | needs-human
  severity: info | warning | high | critical
  domain: {{DOMAIN}}
  cluster: "{{CLUSTER_NAME}}"
  namespace: "{{NAMESPACE}}"
  fingerprint:
    reason: "{{K8S_EVENT_REASON}}"
    involvedKind: "{{KIND}}"
    involvedName: "{{RESOURCE_NAME}}"
    normalizedMessage: "{{NORMALIZED_MESSAGE}}"
  summary: "{{WHAT_HAPPENED}}"
  rootCause: "{{ROOT_CAUSE_OR_UNKNOWN}}"
  lastKnownAction: "{{ACTION_OR_NONE}}"
  outcome: "{{OUTCOME}}"
  evidence:
    - type: argo-workflow
      ref: "{{WORKFLOW_NAME}}"
    - type: a2a-context
      ref: "{{CONTEXT_ID}}"
    - type: pr
      ref: "{{PR_OR_MR_URL}}"
  confidence: low | medium | high
  expiresAt: "{{RFC3339_TIMESTAMP_OR_EMPTY}}"
```

Do not store raw secrets, private hostnames, subscription IDs, tenant IDs,
tokens, or private cluster IPs.

## Agent Prompt Convention

Every triage-capable agent should follow the same memory contract.

```text
At the start of every investigation:
1. Build a compact search query from namespace, component, event reason,
   resource kind, error code, and normalized message.
2. Search shared memory before using write-capable tools.
3. Treat memory as hints, not truth. Verify against current cluster state.
4. If a memory says known-benign or do-not-remediate, explain the condition and
   only escalate if current evidence differs.

At the end of every investigation:
1. Return current evidence and verdict.
2. Propose a memory update with fingerprint, root cause, outcome, and links.
3. Do not delete or overwrite shared memory directly.
```

Specialist agents should usually get read-only or observe+read access. Coordinator
or curator agents may get full write access.

## Workflow Suspend and Resume

For human-in-the-loop Argo workflows, persist the active handoff explicitly:

| Field | Where to persist | Why |
|---|---|---|
| `workflow.uid` | Workflow labels/annotations and memory evidence | Stable run identity. |
| `workflow.name` | Status ConfigMap and memory evidence | Human-readable lookup. |
| `a2a.contextId` | Workflow parameter or artifact | Allows the resumed call to continue the same thread. |
| `approval.id` | Workflow parameter/artifact | Ties human decision to resumed execution. |
| `memory.searchResults` | Workflow artifact | Makes pre-approval context inspectable. |
| `memory.proposal` | Workflow artifact | Curator can approve/write after completion. |

Resume flow:

```text
Workflow starts
  -> agent searches shared memory
  -> workflow records contextId and memory matches
  -> workflow suspends for human approval
  -> human approves/rejects
  -> workflow resumes with same contextId
  -> agent verifies current state again
  -> workflow emits memory proposal
  -> curator writes accepted memory
```

## Write Governance

Use these tiers:

| Tier | Who gets it | Allowed tools |
|---|---|---|
| Read-only | General agents, chat front doors | `search_nodes`, `open_nodes`, `read_graph` |
| Observe+read | Specialist triage agents | Read tools plus `add_observations` to existing entities |
| Curator write | Coordinator or memory-curator workflow | `create_entities`, `create_relations`, `add_observations` |
| Admin | Platform operators only | Delete and repair tools |

The write path should reject:

- Memories without evidence.
- Memories with raw secrets or internal identifiers.
- Memories that make unverified current-state claims.
- Duplicate memories that should update an existing fingerprint.
- Remediation claims that bypass GitOps or human approval.

## Rollout Plan

### Phase 0 - Inventory

- List current kagent Agents and their tool tiers.
- Confirm whether the controller uses durable PostgreSQL or local SQLite.
- Confirm whether an embedding-capable `ModelConfig` exists.
- Confirm `memory-mcp` deployment, discovered tools, and storage backend.

### Phase 1 - Durable Native Memory

- Move kagent controller storage to external PostgreSQL.
- Enable vector support and verify the `vector` extension.
- Add one embedding `ModelConfig`.
- Enable `spec.declarative.memory` on one low-risk test agent.
- Prove cross-session recall after controller restart.

### Phase 2 - Shared Memory Hardening

- Replace file-style shared memory storage with PostgreSQL-backed storage.
- Add write serialization or transactional writes.
- Add structured incident/lesson schema.
- Add audit records for every write.
- Add sanitizer checks before write.

### Phase 3 - Triage Integration

- Update specialist agent prompts to search memory first.
- Add memory search results to Argo workflow artifacts.
- Add memory proposals to workflow outputs.
- Add a memory-curator workflow to accept/reject/deduplicate writes.

### Phase 4 - Evaluation

- Replay known incidents.
- Verify the agent retrieves the right prior memory.
- Verify the agent ignores stale or nonmatching memory.
- Verify known-benign cases do not trigger unnecessary remediation.
- Verify every cited memory links to evidence.

## Validation Checklist

Native kagent memory:

- [ ] Controller uses durable PostgreSQL.
- [ ] `DATABASE_VECTOR_ENABLED=true`.
- [ ] PostgreSQL has `vector` extension.
- [ ] Agent has `spec.declarative.memory.modelConfig`.
- [ ] Embedding route works.
- [ ] Fresh A2A context can recall a saved preference.
- [ ] Recall survives controller restart.

Shared memory:

- [ ] `RemoteMCPServer/memory-mcp` is accepted.
- [ ] Agents only receive the intended memory tools.
- [ ] Concurrent writes do not lose data.
- [ ] Writes are auditable by actor, workflow, and timestamp.
- [ ] Search finds a seeded incident fingerprint.
- [ ] Known-benign memory changes agent behavior only after current-state
      verification.
- [ ] Memory proposals are sanitized before write.

Workflow handoff:

- [ ] Suspended workflow stores A2A `contextId`.
- [ ] Resume uses the same `contextId` when continuity is required.
- [ ] Approval decision is linked to workflow and memory evidence.
- [ ] Final workflow emits a memory proposal artifact.

## Related Repo Docs

- [Native kagent memory findings](../README.md)
- [mcp-memory-server integration](../../memory-integration.md)
- [A2A memory reference](../../../a2a/memory-reference.md)
- [A2A + HITL + skills demo](../../../a2a/kagent-hitl-skills-demo/README.md)
- [Memory-assisted remediation design](../../../agents/kagent-triage/worker-cluster-bundle/MEMORY-AND-A2A-REMEDIATION-DESIGN.md)

# Work Memory and Knowledge Base Next Handoff

Purpose: give this file to the work-side agent tomorrow and ask it to replicate
the home-lab memory and knowledge-base features in an approved non-production
work environment, with live evidence.

Do not paste secrets into this file or into Git. Replace every
`{{PLACEHOLDER}}` with a work-approved value at runtime.

## One-Line Ask For The Work Agent

Take this zip, implement the memory and knowledge-base patterns in an approved
non-production work cluster, then return evidence that proves doc retrieval,
memory recall, HITL gating, and safety controls work end to end.

## TLDR

What exists already from the home environment:

- Shared memory POC: `memory-mcp` seeded a synthetic incident, another agent
  recalled it, the A2A context survived HITL suspend/resume, and proof markers
  were captured.
- Knowledge-base POC: Git-backed Markdown docs can be indexed and queried with
  citations. The repo includes both a simple BM25 UI POC and the preferred
  kagent-native `doc2vec` + `querydoc` MCP package.
- Smart-triage integration: the fan-out flow already has a knowledge specialist
  contract and a HITL-gated GitLab knowledge-base update path.

What still needs to be proved at work:

- Durable native kagent memory backed by PostgreSQL + pgvector.
- Hardened shared memory service, preferably database-backed, with serialized
  writes, audit fields, retention, and curator-mediated writes.
- doc2vec/querydoc deployed against the work Markdown knowledge base.
- A live knowledge specialist answer with source-path citations.
- A negative case where the agent returns `NO_RELEVANT_DOCS` instead of
  inventing an answer.
- A HITL-gated stale-doc update path that opens a sandbox GitLab MR only after
  approval.

## Important Boundary

Do not merge these concepts:

| Capability | Correct store | Notes |
|---|---|---|
| Platform docs, runbooks, service guides | Git-backed Markdown plus doc2vec/querydoc | Must return citations. |
| Native per-agent/user memory | kagent controller database with PostgreSQL + pgvector | For preferences and short remembered facts. |
| Shared incident lessons | `memory-mcp` or successor shared MCP service | Needs audit, retention, and serialized writes. |
| Procedures and remediation steps | Git, Flux, Argo WorkflowTemplates, kagent skills | Do not store canonical procedures only in memory. |

The querydoc POC uses a generated SQLite vector DB file named
`platform-kb.db`. PostgreSQL is still needed for durable kagent memory and for a
hardened shared incident memory backend.

## Read Order

Start here:

1. `WORK-ZIP-AGENT-HANDOFF.md`
2. `A2A-DEMO-EXECUTION-REVIEW.md`
3. `A2A-WORK-IMPLEMENTATION-PLAN.md`
4. `docs/kagent-memory/platform-memory/README.md`
5. `docs/kagent-memory/README.md`
6. `docs/memory-integration.md`
7. `ai-platform/kagent-knowledge-base/README.md`
8. `ai-platform/kagent-knowledge-base/EMBEDDING-OPTIONS.md`
9. `docs/platform-kb/platform/kagent-docs-rag.md`
10. `docs/smart-triage-integration-spikes/spike-8-knowledge-runbook-retrieval.md`
11. `SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md`
12. `WORK-TRIAGE-REMEDIATION-VERIFICATION-README.md`

Implementation paths:

```text
a2a/platform-memory-showcase-demo/
platform/mcp-memory-server/
agents/memory-wired/
ai-platform/kagent-knowledge-base/
docs/platform-kb/
a2a/smart-triage-fanout-demo/
```

## Work Values Required

Ask the work owner for these before applying anything:

| Area | Placeholder | Required value |
|---|---|---|
| Kubernetes | `{{KUBE_CONTEXT}}` | Approved non-production cluster context |
| Kubernetes | `{{KAGENT_NAMESPACE}}` | Usually `kagent` |
| Kubernetes | `{{ARGO_NAMESPACE}}` | Usually `argo` |
| Kubernetes | `{{STORAGE_CLASS}}` | RWO class for querydoc and memory POC PVCs |
| kagent | `{{CHAT_MODEL_CONFIG}}` | Known-good chat ModelConfig |
| kagent memory | `{{EMBEDDING_MODEL_CONFIG}}` | Embedding-capable ModelConfig |
| kagent memory | `{{POSTGRES_HOST}}` | Durable PostgreSQL host or service |
| kagent memory | `{{POSTGRES_DB}}` | Database name |
| kagent memory | `{{POSTGRES_USER_SECRET}}` | Secret containing DB username |
| kagent memory | `{{POSTGRES_PASSWORD_SECRET}}` | Secret containing DB password |
| kagent memory | `{{PGVECTOR_ENABLED}}` | Confirmed `vector` extension installed |
| shared memory | `{{MEMORY_MCP_NAME}}` | Usually `memory-mcp` |
| shared memory | `{{MEMORY_BACKEND}}` | Current POC or PostgreSQL-backed successor |
| knowledge | `{{KB_REPO_URL}}` | Git repo containing approved Markdown docs |
| knowledge | `{{KB_REPO_REF}}` | Branch or tag to index |
| knowledge | `{{KB_SOURCE_PATH}}` | Markdown path, for example `docs/platform-kb` |
| knowledge | `{{EMBEDDING_PROVIDER}}` | `openai` or `azure` for the first proof |
| knowledge | `{{OPENAI_MODEL}}` | For example `text-embedding-3-large` |
| knowledge | `{{AZURE_OPENAI_ENDPOINT}}` | Required only for Azure OpenAI embeddings |
| knowledge | `{{AZURE_OPENAI_DEPLOYMENT_NAME}}` | Required only for Azure OpenAI embeddings |
| knowledge | `{{KB_SECRET_NAME}}` | Secret containing embedding/chat keys |
| GitLab | `{{GITLAB_HOST}}` | GitLab.com or self-managed host |
| GitLab | `{{GITLAB_SANDBOX_PROJECT}}` | Sandbox project for KB MR proof |
| GitLab | `{{GITLAB_TOKEN_SECRET}}` | Secret for sandbox-scoped token if using the lite shim |
| HITL | `{{HITL_FRONT_DOOR}}` | Argo UI, Teams, ITSM, Git approval, or equivalent |
| Evidence | `{{EVIDENCE_DIR}}` | Where the work agent writes captured proof |

## Images To Confirm Or Mirror

Confirm these are allowed by work registry policy, or mirror them before
deployment:

| Image | Why |
|---|---|
| `ghcr.io/kagent-dev/doc2vec/mcp:2.11.0` | querydoc MCP server |
| `node:20-bookworm` | doc2vec indexer CronJob |
| `alpine:3.19` | Argo proof/helper workflow steps |
| `python:3.12-alpine` | GitLab lite MCP shim if using the sandbox path |
| kagent controller/agent runtime image | Existing kagent installation |
| Argo Workflows executor image | Existing workflow installation |
| PostgreSQL image or managed PostgreSQL service | Only if work does not use managed PostgreSQL |

Preferred for work: managed PostgreSQL with pgvector, not an in-cluster
database, unless the work owner explicitly approves an in-cluster test DB.

## Postgres Test Setup

Use this section only for an approved non-production test database. Do not
create production databases from this handoff.

Minimum requirements:

- PostgreSQL reachable from the kagent controller and memory services.
- `vector` extension installed.
- TLS and network policy aligned with work standards.
- Credentials stored as Kubernetes Secrets or external secret references.
- Separate databases or schemas for native kagent memory and shared incident
  memory if both are tested.

Verification commands:

```bash
kubectl --context {{KUBE_CONTEXT}} get secret -n {{KAGENT_NAMESPACE}} \
  {{POSTGRES_USER_SECRET}} {{POSTGRES_PASSWORD_SECRET}}

kubectl --context {{KUBE_CONTEXT}} exec -n {{KAGENT_NAMESPACE}} {{POSTGRES_POD}} -- \
  psql -U {{POSTGRES_USER}} -d {{POSTGRES_DB}} \
  -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

If using managed PostgreSQL, run the `psql` command from an approved admin pod
or workstation instead of assuming a PostgreSQL pod exists.

## Implementation Plan

### Phase 0 - Inventory

Capture current runtime state:

```bash
kubectl --context {{KUBE_CONTEXT}} get ns
kubectl --context {{KUBE_CONTEXT}} get crd | rg 'agents.kagent.dev|modelconfigs.kagent.dev|remotemcpservers.kagent.dev|workflows.argoproj.io'
kubectl --context {{KUBE_CONTEXT}} get agents,modelconfigs,remotemcpservers -n {{KAGENT_NAMESPACE}}
kubectl --context {{KUBE_CONTEXT}} get workflowtemplates,workflows -n {{ARGO_NAMESPACE}}
```

Record whether kagent is using SQLite, PostgreSQL, or another database:

```bash
kubectl --context {{KUBE_CONTEXT}} get deploy -n {{KAGENT_NAMESPACE}} -o yaml | \
  rg -n 'DATABASE_TYPE|DATABASE_VECTOR_ENABLED|POSTGRES|SQLITE|TURSO'
```

### Phase 1 - Knowledge Base Retrieval

Adapt `ai-platform/kagent-knowledge-base/` to the work KB repo.

Expected changes:

- Set `KB_REPO_URL={{KB_REPO_URL}}`.
- Set `KB_REPO_REF={{KB_REPO_REF}}`.
- Set `KB_SOURCE_PATH={{KB_SOURCE_PATH}}`.
- Configure `platform-kb-embedding-config`.
- Create the approved embedding secret.
- Deploy querydoc, RemoteMCPServer, and platform knowledge agent.

Validation:

```bash
cd ai-platform/kagent-knowledge-base
./scripts/validate.sh

kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} create secret generic {{KB_SECRET_NAME}} \
  --from-literal=OPENAI_API_KEY="{{OPENAI_API_KEY_OR_CHAT_KEY}}" \
  --from-literal=AZURE_OPENAI_KEY="{{AZURE_OPENAI_KEY_IF_USED}}" \
  --dry-run=client -o yaml | kubectl --context {{KUBE_CONTEXT}} apply -f -

kubectl --context {{KUBE_CONTEXT}} apply -k ai-platform/kagent-knowledge-base/k8s

kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} create job \
  --from=cronjob/platform-kb-indexer platform-kb-indexer-manual-$(date +%s)

kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} rollout status deploy/platform-kb-querydoc
kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} get remotemcpserver platform-kb-querydoc -o yaml
```

Required proof:

```text
SPECIALIST_KNOWLEDGE: completed
EVIDENCE_SOURCE: platform-kb
CITATIONS: {{KB_SOURCE_PATH}}/{{DOC_PATH}}#chunk-{{N}}
ANSWER_GROUNDED: yes
```

Negative proof:

```text
NO_RELEVANT_DOCS
ANSWER_GROUNDED: no
```

### Phase 2 - Native kagent Memory

Goal: prove durable per-agent/user memory with PostgreSQL + pgvector.

Implementation requirements:

- kagent controller uses durable PostgreSQL.
- `DATABASE_VECTOR_ENABLED=true`.
- PostgreSQL has `vector` extension.
- one low-risk test agent has `spec.declarative.memory.modelConfig`.
- embedding ModelConfig works.

Evidence commands:

```bash
kubectl --context {{KUBE_CONTEXT}} get cm -n {{KAGENT_NAMESPACE}} kagent-controller \
  -o jsonpath='{.data.DATABASE_VECTOR_ENABLED}{"\n"}'

kubectl --context {{KUBE_CONTEXT}} get agent -n {{KAGENT_NAMESPACE}} {{MEMORY_TEST_AGENT}} -o yaml | \
  rg -n 'memory:|modelConfig:|ttlDays'
```

Required proof:

```text
NATIVE_MEMORY_WRITE: stored
NATIVE_MEMORY_LOOKUP: hit
NATIVE_MEMORY_ISOLATION: passed
NATIVE_MEMORY_RESTART_SURVIVAL: passed
```

Do not claim this phase complete until recall survives a kagent controller
restart or a work-approved equivalent failover test.

### Phase 3 - Shared Incident Memory

Goal: reproduce the home `memory-mcp` pattern, then harden it for work.

First proof can reuse:

```text
a2a/platform-memory-showcase-demo/
platform/mcp-memory-server/
```

Required proof markers:

```text
MEMORY_WRITE: stored
MEMORY_LOOKUP: hit
A2A_CONTEXT_REUSED: yes
HITL_STATUS: resumed
WORKFLOW_MEMORY_PATTERN: proven
```

Production hardening requirements:

- read-only tools for general agents;
- observe+read tools for triage specialists only if approved;
- write tools only on a memory curator workflow or coordinator;
- audit fields on every memory write;
- retention or cleanup process for synthetic and real incident records;
- serialized writes or database transactions;
- sanitizer checks before any write.

### Phase 4 - HITL-Gated KB Update

Goal: after HITL, open a sandbox GitLab MR for a stale or missing KB entry.

Use the proven GitLab lite MCP shim for the first sandbox proof unless the
official GitLab MCP auth path is already approved and verified in work.

Required proof markers:

```text
HITL_STATUS: resumed
KB_UPDATE_MR: created
GITLAB_BRANCH: created
GITLAB_FILE: created_or_updated
GITLAB_MR: created
OUTPUT_SANITIZED: yes
```

Safety rules:

- sandbox project only;
- feature branch only;
- no default-branch direct pushes;
- no GitLab write tools on the read-only knowledge agent;
- no MR creation before HITL.

### Phase 5 - Smart Triage Integration

Wire the knowledge and memory specialists into the smart-triage workflow:

```text
alert or chaos event
  -> normalize incident
  -> fanout Kubernetes / network / Grafana / GitOps / knowledge / policy / trace
  -> memory lookup
  -> synthesis
  -> HITL
  -> optional GitLab MR or memory-curator write
  -> eval
  -> evidence package
```

Required combined markers:

```text
SMART_TRIAGE_FANOUT: started
SPECIALIST_KNOWLEDGE: completed
MEMORY_LOOKUP: hit
CITATIONS: {{KB_SOURCE_PATH}}/{{DOC_PATH}}#chunk-{{N}}
HITL_STATUS: resumed
REMEDIATION_MODE: gitops_or_workflow_only
OUTPUT_SANITIZED: yes
SMART_TRIAGE_PATTERN: proven
```

## Agent Prompt To Use Tomorrow

Copy this prompt into the work-side agent session:

```text
You are implementing the memory and knowledge-base replication from this
kagent-public handoff in an approved non-production work environment.

Read these files first:
- WORK-MEMORY-KB-NEXT-HANDOFF-README.md
- WORK-ZIP-AGENT-HANDOFF.md
- A2A-DEMO-EXECUTION-REVIEW.md
- A2A-WORK-IMPLEMENTATION-PLAN.md
- docs/kagent-memory/platform-memory/README.md
- docs/kagent-memory/README.md
- docs/memory-integration.md
- ai-platform/kagent-knowledge-base/README.md
- docs/platform-kb/platform/kagent-docs-rag.md
- docs/smart-triage-integration-spikes/spike-8-knowledge-runbook-retrieval.md

Your goal is to replicate and prove:
1. doc2vec/querydoc knowledge retrieval from the approved work Markdown KB;
2. a read-only knowledge specialist returning source citations;
3. a negative NO_RELEVANT_DOCS case;
4. native kagent memory backed by PostgreSQL + pgvector, if approved;
5. shared incident memory via memory-mcp or a hardened successor;
6. A2A context continuity across HITL;
7. HITL-gated GitLab sandbox MR creation for a stale/missing KB update;
8. eval/evidence output showing the system is safe and useful.

Do not claim completion from manifests alone. Capture live evidence:
- commands run;
- workflow name;
- Argo node table;
- RemoteMCPServer status;
- pod logs or A2A responses containing proof markers;
- one cited KB answer;
- one NO_RELEVANT_DOCS answer;
- one memory write and lookup;
- one HITL resume;
- one sandbox GitLab MR URL or sanitized MR reference;
- eval score and pass/fail result.

Keep all secrets out of Git. Use placeholders in committed files and Kubernetes
Secrets or approved external secret references for real values. Keep read-only
agents separate from write-capable agents.

At the end, produce:
- WORK-MEMORY-KB-EXECUTION-REVIEW.md
- WORK-MEMORY-KB-LIVE-EVIDENCE.md
- updated HTML/presenter evidence if available
- a concise Teams TLDR for stakeholders
- a list of unresolved blockers and next actions
```

## Evidence Pack Required

The work-side agent should create these files:

```text
WORK-MEMORY-KB-LIVE-EVIDENCE.md
WORK-MEMORY-KB-EXECUTION-REVIEW.md
WORK-MEMORY-KB-PR-SUMMARY.md
```

Minimum evidence:

| Evidence | Required proof |
|---|---|
| Querydoc deployment | Deployment ready, service reachable, RemoteMCPServer accepted |
| Index build | indexer job logs and generated DB manifest |
| Cited answer | source path and chunk in agent output |
| Negative retrieval | `NO_RELEVANT_DOCS` without hallucinated citation |
| Native memory | write, lookup, isolation, restart survival |
| Shared memory | `MEMORY_WRITE`, `MEMORY_LOOKUP`, `A2A_CONTEXT_REUSED` |
| HITL | suspend node and resume actor or approval ID |
| GitLab MR | branch, file update, MR, note, all sanitized |
| Eval | score, pass/fail, hard-gate status |
| Public safety | secret/private value sweep output |

## Public-Safety Sweep

Run this before handing evidence back:

```bash
rg -n '(subscriptionId|tenantId|clientId|password|token|secret|https?://[^\{\s\)]+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})' \
  WORK-MEMORY-KB-LIVE-EVIDENCE.md \
  WORK-MEMORY-KB-EXECUTION-REVIEW.md \
  WORK-MEMORY-KB-PR-SUMMARY.md \
  ai-platform/kagent-knowledge-base \
  a2a/platform-memory-showcase-demo \
  platform/mcp-memory-server
```

Expected result: only placeholder values, public URLs, and explicit safety
warnings. No real secrets, private hostnames, private cluster IPs, subscription
IDs, tenant IDs, or internal URLs.

## Done Criteria

This handoff is complete only when the work-side agent can show:

- querydoc retrieved work KB docs with citations;
- the read-only knowledge agent refused unsupported questions cleanly;
- native memory uses PostgreSQL + pgvector or is explicitly deferred with a
  blocker;
- shared incident memory wrote and recalled a synthetic incident;
- the A2A context survived HITL suspend/resume;
- KB update MR creation happened only after HITL and only in a sandbox project;
- eval passed with no hard failures;
- evidence files are sanitized and reviewable.


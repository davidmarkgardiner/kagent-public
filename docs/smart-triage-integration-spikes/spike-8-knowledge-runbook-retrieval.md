# Spike 8 — Knowledge & Runbook Retrieval

**Implementation order: 2 of 5.**

**Status:** implemented and live-proven as a public-safe contract proof on
2026-06-01.

Evidence:

- Workflow: `smart-triage-alert-b8gkz`, `Succeeded`, `14/14`.
- Marker: `SPECIALIST_KNOWLEDGE: completed`.
- Citation: `docs/platform-kb/runbooks/checkout-api-crashloop.md#chunk-1`.
- Negative case marker: `NO_RELEVANT_DOCS_CASE: validated`.
- HITL-gated write marker: `KB_UPDATE_MR: dry_run_after_hitl`.
- Proof helper:
  `a2a/smart-triage-fanout-demo/scripts/prove-knowledge-citation.sh`.

## Objective

Let smart-triage agents retrieve approved runbooks, platform docs, previous
incident notes, and service-specific knowledge from Git-backed Markdown — with
citations — and convert stale/missing knowledge into a sandbox GitLab MR after
HITL. This is the one spike with a write step (the MR), and it stays behind HITL.

## Existing Repo Reuse (do not rebuild)

Three retrieval patterns and a write path already exist:

| Pattern | Location | What it gives you |
|---|---|---|
| BM25-style Git-backed Markdown retrieval + stale-doc PR behavior | `agents/kagent-knowledge-ui/` | UI retrieval service + read-only answer agent (`k8s/kagent-agent.yaml`) that cites source paths and routes "stale/wrong" feedback to a PR |
| doc2vec / querydoc vector retrieval via MCP `query_documentation` | `ai-platform/kagent-knowledge-base/` | `config/doc2vec-platform-kb.yaml`, `k8s/querydoc-{deployment,service}.yaml`, `k8s/remotemcpserver.yaml` (`platform-kb-querydoc`), `k8s/indexer-cronjob.yaml` (nightly), `scripts/build-platform-kb-db.sh` |
| Architecture rationale (why Git + index, not kagent memory) | `docs/platform-kb/platform/kagent-docs-rag.md` | Permissions model (read-only chat, separate write path), freshness model (nightly + manual refresh) |
| GitLab write path (branch/file/MR/note) | Official MCP manifests: `a2a/smart-triage-fanout-demo/gitlab-mcp-agent.yaml` + `gitlab-mcp-remotemcpserver.yaml`; proven local shim: `gitlab-lite-mcp.yaml` + `gitlab-lite-agent.yaml` | Use the proven shim for the first sandbox proof unless official GitLab MCP OAuth/auth is approved and verified |

Sandbox knowledge repo (already public, already referenced in the brief and in
`observability/prometheus-alertmanager/04-workflow-template.yaml`):

```text
https://{{GITLAB_HOST}}/{{GITLAB_SANDBOX_PROJECT}}
```

## Proposed Architecture

Read path and write path are **separate agents** (per the docs-rag permissions
model):

```text
specialist / commander needs context
  -> knowledge specialist (READ-ONLY)
       -> query_documentation (querydoc MCP)  OR  UI BM25 retrieval
       -> answer with source-path citations
  -> incident commander folds knowledge into HITL packet
  -> HITL: operator approves a doc fix
  -> gitlab writer agent (WRITE, sandbox only)
       -> feature branch -> create_or_update_file -> merge_request -> note
  -> nightly/manual indexer refresh after merge
```

Phase 0 decision for the next agent: **BM25 vs doc2vec/querydoc for the first
proof.** Recommendation: doc2vec/querydoc, because `query_documentation` is
already an MCP tool the fan-out can call the same way it calls every other tool,
and the indexer CronJob + RemoteMCPServer already exist.

## First Safe Proof

1. Add a small `docs/platform-kb/` Markdown corpus to the sandbox GitLab repo.
2. Index it (`scripts/build-platform-kb-db.sh` → `platform-kb.db`, mounted by
   querydoc).
3. Have the knowledge specialist answer one runbook question **with citations**
   (source path + chunk).
4. Then, and only after HITL approval, open one sandbox MR that updates one
   stale or missing doc.

Read proof is read-only. The MR is the explicit, HITL-gated write this spike is
allowed.

## Required MCP / Tool / Server Shape

Read side (reuse `ai-platform/kagent-knowledge-base/k8s/remotemcpserver.yaml`):

```yaml
apiVersion: kagent.dev/v1alpha2
kind: RemoteMCPServer
metadata:
  name: platform-kb-querydoc
spec:
  protocol: STREAMABLE_HTTP
  url: http://platform-kb-querydoc.{{KAGENT_NAMESPACE}}.svc.cluster.local:8080/mcp
# tool: query_documentation
```

Write side:

- Preferred production target: official GitLab MCP at
  `https://{{GITLAB_HOST}}/api/v4/mcp`, but only after the work-approved
  OAuth/auth model is verified through kagent. Static header auth returned
  `Unauthorized` in the local proof, so do not assume a bearer-token shortcut.
- First sandbox proof target: reuse the proven lite MCP shim
  (`gitlab-lite-mcp.yaml` + `gitlab-lite-agent.yaml`) with a sandbox-scoped
  token in a Kubernetes Secret. The shim exposes one purpose-built tool for
  branch/file/MR/note creation.

Never inline credentials. Use `headersFrom` or `secretKeyRef` only.

## kagent Agent Contract

Two agents.

Knowledge specialist (read-only) — required markers:

```text
SPECIALIST_KNOWLEDGE: completed
EVIDENCE_SOURCE: platform-kb
CITATIONS: <source-path#chunk>[, ...]   # at least one, or NO_RELEVANT_DOCS
ANSWER_GROUNDED: yes|no
RECOMMENDATION: <runbook step | open KB gap as MR>
```

Hard rule in `systemMessage`: answer **only** from retrieved chunks; if retrieval
does not cover it, return `NO_RELEVANT_DOCS` and a raise-ticket recommendation
(mirror the knowledge-ui agent's "Sorry, we couldn't help…" contract). No
invented citations.

GitLab writer (write, sandbox only) — use the existing marker contract, but make
the tool binding explicit for the selected auth path:

```text
SPECIALIST_GITOPS: completed
GITLAB_BRANCH: created
GITLAB_FILE: created_or_updated
GITLAB_MR: created
REMEDIATION_MODE: gitops_or_workflow_only
OUTPUT_SANITIZED: yes
```

## Argo Workflow Integration Point

- Add `fanout-knowledge` to the DAG (depends on `normalize-incident`), using the
  existing `call-specialist` template; feed its output into
  `synthesize-incident` and `prove-result`.
- How other specialists request knowledge — three options; recommend **(b)** for
  the first proof:
  - (a) workflow-side retrieval step (deterministic, easiest to evidence)
  - (b) each specialist calls the knowledge specialist via A2A when it needs a
    runbook (most realistic)
  - (c) direct MCP `query_documentation` from any specialist (most coupling)
- The MR writer runs **after** `wait-for-human-review`, only on approve, only
  against `{{GITLAB_SANDBOX_PROJECT}}`.

## HITL Requirement

- Read/answer with citations: no HITL needed (read-only).
- Stale-doc MR: HITL mandatory. The writer agent only runs post-resume on an
  approved decision, and only opens an MR (never pushes to the default branch).

## Required Manifests / Scripts To Create

| Artifact | Purpose |
|---|---|
| Sandbox repo `docs/platform-kb/*.md` | Small public-safe corpus to index |
| `knowledge-specialist-agent.yaml` | Read-only KB agent referencing `platform-kb-querydoc` |
| Reuse `gitlab-lite-mcp.yaml` + `gitlab-lite-agent.yaml` for first proof | Proven sandbox MR writer + server |
| Optional: `gitlab-mcp-agent.yaml` + `gitlab-mcp-remotemcpserver.yaml` | Official GitLab MCP path after OAuth/auth is approved |
| Edit `workflow.yaml` | Add `fanout-knowledge` + post-HITL MR step |
| `scripts/index-knowledge.sh` | Wrap `build-platform-kb-db.sh` + refresh trigger |
| `scripts/prove-knowledge-citation.sh` | One A2A query asserting a citation is returned |

## Validation Commands

```bash
kubectl apply --dry-run=server -f .../knowledge-specialist-agent.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/gitlab-lite-mcp.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/gitlab-lite-agent.yaml
kubectl get remotemcpserver -n {{KAGENT_NAMESPACE}} platform-kb-querydoc
bash -n scripts/index-knowledge.sh scripts/prove-knowledge-citation.sh
```

## Public-Safe Placeholders

| Placeholder | Use |
|---|---|
| `{{GITLAB_SANDBOX_PROJECT}}` | `{{GITLAB_SANDBOX_PROJECT}}` |
| `{{KB_REPO_PATH}}` | `docs/platform-kb/` in the sandbox repo |
| `{{KAGENT_NAMESPACE}}` | kagent |
| `{{KB_REFRESH_SCHEDULE}}` | nightly cron + manual post-merge |
| `{{GITLAB_TOKEN_SECRET}}` | Secret name holding the sandbox PAT |

## Evidence To Capture

- One answer with a real `source-path#chunk` citation.
- A `NO_RELEVANT_DOCS` negative case (question outside the corpus).
- The sandbox MR URL (sanitized) and its proof-marker note.
- Index refresh log showing the updated doc is retrievable after merge.

## Failure Classes

| Class | Meaning | Evidence |
|---|---|---|
| `KB_REPO_UNAVAILABLE` | Repo/clone/index source unreachable | indexer job logs |
| `KB_INDEX_STALE` | DB older than threshold / pre-dates last merge | index timestamp vs repo HEAD |
| `NO_RELEVANT_DOCS` | Retrieval returned nothing usable (expected path) | retrieval output |
| `CITATION_MISSING` | Agent answered without a source path (contract fail) | agent output, marker check |
| `WRITE_APPROVAL_MISSING` | MR attempted without HITL approval | suspend node, approval record |
| `MCP_UNAVAILABLE` | querydoc or GitLab MCP cannot init/execute | RemoteMCPServer status, agent logs |

## Rollback / Disable Path

```bash
kubectl delete -f .../knowledge-specialist-agent.yaml --ignore-not-found
kubectl delete -f a2a/smart-triage-fanout-demo/gitlab-lite-agent.yaml --ignore-not-found
kubectl delete -f a2a/smart-triage-fanout-demo/gitlab-lite-mcp.yaml --ignore-not-found
kubectl delete secret -n {{KAGENT_NAMESPACE}} {{GITLAB_TOKEN_SECRET}} --ignore-not-found
# Indexer CronJob: kubectl delete cronjob -n {{KAGENT_NAMESPACE}} platform-kb-indexer --ignore-not-found
# Sandbox MR is reversible: close MR, delete feature branch in the sandbox repo.
```

## Known Risks

- Citation hallucination — enforce "answer only from retrieved chunks" and grep
  for a real path in the marker check; reject if absent.
- Index staleness after merge — the nightly cron can lag; wire a manual refresh
  to the post-merge step so the proof is deterministic.
- Write-path blast radius — keep the writer scoped to the sandbox project and
  feature branches; the Kyverno dangerous-verb policy must not be bypassed for
  the read-only knowledge agent (it carries no write tools).
- BM25 vs doc2vec divergence — pick one for the first proof; supporting both
  doubles the surface area.

## Exit Criteria

- Knowledge specialist answers one runbook question with a verifiable citation.
- Negative case returns `NO_RELEVANT_DOCS`, not a fabricated answer.
- One sandbox MR opened only after HITL, with proof markers in the MR note.
- Index refresh proven; updated doc retrievable post-merge.
- Read agent carries no write tools (passes dangerous-verb policy).

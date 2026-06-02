# Work Memory and Knowledge Base Verification Prompt

Purpose: give this prompt to the work-side agent after it says the memory,
knowledge-base, doc2vec, Postgres, and GitLab MCP handoff work is complete.
The goal is to force live proof, not another implementation summary.

Use only approved non-production systems. Keep all real endpoints, tokens,
hostnames, issue IDs, MR URLs, and user identities out of committed public
files. Use `{{PLACEHOLDER}}` values in evidence committed back to this repo.

## Copy/Paste Prompt For The Work Agent

```text
You said the memory and knowledge-base handoff is implemented. Now verify it
with live evidence.

Read these first:
- WORK-MEMORY-KB-NEXT-HANDOFF-README.md
- ai-platform/kagent-knowledge-base/README.md
- docs/platform-kb/platform/kagent-docs-rag.md
- docs/kagent-memory/platform-memory/README.md
- docs/kagent-memory/README.md
- docs/memory-integration.md
- A2A-DEMO-EXECUTION-REVIEW.md
- SMART-TRIAGE-GITLAB-MCP-MR-DEMO.md
- WORK-TRIAGE-REMEDIATION-VERIFICATION-README.md

Your task is to prove, with commands and captured outputs, that the work
implementation is complete. Do not claim success from YAML existing on disk.

Verify these capabilities:

1. doc2vec ingestion:
   - The approved GitLab/Git repo was cloned or pulled.
   - The configured Markdown knowledge-base path was indexed.
   - doc2vec generated a non-empty vector DB.
   - the index manifest records repo, branch/ref, source path, and timestamp.

2. querydoc MCP:
   - querydoc is deployed and healthy.
   - RemoteMCPServer is Accepted.
   - discovered tools include query_documentation.
   - an agent can call query_documentation through kagent, not only locally.

3. knowledge specialist:
   - one real question returns an answer grounded in retrieved docs.
   - the answer includes a source-path citation and chunk or heading.
   - one unsupported question returns NO_RELEVANT_DOCS or equivalent refusal.
   - the agent does not invent citations.

4. native kagent memory:
   - kagent is backed by PostgreSQL or the approved test database.
   - pgvector/vector extension is enabled.
   - a test agent has spec.declarative.memory configured with an embedding ModelConfig.
   - a fact can be saved and recalled in a fresh A2A context.
   - memory is isolated by agent/user.
   - recall survives a controller restart or approved equivalent failover test.

5. shared incident memory:
   - memory-mcp or its successor is reachable from kagent.
   - a synthetic incident memory is written.
   - a second agent recalls it.
   - A2A context continuity is preserved across HITL suspend/resume.
   - write-capable memory tools are only on the curator/coordinator path.

6. GitLab MCP repository write:
   - the GitLab MCP path is mounted into kagent, or the approved shim is mounted.
   - the agent creates a feature branch in the sandbox project.
   - the agent creates or updates one Markdown file.
   - the agent opens a merge request.
   - the agent posts a note with proof markers.
   - this is done through the kagent-mounted MCP path, not only terminal glab.

7. GitLab MCP issue operations:
   - the agent lists or reads issues in the sandbox project.
   - the agent creates or updates one issue, or posts a comment to an existing issue.
   - the issue update links to the MR or evidence file.
   - the action is verified with GitLab API, GitLab MCP output, or glab.

8. HITL and safety:
   - no repository write happens before HITL approval if the action is framed as remediation.
   - read-only agents do not have GitLab write tools or memory write tools.
   - public-safety scan finds no secrets or private values.

9. evaluation:
   - run the available eval or verification script.
   - capture score, pass/fail, and any hard failures.
   - hard failures must include missing HITL, missing citations, missing memory proof,
     missing GitLab verification, or unsafe output.

Produce these files:
- WORK-MEMORY-KB-VERIFY-EVIDENCE.md
- WORK-MEMORY-KB-VERIFY-REVIEW.md
- WORK-MEMORY-KB-VERIFY-TLDR.md

Each file must separate "verified live" from "configured but not proven".
Include exact commands run and short, sanitized output snippets.
```

## Verification Variables

Fill these in at runtime only:

| Placeholder | Meaning |
|---|---|
| `{{KUBE_CONTEXT}}` | Approved non-production kube context |
| `{{KAGENT_NAMESPACE}}` | Namespace where kagent runs |
| `{{ARGO_NAMESPACE}}` | Namespace where Argo Workflows runs |
| `{{KB_REPO_URL}}` | Git repo containing Markdown knowledge-base articles |
| `{{KB_REPO_REF}}` | Branch/ref indexed by doc2vec |
| `{{KB_SOURCE_PATH}}` | Markdown source path, for example `docs/platform-kb` |
| `{{KB_QUERY}}` | A question that should be answered from the KB |
| `{{KB_NEGATIVE_QUERY}}` | A question intentionally outside the KB |
| `{{POSTGRES_DB}}` | kagent memory database |
| `{{POSTGRES_ADMIN_POD_OR_CLIENT}}` | Approved pod/client for psql checks |
| `{{MEMORY_TEST_AGENT}}` | Low-risk memory-enabled test agent |
| `{{MEMORY_MCP_NAME}}` | Usually `memory-mcp` |
| `{{GITLAB_HOST}}` | GitLab host |
| `{{GITLAB_SANDBOX_PROJECT}}` | Sandbox project path or numeric ID |
| `{{GITLAB_TEST_ISSUE_IID}}` | Existing sandbox issue IID, if updating one |
| `{{GITLAB_AGENT}}` | kagent GitLab specialist name |
| `{{KNOWLEDGE_AGENT}}` | kagent knowledge specialist name |

## Commands To Run

### 1. Inventory Runtime

```bash
kubectl --context {{KUBE_CONTEXT}} get ns
kubectl --context {{KUBE_CONTEXT}} get crd | \
  rg 'agents.kagent.dev|modelconfigs.kagent.dev|remotemcpservers.kagent.dev|workflows.argoproj.io'
kubectl --context {{KUBE_CONTEXT}} get agents,modelconfigs,remotemcpservers -n {{KAGENT_NAMESPACE}}
kubectl --context {{KUBE_CONTEXT}} get workflows -n {{ARGO_NAMESPACE}} --sort-by=.metadata.creationTimestamp | tail -20
```

Evidence expected:

```text
RUNTIME_INVENTORY: captured
KAGENT_CRDS: present
ARGO_WORKFLOWS: present
```

### 2. Prove doc2vec Read The KB Repo

```bash
kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} get cronjob platform-kb-indexer -o yaml | \
  rg -n 'KB_REPO_URL|KB_REPO_REF|KB_SOURCE_PATH|DOC2VEC_REF|EMBEDDING_PROVIDER'

kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} create job \
  --from=cronjob/platform-kb-indexer platform-kb-indexer-verify-$(date +%s)

kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} get jobs,pods | rg platform-kb-indexer
kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} logs job/{{INDEXER_JOB_NAME}} --tail=200
```

Then verify the generated DB and manifest from the querydoc pod:

```bash
QUERYDOC_POD="$(kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} get pod \
  -l app.kubernetes.io/name=platform-kb-querydoc -o jsonpath='{.items[0].metadata.name}')"

kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} exec "$QUERYDOC_POD" -- \
  sh -c 'ls -lh /data/platform-kb.db /data/platform-kb-manifest.json && cat /data/platform-kb-manifest.json'
```

Evidence expected:

```text
DOC2VEC_REPO_CLONED: yes
DOC2VEC_SOURCE_PATH: {{KB_SOURCE_PATH}}
DOC2VEC_DB_CREATED: yes
DOC2VEC_DB_NONEMPTY: yes
DOC2VEC_MANIFEST: captured
```

### 3. Prove querydoc MCP Is Mounted

```bash
kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} rollout status deploy/platform-kb-querydoc
kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} get svc platform-kb-querydoc -o wide
kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} get remotemcpserver platform-kb-querydoc -o yaml | \
  rg -n 'Accepted|query_documentation|platform-kb-querydoc|discoveredTools'
kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} get agent {{KNOWLEDGE_AGENT}} -o yaml | \
  rg -n 'platform-kb-querydoc|query_documentation|modelConfig|tools:'
```

Evidence expected:

```text
QUERYDOC_DEPLOYMENT_READY: yes
QUERYDOC_MCP_ACCEPTED: yes
QUERYDOC_TOOL_DISCOVERED: query_documentation
KNOWLEDGE_AGENT_TOOL_BOUND: yes
```

### 4. Ask The Knowledge Agent

Port-forward kagent if needed:

```bash
kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} port-forward svc/kagent 18083:80
```

Positive query:

```bash
curl -sS -X POST "http://127.0.0.1:18083/api/a2a/kagent/{{KNOWLEDGE_AGENT}}/" \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0",
    "id":"kb-positive-verify",
    "method":"message/send",
    "params":{
      "message":{
        "role":"user",
        "parts":[{
          "kind":"text",
          "text":"Use query_documentation. Answer from the platform KB only. Question: {{KB_QUERY}}. Return markers SPECIALIST_KNOWLEDGE, CITATIONS, ANSWER_GROUNDED."
        }]
      }
    }
  }' | tee /tmp/kb-positive.json
```

Negative query:

```bash
curl -sS -X POST "http://127.0.0.1:18083/api/a2a/kagent/{{KNOWLEDGE_AGENT}}/" \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0",
    "id":"kb-negative-verify",
    "method":"message/send",
    "params":{
      "message":{
        "role":"user",
        "parts":[{
          "kind":"text",
          "text":"Use query_documentation. If the KB does not answer this, return NO_RELEVANT_DOCS and do not invent citations. Question: {{KB_NEGATIVE_QUERY}}."
        }]
      }
    }
  }' | tee /tmp/kb-negative.json
```

Evidence expected:

```text
SPECIALIST_KNOWLEDGE: completed
EVIDENCE_SOURCE: platform-kb
CITATIONS: {{KB_SOURCE_PATH}}/{{DOC_PATH}}#{{CHUNK_OR_HEADING}}
ANSWER_GROUNDED: yes
NO_RELEVANT_DOCS: validated
```

### 5. Prove PostgreSQL + pgvector For Native Memory

```bash
kubectl --context {{KUBE_CONTEXT}} get deploy -n {{KAGENT_NAMESPACE}} -o yaml | \
  rg -n 'DATABASE_TYPE|DATABASE_VECTOR_ENABLED|POSTGRES|PGHOST|SQLITE'

kubectl --context {{KUBE_CONTEXT}} exec -n {{KAGENT_NAMESPACE}} {{POSTGRES_ADMIN_POD_OR_CLIENT}} -- \
  psql -d {{POSTGRES_DB}} -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"

kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} get agent {{MEMORY_TEST_AGENT}} -o yaml | \
  rg -n 'memory:|modelConfig:|ttlDays'
```

Then use the memory-enabled agent to save and recall a unique test fact:

```text
Ask {{MEMORY_TEST_AGENT}}:
"Remember this verification token for this user: {{MEMORY_TOKEN}}. Return NATIVE_MEMORY_WRITE: stored."

Start a fresh A2A context and ask:
"What verification token did I ask you to remember? Return NATIVE_MEMORY_LOOKUP: hit if you can recall it."
```

Restart or fail over the kagent controller only if this is approved:

```bash
kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} rollout restart deploy/{{KAGENT_CONTROLLER_DEPLOYMENT}}
kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} rollout status deploy/{{KAGENT_CONTROLLER_DEPLOYMENT}}
```

Evidence expected:

```text
POSTGRES_MEMORY_BACKEND: yes
PGVECTOR_ENABLED: yes
NATIVE_MEMORY_WRITE: stored
NATIVE_MEMORY_LOOKUP: hit
NATIVE_MEMORY_ISOLATION: passed
NATIVE_MEMORY_RESTART_SURVIVAL: passed
```

### 6. Prove Shared Incident Memory And HITL

Run the memory showcase or the work equivalent:

```bash
KUBE_CONTEXT={{KUBE_CONTEXT}} MODEL_CONFIG={{CHAT_MODEL_CONFIG}} \
  a2a/platform-memory-showcase-demo/scripts/run-demo.sh
```

Capture workflow evidence:

```bash
argo --context {{KUBE_CONTEXT}} -n {{ARGO_NAMESPACE}} get {{MEMORY_WORKFLOW_NAME}}
kubectl --context {{KUBE_CONTEXT}} -n {{ARGO_NAMESPACE}} logs -l workflows.argoproj.io/workflow={{MEMORY_WORKFLOW_NAME}} --all-containers=true | \
  rg 'MEMORY_WRITE|MEMORY_LOOKUP|A2A_CONTEXT_REUSED|HITL_STATUS|WORKFLOW_MEMORY_PATTERN'
```

Evidence expected:

```text
MEMORY_WRITE: stored
MEMORY_LOOKUP: hit
A2A_CONTEXT_REUSED: yes
HITL_STATUS: resumed
WORKFLOW_MEMORY_PATTERN: proven
```

### 7. Prove GitLab MCP Can Commit, Open MR, And Update Issues

Ask the GitLab specialist through the kagent A2A endpoint. The action must use
the mounted GitLab MCP or approved shim, not terminal-only `glab`.

```bash
curl -sS -X POST "http://127.0.0.1:18083/api/a2a/kagent/{{GITLAB_AGENT}}/" \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0",
    "id":"gitlab-mcp-verify",
    "method":"message/send",
    "params":{
      "message":{
        "role":"user",
        "parts":[{
          "kind":"text",
          "text":"Use the mounted GitLab MCP tools against sandbox project {{GITLAB_SANDBOX_PROJECT}}. After HITL approval is represented by this verification request, create a feature branch, create or update docs/kagent-verification/memory-kb-verify.md with a short sanitized proof note, open an MR, then read issue {{GITLAB_TEST_ISSUE_IID}} or list open issues, and post a comment linking the MR/evidence. Return markers GITLAB_BRANCH, GITLAB_FILE, GITLAB_MR, GITLAB_ISSUE_READ, GITLAB_ISSUE_UPDATED, OUTPUT_SANITIZED. Do not fabricate URLs; only report values returned by tools."
        }]
      }
    }
  }' | tee /tmp/gitlab-mcp-verify.json
```

Verify independently with GitLab API, MCP output, or `glab`:

```bash
glab repo view {{GITLAB_SANDBOX_PROJECT}}
glab mr list -R {{GITLAB_SANDBOX_PROJECT}} --state opened
glab issue list -R {{GITLAB_SANDBOX_PROJECT}} --state opened
glab issue view {{GITLAB_TEST_ISSUE_IID}} -R {{GITLAB_SANDBOX_PROJECT}}
```

Evidence expected:

```text
GITLAB_MCP_MOUNTED: yes
GITLAB_BRANCH: created
GITLAB_FILE: created_or_updated
GITLAB_MR: created
GITLAB_ISSUE_READ: yes
GITLAB_ISSUE_UPDATED: yes
OUTPUT_SANITIZED: yes
```

### 8. Run Eval Or Verification Gates

Use the repo evals if they were lifted into work, or run the work equivalent:

```bash
find observability/agent-evals -maxdepth 3 -type f | sort
rg -n 'score|passed|hard_fail|HITL|CITATIONS|MEMORY|GITLAB' observability/agent-evals WORK-*.md
```

Expected result:

```text
EVAL_SCORE: {{SCORE}}
EVAL_PASSED: true
HARD_FAILURES: none
```

Hard failures:

- missing citation for positive KB answer;
- invented citation;
- no negative `NO_RELEVANT_DOCS` case;
- no memory write/lookup proof;
- no HITL proof;
- GitLab MR created only from terminal, not kagent-mounted MCP;
- issue update not verified;
- unsafe output or secret leak.

### 9. Public Safety Sweep

```bash
rg -n '(subscriptionId|tenantId|clientId|password|token|secret|https?://[^\{\s\)]+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})' \
  WORK-MEMORY-KB-VERIFY-EVIDENCE.md \
  WORK-MEMORY-KB-VERIFY-REVIEW.md \
  WORK-MEMORY-KB-VERIFY-TLDR.md
```

Expected result: only placeholders, public URLs, and explicit safety wording.

## How To Answer The doc2vec Question

Yes: doc2vec can read knowledge-base articles from a Git repo into a vector
database, and querydoc can expose that DB to kagent as an MCP tool.

The proof chain should look like this:

```text
{{KB_REPO_URL}} at {{KB_REPO_REF}}
  -> clone/pull
  -> read {{KB_SOURCE_PATH}} Markdown articles
  -> doc2vec chunks and embeds the articles
  -> writes /data/platform-kb.db
  -> writes /data/platform-kb-manifest.json
  -> querydoc serves /mcp
  -> RemoteMCPServer/platform-kb-querydoc Accepted
  -> platform knowledge agent calls query_documentation
  -> answer includes source-path citation
```

Do not accept "the agent has knowledge" as proof. Accept only cited answers
that can be traced back to indexed source files.

## Evidence Review Template

The work-side agent should fill this in:

```markdown
# Work Memory and KB Verification Review

Review date: {{DATE}}
Cluster: {{CLUSTER_REDACTED_OR_PLACEHOLDER}}
GitLab project: {{GITLAB_SANDBOX_PROJECT_PLACEHOLDER}}

## Verdict

- [ ] Complete and live-proven
- [ ] Partially complete, blockers listed
- [ ] Not complete

## Live Evidence

| Capability | Evidence | Status |
|---|---|---|
| doc2vec indexed KB repo | {{INDEXER_JOB}}, {{MANIFEST_SNIPPET}} | {{STATUS}} |
| querydoc MCP accepted | {{REMOTEMCP_STATUS}} | {{STATUS}} |
| knowledge citation | {{CITATION}} | {{STATUS}} |
| negative KB case | {{NO_RELEVANT_DOCS_OUTPUT}} | {{STATUS}} |
| Postgres + pgvector | {{PGVECTOR_OUTPUT}} | {{STATUS}} |
| native memory recall | {{MEMORY_TOKEN_RECALL}} | {{STATUS}} |
| shared memory recall | {{MEMORY_MARKERS}} | {{STATUS}} |
| HITL resume | {{WORKFLOW_NODE_OR_APPROVAL}} | {{STATUS}} |
| GitLab MR | {{MR_PLACEHOLDER}} | {{STATUS}} |
| GitLab issue update | {{ISSUE_PLACEHOLDER}} | {{STATUS}} |
| eval | {{SCORE_AND_PASS_FAIL}} | {{STATUS}} |
| public safety | {{RG_RESULT}} | {{STATUS}} |

## Blockers

{{BLOCKERS_OR_NONE}}

## Next Actions

{{NEXT_ACTIONS_OR_NONE}}
```


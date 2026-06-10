# Work Kagent Triage V2 KB Querydoc Proof

Date: 2026-06-04

Purpose: record the current home-lab status for the doc2vec/querydoc knowledge
path after the Kagent triage v2 review. This closes the ambiguity around the
synthetic citation marker: the static package is validated, but a real vector
query still requires an embedding key.

## Status

**PARTIAL / ready to run with embedding credentials.**

The local repo has the platform KB corpus, doc2vec config, querydoc Kubernetes
manifests, RemoteMCPServer, platform knowledge Agent, and validation scripts.
Static validation passed. A real cited-hit and `NO_RELEVANT_DOCS` query was not
run because `OPENAI_API_KEY` is not present in this shell.

The corpus now includes Kagent triage v2 agent guidance under
`docs/platform-kb/agents/` and a copyable GitLab MCP update-loop acceptance test
under `demos/kb-gitlab-mcp-update/`.

## Validation Run

Command:

```bash
cd ai-platform/kagent-knowledge-base
./scripts/validate.sh
```

Result:

```text
validation complete
```

Rendered resources:

```text
Agent/platform-knowledge-agent
ConfigMap/platform-kb-embedding-config
CronJob/platform-kb-indexer
Deployment/platform-kb-querydoc
ModelConfig/platform-kb-openai
Namespace/kagent
PersistentVolumeClaim/platform-kb-data
RemoteMCPServer/platform-kb-querydoc
Service/platform-kb-querydoc
```

Safety result:

```text
ok: no Azure/KRO provisioning resource kinds found
```

Tooling check:

```text
Docker: present
npm: present
OPENAI_API_KEY: missing
```

## Why The Live Query Was Not Run

`scripts/build-platform-kb-db.sh` requires an embedding provider. With the
default OpenAI provider, it exits unless `OPENAI_API_KEY` is set. The local
`scripts/smoke-querydoc-local.sh` also requires `OPENAI_API_KEY` because
querydoc embeds user queries at runtime.

This is the correct blocker. Do not claim live querydoc retrieval until the
database build and query smoke have both run with an approved embedding key.

## Exact Live Proof To Run Next

```bash
export OPENAI_API_KEY="{{OPENAI_API_KEY}}"
cd ai-platform/kagent-knowledge-base
./scripts/build-platform-kb-db.sh
./scripts/smoke-querydoc-local.sh
```

Then prove two query cases through the querydoc MCP path:

```text
1. Cited hit:
   Question: "How should the platform handle checkout-api CrashLoopBackOff?"
   Expected: answer cites docs/platform-kb/runbooks/checkout-api-crashloop.md

2. Cited hit:
   Question: "How does Kagent triage v2 use GitLab MCP to update the knowledge base?"
   Expected: answer cites docs/platform-kb/agents/gitlab-mcp-kb-update-loop.md

3. No-docs fallback:
   Question: "How should the platform operate a fictional service not present
   in the corpus?"
   Expected: NO_RELEVANT_DOCS, no invented citation.
```

## Work-Agent Requirement

The work agent must run the same proof against the approved work KB, embedding
provider, and querydoc MCP service before claiming live KB retrieval.

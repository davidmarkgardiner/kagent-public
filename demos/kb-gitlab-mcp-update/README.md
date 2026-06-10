# KB Update Through GitLab MCP Demo

Purpose: give the work-side agent a copyable acceptance test for the knowledge
base update loop. The agent should create or update KB Markdown through GitLab
MCP, update the KB index, rebuild doc2vec/querydoc, and prove the platform
knowledge agent can cite the new docs from the kagent UI or A2A path.

This is local/static in the public repo. The work agent must replace
placeholders, use approved work credentials, and return live evidence before
claiming the loop is complete.

## What This Proves

```text
SRE or triage agent identifies a KB gap
  -> KB author agent uses GitLab MCP
  -> branch and Markdown update
  -> INDEX.md update
  -> merge request and note
  -> doc2vec rebuild
  -> querydoc retrieval
  -> platform knowledge agent cites the new document
  -> triage coordinator uses the cited answer
```

## Read Order

1. `requests/kb-update-request.yaml`
2. `prompts/01-create-kb-docs-via-gitlab-mcp.md`
3. `prompts/02-reindex-and-querydoc-proof.md`
4. `prompts/03-triage-agent-kb-lookup.md`
5. `expected/platform-kb-author-agent.yaml`
6. `expected/kb-update-evidence-contract.yaml`
7. `expected/platform-knowledge-agent-query-contract.yaml`

## Source KB Docs

The home-lab seed documents are already in the real platform KB corpus:

- `docs/platform-kb/agents/kagent-triage-v2-overview.md`
- `docs/platform-kb/agents/gitlab-mcp-kb-update-loop.md`
- `docs/platform-kb/agents/querydoc-knowledge-agent.md`
- `docs/platform-kb/agents/triage-agent-kb-lookup.md`

The work agent can use those files as the desired content and recreate or update
them through GitLab MCP in the work repository.

## Local Verification

From the repo root:

```bash
bash demos/kb-gitlab-mcp-update/scripts/verify-demo.sh
```

This checks the local package, YAML files, required markers, KB docs, index
links, and public-safety patterns. It does not call GitLab or querydoc.

## Work-Lab Definition Of Done

The work agent must return:

- GitLab MCP tool list or equivalent wrapper description;
- branch name and commit IDs;
- created or updated KB file paths;
- updated `docs/platform-kb/INDEX.md` diff;
- merge request URL;
- merge request note proof;
- doc2vec rebuild command and output;
- querydoc cited-hit result for the new GitLab MCP KB document;
- no-docs fallback result;
- kagent UI or A2A transcript showing the knowledge agent citation;
- triage synthesis using the cited KB answer.

Do not claim live proof from a local file edit. The GitLab write must happen
through the kagent-mounted MCP path or an approved work wrapper MCP.

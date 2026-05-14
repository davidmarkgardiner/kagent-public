# Architecture

## Target Shape

```text
Git repository
  docs/platform-kb/
    INDEX.md
    aks/*.md
    platform/*.md
        |
        | nightly or manual refresh
        v
platform-kb-indexer CronJob
  clones repo
  runs kagent-dev/doc2vec
  writes /data/platform-kb.db
        |
        | shared PVC
        v
platform-kb-querydoc Deployment
  runs ghcr.io/kagent-dev/doc2vec/mcp
  serves /mcp
        |
        | RemoteMCPServer
        v
platform-knowledge-agent
  tool: query_documentation
```

## Why This Pattern

This follows the official kagent documentation-agent pattern. `doc2vec` owns crawling, chunking, embedding, and vector database creation. `querydoc` owns MCP serving. kagent owns tool discovery, agent prompting, and chat interaction.

## Runtime Responsibilities

| Component | Responsibility | Credentials |
|---|---|---|
| `platform-kb-indexer` | Pull docs repo and build `platform-kb.db` | Git read token if repo is private; embedding provider key |
| `platform-kb-querydoc` | Serve the vector DB as an MCP server | Embedding provider key for query embeddings |
| `platform-knowledge-agent` | Answer user questions by calling `query_documentation` | No Git credentials |
| stale-doc workflow | Open docs PRs after user approval | GitHub write credentials |

## Why Not Direct Git Pull in the Chat Agent

A chat agent can clone the repo per session, but that couples every user session to Git credentials, network access, indexing logic, and working-tree lifecycle. The MCP pattern keeps the chat agent read-only and gives all sessions a shared, refreshed search surface.

## Freshness

The POC defines a nightly CronJob at `02:17 UTC`, but it is suspended by default. Manual refresh is supported by creating a Job from the CronJob. A production deployment can unsuspend the CronJob or trigger the same rebuild from a docs-merge webhook.

## Storage

The POC uses a PVC named `platform-kb-data`. The indexer writes the database, and querydoc mounts it read-only. For a production environment, the same pattern can move to object storage or a signed image containing the DB artifact.

## Failure Modes

| Failure | Expected behavior |
|---|---|
| Missing embedding key | Indexer/querydoc fail fast; existing DB remains on PVC |
| Docs repo unavailable | Indexer job fails; querydoc keeps serving last successful DB |
| No matching docs | Agent says the docs do not answer and gives the ticket path |
| User reports stale docs | Agent summarizes the gap and routes to PR workflow; chat agent does not push Git |

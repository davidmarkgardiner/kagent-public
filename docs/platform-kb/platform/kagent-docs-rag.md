# Kagent Documentation RAG Pattern

## Summary

The platform knowledge-base POC uses kagent's documentation lookup pattern rather than kagent's built-in memory feature. The documentation pattern uses `doc2vec` to create a vector database from Markdown and `querydoc` to expose that database as an MCP server with a `query_documentation` tool.

## Components

1. A nightly indexer pulls the Git repository and runs `doc2vec` against `docs/platform-kb`.
2. `doc2vec` chunks the documents, generates embeddings, and writes `platform-kb.db`.
3. A `querydoc` MCP server mounts the database and exposes `/mcp`.
4. A kagent `RemoteMCPServer` points to the querydoc service.
5. A kagent `Agent` references the `query_documentation` tool.

## Why Not Kagent Memory

Kagent memory is designed for cross-session memories such as user preferences, key learnings, and prior conversation facts. It is not the canonical store for platform documentation. Platform docs should remain in Git, be indexed into a queryable database, and be cited by source path.

## Permissions Model

The chat agent should be read-only. It can query documentation and answer users, but it should not push to Git. Stale or missing documentation feedback should be routed to a separate PR workflow or write-capable agent that requires explicit approval.

## Freshness Model

The POC uses a nightly CronJob. A production deployment can also support a manual refresh job triggered after documentation merges.


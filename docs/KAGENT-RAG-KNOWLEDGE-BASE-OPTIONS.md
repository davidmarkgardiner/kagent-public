# Kagent RAG and Knowledge Base Options

Date: 2026-05-13

## Finding

Kagent has two related but distinct capabilities:

1. **Agent memory**: built-in long-term memory for past conversations.
2. **Documentation/RAG lookup**: implemented through `doc2vec` and a `query_documentation` MCP server.

For an AKS platform documentation assistant, the documentation/RAG pattern is the one to copy. Built-in memory is useful for user/session preferences and learned facts, but the local kagent design doc explicitly lists "RAG and Knowledge Base" as a non-goal for memory.

## Local Repository Evidence

### Built-in memory is not intended as the platform docs knowledge base

Local file: `kagent/design/EP-1256-memory.md`

Relevant points:

- Memory is designed for efficient storage and retrieval of memories.
- Goals include a built-in vector store and semantic search for agent memory.
- Non-goals include "RAG and Knowledge Base".
- Memory uses `pgvector` for Postgres and vector search for retrieval.
- The Python runtime exposes `save_memory`, `load_memory`, and `prefetch_memory`.

### Kagent already packages a documentation query tool

Local file: `kagent/helm/tools/querydoc/`

Relevant points:

- Chart name: `querydoc`
- Description: document query MCP server for kagent.
- Image: `ghcr.io/kagent-dev/doc2vec/mcp`
- The service is labelled for MCP discovery with `kagent.dev/mcp-service: "true"`.
- The MCP tool exposed by the upstream docs is `query_documentation`.

### Bundled agents already reference documentation lookup

Local examples:

- `kagent/helm/agents/kgateway/templates/agent.yaml`
- `kagent/helm/agents/istio/templates/agent.yaml`
- `kagent/helm/agents/helm/templates/agent.yaml`

These agents instruct themselves to use `query_documentation` for official docs, best practices, examples, and troubleshooting.

## Upstream Evidence

Official kagent docs have a "Using documentation in your agents" guide:

- It uses `kagent-dev/doc2vec` to crawl documentation and build a SQLite-vec database.
- It deploys an MCP server that serves the vector database.
- It registers that MCP server in kagent as a `RemoteMCPServer`.
- It creates an Agent with the `query_documentation` tool.

Official doc2vec repo:

- Crawls websites, GitHub repositories, local directories, Zendesk, and S3.
- Converts content to Markdown.
- Chunks content.
- Generates embeddings.
- Stores vectors in SQLite with `sqlite-vec` or Qdrant.
- Provides an MCP server for documentation and code search.

## Recommended Direction for the Platform KB

Use the upstream kagent pattern, but adapt it for the platform repository:

```text
Nightly indexing job
  -> pulls davidmarkgardiner/kagent-public or the private platform repo
  -> runs doc2vec against docs/platform-kb or equivalent
  -> produces platform-kb.db
  -> publishes the DB into an image, PVC, or object-backed volume

querydoc MCP server
  -> serves platform-kb.db
  -> exposes query_documentation

knowledge-base agent
  -> gets query_documentation as a tool
  -> answers docs questions with citations
  -> falls back to ticket path when docs do not answer
```

## Why This Is Better Than the PR #8 FastAPI Retrieval Service

The PR #8 service proved the concept, but it reimplements retrieval, indexing, source citation, and feedback routing.

The kagent-native version can reuse:

- `doc2vec` for crawling/chunking/embedding.
- `querydoc` Helm chart for the MCP server.
- kagent `RemoteMCPServer` for tool registration.
- existing Agent `tools` wiring for `query_documentation`.

That puts the docs assistant on the same extension path as the rest of kagent.

## Recommended First Implementation

1. Create a curated `docs/platform-kb/` tree and an `INDEX.md`.
2. Create a `doc2vec` config with `type: local_directory` or `type: code` depending on the source shape.
3. Generate `platform-kb.db`.
4. Package `platform-kb.db` into a querydoc-derived image or mount it into the querydoc pod.
5. Deploy a `RemoteMCPServer` pointing to the querydoc service.
6. Create a `platform-knowledge-agent` with the `query_documentation` tool.
7. Keep stale-doc PR creation as a separate workflow or tool with explicit approval.

## Caveat

Do not use kagent memory as the primary documentation store. It is per-agent/user memory with TTL and no cross-agent sharing. Use it for conversation memory, not canonical platform documentation.


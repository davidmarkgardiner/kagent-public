# Embedding Options

`doc2vec` and `querydoc` both need an embedding provider:

- `doc2vec` embeds the documentation into `platform-kb.db`.
- `querydoc` embeds each user query at runtime before vector search.

The same embedding model family and vector dimension must be used for both sides.

## Option 1: Direct OpenAI

This is the simplest route for a demo.

```bash
export EMBEDDING_PROVIDER=openai
export OPENAI_API_KEY="<real-openai-key>"
export OPENAI_MODEL="text-embedding-3-large"
```

Expected vector dimension: `3072`.

## Option 2: Azure OpenAI

Use this when the platform already has an approved Azure OpenAI embeddings deployment.

```bash
export EMBEDDING_PROVIDER=azure
export AZURE_OPENAI_KEY="<key>"
export AZURE_OPENAI_ENDPOINT="https://<resource>.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT_NAME="text-embedding-3-large"
export AZURE_OPENAI_API_VERSION="2024-10-21"
```

Expected vector dimension depends on the deployed embedding model. For `text-embedding-3-large`, use `3072`.

## Option 3: Local OpenAI-Compatible Embeddings

This is the local Qwen-style route. It requires an embeddings model, not a chat model.

Examples:

- `Qwen/Qwen3-Embedding-0.6B`
- `Qwen/Qwen3-Embedding-4B`
- `Qwen/Qwen3-Embedding-8B`
- `BAAI/bge-m3`
- `nomic-embed-text`

Serve the model with an OpenAI-compatible `/v1/embeddings` API, then point the OpenAI provider at it:

```bash
export EMBEDDING_PROVIDER=openai
export OPENAI_BASE_URL="http://<embedding-server>:<port>/v1"
export OPENAI_API_KEY="local-placeholder"
export OPENAI_MODEL="<served-embedding-model-name>"
export EMBEDDING_DIMENSION="<model-vector-dimension>"
```

The OpenAI Node SDK used by both `doc2vec` and `querydoc` reads `OPENAI_BASE_URL`, so this works without changing the provider name away from `openai`.

Important constraints:

- The endpoint must implement OpenAI-compatible `POST /v1/embeddings`.
- The model name must match what the local server exposes.
- `EMBEDDING_DIMENSION` must match the actual embedding vector size.
- Rebuild `platform-kb.db` whenever changing embedding model or dimension.

## Option 4: Gemini

The `querydoc` MCP image supports `EMBEDDING_PROVIDER=gemini`, but the current `doc2vec` indexer path in this POC is wired for `openai` and `azure`. Do not use Gemini for this POC unless the indexer is updated to generate the DB with the same Gemini embedding model and dimension.

## Recommendation

For a quick working demo, use direct OpenAI or Azure OpenAI.

For the homelab demo, use a local OpenAI-compatible embedding server with a small embeddings model such as `Qwen3-Embedding-0.6B`, then set `OPENAI_BASE_URL`, `OPENAI_MODEL`, and the correct dimension in both the indexer and querydoc deployment.

# OpenAI Embedding Setup

Use this when preparing the `doc2vec` + `querydoc` POC with OpenAI embeddings.

## Model

Use this model for the first demo:

```bash
text-embedding-3-large
```

Default vector dimension:

```bash
3072
```

`text-embedding-3-small` also works and uses dimension `1536`, but the POC manifests currently default to `text-embedding-3-large`.

## Create an API Key

1. Open the OpenAI platform dashboard.
2. Create or select a project.
3. Create a project API key.
4. Store the key in your shell only long enough to create the Kubernetes secret.

Local shell:

```bash
export OPENAI_API_KEY="<your-openai-api-key>"
export OPENAI_MODEL="text-embedding-3-large"
export EMBEDDING_PROVIDER="openai"
```

## Validate Locally

From the repo root:

```bash
cd ai-platform/kagent-knowledge-base
./scripts/build-platform-kb-db.sh
./scripts/smoke-querydoc-local.sh
```

If `doc2vec` returns:

```text
429 You exceeded your current quota
```

the key is reaching OpenAI, but the selected project does not currently have usable API quota or billing. Add billing/credits to the project or create a key under a project with API quota, then rerun the build.

## Update GEECOM Secret

This creates a dedicated secret for the POC in the `kagent` namespace.

```bash
kubectl -n kagent delete secret platform-kb-openai --ignore-not-found
kubectl -n kagent create secret generic platform-kb-openai \
  --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY}"
```

Do not paste the key into Git or any Markdown evidence file.

## Expected POC Settings

```bash
EMBEDDING_PROVIDER=openai
OPENAI_MODEL=text-embedding-3-large
EMBEDDING_DIMENSION=3072
```

If the model or dimension changes, rebuild `platform-kb.db` before running `querydoc`.

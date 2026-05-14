# K-Agent Knowledge UI POC

This proof of concept provides a small web UI for AKS platform questions backed by a Git-based Markdown knowledge base. It retrieves relevant docs, returns grounded step-by-step answers with citations, shows a ticket link for every response, and can open a GitHub PR when a user marks an answer as wrong or stale.

## Architecture

```text
Browser
  |
  | /api/query, /api/refresh, /api/feedback
  v
FastAPI UI service
  |-- clone/pull Git knowledge repo at startup and on refresh
  |-- build BM25-style Markdown chunk index
  |-- answer from retrieved chunks with source citations
  |-- call gh to open stale-doc PRs
  v
davidmarkgardiner/kagent-public knowledge docs

kagent Agent CR
  |-- declares AKS platform knowledge skill
  |-- owns in-cluster agent contract and response rules
```

The app is intentionally deterministic for the POC: it uses lexical BM25-style retrieval instead of a hosted embedding model, so the smoke tests run without cloud credentials. The Kubernetes manifests include the kagent `Agent` resource that defines the runtime contract for the platform assistant.

## Local Development

From this repository root:

```bash
cd agents/kagent-knowledge-ui
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=app KB_LOCAL_PATH="$(git rev-parse --show-toplevel)" uvicorn kagent_knowledge_ui.api:app --reload --port 8080
```

Open `http://127.0.0.1:8080` and ask one of:

- `How do I secure my pod?`
- `How do I bring my own domain?`
- `How do I set up a pod disruption budget?`
- `What Kubernetes resources are available on the shared AKS platform?`

## Test

```bash
cd agents/kagent-knowledge-ui
PYTHONPATH=app python3 -m unittest discover -s tests -v
```

The tests prove:

- all four required example queries return non-empty grounded answers;
- an unrelated question returns the fallback message and ticket link;
- stale-doc feedback creates a simulated PR artifact.

## Deploy to Kubernetes

Build and publish an image, then apply the manifests:

```bash
cd agents/kagent-knowledge-ui
docker build -t ghcr.io/davidmarkgardiner/kagent-knowledge-ui:mil-128 .
docker push ghcr.io/davidmarkgardiner/kagent-knowledge-ui:mil-128
kubectl apply -k k8s/
kubectl -n kagent-knowledge-ui port-forward svc/kagent-knowledge-ui 8080:80
```

Prerequisites:

- a local cluster such as kind or minikube;
- kagent installed in the `kagent` namespace for `k8s/kagent-agent.yaml`;
- GitHub CLI auth in the running container if real PR creation is enabled from the UI.

For a cluster without kagent CRDs, validate the app-only resources with:

```bash
kubectl apply --dry-run=client -f k8s/namespace.yaml -f k8s/deployment.yaml
```

## Point at Another Knowledge Base

Set these environment variables on the deployment or local process:

| Variable | Purpose | Default |
|---|---|---|
| `KB_REPO_URL` | Git URL to clone | `https://github.com/davidmarkgardiner/kagent-public.git` |
| `KB_REPO_REF` | Branch or tag to checkout | `main` |
| `KB_LOCAL_PATH` | Local repo path for development and tests | unset |
| `KB_CLONE_DIR` | Clone destination in the container | `/tmp/kagent-knowledge-ui/kagent-public` |
| `TICKET_URL` | Platform support ticket URL | MIL-128 Linear URL |
| `GITHUB_REPO` | Repo for stale-doc PRs | `davidmarkgardiner/kagent-public` |
| `GITHUB_BASE_BRANCH` | PR target branch | `main` |

When `docs/platform-kb/` exists, the indexer scopes retrieval to that folder so application docs do not outrank platform knowledge. If that folder does not exist, it scans Markdown files under the configured repository and excludes `.git`, `node_modules`, and `.venv`.

## How It Works

1. Startup runs `git clone` or `git pull` for the configured knowledge-base repo.
2. Markdown files are split by headings into chunks.
3. A BM25-style index scores chunks against the natural-language query.
4. The answerer formats the top chunks as short numbered guidance and attaches source links.
5. If the best score is below the confidence threshold, the UI returns: `Sorry, we couldn't help solve your problem. Please raise a ticket here.`
6. If a user clicks `Wrong or outdated`, the API appends a review note to the cited source document, commits it on a new branch, pushes it, and opens a ready-to-review PR with `gh pr create`.

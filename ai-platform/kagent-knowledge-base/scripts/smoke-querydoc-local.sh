#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
POC_DIR="${ROOT}/ai-platform/kagent-knowledge-base"
DB_PATH="${DB_PATH:-${POC_DIR}/dist/platform-kb.db}"
IMAGE="${QUERYDOC_IMAGE:-ghcr.io/kagent-dev/doc2vec/mcp:1.1.14}"
PORT="${PORT:-18080}"
CONTAINER_NAME="${CONTAINER_NAME:-platform-kb-querydoc-smoke}"

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "ERROR: OPENAI_API_KEY is required because querydoc embeds user queries at runtime" >&2
  exit 2
fi

if [ ! -s "${DB_PATH}" ]; then
  echo "ERROR: database not found or empty: ${DB_PATH}" >&2
  echo "Run ./scripts/build-platform-kb-db.sh first." >&2
  exit 1
fi

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
docker run -d \
  --name "${CONTAINER_NAME}" \
  -p "127.0.0.1:${PORT}:8080" \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -e SQLITE_DB_DIR=/data \
  -e VECTOR_DB_TYPE=sqlite \
  -e PORT=8080 \
  -e TRANSPORT_TYPE=http \
  -v "$(dirname "${DB_PATH}"):/data:ro" \
  "${IMAGE}" >/dev/null

cleanup() {
  docker logs "${CONTAINER_NAME}" > "${POC_DIR}/evidence/querydoc-smoke-container.log" 2>&1 || true
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Waiting for querydoc health on http://127.0.0.1:${PORT}/health"
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null; then
    curl -fsS "http://127.0.0.1:${PORT}/health"
    echo
    echo "querydoc health check passed"
    exit 0
  fi
  sleep 2
done

echo "ERROR: querydoc did not become healthy" >&2
exit 1


#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
POC_DIR="${ROOT}/ai-platform/kagent-knowledge-base"

DOC2VEC_REPO="${DOC2VEC_REPO:-https://github.com/kagent-dev/doc2vec.git}"
DOC2VEC_REF="${DOC2VEC_REF:-v2.11.0}"
KB_REPO_URL="${KB_REPO_URL:-}"
KB_REPO_REF="${KB_REPO_REF:-main}"
KB_LOCAL_PATH="${KB_LOCAL_PATH:-${ROOT}}"
KB_SOURCE_PATH="${KB_SOURCE_PATH:-docs/platform-kb}"
WORKDIR="${WORKDIR:-${POC_DIR}/work}"
DIST_DIR="${DIST_DIR:-${POC_DIR}/dist}"
EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER:-openai}"
EMBEDDING_DIMENSION="${EMBEDDING_DIMENSION:-3072}"
OPENAI_MODEL="${OPENAI_MODEL:-text-embedding-3-large}"
AZURE_OPENAI_API_VERSION="${AZURE_OPENAI_API_VERSION:-2024-10-21}"
BUILD_LOG="${DIST_DIR}/doc2vec-build.log"

case "${EMBEDDING_PROVIDER}" in
  openai)
    : "${OPENAI_API_KEY:?OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai}"
    ;;
  azure)
    : "${AZURE_OPENAI_KEY:?AZURE_OPENAI_KEY is required when EMBEDDING_PROVIDER=azure}"
    : "${AZURE_OPENAI_ENDPOINT:?AZURE_OPENAI_ENDPOINT is required when EMBEDDING_PROVIDER=azure}"
    : "${AZURE_OPENAI_DEPLOYMENT_NAME:?AZURE_OPENAI_DEPLOYMENT_NAME is required when EMBEDDING_PROVIDER=azure}"
    if [[ "${AZURE_OPENAI_ENDPOINT}" == *"{{"* ]]; then
      echo "ERROR: AZURE_OPENAI_ENDPOINT must be a real Azure OpenAI endpoint, not a placeholder" >&2
      exit 2
    fi
    ;;
  *)
    echo "ERROR: unsupported EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER}; expected openai or azure" >&2
    exit 2
    ;;
esac

rm -rf "${WORKDIR}"
mkdir -p "${WORKDIR}" "${DIST_DIR}"
rm -f "${DIST_DIR}/platform-kb.db" "${DIST_DIR}/platform-kb-manifest.json" "${BUILD_LOG}"

if [ -n "${KB_REPO_URL}" ]; then
  echo "Cloning KB repo ${KB_REPO_URL} (${KB_REPO_REF})"
  git clone --depth 1 --branch "${KB_REPO_REF}" "${KB_REPO_URL}" "${WORKDIR}/kb"
  KB_ROOT="${WORKDIR}/kb"
else
  echo "Using local KB repo ${KB_LOCAL_PATH}"
  KB_ROOT="${KB_LOCAL_PATH}"
fi

KB_ABS="${KB_ROOT}/${KB_SOURCE_PATH}"
if [ ! -d "${KB_ABS}" ]; then
  echo "ERROR: KB source path not found: ${KB_ABS}" >&2
  exit 1
fi

echo "Cloning doc2vec from ${DOC2VEC_REPO} (${DOC2VEC_REF})"
git clone --depth 1 --branch "${DOC2VEC_REF}" "${DOC2VEC_REPO}" "${WORKDIR}/doc2vec"
mkdir -p "${WORKDIR}/doc2vec/platform-kb" "${WORKDIR}/doc2vec/vector-dbs"
cp -R "${KB_ABS}/." "${WORKDIR}/doc2vec/platform-kb/"

case "${EMBEDDING_PROVIDER}" in
  openai)
    cat > "${WORKDIR}/doc2vec/config.yaml" <<EOF
embedding:
  provider: 'openai'
  dimension: ${EMBEDDING_DIMENSION}
  openai:
    api_key: '${OPENAI_API_KEY}'
    model: '${OPENAI_MODEL}'

sources:
  - type: 'local_directory'
    product_name: 'platform-kb'
    version: 'current'
    path: './platform-kb'
    include_extensions:
      - '.md'
    recursive: true
    max_size: 1048576
    database_config:
      type: 'sqlite'
      params:
        db_path: './vector-dbs/platform-kb.db'
EOF
    ;;
  azure)
    cat > "${WORKDIR}/doc2vec/config.yaml" <<EOF
embedding:
  provider: 'azure'
  dimension: ${EMBEDDING_DIMENSION}
  azure:
    api_key: '${AZURE_OPENAI_KEY}'
    endpoint: '${AZURE_OPENAI_ENDPOINT}'
    deployment_name: '${AZURE_OPENAI_DEPLOYMENT_NAME}'
    api_version: '${AZURE_OPENAI_API_VERSION}'

sources:
  - type: 'local_directory'
    product_name: 'platform-kb'
    version: 'current'
    path: './platform-kb'
    include_extensions:
      - '.md'
    recursive: true
    max_size: 1048576
    database_config:
      type: 'sqlite'
      params:
        db_path: './vector-dbs/platform-kb.db'
EOF
    ;;
esac

echo "Installing doc2vec dependencies"
cd "${WORKDIR}/doc2vec"
PUPPETEER_SKIP_DOWNLOAD=true npm install

echo "Running doc2vec"
npm start 2>&1 | tee "${BUILD_LOG}"

if grep -E -i "incorrect api key|401 unauthorized|error generating embeddings|failed to generate embeddings|failed to create embeddings|embedding failed|embedding error|error:" "${BUILD_LOG}" >/dev/null 2>&1; then
  echo "ERROR: doc2vec reported embedding failures; refusing to publish platform-kb.db" >&2
  exit 3
fi

test -s "${WORKDIR}/doc2vec/vector-dbs/platform-kb.db"
cp "${WORKDIR}/doc2vec/vector-dbs/platform-kb.db" "${DIST_DIR}/platform-kb.db"

cat > "${DIST_DIR}/platform-kb-manifest.json" <<EOF
{
  "source": "${KB_REPO_URL:-local:${KB_LOCAL_PATH}}",
  "ref": "${KB_REPO_REF}",
  "source_path": "${KB_SOURCE_PATH}",
  "embedding_provider": "${EMBEDDING_PROVIDER}",
  "doc2vec_ref": "${DOC2VEC_REF}",
  "db": "platform-kb.db",
  "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "Built ${DIST_DIR}/platform-kb.db"
echo "Wrote ${DIST_DIR}/platform-kb-manifest.json"

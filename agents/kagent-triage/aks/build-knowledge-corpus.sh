#!/usr/bin/env bash
# Build the knowledge-concierge corpus ConfigMap from kagent-triage/docs/*.md
#
# One ConfigMap, one key per markdown file. The knowledge-query workflow
# mounts this at /corpus/ and runs ripgrep over it for retrieval.
#
# Idempotent — uses kubectl apply via dry-run.
#
# Usage:
#   ./build-knowledge-corpus.sh                  # apply to current cluster
#   ./build-knowledge-corpus.sh --dry-run        # print YAML, no apply
#   KUBECONFIG=... NAMESPACE=kagent ./build-knowledge-corpus.sh
set -euo pipefail

NAMESPACE="${NAMESPACE:-kagent}"
CONFIGMAP_NAME="${CONFIGMAP_NAME:-kagent-knowledge-corpus}"
INDEX_NAME="${INDEX_NAME:-kagent-doc-index}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCS_DIR="${DOCS_DIR:-${SCRIPT_DIR}/../docs}"

if [ ! -d "$DOCS_DIR" ]; then
  echo "ERROR: docs dir not found: $DOCS_DIR" >&2
  exit 1
fi

DRY_RUN=""
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN="--dry-run=client"
fi

# Stage only the .md files (avoid PDFs, PPTX, hidden dirs)
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

count=0
for f in "$DOCS_DIR"/*.md; do
  [ -e "$f" ] || continue
  cp "$f" "$STAGE/$(basename "$f")"
  count=$((count + 1))
done

if [ "$count" -eq 0 ]; then
  echo "ERROR: no *.md files in $DOCS_DIR" >&2
  exit 1
fi
echo "Staged $count markdown files from $DOCS_DIR" >&2

# Build the index — filename + first markdown heading + first non-empty paragraph
INDEX="$STAGE/_index.txt"
{
  echo "# Knowledge corpus index"
  echo "# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  for f in "$STAGE"/*.md; do
    name=$(basename "$f")
    title=$(grep -m1 '^# ' "$f" 2>/dev/null | sed 's/^# *//' || true)
    [ -z "$title" ] && title="$name"
    summary=$(awk 'NR>1 && /^[A-Za-z]/ {print; exit}' "$f" | head -c 200)
    echo "- ${name} — ${title}"
    [ -n "$summary" ] && echo "    ${summary}"
  done
} > "$INDEX"

# Create/update the corpus ConfigMap (one key per .md file + the index)
kubectl create configmap "$CONFIGMAP_NAME" \
  --namespace "$NAMESPACE" \
  --from-file="$STAGE" \
  --dry-run=client -o yaml | \
  kubectl ${DRY_RUN:+--dry-run=client} apply -f -

echo "Done. ConfigMap: $NAMESPACE/$CONFIGMAP_NAME ($count docs + index)"
echo
echo "Verify:"
echo "  kubectl -n $NAMESPACE get cm $CONFIGMAP_NAME -o jsonpath='{.data._index\\.txt}'"

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
project="azure-mcp-kagent-poc"
cleanup() { docker compose -p "$project" down --remove-orphans; }
trap cleanup EXIT
docker compose -p "$project" up -d --build
ready=0
for attempt in {1..30}; do
  if curl --silent --max-time 2 http://127.0.0.1:18081/mcp >/dev/null && \
     curl --silent --max-time 2 http://127.0.0.1:18080/azure/mcp >/dev/null; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" != 1 ]]; then
  docker compose -p "$project" logs --tail 30
  exit 1
fi
python3 verify_mcp.py

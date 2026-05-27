#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${CONFLUENT_ENV_FILE:-${ROOT_DIR}/confluent.io/.bootstrap.env}"

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: missing required command: $1" >&2
    exit 1
  }
}

require curl
require jq

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

: "${CONFLUENT_CLUSTER_ID:?missing CONFLUENT_CLUSTER_ID}"
: "${CONFLUENT_ALERTS_TOPIC:?missing CONFLUENT_ALERTS_TOPIC}"
: "${CONFLUENT_SA_KEY:?missing CONFLUENT_SA_KEY}"
: "${CONFLUENT_SA_SECRET:?missing CONFLUENT_SA_SECRET}"

REST_ENDPOINT="${CONFLUENT_REST_ENDPOINT:-}"
if [ -z "$REST_ENDPOINT" ]; then
  require confluent
  REST_ENDPOINT="$(confluent kafka cluster describe "$CONFLUENT_CLUSTER_ID" -o json | jq -r '.rest_endpoint // .restEndpoint // empty')"
fi

if [ -z "$REST_ENDPOINT" ]; then
  echo "ERROR: could not determine CONFLUENT_REST_ENDPOINT" >&2
  exit 1
fi

REST_ENDPOINT="${REST_ENDPOINT%/}"
TOPIC="${SMOKE_TOPIC:-$CONFLUENT_ALERTS_TOPIC}"
RUN_ID="${SMOKE_RUN_ID:-rest-smoke-$(date -u +%Y%m%dT%H%M%SZ)}"
SMOKE_KEY="${SMOKE_KEY:-$RUN_ID}"
SMOKE_SOURCE="${SMOKE_SOURCE:-manual-rest-smoke}"
SMOKE_STATUS="${SMOKE_STATUS:-firing}"
SMOKE_MESSAGE="${SMOKE_MESSAGE:-Confluent REST v3 smoke test}"

tmp_payload="$(mktemp)"
tmp_response="$(mktemp)"
cleanup() {
  rm -f "$tmp_payload" "$tmp_response"
}
trap cleanup EXIT
chmod 600 "$tmp_payload" "$tmp_response"

if [ -n "${SMOKE_PAYLOAD_FILE:-}" ]; then
  jq -c . "$SMOKE_PAYLOAD_FILE" >/dev/null
  jq -n \
    --arg key "$SMOKE_KEY" \
    --slurpfile data "$SMOKE_PAYLOAD_FILE" \
    '{
      key: {type: "STRING", data: $key},
      value: {type: "JSON", data: $data[0]}
    }' > "$tmp_payload"
else
  jq -n \
    --arg key "$SMOKE_KEY" \
    --arg runId "$RUN_ID" \
    --arg source "$SMOKE_SOURCE" \
    --arg status "$SMOKE_STATUS" \
    --arg message "$SMOKE_MESSAGE" \
    --arg topic "$TOPIC" \
    '{
      key: {type: "STRING", data: $key},
      value: {
        type: "JSON",
        data: {
          source: $source,
          status: $status,
          message: $message,
          run_id: $runId,
          topic: $topic,
          sent_at: (now | todateiso8601)
        }
      }
    }' > "$tmp_payload"
fi

produce_url="${REST_ENDPOINT}/kafka/v3/clusters/${CONFLUENT_CLUSTER_ID}/topics/${TOPIC}/records"

status="$(
  curl -sS \
    -u "${CONFLUENT_SA_KEY}:${CONFLUENT_SA_SECRET}" \
    -o "$tmp_response" \
    -w "%{http_code}" \
    -X POST "$produce_url" \
    -H "Content-Type: application/json" \
    --data-binary "@${tmp_payload}"
)"

case "$status" in
  2*)
    jq -e '.error_code and ((.error_code / 100 | floor) == 2)' "$tmp_response" >/dev/null
    jq \
      --arg http_status "$status" \
      --arg run_id "$RUN_ID" \
      '{
        http_status: ($http_status | tonumber),
        error_code,
        cluster_id: "<redacted>",
        topic_name,
        partition_id,
        offset,
        run_id: $run_id,
        value_size: .value.size
      }' "$tmp_response"
    ;;
  *)
    echo "ERROR: Confluent REST produce failed with HTTP ${status}" >&2
    jq -r '.message // .error // .' "$tmp_response" >&2 || cat "$tmp_response" >&2
    exit 1
    ;;
esac

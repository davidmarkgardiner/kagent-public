#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${ROOT_DIR}/confluent.io/.bootstrap.env"

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: missing required command: $1" >&2
    exit 1
  }
}

require curl
require jq
require confluent

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: missing ${ENV_FILE}. Run observability/confluent-cloud-pipeline/00-cluster-bootstrap.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

: "${CONFLUENT_CLUSTER_ID:?missing CONFLUENT_CLUSTER_ID in ${ENV_FILE}}"
: "${CONFLUENT_ALERTS_TOPIC:?missing CONFLUENT_ALERTS_TOPIC in ${ENV_FILE}}"
: "${CONFLUENT_SA_KEY:?missing CONFLUENT_SA_KEY in ${ENV_FILE}}"
: "${CONFLUENT_SA_SECRET:?missing CONFLUENT_SA_SECRET in ${ENV_FILE}}"

GRAFANA_URL="${GRAFANA_URL:-http://127.0.0.1:13030}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-admin}"
CONTACT_POINT_NAME="${GRAFANA_CONTACT_POINT_NAME:-confluent-kafka-rest-alerts}"
CONTACT_POINT_UID="${GRAFANA_CONTACT_POINT_UID:-confluent-kafka-rest-alerts}"
KAFKA_TOPIC="${GRAFANA_KAFKA_TOPIC:-$CONFLUENT_ALERTS_TOPIC}"

REST_ENDPOINT="${CONFLUENT_REST_ENDPOINT:-}"
if [ -z "$REST_ENDPOINT" ]; then
  REST_ENDPOINT="$(confluent kafka cluster describe "$CONFLUENT_CLUSTER_ID" -o json | jq -r '.rest_endpoint // .restEndpoint // empty')"
fi

if [ -z "$REST_ENDPOINT" ]; then
  echo "ERROR: could not determine Confluent REST endpoint for ${CONFLUENT_CLUSTER_ID}" >&2
  exit 1
fi

REST_ENDPOINT="${REST_ENDPOINT%/}"
case "$REST_ENDPOINT" in
  */kafka) KAFKA_REST_PROXY="$REST_ENDPOINT" ;;
  *) KAFKA_REST_PROXY="${REST_ENDPOINT}/kafka" ;;
esac

tmp_payload="$(mktemp)"
tmp_response="$(mktemp)"
cleanup() {
  rm -f "$tmp_payload" "$tmp_response"
}
trap cleanup EXIT
chmod 600 "$tmp_payload" "$tmp_response"

jq -n \
  --arg uid "$CONTACT_POINT_UID" \
  --arg name "$CONTACT_POINT_NAME" \
  --arg restProxy "$KAFKA_REST_PROXY" \
  --arg topic "$KAFKA_TOPIC" \
  --arg username "$CONFLUENT_SA_KEY" \
  --arg password "$CONFLUENT_SA_SECRET" \
  --arg clusterId "$CONFLUENT_CLUSTER_ID" \
  '{
    uid: $uid,
    name: $name,
    type: "kafka",
    settings: {
      kafkaRestProxy: $restProxy,
      kafkaTopic: $topic,
      username: $username,
      password: $password,
      apiVersion: "v3",
      kafkaClusterId: $clusterId
    },
    disableResolveMessage: false,
    provenance: "api"
  }' > "$tmp_payload"

existing_uid="$(
  curl -fsS -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
    "${GRAFANA_URL%/}/api/v1/provisioning/contact-points" |
    jq -r --arg uid "$CONTACT_POINT_UID" --arg name "$CONTACT_POINT_NAME" \
      '.[] | select(.uid == $uid or .name == $name) | .uid' | head -1
)"

if [ -n "$existing_uid" ]; then
  status="$(
    curl -sS -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
      -o "$tmp_response" -w "%{http_code}" \
      -X PUT "${GRAFANA_URL%/}/api/v1/provisioning/contact-points/${existing_uid}" \
      -H "Content-Type: application/json" \
      --data-binary "@${tmp_payload}"
  )"
  action="updated"
else
  status="$(
    curl -sS -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
      -o "$tmp_response" -w "%{http_code}" \
      -X POST "${GRAFANA_URL%/}/api/v1/provisioning/contact-points" \
      -H "Content-Type: application/json" \
      --data-binary "@${tmp_payload}"
  )"
  action="created"
fi

case "$status" in
  200|201|202)
    echo "Grafana contact point ${action}: ${CONTACT_POINT_NAME}"
    echo "Kafka topic: ${KAFKA_TOPIC}"
    echo "Kafka API version: v3"
    ;;
  *)
    echo "ERROR: Grafana contact point request failed with HTTP ${status}" >&2
    jq -r '.message // .error // .' "$tmp_response" >&2 || cat "$tmp_response" >&2
    exit 1
    ;;
esac

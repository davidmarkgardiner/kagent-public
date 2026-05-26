#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="${ROOT_DIR}/confluent.io"
BOOTSTRAP_ENV="${OUT_DIR}/.bootstrap.env"
KEY_FILE="${OUT_DIR}/.kafka-key"

ENV_NAME="${CONFLUENT_ENV_NAME:-kagent-poc}"
CLUSTER_NAME="${CONFLUENT_CLUSTER_NAME:-kagent-poc}"
CLOUD="${CONFLUENT_CLOUD:-aws}"
REGION="${CONFLUENT_REGION:-eu-west-1}"
K8S_TOPIC="${CONFLUENT_K8S_TOPIC:-k8s-events}"
ALERTS_TOPIC="${CONFLUENT_ALERTS_TOPIC:-alertmanager-events}"
SERVICE_ACCOUNT="${CONFLUENT_SERVICE_ACCOUNT:-kagent-pipeline}"

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: missing required command: $1" >&2
    exit 1
  }
}

json_value() {
  jq -r "$1 // empty"
}

api_key_value() {
  jq -r '.api_key // .key // empty'
}

api_secret_value() {
  jq -r '.api_secret // .secret // empty'
}

require confluent
require jq

mkdir -p "$OUT_DIR"

if ! confluent organization list >/dev/null 2>&1; then
  echo "ERROR: Confluent CLI is not logged in. Run: confluent login" >&2
  exit 1
fi

if ! git -C "$ROOT_DIR" check-ignore -q confluent.io/.bootstrap.env; then
  echo "ERROR: local Confluent bootstrap env is not ignored by git." >&2
  echo "Run: git check-ignore -v confluent.io/.bootstrap.env" >&2
  exit 1
fi

if ! git -C "$ROOT_DIR" check-ignore -q confluent.io/.kafka-key; then
  echo "ERROR: local Confluent output files are not ignored by git." >&2
  echo "Run: git check-ignore -v confluent.io/.kafka-key" >&2
  exit 1
fi

cat <<EOF
This will create or reuse Confluent Cloud resources:
  environment:      ${ENV_NAME}
  cluster:          ${CLUSTER_NAME}
  cloud/region:     ${CLOUD}/${REGION}
  topics:           ${K8S_TOPIC}, ${ALERTS_TOPIC}
  service account:  ${SERVICE_ACCOUNT}

Confluent Cloud resources may incur cost.
EOF

read -r -p "Continue? Type 'yes': " confirm
if [ "$confirm" != "yes" ]; then
  echo "Aborted."
  exit 0
fi

echo "Finding or creating environment ${ENV_NAME}..."
ENV_ID="$(confluent environment list -o json | jq -r --arg name "$ENV_NAME" '.[] | select(.name == $name) | .id' | head -1)"
if [ -z "$ENV_ID" ]; then
  ENV_ID="$(confluent environment create "$ENV_NAME" -o json | json_value '.id')"
fi
confluent environment use "$ENV_ID" >/dev/null

echo "Finding or creating Kafka cluster ${CLUSTER_NAME}..."
CLUSTER_ID="$(confluent kafka cluster list -o json | jq -r --arg name "$CLUSTER_NAME" '.[] | select(.name == $name) | .id' | head -1)"
if [ -z "$CLUSTER_ID" ]; then
  CLUSTER_ID="$(confluent kafka cluster create "$CLUSTER_NAME" --cloud "$CLOUD" --region "$REGION" --type basic -o json | json_value '.id')"
fi
confluent kafka cluster use "$CLUSTER_ID" >/dev/null

BOOTSTRAP="$(confluent kafka cluster describe "$CLUSTER_ID" -o json | jq -r '.endpoint // .bootstrap_endpoint // empty' | sed -E 's#^SASL_SSL://##')"
if [ -z "$BOOTSTRAP" ]; then
  echo "ERROR: could not determine Confluent bootstrap endpoint for ${CLUSTER_ID}" >&2
  exit 1
fi

REST_ENDPOINT="$(confluent kafka cluster describe "$CLUSTER_ID" -o json | jq -r '.rest_endpoint // .restEndpoint // empty')"
if [ -z "$REST_ENDPOINT" ]; then
  echo "ERROR: could not determine Confluent REST endpoint for ${CLUSTER_ID}" >&2
  exit 1
fi

for topic in "$K8S_TOPIC" "$ALERTS_TOPIC"; do
  echo "Finding or creating topic ${topic}..."
  if ! confluent kafka topic describe "$topic" --cluster "$CLUSTER_ID" >/dev/null 2>&1; then
    confluent kafka topic create "$topic" --partitions 6 --cluster "$CLUSTER_ID" >/dev/null
  fi
done

echo "Finding or creating service account ${SERVICE_ACCOUNT}..."
SA_ID="$(confluent iam service-account list -o json | jq -r --arg name "$SERVICE_ACCOUNT" '.[] | select(.name == $name) | .id' | head -1)"
if [ -z "$SA_ID" ]; then
  SA_ID="$(confluent iam service-account create "$SERVICE_ACCOUNT" --description "kagent Confluent pipeline PoC" -o json | json_value '.id')"
fi

if [ -f "$KEY_FILE" ]; then
  # shellcheck disable=SC1090
  source "$KEY_FILE"
else
  echo "Creating Kafka API key for ${SA_ID}..."
  key_json="$(confluent api-key create --resource "$CLUSTER_ID" --service-account "$SA_ID" -o json)"
  CONFLUENT_SA_KEY="$(printf '%s' "$key_json" | api_key_value)"
  CONFLUENT_SA_SECRET="$(printf '%s' "$key_json" | api_secret_value)"
  if [ -z "$CONFLUENT_SA_KEY" ] || [ -z "$CONFLUENT_SA_SECRET" ]; then
    echo "ERROR: Confluent API key create output did not include api_key/api_secret." >&2
    exit 1
  fi
  umask 077
  {
    printf 'CONFLUENT_SA_KEY=%q\n' "$CONFLUENT_SA_KEY"
    printf 'CONFLUENT_SA_SECRET=%q\n' "$CONFLUENT_SA_SECRET"
  } > "$KEY_FILE"
fi

for topic in "$K8S_TOPIC" "$ALERTS_TOPIC"; do
  confluent kafka acl create --allow --service-account "$SA_ID" --operations write,read,describe --topic "$topic" --cluster "$CLUSTER_ID" >/dev/null || true
done

confluent kafka acl create --allow --service-account "$SA_ID" --operations read,describe --consumer-group 'kagent-critical-' --prefix --cluster "$CLUSTER_ID" >/dev/null || true
confluent kafka acl create --allow --service-account "$SA_ID" --operations read,describe --consumer-group 'kagent-alertmanager-' --prefix --cluster "$CLUSTER_ID" >/dev/null || true
confluent kafka acl create --allow --service-account "$SA_ID" --operations read,describe --consumer-group 'verify-' --prefix --cluster "$CLUSTER_ID" >/dev/null || true

umask 077
{
  printf 'CONFLUENT_ENVIRONMENT_ID=%q\n' "$ENV_ID"
  printf 'CONFLUENT_CLUSTER_ID=%q\n' "$CLUSTER_ID"
  printf 'CONFLUENT_BOOTSTRAP=%q\n' "$BOOTSTRAP"
  printf 'CONFLUENT_REST_ENDPOINT=%q\n' "$REST_ENDPOINT"
  printf 'CONFLUENT_K8S_TOPIC=%q\n' "$K8S_TOPIC"
  printf 'CONFLUENT_ALERTS_TOPIC=%q\n' "$ALERTS_TOPIC"
  printf 'CONFLUENT_SA_ID=%q\n' "$SA_ID"
  printf 'CONFLUENT_SA_KEY=%q\n' "$CONFLUENT_SA_KEY"
  printf 'CONFLUENT_SA_SECRET=%q\n' "$CONFLUENT_SA_SECRET"
} > "$BOOTSTRAP_ENV"

echo "Wrote local bootstrap env: ${BOOTSTRAP_ENV}"
echo "Wrote local API key file: ${KEY_FILE}"

#!/usr/bin/env bash
# Disposable containers only; no kube context, host ports, or external credentials.
set -euo pipefail
BUNDLE=$(cd "$(dirname "$0")" && pwd)
RUN="admission-proof-$$"
TEMP_DIR=$(mktemp -d)
cleanup() {
  docker rm -f "$RUN-vector" "$RUN-intake" "$RUN-kafka" "$RUN-pg" >/dev/null 2>&1 || true
  docker network rm "$RUN" >/dev/null 2>&1 || true
  rm -rf "$TEMP_DIR"
}
trap cleanup EXIT
docker build -q -t namespace-alert-admission:local "$BUNDLE"
docker network create "$RUN" >/dev/null
docker run -d --name "$RUN-pg" --network "$RUN" --network-alias pg \
  -e POSTGRES_USER=admission -e POSTGRES_DB=admission -e POSTGRES_HOST_AUTH_METHOD=trust \
  postgres:16-alpine >/dev/null
for attempt in $(seq 1 30); do
  if docker exec "$RUN-pg" pg_isready -U admission >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec "$RUN-pg" pg_isready -U admission
COMMON=(--rm --network "$RUN" -e TEST_DATABASE_URL=postgresql://admission@pg/admission
  -v "$BUNDLE:/work:ro" -w /work)
docker run "${COMMON[@]}" namespace-alert-admission:local python -m unittest test_gate -v

# Render the real sink implementation into a tiny HTTP-source fixture.
docker run "${COMMON[@]}" namespace-alert-admission:local python -c '
import yaml
from render_vector import render
source=yaml.safe_dump({"kind":"ConfigMap","data":{"vector.yaml":yaml.safe_dump({
 "sources":{"input":{"type":"http_server","address":"0.0.0.0:8088","decoding":{"codec":"json"}}},
 "transforms":{"incident_signals":{"type":"remap","inputs":["input"],"source":". = ."}},
 "sinks":{"kafka":{"type":"kafka"}}})}})
print(list(yaml.safe_load_all(render(source,"http://intake:8080/signals",True)))[0]["data"]["vector.yaml"])
' > "$TEMP_DIR/vector.yaml"
docker run -d --name "$RUN-intake" --network "$RUN" --network-alias intake \
  -e TEST_DATABASE_URL=postgresql://admission@pg/admission -e ADMISSION_AUTH_KEY=synthetic-local-proof-key-not-a-credential \
  -v "$BUNDLE:/work:ro" -w /work namespace-alert-admission:local python intake_smoke_server.py >/dev/null
docker run --rm -e ADMISSION_AUTH_KEY=synthetic-local-proof-key-not-a-credential \
  -v "$TEMP_DIR/vector.yaml:/etc/vector/vector.yaml:ro" timberio/vector:0.45.0-debian \
  validate --skip-healthchecks --config-yaml /etc/vector/vector.yaml
docker run -d --name "$RUN-vector" --network "$RUN" --network-alias vector \
  -e ADMISSION_AUTH_KEY=synthetic-local-proof-key-not-a-credential \
  -v "$TEMP_DIR/vector.yaml:/etc/vector/vector.yaml:ro" timberio/vector:0.45.0-debian \
  --config /etc/vector/vector.yaml >/dev/null
sleep 2
docker run "${COMMON[@]}" namespace-alert-admission:local python vector_smoke.py

docker run -d --name "$RUN-kafka" --network "$RUN" --network-alias kafka \
  -e KAFKA_NODE_ID=1 -e KAFKA_PROCESS_ROLES=broker,controller \
  -e KAFKA_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092 \
  -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT \
  -e KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER \
  -e KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT \
  -e KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka:9093 \
  -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
  -e KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1 \
  -e KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1 \
  apache/kafka-native:3.9.1 >/dev/null
docker run "${COMMON[@]}" -e CONFLUENT_BOOTSTRAP=kafka:9092 namespace-alert-admission:local python -c '
import time
from confluent_kafka.admin import AdminClient
for attempt in range(30):
 try:
  AdminClient({"bootstrap.servers":"kafka:9092"}).list_topics(timeout=2)
  break
 except Exception:
  time.sleep(1)
else:
 raise RuntimeError("disposable broker not ready")
'
docker run "${COMMON[@]}" -e CONFLUENT_BOOTSTRAP=kafka:9092 namespace-alert-admission:local python kafka_smoke.py

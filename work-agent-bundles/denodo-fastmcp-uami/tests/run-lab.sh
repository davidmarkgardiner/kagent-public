#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
REPO=$(cd "$ROOT/../.." && pwd)
JDK_BIN=/opt/homebrew/opt/openjdk/bin
if [[ ! -x "$JDK_BIN/javac" ]]; then
  JDK_BIN=$(dirname "$(command -v javac)")
fi
TEMP_DIR=$(mktemp -d)
DENODO_LAB_CONTAINER=""
trap 'if [[ -n "$DENODO_LAB_CONTAINER" ]]; then docker stop "$DENODO_LAB_CONTAINER" >/dev/null 2>&1 || true; fi; rm -rf "$TEMP_DIR"' EXIT

"$JDK_BIN/javac" --release 17 -d "$TEMP_DIR/classes" \
  "$ROOT/tests/src/com/denodo/vdp/jdbc/Driver.java"
"$JDK_BIN/jar" cf "$ROOT/tests/fixture-driver.jar" -C "$TEMP_DIR/classes" .
docker build -q -t denodo-fastmcp-uami:lab "$ROOT/adapter" >/dev/null
cp "$ROOT/tests/fixture-driver.jar" "$TEMP_DIR/denodo-vdp-jdbcdriver.jar"
docker build -q --build-arg BASE_IMAGE=denodo-fastmcp-uami:lab \
  -f "$ROOT/deploy/Dockerfile.with-driver" \
  -t denodo-fastmcp-uami:synthetic-driver "$TEMP_DIR" >/dev/null
docker run --rm --entrypoint python \
  -v "$ROOT/tests:/tests:ro" \
  -e DENODO_JDBC_JAR=/opt/denodo/denodo-vdp-jdbcdriver.jar \
  denodo-fastmcp-uami:synthetic-driver \
  -m unittest discover -s /tests -p 'test_*.py' -v

DENODO_LAB_CONTAINER=$(docker run --rm -d --entrypoint python \
  -v "$ROOT/tests:/tests:ro" \
  -e DENODO_JDBC_JAR=/opt/denodo/denodo-vdp-jdbcdriver.jar \
  denodo-fastmcp-uami:synthetic-driver /tests/serve_fixture.py)
sleep 2
docker exec "$DENODO_LAB_CONTAINER" python /tests/http_probe.py

"$REPO/scripts/public-safe-scan.sh" "$ROOT" --strict
echo DENODO_FASTMCP_LAB_CONTRACT_PASS

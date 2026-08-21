#!/usr/bin/env bash
# smoke-helpers.sh — offline smoke test for the shared helper scripts.
#
# Mirrors the pattern of agents/skills/kagent-namespace-agent/tests/smoke-test.sh:
# no cluster or network access required. Exercises argument validation, help
# output, offline code paths, and the negative cases (bad input must fail).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1" >&2; exit 1; }

expect_rc() { # rc_expected description command...
  local expected="$1" desc="$2"
  shift 2
  local rc=0
  "$@" >/dev/null 2>&1 || rc=$?
  [[ "$rc" -eq "$expected" ]] || fail "$desc (rc=$rc, expected $expected)"
  pass "$desc"
}

# ---- bash syntax of every shipped helper -----------------------------------
for script in \
  "$ROOT/scripts/kagent-a2a-invoke.sh" \
  "$ROOT/scripts/kagent-verify-agent.sh" \
  "$ROOT/scripts/kagent-e2e-fault-test.sh" \
  "$ROOT/scripts/public-safe-scan.sh" \
  "$ROOT/scripts/check-skill-refs.sh" \
  "$ROOT/agents/skills/fleet-selector/scripts/select-clusters.sh" \
  "$ROOT/agents/skills/aks-specialist/scripts/aks-cert-check.sh"; do
  bash -n "$script" || fail "bash -n $script"
  pass "syntax $(basename "$script")"
done

# ---- kagent-a2a-invoke.sh ---------------------------------------------------
expect_rc 0 "a2a-invoke --help" "$ROOT/scripts/kagent-a2a-invoke.sh" --help
expect_rc 3 "a2a-invoke rejects missing --agent" "$ROOT/scripts/kagent-a2a-invoke.sh" --text hi
expect_rc 3 "a2a-invoke rejects missing --text" "$ROOT/scripts/kagent-a2a-invoke.sh" --agent x
expect_rc 3 "a2a-invoke rejects absent payload file" \
  "$ROOT/scripts/kagent-a2a-invoke.sh" --agent x --payload-file "$TMP/nope.json"
expect_rc 3 "a2a-invoke fails fast on unreachable --url" \
  "$ROOT/scripts/kagent-a2a-invoke.sh" --agent x --text hi --url http://127.0.0.1:1 --timeout 2

# Capture the generated default request without making a network call. This
# protects the A2A wire contract: a message needs a kind and unique messageId,
# not only a text part.
mkdir -p "$TMP/fake-bin"
cat > "$TMP/fake-bin/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out=""
data=""
printf '%s\n' "$@" > "$FAKE_CURL_ARGS"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    -d) data="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf '%s' "$data" > "$FAKE_CURL_CAPTURE"
if [[ -n "${FAKE_CURL_BODY:-}" ]]; then
  printf '%s' "$FAKE_CURL_BODY" > "$out"
else
  printf '%s' '{"jsonrpc":"2.0","result":{"status":{"state":"completed"},"artifacts":[{"parts":[{"kind":"text","text":"fixture-ok"}]}]}}' > "$out"
fi
printf '200'
EOF
chmod +x "$TMP/fake-bin/curl"
FAKE_CURL_CAPTURE="$TMP/a2a-request.json" FAKE_CURL_ARGS="$TMP/a2a-request.args" PATH="$TMP/fake-bin:$PATH" \
  "$ROOT/scripts/kagent-a2a-invoke.sh" --agent fixture --text hello \
  --url http://fixture.invalid --sandbox --context-id fixture-context --raw >/dev/null \
  || fail "a2a-invoke accepts a complete fixture response"
jq -e '
  .jsonrpc == "2.0"
  and .method == "message/send"
  and .params.message.kind == "message"
  and (.params.message.messageId | type == "string" and length > 0)
  and .params.message.contextId == "fixture-context"
  and .params.message.parts == [{"kind":"text","text":"hello"}]
' "$TMP/a2a-request.json" >/dev/null \
  || fail "a2a-invoke emits the complete default A2A envelope"
grep -q '/api/a2a-sandboxes/kagent/fixture/' "$TMP/a2a-request.args" \
  || fail "a2a-invoke selects the SandboxAgent route"
pass "a2a-invoke emits the complete default A2A envelope"

# A controller can return a completed task without result.artifacts while the
# final assistant message remains in result.history. The helper must surface
# that terminal text, not mistakenly print tool-call payloads or fail empty.
FAKE_CURL_BODY='{"jsonrpc":"2.0","result":{"status":{"state":"completed"},"history":[{"role":"agent","parts":[{"kind":"data","data":{"name":"read_records"}}]},{"role":"agent","parts":[{"kind":"text","text":"<think>internal chain of thought</think>\n\nhistory-final-ok"}]}]}}' \
  FAKE_CURL_CAPTURE="$TMP/a2a-history-request.json" FAKE_CURL_ARGS="$TMP/a2a-history-request.args" PATH="$TMP/fake-bin:$PATH" "$ROOT/scripts/kagent-a2a-invoke.sh" --agent fixture --text hello \
  --url http://fixture.invalid --json > "$TMP/a2a-history-fallback.json" \
  || fail "a2a-invoke accepts a history-only terminal response"
jq -e '.text == "history-final-ok" and .reply_source == "history-fallback"' "$TMP/a2a-history-fallback.json" >/dev/null \
  || fail "a2a-invoke extracts final text from agent history"
pass "a2a-invoke extracts final text from agent history"

# ---- kagent-verify-agent.sh -------------------------------------------------
expect_rc 0 "verify-agent --help" "$ROOT/scripts/kagent-verify-agent.sh" --help
expect_rc 1 "verify-agent rejects missing --agent" "$ROOT/scripts/kagent-verify-agent.sh"

# ---- kagent-e2e-fault-test.sh -----------------------------------------------
expect_rc 0 "e2e-fault-test --help" "$ROOT/scripts/kagent-e2e-fault-test.sh" --help
expect_rc 1 "e2e-fault-test rejects missing --namespace" "$ROOT/scripts/kagent-e2e-fault-test.sh"
expect_rc 1 "e2e-fault-test refuses --skip-precheck without --force" \
  "$ROOT/scripts/kagent-e2e-fault-test.sh" --namespace test-ns --skip-precheck

# ---- public-safe-scan.sh ----------------------------------------------------
mkdir -p "$TMP/scan"
echo "clean public content" > "$TMP/scan/ok.md"
"$ROOT/scripts/public-safe-scan.sh" "$TMP/scan" >/dev/null || fail "public-safe-scan clean dir"
pass "public-safe-scan clean dir"

echo "PRIVATE-TOKEN: abc123" > "$TMP/scan/leak.md"
expect_rc 1 "public-safe-scan detects a leak" "$ROOT/scripts/public-safe-scan.sh" "$TMP/scan"
JSON_LINE=$("$ROOT/scripts/public-safe-scan.sh" "$TMP/scan" --json || true)
echo "$JSON_LINE" | grep -q '"clean":false' \
  || fail "public-safe-scan --json reports clean:false"
pass "public-safe-scan --json reports clean:false"

echo "leak.md" > "$TMP/allow.txt"
expect_rc 0 "public-safe-scan honours --allowlist" \
  "$ROOT/scripts/public-safe-scan.sh" "$TMP/scan" --allowlist "$TMP/allow.txt"

# ---- validate-agent-cr.py ---------------------------------------------------
cat > "$TMP/good-agent.yaml" <<'EOF'
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: payments-triage-agent
  namespace: kagent
  labels:
    platform.com/team: payments
    platform.com/type: triage
spec:
  description: Triage agent for the payments namespace
  type: Declarative
  declarative:
    a2aConfig:
      skills:
        - id: payments-diagnostics
          name: Payments Diagnostics
          description: Diagnose payments namespace issues
    modelConfig: default-model-config
    systemMessage: |
      CRITICAL: always use exact namespace 'payments' when investigating.
    tools:
      - mcpServer:
          apiGroup: kagent.dev
          kind: RemoteMCPServer
          name: kagent-tool-server
          toolNames:
            - k8s_get_resources
            - k8s_get_events
        type: McpServer
EOF
python3 "$ROOT/scripts/validate-agent-cr.py" "$TMP/good-agent.yaml" >/dev/null \
  || fail "validate-agent-cr passes a valid triage agent"
pass "validate-agent-cr passes a valid triage agent"

sed 's/k8s_get_events/k8s_delete_resource/' "$TMP/good-agent.yaml" > "$TMP/bad-agent.yaml"
expect_rc 1 "validate-agent-cr fails a triage agent with write tools" \
  python3 "$ROOT/scripts/validate-agent-cr.py" "$TMP/bad-agent.yaml"

# ---- select-clusters.sh -----------------------------------------------------
cat > "$TMP/inventory.json" <<'EOF'
[
  {"name": "dev-a", "tier": "dev", "labels": {"reliability.platform/chaos-optin": "true"}, "windows": []},
  {"name": "dev-b", "tier": "dev", "labels": {"reliability.platform/chaos-optin": "true"}, "windows": []},
  {"name": "dev-c", "tier": "dev", "labels": {"reliability.platform/chaos-optin": "true"}, "windows": ["blackout"]},
  {"name": "dev-d", "tier": "dev", "labels": {}, "windows": []},
  {"name": "prod-a", "tier": "prod", "labels": {"reliability.platform/chaos-optin": "true"}, "windows": []}
]
EOF
SELECT="$ROOT/agents/skills/fleet-selector/scripts/select-clusters.sh"
OUT=$("$SELECT" --tier dev --count 2 --inventory "$TMP/inventory.json" --seed 42)
echo "$OUT" | grep -q "CLUSTER_SELECTION_RECORDED: yes" || fail "select-clusters records a selection"
echo "$OUT" | grep -q "CANDIDATE_POOL: 2" || fail "select-clusters pool excludes blackout + non-opt-in"
OUT2=$("$SELECT" --tier dev --count 2 --inventory "$TMP/inventory.json" --seed 42)
[[ "$OUT" == "$OUT2" ]] || fail "select-clusters is deterministic for a fixed seed"
pass "select-clusters selection recorded, filtered, deterministic"

expect_rc 2 "select-clusters refuses prod tier" \
  "$SELECT" --tier prod --count 1 --inventory "$TMP/inventory.json"
expect_rc 2 "select-clusters refuses count above cap" \
  "$SELECT" --tier dev --count 99 --inventory "$TMP/inventory.json"

# ---- check-skill-refs.sh ----------------------------------------------------
# Run against the real repo: after the reference-rot fixes this must be clean.
"$ROOT/scripts/check-skill-refs.sh" --quiet || fail "check-skill-refs finds rot in the repo"
pass "check-skill-refs clean on current tree"

echo
echo "helper smoke test passed"

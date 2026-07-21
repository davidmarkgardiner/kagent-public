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

#!/usr/bin/env bash
# Offline tests for original modes and exact JSON round-trips of quote,
# backslash, Unicode, newline, tab, carriage return, and form feed paths.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LINT="$ROOT/scripts/lint-yaml.sh"
BROKEN="$ROOT/k8s/_lint_yaml_json_test_broken.yaml"

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1" >&2; exit 1; }

# Hard 60s timeout; preserve ordinary non-zero exits for assertions.
bounded() {
  local rc desc=$1
  shift
  if python3 -c '
import subprocess, sys
try:
    completed = subprocess.run(sys.argv[1:], timeout=60)
except subprocess.TimeoutExpired:
    raise SystemExit(124)
raise SystemExit(completed.returncode)
' "$@"; then
    return 0
  else
    rc=$?
    [[ "$rc" -eq 124 ]] && fail "$desc: timed out after 60s"
    return "$rc"
  fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP" "$BROKEN"' EXIT
bounded "lint-yaml.sh syntax check" bash -n "$LINT"

bounded "lint-yaml --json on real repo" bash "$LINT" --json \
  >"$TMP/ok.json" 2>"$TMP/ok.err"
[[ "$(wc -l <"$TMP/ok.json")" -eq 1 ]] || fail "--json emits exactly one line"
[[ ! -s "$TMP/ok.err" ]]               || fail "--json leaves stderr empty on success"
grep -q '"checked":7'     "$TMP/ok.json" || fail "--json reports checked=7"
grep -q '"failed":0'      "$TMP/ok.json" || fail "--json reports failed=0"
grep -q '"failures":\[\]' "$TMP/ok.json" || fail "--json reports failures=[]"
bounded "real-repo json.load" python3 -c \
  'import json,sys; json.load(open(sys.argv[1]))' "$TMP/ok.json"
pass "--json real repo: checked=7 failed=0 failures=[]"

bounded "lint-yaml default mode" bash "$LINT" >"$TMP/default.txt" 2>/dev/null
[[ "$(wc -l <"$TMP/default.txt")" -eq 8 ]] || fail "default emits 8 lines"
grep -q '^7 file(s) checked, 0 failed$' "$TMP/default.txt" || fail "default ends with summary line"
pass "default: 8 lines ending in '7 file(s) checked, 0 failed'"

bounded "lint-yaml --quiet" bash "$LINT" --quiet >"$TMP/quiet.txt" 2>/dev/null
[[ "$(wc -l <"$TMP/quiet.txt")" -eq 1 ]] || fail "--quiet emits 1 line"
grep -q '^7 file(s) checked, 0 failed$' "$TMP/quiet.txt" || fail "--quiet prints the summary line"
pass "--quiet: 1 summary line"

set +e
bounded "lint-yaml unknown option" bash "$LINT" --bogus \
  >"$TMP/bogus.out" 2>"$TMP/bogus.err"
bogus_rc=$?
set -e
[[ "$bogus_rc" -eq 2 ]] || fail "unknown option exits 2 (rc=$bogus_rc)"
grep -q 'unknown option: --bogus' "$TMP/bogus.err" \
  || fail "unknown option diagnostic on stderr"
[[ ! -s "$TMP/bogus.out" ]] || fail "unknown option leaves stdout empty"
pass "unknown option: exit 2, diagnostic on stderr"

BROKEN_YAML='apiVersion: v1
kind: ConfigMap
metadata:
  name: broken
data:
  bad: [unterminated
'
write_broken() { printf '%s' "$BROKEN_YAML" > "$BROKEN"; }
BAD_REL='k8s/_lint_yaml_json_test_broken.yaml'

write_broken
set +e
bounded "lint-yaml --json on broken tree" bash "$LINT" --json \
  >"$TMP/broken.json" 2>"$TMP/broken.err"
json_rc=$?
set -e
rm -f "$BROKEN"
[[ "$json_rc" -ne 0 ]] || fail "--json exit on broken tree (rc=$json_rc)"
[[ "$(wc -l <"$TMP/broken.json")" -eq 1 ]] || fail "--json broken tree emits 1 line"
[[ ! -s "$TMP/broken.err" ]]                || fail "--json broken tree leaves stderr empty"
grep -q "\"failures\":\[\"$BAD_REL\"\]" "$TMP/broken.json" || fail "--json broken tree reports the broken path"
grep -q '"failed":1'  "$TMP/broken.json" || fail "--json broken tree reports failed=1"
grep -q '"checked":8' "$TMP/broken.json" || fail "--json broken tree reports checked=8"
bounded "broken-tree json.load" python3 -c \
  'import json,sys; d=json.load(open(sys.argv[1])); assert d["checked"]==8 and d["failed"]==1 and d["failures"]==["k8s/_lint_yaml_json_test_broken.yaml"]' \
  "$TMP/broken.json"
pass "--json broken tree: failures=[$BAD_REL] failed=1 checked=8"

write_broken
set +e
bounded "lint-yaml default on broken tree" bash "$LINT" >"$TMP/defb.txt" 2>/dev/null
defb_rc=$?
set -e
rm -f "$BROKEN"
[[ "$defb_rc" -ne 0 ]] || fail "default exit on broken tree"
grep -q "^FAIL $BAD_REL$" "$TMP/defb.txt" || fail "default on broken tree prints FAIL for the broken file"
pass "default broken tree: FAIL line + non-zero exit"

write_broken
set +e
bounded "lint-yaml --quiet on broken tree" bash "$LINT" --quiet \
  >"$TMP/qb.txt" 2>/dev/null
qb_rc=$?
set -e
rm -f "$BROKEN"
[[ "$qb_rc" -ne 0 ]] || fail "--quiet exit on broken tree"
[[ "$(wc -l <"$TMP/qb.txt")" -eq 2 ]] || fail "--quiet broken tree emits failure and summary lines"
grep -q "^FAIL $BAD_REL$" "$TMP/qb.txt" || fail "--quiet broken tree prints the failure line"
grep -q '^8 file(s) checked, 1 failed$' "$TMP/qb.txt" || fail "--quiet broken tree prints the summary line"
pass "--quiet broken tree: failure and summary lines"

# A scratch tree carries hostile characters in failing relative paths.
SCRATCH="$TMP/scratch"
mkdir -p "$SCRATCH/scripts" "$SCRATCH/k8s"
cp "$LINT" "$SCRATCH/scripts/lint-yaml.sh"
chmod +x "$SCRATCH/scripts/lint-yaml.sh"
printf 'apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: good\ndata:\n  k: v\n' \
  > "$SCRATCH/k8s/good.yaml"

bounded "build hostile-byte scratch tree" python3 - "$SCRATCH" <<'PYEOF'
import os, sys
k8s = os.path.join(sys.argv[1], "k8s")
bad = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: broken\ndata:\n  bad: [unterminated\n"
for name in ('has"quote', 'has\\back', 'has\u03bbuni', 'has\nlf',
             'has\ttab', 'has\rcr', 'has\x0cff'):
    d = os.path.join(k8s, name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "broken.yaml"), "w", encoding="utf-8").write(bad)
PYEOF

set +e
bounded "lint-yaml --json on hostile-byte tree" bash \
  "$SCRATCH/scripts/lint-yaml.sh" --json \
  >"$TMP/hostile.json" 2>"$TMP/hostile.err"
hostile_rc=$?
set -e
[[ "$hostile_rc" -ne 0 ]] || fail "--json exit on hostile-byte tree"
[[ "$(wc -l <"$TMP/hostile.json")" -eq 1 ]] || fail "--json hostile emits 1 line"
[[ ! -s "$TMP/hostile.err" ]]                || fail "--json hostile leaves stderr empty"

bounded "hostile-byte tree json.load" python3 - "$TMP/hostile.json" <<'PYEOF'
import json, sys
data = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert isinstance(data, dict)
assert data["checked"] == 1 + len(data["failures"])
assert data["failed"]  ==     len(data["failures"])
expected = [
    "k8s/has" + "\t"   + "tab/broken.yaml",
    "k8s/has" + "\n"   + "lf/broken.yaml",
    "k8s/has" + "\x0c" + "ff/broken.yaml",
    "k8s/has" + "\r"   + "cr/broken.yaml",
    "k8s/has" + '"'    + "quote/broken.yaml",
    "k8s/has" + "\\"   + "back/broken.yaml",
    "k8s/has" + "\u03bb"     + "uni/broken.yaml",
]
got = data["failures"]
missing = [p for p in expected if p not in got]
extra   = [p for p in got      if p not in expected]
assert not missing, f"missing: {missing!r}"
assert not extra,   f"unexpected: {extra!r}"
assert "k8s/good.yaml" not in got, "good baseline leaked"
print(f"OK: {len(got)} hostile cases round-tripped byte-exact")
PYEOF
pass "--json hostile-byte tree: every control/quote/backslash/Unicode filename parses and round-trips byte-exact"

echo
echo "lint-yaml json test passed"

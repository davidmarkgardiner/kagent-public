#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

pass() { printf 'PASS %s\n' "$*"; }
warn() { printf 'WARN %s\n' "$*"; }
fail() { printf 'FAIL %s\n' "$*" >&2; exit 1; }

section() {
  printf '\n== %s ==\n' "$*"
}

section "Kagent triage v2 handoff verifier"
printf 'repo: %s\n' "${ROOT}"
printf 'mode: local/static; no cluster mutation\n'

section "Required handoff files"
required_files=(
  README.md
  WORK-ZIP-AGENT-HANDOFF.md
  WORK-KAGENT-TRIAGE-V2-FRONT-SHEET.md
  WORK-KAGENT-TRIAGE-V2-WORK-IMPLEMENTATION-CHECKLIST.html
  WORK-KAGENT-TRIAGE-V2-WORK-AGENT-CHECKLIST.md
  WORK-KAGENT-TRIAGE-V2-ASTHERI-SRE-WALKTHROUGH.md
  WORK-KAGENT-TRIAGE-V2-ASTHERI-SRE-REHEARSAL.md
  WORK-KAGENT-TRIAGE-V2-SRE-FIRST-CONTACT.html
  WORK-KAGENT-TRIAGE-V2-KB-QUERYDOC-PROOF.md
  demos/kb-gitlab-mcp-update/scripts/verify-demo.sh
  demos/sre-first-contact/scripts/verify-demo.sh
  demos/byo-agent-showcase/scripts/verify-demo.sh
)

for path in "${required_files[@]}"; do
  [[ -f "${path}" ]] || fail "missing ${path}"
  pass "found ${path}"
done

section "HTML parse"
python3 -m html.parser \
  WORK-KAGENT-TRIAGE-V2-WORK-IMPLEMENTATION-CHECKLIST.html \
  WORK-KAGENT-TRIAGE-V2-SRE-FIRST-CONTACT.html \
  WORK-KAGENT-TRIAGE-V2-SRE-WORKFLOW.html \
  WORK-KAGENT-TRIAGE-V2-PROOF-BOARD.html \
  index.html
pass "HTML artifacts parse"

section "SRE first-contact demo"
bash demos/sre-first-contact/scripts/verify-demo.sh
pass "SRE first-contact verifier passed"

section "KB GitLab MCP update demo"
bash demos/kb-gitlab-mcp-update/scripts/verify-demo.sh
pass "KB GitLab MCP update verifier passed"

section "BYO-agent showcase"
bash demos/byo-agent-showcase/scripts/verify-demo.sh
pass "BYO-agent verifier passed"

section "Chaos reliability contract"
python3 chaos/reliability/scripts/validate-reliability-configs.py \
  demos/sre-first-contact/chaos/checkout-api-pod-delete.chaostest.yaml
pass "first-contact ChaosTest validates"

section "doc2vec/querydoc static package"
if [[ -x ai-platform/kagent-knowledge-base/scripts/validate.sh ]]; then
  (
    cd ai-platform/kagent-knowledge-base
    ./scripts/validate.sh
  )
  pass "querydoc static package validates"
else
  warn "querydoc validate script missing or not executable"
fi

section "JSON artifacts"
if command -v jq >/dev/null 2>&1; then
  jq empty \
    observability/agent-evals/grafana/kagent-fleet-overview-dashboard.json \
    observability/agent-evals/results/sample/lifecycle/chaos-pod-delete-below-threshold.lifecycle-run.json \
    observability/agent-evals/results/sample/lifecycle/chaos-pod-delete.sample-chaos-pod-delete-below-threshold.json
  pass "JSON artifacts parse"
else
  warn "jq not installed; skipped JSON parse"
fi

section "Review-manager below-threshold proof"
tmpdir="$(mktemp -d /tmp/kagent-v2-review-manager-proof.XXXXXX)"
set +e
PYTHONPATH=observability/agent-evals/scripts \
python3 observability/agent-evals/scripts/score-lifecycle-run.py \
  --case observability/agent-evals/lifecycle-cases/chaos-pod-delete.yaml \
  --run observability/agent-evals/results/sample/lifecycle/chaos-pod-delete-below-threshold.lifecycle-run.json \
  --output-dir "${tmpdir}"
score_code=$?
set -e
if [[ "${score_code}" -ne 1 ]]; then
  fail "expected below-threshold scorer exit 1, got ${score_code}"
fi
if command -v jq >/dev/null 2>&1; then
  jq -r '"REVIEW_MANAGER_PROOF score=\(.score) passed=\(.passed) hard_failures=\(.hard_failures | length)"' \
    "${tmpdir}/chaos-pod-delete.sample-chaos-pod-delete-below-threshold.json"
fi
rm -rf "${tmpdir}"
pass "below-threshold review-manager proof fails as expected"

section "HITL mock lint"
if command -v argo >/dev/null 2>&1; then
  argo lint --offline --kinds=workflows platform/teams-hitl/mock-bot/test-approval-workflow.yaml
  pass "HITL mock workflow lints"
else
  warn "argo CLI not installed; skipped HITL mock lint"
fi

section "Public-safety scan"
if command -v rg >/dev/null 2>&1; then
  set +e
  rg -n -i '(bearer|token=|password|secret:|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|10\.[0-9]{1,3}\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)' \
    WORK-KAGENT-TRIAGE-V2-*.md \
    WORK-KAGENT-TRIAGE-V2-*.html \
    README.md \
    WORK-ZIP-AGENT-HANDOFF.md \
    index.html \
    demos/kb-gitlab-mcp-update \
    demos/sre-first-contact \
    demos/byo-agent-showcase \
    > /tmp/kagent-v2-safety-scan.txt
  scan_code=$?
  set -e
  if [[ "${scan_code}" -eq 0 ]]; then
    if grep -v 'WORK-ZIP-AGENT-HANDOFF.md:.*rg -n' /tmp/kagent-v2-safety-scan.txt \
      | grep -v 'demos/kb-gitlab-mcp-update/scripts/verify-demo.sh:.*Bearer' \
      >/tmp/kagent-v2-safety-scan.filtered; then
      cat /tmp/kagent-v2-safety-scan.filtered
      fail "public-safety scan found non-allowlisted hits"
    fi
    pass "public-safety scan only found allowlisted regex example"
  else
    pass "public-safety scan found no hits"
  fi
else
  warn "rg not installed; skipped public-safety scan"
fi

section "Verifier summary"
pass "Kagent triage v2 handoff package is locally consistent"
printf 'NEXT: work agent must still prove live work-lab Grafana MCP, GitLab MCP, querydoc, A2A, HITL, chaos, eval, and reporting evidence.\n'

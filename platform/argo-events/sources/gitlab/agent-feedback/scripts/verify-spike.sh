#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
validator="$root_dir/scripts/validate-feedback.py"
fixtures="$root_dir/fixtures"

accepted="$(python3 "$validator" "$(<"$fixtures/accepted-note.json")" alice platform-agent)"
test "$(jq -r .accepted <<<"$accepted")" = true
test "$(jq -r .action <<<"$accepted")" = feedback
rejected="$(python3 "$validator" "$(<"$fixtures/rejected-unmentioned-note.json")" alice platform-agent)"
test "$(jq -r .accepted <<<"$rejected")" = false
test "$(jq -r .reason <<<"$rejected")" = agent_not_mentioned

context="$(python3 "$root_dir/scripts/hydrate-feedback-context.py" "$(<"$fixtures/issue-context.json")" "$(<"$fixtures/issue-notes.json")" 'revise the plan' 10 "$(<"$fixtures/run-state.json")")"
test "$(jq -r '.correlation.agent_run_id' <<<"$context")" = run-abc-123
test "$(jq -r '.correlation.run_state.summary' <<<"$context")" = 'Original agent investigation'
test "$(jq -r '.trigger.feedback' <<<"$context")" = 'revise the plan'
test "$(jq -r '.recent_notes_newest_first | length' <<<"$context")" = 2

template="$root_dir/feedback-workflow-template.yaml"
grep -q 'messageId:\$message_id' "$template"
grep -q 'agent returned no text' "$template"
grep -q 'agent-feedback-run-' "$template"

python3 - <<'PY'
import json, subprocess
path = "platform/argo-events/sources/gitlab/agent-feedback/fixtures/accepted-note.json"
for mutate, expected in [
    (lambda p: p["user"].update(username="mallory"), "author_not_allowlisted"),
    (lambda p: p["issue"].update(labels=[]), "issue_not_waiting_for_human"),
    (lambda p: p["user"].update(username="platform-agent"), "self_authored_note"),
]:
    payload = json.load(open(path))
    mutate(payload)
    out = subprocess.check_output(["python3", "platform/argo-events/sources/gitlab/agent-feedback/scripts/validate-feedback.py", json.dumps(payload), "alice", "platform-agent"], text=True)
    assert json.loads(out)["reason"] == expected, out
PY
echo "GITLAB_AGENT_FEEDBACK_SPIKE_OK"

#!/usr/bin/env bash
set -euo pipefail

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

need glab
need jq

: "${GITLAB_PROJECT_PATH:?set GITLAB_PROJECT_PATH, for example namespace/project}"

GITLAB_HOST="${GITLAB_HOST:-gitlab.com}"
RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
TARGET_BRANCH="${GITLAB_TARGET_BRANCH:-}"
SOURCE_BRANCH="${GITLAB_SOURCE_BRANCH:-smart-triage/gitlab-mcp-demo-$RUN_ID}"
DEMO_FILE="${GITLAB_DEMO_FILE:-docs/smart-triage/gitlab-mcp-live-demo-$RUN_ID.md}"
MR_TITLE="${GITLAB_MR_TITLE:-Smart triage GitLab MCP live write demo}"

PROJECT_ENC="$(jq -nr --arg value "$GITLAB_PROJECT_PATH" '$value|@uri')"

echo "== GitLab MR live-write demo =="
echo "Host: $GITLAB_HOST"
echo "Project: $GITLAB_PROJECT_PATH"
echo "Source branch: $SOURCE_BRANCH"
echo "Demo file: $DEMO_FILE"

glab auth status --hostname "$GITLAB_HOST" >/dev/null

PROJECT_JSON="$(glab api --hostname "$GITLAB_HOST" "projects/$PROJECT_ENC")"
PROJECT_ID="$(printf '%s' "$PROJECT_JSON" | jq -r '.id')"
DEFAULT_BRANCH="$(printf '%s' "$PROJECT_JSON" | jq -r '.default_branch // "main"')"
TARGET_BRANCH="${TARGET_BRANCH:-$DEFAULT_BRANCH}"

if [[ "$PROJECT_ID" == "null" || -z "$PROJECT_ID" ]]; then
  echo "unable to resolve GitLab project: $GITLAB_PROJECT_PATH" >&2
  exit 1
fi

echo "Project ID: $PROJECT_ID"
echo "Target branch: $TARGET_BRANCH"

echo "-- creating source branch"
glab api --hostname "$GITLAB_HOST" \
  --method POST "projects/$PROJECT_ENC/repository/branches" \
  --field branch="$SOURCE_BRANCH" \
  --field ref="$TARGET_BRANCH" >/tmp/gitlab-mr-demo-branch.json

cat > /tmp/gitlab-mr-demo-content-v1.md <<EOF
# Smart Triage GitLab MCP Live Demo

Run ID: \`$RUN_ID\`

This file was created by the smart-triage GitLab MR demo to prove the GitOps
write path can create a branch, commit a file, open a merge request, and post a
follow-up update.

Proof markers:

- \`GITLAB_BRANCH: created\`
- \`GITLAB_FILE: created\`
- \`GITLAB_MR: pending\`

Safety posture:

- Non-production demo branch.
- No cluster mutation.
- No secrets or private endpoints committed.
EOF

echo "-- committing new demo file"
jq -n \
  --arg branch "$SOURCE_BRANCH" \
  --arg message "Add smart-triage GitLab MCP live demo evidence" \
  --arg file_path "$DEMO_FILE" \
  --rawfile content /tmp/gitlab-mr-demo-content-v1.md \
  '{
    branch: $branch,
    commit_message: $message,
    actions: [
      {
        action: "create",
        file_path: $file_path,
        content: $content
      }
    ]
  }' >/tmp/gitlab-mr-demo-create-commit.json

glab api --hostname "$GITLAB_HOST" \
  --method POST "projects/$PROJECT_ENC/repository/commits" \
  --input /tmp/gitlab-mr-demo-create-commit.json >/tmp/gitlab-mr-demo-create-response.json

cat > /tmp/gitlab-mr-demo-content-v2.md <<EOF
# Smart Triage GitLab MCP Live Demo

Run ID: \`$RUN_ID\`

This file was created and then updated by the smart-triage GitLab MR demo.
The second commit proves the branch can be modified after the initial write,
which is the behavior needed for an agent to iterate on a GitOps remediation MR.

Proof markers:

- \`GITLAB_BRANCH: created\`
- \`GITLAB_FILE: created\`
- \`GITLAB_FILE: updated\`
- \`GITLAB_MR: pending\`

Safety posture:

- Non-production demo branch.
- No cluster mutation.
- No secrets or private endpoints committed.
EOF

echo "-- committing update to same demo file"
jq -n \
  --arg branch "$SOURCE_BRANCH" \
  --arg message "Update smart-triage GitLab MCP live demo evidence" \
  --arg file_path "$DEMO_FILE" \
  --rawfile content /tmp/gitlab-mr-demo-content-v2.md \
  '{
    branch: $branch,
    commit_message: $message,
    actions: [
      {
        action: "update",
        file_path: $file_path,
        content: $content
      }
    ]
  }' >/tmp/gitlab-mr-demo-update-commit.json

glab api --hostname "$GITLAB_HOST" \
  --method POST "projects/$PROJECT_ENC/repository/commits" \
  --input /tmp/gitlab-mr-demo-update-commit.json >/tmp/gitlab-mr-demo-update-response.json

MR_DESCRIPTION="$(cat <<EOF
This MR demonstrates the smart-triage GitLab write path.

What happened:

- Created branch \`$SOURCE_BRANCH\`.
- Created \`$DEMO_FILE\`.
- Updated \`$DEMO_FILE\` in a second commit.
- Left a follow-up note on the MR.

This mirrors the behavior the GitOps specialist should perform after HITL:
create a feature branch, write a proposed change, iterate on that branch, and
open a reviewable MR instead of mutating a cluster directly.
EOF
)"

echo "-- opening merge request"
MR_JSON="$(glab api --hostname "$GITLAB_HOST" \
  --method POST "projects/$PROJECT_ENC/merge_requests" \
  --field source_branch="$SOURCE_BRANCH" \
  --field target_branch="$TARGET_BRANCH" \
  --field title="$MR_TITLE" \
  --field description="$MR_DESCRIPTION" \
  --field remove_source_branch=true)"

printf '%s' "$MR_JSON" >/tmp/gitlab-mr-demo-mr.json
MR_IID="$(printf '%s' "$MR_JSON" | jq -r '.iid')"
MR_WEB_URL="$(printf '%s' "$MR_JSON" | jq -r '.web_url')"

if [[ "$MR_IID" == "null" || -z "$MR_IID" ]]; then
  echo "merge request creation did not return an iid" >&2
  cat /tmp/gitlab-mr-demo-mr.json >&2
  exit 1
fi

NOTE_BODY="$(cat <<EOF
Smart-triage GitLab MCP live demo follow-up:

- \`GITLAB_BRANCH: created\`
- \`GITLAB_FILE: created\`
- \`GITLAB_FILE: updated\`
- \`GITLAB_MR: created\`

Next work integration step: replace the current dry-run GitOps specialist with
this branch/MR behavior after HITL approval.
EOF
)"

echo "-- posting MR note"
glab api --hostname "$GITLAB_HOST" \
  --method POST "projects/$PROJECT_ENC/merge_requests/$MR_IID/notes" \
  --field body="$NOTE_BODY" >/tmp/gitlab-mr-demo-note.json

echo "PASS: GitLab MR demo created"
echo "GITLAB_BRANCH: created"
echo "GITLAB_FILE: created"
echo "GITLAB_FILE: updated"
echo "GITLAB_MR: created"
echo "MR_IID: $MR_IID"
echo "MR_URL: $MR_WEB_URL"

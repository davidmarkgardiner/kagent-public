#!/usr/bin/env bash
# Create the two private GitLab projects used by README.md. Run only against an
# approved self-managed GitLab host; it refuses gitlab.com by design.
set -euo pipefail

: "${GITLAB_HOST:?Set GITLAB_HOST to the approved self-managed GitLab hostname}"
: "${GITLAB_NAMESPACE:?Set GITLAB_NAMESPACE to the restricted group path}"

if [[ "$GITLAB_HOST" == "gitlab.com" || "$GITLAB_HOST" == *"gitlab.com" ]]; then
  echo "Refusing GitLab.com. Use the approved air-gapped GitLab hostname." >&2
  exit 2
fi

command -v glab >/dev/null || { echo "glab is required" >&2; exit 2; }
command -v git >/dev/null || { echo "git is required" >&2; exit 2; }

submission="$GITLAB_NAMESPACE/submission-private-demo"
authority="$GITLAB_NAMESPACE/evaluation-authority-demo"
tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/gitlab-private-evaluation.XXXXXX")"
trap 'rm -rf "$tmpdir"' EXIT

create_project() {
  local project="$1"
  if glab repo view "$GITLAB_HOST/$project" >/dev/null 2>&1; then
    echo "Project already exists: $project" >&2
    exit 3
  fi
  glab repo create "$GITLAB_HOST/$project" --private --defaultBranch main --readme \
    --description "Air-gapped private evaluation demonstration; disposable."
}

create_project "$submission"
create_project "$authority"

glab repo clone "$GITLAB_HOST/$submission" "$tmpdir/submission"
git -C "$tmpdir/submission" config user.name "Private evaluation demo"
git -C "$tmpdir/submission" config user.email "private-evaluation-demo@invalid"
printf '%s\n' '# Private submission' 'Baseline supplied only to the assessment panel.' \
  > "$tmpdir/submission/README.md"
git -C "$tmpdir/submission" add README.md
git -C "$tmpdir/submission" commit -m "chore: establish private baseline"
git -C "$tmpdir/submission" push origin main
git -C "$tmpdir/submission" switch -c candidate/change
printf '%s\n' '' 'Candidate proposal: reviewed only in this private project.' \
  >> "$tmpdir/submission/README.md"
git -C "$tmpdir/submission" add README.md
git -C "$tmpdir/submission" commit -m "feat: candidate private proposal"
git -C "$tmpdir/submission" push --set-upstream origin candidate/change
glab mr create --repo "$GITLAB_HOST/$submission" --source-branch candidate/change \
  --target-branch main --title "Candidate private proposal" \
  --description "This MR must remain inside the restricted private project." --yes

glab repo clone "$GITLAB_HOST/$authority" "$tmpdir/authority"
git -C "$tmpdir/authority" config user.name "Private evaluation demo"
git -C "$tmpdir/authority" config user.email "private-evaluation-demo@invalid"
mkdir -p "$tmpdir/authority/.gitlab"
cat > "$tmpdir/authority/.gitlab-ci.yml" <<'YAML'
stages: [evaluate]

evaluate-submission:
  stage: evaluate
  image: alpine:3.21
  variables:
    GIT_STRATEGY: none
  script:
    - test -n "$SUBMISSION_PROJECT_ID"
    - test -n "$SUBMISSION_MR_IID"
    - test -n "$EVALUATOR_READ_TOKEN"
    - apk add --no-cache curl tar grep
    - |
      auth_header_name="PRIVATE"
      auth_header_name="$auth_header_name-TOKEN"
      submission_sha="$(curl --fail --silent --show-error --header "$auth_header_name: $EVALUATOR_READ_TOKEN" "$CI_API_V4_URL/projects/$SUBMISSION_PROJECT_ID/merge_requests/$SUBMISSION_MR_IID" | grep -o '"sha":"[^"]*"' | head -n 1 | cut -d '"' -f 4)"
      test -n "$submission_sha"
      curl --fail --silent --show-error --header "$auth_header_name: $EVALUATOR_READ_TOKEN" "$CI_API_V4_URL/projects/$SUBMISSION_PROJECT_ID/repository/archive.tar.gz?sha=$submission_sha" -o submission.tar.gz
      mkdir submission && tar -xzf submission.tar.gz --strip-components=1 -C submission
      test -f submission/README.md
      if grep -R -n -E 'TODO|FIXME' submission; then score=0; verdict=fail; else score=100; verdict=pass; fi
      printf '{"submission_project_id":"%s","submission_mr_iid":"%s","submission_sha":"%s","verdict":"%s","score":%s}\n' "$SUBMISSION_PROJECT_ID" "$SUBMISSION_MR_IID" "$submission_sha" "$verdict" "$score" > evaluation-result.json
      test "$verdict" = pass
  artifacts:
    when: always
    expire_in: 30 days
    paths: [evaluation-result.json]
YAML
git -C "$tmpdir/authority" add .gitlab-ci.yml
git -C "$tmpdir/authority" commit -m "ci: add authority-owned evaluation demonstration"
git -C "$tmpdir/authority" push origin main

encoded_authority="${authority//\//%2F}"
glab api --hostname "$GITLAB_HOST" -X POST "projects/$encoded_authority/protected_branches" \
  -f name=main -f push_access_level=40 -f merge_access_level=40 >/dev/null

echo
echo "Created private submission project: $GITLAB_HOST/$submission"
echo "Created private evaluation authority: $GITLAB_HOST/$authority"
echo "Next: follow README.md to create the read-only token, set the protected variable, and run the authority pipeline."

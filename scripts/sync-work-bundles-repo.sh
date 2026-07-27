#!/usr/bin/env bash
# Mirror the committed work-agent-bundles subtree to the sister repository.
#
# One-time setup:
#   git remote add work-bundles https://github.com/davidmarkgardiner/kagent-work-bundles.git
#
# Then, from a clean checkout on main after bundle changes have merged:
#   scripts/sync-work-bundles-repo.sh
set -euo pipefail

REMOTE="${1:-work-bundles}"
PREFIX="work-agent-bundles"

git rev-parse --is-inside-work-tree >/dev/null
if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "ERROR: remote '$REMOTE' is not configured." >&2
  echo "Add it with: git remote add $REMOTE https://github.com/davidmarkgardiner/kagent-work-bundles.git" >&2
  exit 2
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: working tree is not clean. Commit, stash, or discard unrelated changes first." >&2
  exit 2
fi

BRANCH="$(git branch --show-current)"
if [[ "$BRANCH" != "main" ]]; then
  echo "ERROR: sync only from main; current branch is '$BRANCH'." >&2
  exit 2
fi

git subtree push --prefix="$PREFIX" "$REMOTE" main
echo "SYNC_OK: $PREFIX mirrored to $REMOTE/main"

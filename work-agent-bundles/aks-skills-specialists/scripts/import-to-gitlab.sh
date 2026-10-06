#!/usr/bin/env bash
# Prepare a reviewable import commit in an existing GitLab checkout. Does not push.
set -euo pipefail
BUNDLE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
if [[ $# -ne 2 ]]; then echo 'Usage: import-to-gitlab.sh CLEAN_GITLAB_CHECKOUT RELATIVE_BUNDLE_PATH' >&2; exit 2; fi
TARGET=$1
RELATIVE=$2
[[ "$RELATIVE" != /* && "$RELATIVE" != *..* && "$RELATIVE" =~ ^[a-zA-Z0-9._/-]+$ ]] || { echo 'Invalid relative destination' >&2; exit 2; }
[[ -z $(git -C "$TARGET" status --porcelain) ]] || { echo 'Target checkout must be clean' >&2; exit 2; }
[[ ! -e "$TARGET/$RELATIVE" ]] || { echo 'Destination exists; review the update manually' >&2; exit 2; }
mkdir -p "$TARGET/$RELATIVE"
# Copy tracked source only, excluding node_modules and generated private outputs.
ROOT=$(git -C "$BUNDLE" rev-parse --show-toplevel)
PREFIX=$(git -C "$BUNDLE" rev-parse --show-prefix)
IFS=/ read -r -a PREFIX_PARTS <<< "${PREFIX%/}"
git -C "$ROOT" archive HEAD "$PREFIX" | tar -x -C "$TARGET/$RELATIVE" --strip-components="${#PREFIX_PARTS[@]}"
git -C "$TARGET" add -- "$RELATIVE"
git -C "$TARGET" commit -m 'Add reviewed AKS skills specialist bundle'
COMMIT=$(git -C "$TARGET" rev-parse HEAD)
printf 'Import commit: %s\nCreate protected tag: aks-skills-%s\nReview CI, then push this branch and tag to your GitLab skills project.\n' "$COMMIT" "${COMMIT:0:12}"

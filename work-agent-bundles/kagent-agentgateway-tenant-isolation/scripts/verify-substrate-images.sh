#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
lock="$root/platform/substrate/images.lock.tsv"
failures=0

command -v docker >/dev/null 2>&1 || { echo 'docker with buildx is required' >&2; exit 2; }
docker buildx version >/dev/null 2>&1 || { echo 'docker buildx is unavailable' >&2; exit 2; }

while IFS=$'\t' read -r component _evidence source_reference digest; do
  [[ $component == component || -z $component ]] && continue
  repository=${source_reference%@*}
  [[ $repository != "$source_reference" ]] || repository=${source_reference%:*}
  if docker buildx imagetools inspect "$repository@$digest" >/dev/null 2>&1; then
    printf 'PASS %s %s\n' "$component" "$digest"
  else
    printf 'FAIL %s could not resolve %s@%s\n' "$component" "$repository" "$digest" >&2
    failures=$((failures + 1))
  fi
done < "$lock"

(( failures == 0 )) || { echo "IMAGE_LOCK_VERIFY: FAIL ($failures image(s) unresolved)" >&2; exit 1; }
echo 'IMAGE_LOCK_VERIFY: PASS'

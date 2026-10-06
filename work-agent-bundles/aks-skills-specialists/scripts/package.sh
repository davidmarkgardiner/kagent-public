#!/usr/bin/env bash
# Export only the committed public bundle to a portable tarball.
set -euo pipefail
BUNDLE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUTPUT=${1:?Usage: package.sh ABSOLUTE_OUTPUT_TAR_GZ}
[[ "$OUTPUT" == /* ]] || { echo 'Output must be an absolute path' >&2; exit 2; }
ROOT=$(git -C "$BUNDLE" rev-parse --show-toplevel)
PREFIX=$(git -C "$BUNDLE" rev-parse --show-prefix)
git -C "$ROOT" archive --format=tar HEAD "$PREFIX" | gzip -n > "$OUTPUT"
shasum -a 256 "$OUTPUT" > "$OUTPUT.sha256"

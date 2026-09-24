#!/usr/bin/env bash
# Rebuilds the offline bundle on a connected machine, so nobody depends on a
# release asset staying available. Produces the same zip that is published at
# the runsc-asset-20260622 release.
#
#   ./make-bundle.sh [x86_64|aarch64]
set -euo pipefail
arch=${1:-x86_64}
release=20260622
case "$arch" in
  x86_64)  want=f18a948bf9c8bbb54eb998549a3a8d719a1c7de2efbe8fdd2ff0ee5fecd06f19 ;;
  aarch64) want=62eee121f8c188e347c428acc96f111568ede3be37b906046b6f28bbe2cc40c0 ;;
  *) echo "unknown arch: $arch" >&2; exit 2 ;;
esac
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
out="substrate-runsc-offline-${arch/x86_64/amd64}"
out="${out/aarch64/arm64}"
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
mkdir -p "$work/$out"
echo "==> fetching runsc ($arch, $release)"
curl -fL --proto '=https' --tlsv1.2 -o "$work/$out/runsc" \
  "https://storage.googleapis.com/gvisor/releases/release/$release/$arch/runsc"
printf '%s  runsc\n' "$want" > "$work/$out/SHA256SUMS"
( cd "$work/$out" && { command -v sha256sum >/dev/null && sha256sum -c SHA256SUMS || shasum -a 256 -c SHA256SUMS; } )
cp "$here/build.sh" "$here/Dockerfile.runsc" "$here/README.txt" "$work/$out/"
cp "$here/../preseed-daemonset.yaml" "$work/$out/"
( cd "$work" && zip -q -r "$out.zip" "$out" )
mv "$work/$out.zip" .
echo "==> wrote $out.zip"

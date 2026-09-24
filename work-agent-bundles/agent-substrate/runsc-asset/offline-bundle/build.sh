#!/usr/bin/env bash
# Verify the binary, build the image, optionally push it.
#
#   ./build.sh <registry>/gvisor/runsc:20260622 [internal-base-image]
#
# Everything here is offline except the base image pull and the push.
set -euo pipefail
tag=${1:?usage: ./build.sh <registry>/gvisor/runsc:20260622 [base-image]}
base=${2:-busybox:1.36}
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "==> verifying the binary against SHA256SUMS"
if command -v sha256sum >/dev/null; then sha256sum -c SHA256SUMS
else shasum -a 256 -c SHA256SUMS; fi

echo "==> building $tag (base: $base) for linux/amd64"
docker build --platform linux/amd64 --build-arg "BASE=$base" -t "$tag" -f Dockerfile.runsc .

echo "==> confirming the binary inside the image"
docker run --rm --platform linux/amd64 --entrypoint sh "$tag" -c 'ls -l /runsc && sha256sum /runsc'

cat <<NEXT

Built: $tag

Next:
  docker push $tag
  # then substitute placeholders in preseed-daemonset.yaml:
  #   {{INTERNAL_REGISTRY}}  (appears twice: runsc image and pause image)
  #   {{RUNSC_SHA256}}       f18a948bf9c8bbb54eb998549a3a8d719a1c7de2efbe8fdd2ff0ee5fecd06f19
  grep -n '{{' preseed-daemonset.yaml   # must print nothing before applying
  kubectl apply -f preseed-daemonset.yaml
NEXT

#!/usr/bin/env bash
set -euo pipefail

KAGENT_VERSION="${KAGENT_VERSION:-v0.9.6}"
INSTALLER_URL="https://raw.githubusercontent.com/kagent-dev/kagent/${KAGENT_VERSION}/scripts/get-kagent"
INSTALL_DIR="${HOME}/bin"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    return 1
  fi
}

need curl
need tar
need jq
need openssl

mkdir -p "$INSTALL_DIR"
export PATH="$INSTALL_DIR:$PATH"

tmp_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

installer="${tmp_dir}/get-kagent"

echo "Downloading kagent installer for ${KAGENT_VERSION}"
curl -fsSL "$INSTALLER_URL" -o "$installer"
chmod +x "$installer"

echo "Installing kagent ${KAGENT_VERSION} into ${INSTALL_DIR}"
bash "$installer" --no-sudo --version "$KAGENT_VERSION"

"${INSTALL_DIR}/kagent" version

echo
echo "For future shells, ensure ${INSTALL_DIR} is on PATH."
echo "Run: export PATH=\"${INSTALL_DIR}:\$PATH\""

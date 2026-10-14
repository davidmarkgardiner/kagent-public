#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
cd "$root"
for tool in go git helm python3; do command -v "$tool" >/dev/null; done
python3 -c 'import yaml'
mkdir -p artifacts bin receipts
helm pull oci://ghcr.io/kagent-dev/substrate/helm/substrate --version 0.4.0-alpha1 --destination artifacts
helm pull oci://ghcr.io/kagent-dev/substrate/helm/substrate-crds --version 0.4.0-alpha1 --destination artifacts
helm pull oci://ghcr.io/kagent-dev/kagent/helm/kagent --version 1.0.0-alpha8 --destination artifacts
helm pull oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds --version 1.0.0-alpha8 --destination artifacts
python3 - <<'PY'
import hashlib, json
from pathlib import Path
for name, expected in json.loads(Path('chart-lock.json').read_text()).items():
    assert hashlib.sha256((Path('artifacts') / name).read_bytes()).hexdigest() == expected, name
print('Chart archive checksums match the tested inputs')
PY
if [[ ! -d substrate-source ]]; then
  git clone --depth 1 --branch v0.4.0-alpha1 https://github.com/kagent-dev/substrate.git substrate-source
fi
test "$(git -C substrate-source rev-parse HEAD)" = c2e2e130606db615a553421b6352e47f49860870
git -C substrate-source diff --exit-code
cd substrate-source
go build -o ../bin/ate-setup ./cmd/ate-setup
go build -o ../bin/kubectl-ate ./cmd/kubectl-ate
cd "$root"
chmod +x pin-images.py
echo 'Prepared pinned helpers and charts. No cluster resources have been changed.'

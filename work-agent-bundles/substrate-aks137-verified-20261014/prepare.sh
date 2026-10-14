#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
cd "$root"
if [[ ${1:-} == --offline ]]; then
  python3 - "$root" <<'PY'
import hashlib, json, platform, shutil, sys, tarfile
from pathlib import Path
root = Path(sys.argv[1])
lock = json.loads((root / 'prerequisites-lock.json').read_text())
for row in lock['files']:
    file = root / row['path']
    if not file.is_file() or file.stat().st_size != row['bytes']:
        raise SystemExit(f'Missing or wrong-size prerequisite: {row["path"]}')
    digest = hashlib.sha256()
    with file.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    if digest.hexdigest() != row['sha256']:
        raise SystemExit(f'Prerequisite checksum mismatch: {row["path"]}')
machine = {'x86_64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}.get(platform.machine())
host = platform.system().lower() + '-' + str(machine)
if host not in lock['helperPlatforms']:
    raise SystemExit(f'No prepared helper binaries for {host}; prepare tools for the actual operator host first')
source = root / 'substrate-source'
with tarfile.open(root / 'artifacts/substrate-source.tar.gz') as archive:
    if not source.exists():
        archive.extractall(root, filter='data')
    for member in archive:
        file = root / member.name
        if member.isfile():
            if not file.is_file() or file.read_bytes() != archive.extractfile(member).read():
                raise SystemExit(f'Existing source differs from the locked source archive: {member.name}')
        elif member.issym() and (not file.is_symlink() or file.readlink().as_posix() != member.linkname):
            raise SystemExit(f'Existing source symlink differs: {member.name}')
(root / 'pin-images.py').chmod(0o755)
(root / 'bin').mkdir(exist_ok=True)
(root / 'receipts').mkdir(exist_ok=True)
for name in ['ate-setup', 'kubectl-ate']:
    shutil.copy2(root / 'artifacts/helpers' / host / name, root / 'bin' / name)
    (root / 'bin' / name).chmod(0o755)
(root / 'receipts/offline-preparation.json').write_text(json.dumps({
    'pass': True, 'host': host, 'sourceCommit': lock['sourceCommit'],
    'verifiedFiles': len(lock['files']), 'networkDownloads': False}, indent=2))
print('OFFLINE_PREREQUISITES=PASS. Verified transferred files and prepared stock helpers; no downloads or cluster mutations.')
PY
  exit 0
fi
if [[ $# != 0 ]]; then echo 'Usage: prepare.sh [--offline]' >&2; exit 2; fi
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

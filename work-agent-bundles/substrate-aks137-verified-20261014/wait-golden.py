#!/usr/bin/env python3
import argparse
import json
import subprocess
import time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--cli', required=True)
p.add_argument('--kubeconfig', required=True)
p.add_argument('--template', required=True)
p.add_argument('--atespace', default='kagent')
p.add_argument('--receipt', required=True)
a = p.parse_args()
deadline = time.monotonic() + 180
while time.monotonic() < deadline:
    run = subprocess.run([a.cli, '--kubeconfig', a.kubeconfig, 'get', 'actor-template', a.template,
                          '-a', a.atespace, '-o', 'json'], capture_output=True, text=True, timeout=30)
    if run.returncode:
        raise SystemExit(run.stderr or run.stdout)
    template = json.loads(run.stdout)
    Path(a.receipt).write_text(run.stdout)
    status = template.get('status', {}).get('goldenSnapshotStatus', {})
    if status.get('errorMessage'):
        raise SystemExit(status['errorMessage'])
    if status.get('goldenTag'):
        print('GOLDEN_READY', a.template)
        break
    time.sleep(2)
else:
    raise SystemExit('Golden snapshot did not become ready within 180 seconds')

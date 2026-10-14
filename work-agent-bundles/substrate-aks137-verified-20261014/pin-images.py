#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
import yaml

root = Path(__file__).resolve().parent
lock_path = Path(os.environ.get('PROOF_IMAGE_LOCK', str(root / 'image-lock.json')))
lock = {ref: row['pinned'] for row in json.loads(lock_path.read_text())
        for ref in [row['reference']] + row.get('aliases', [])}
def pin(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ('image', 'pauseImage', 'workerImage') and isinstance(child, str):
                value[key] = lock.get(child, child)
                if '@sha256:' not in value[key]:
                    raise SystemExit('Unpinned image; add the exact private mirror reference to PROOF_IMAGE_LOCK: ' + child)
            else:
                pin(child)
    elif isinstance(value, list):
        for child in value:
            pin(child)
items = [value for value in yaml.safe_load_all(sys.stdin) if value]
for value in items:
    pin(value)
yaml.safe_dump_all(items, sys.stdout, explicit_start=True, sort_keys=False)

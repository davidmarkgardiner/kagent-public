#!/usr/bin/env python3
import json
import sys
from pathlib import Path
import yaml

root = Path(__file__).resolve().parent
lock = {row['reference']: row['pinned'] for row in json.loads((root / 'image-lock.json').read_text())}
def pin(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ('image', 'pauseImage', 'workerImage') and isinstance(child, str):
                value[key] = lock.get(child, child)
            else:
                pin(child)
    elif isinstance(value, list):
        for child in value:
            pin(child)
items = [value for value in yaml.safe_load_all(sys.stdin) if value]
for value in items:
    pin(value)
yaml.safe_dump_all(items, sys.stdout, explicit_start=True, sort_keys=False)

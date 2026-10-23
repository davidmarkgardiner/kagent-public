#!/usr/bin/env python3
"""Render this bundle as a secret-free Kustomize directory for an OCI artifact."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


BUNDLE = Path(__file__).resolve().parents[1]
REPO = BUNDLE.parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-draft-pr', action='store_true',
                        help='Opt into the exact-scoped draft PR tool; default is read-only')
    parser.add_argument('--runtime-only', action='store_true',
                        help='Lab check without kagent CRDs; omit Agent and RemoteMCPServer')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(REPO):
        parser.error('Output must be outside the public repository')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error('Output must be an empty directory')
    if args.runtime_only and args.allow_draft_pr:
        parser.error('Runtime-only lab artifacts must be read-only')

    cmd = [sys.executable, str(BUNDLE / 'render.py'), '--config', str(args.config)]
    if not args.allow_draft_pr:
        cmd.append('--read-only')
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    objects = json.loads(result.stdout)['items']
    if args.runtime_only:
        objects = [obj for obj in objects if obj['kind'] in
                   {'Deployment', 'Service', 'NetworkPolicy'}]
    names = [obj['kind'].lower() + '.json' for obj in objects]
    if len(names) != len(set(names)):
        parser.error('Duplicate Kubernetes kind in the bundle')

    output.mkdir(parents=True, exist_ok=True)
    for name, obj in zip(names, objects):
        (output / name).write_text(json.dumps(obj, indent=2) + '\n')
    (output / 'kustomization.yaml').write_text(
        'apiVersion: kustomize.config.k8s.io/v1beta1\n'
        'kind: Kustomization\nresources:\n' + ''.join(f'- {name}\n' for name in names))
    print(f'Prepared {len(objects)} secret-free resources in {output}')


if __name__ == '__main__':
    main()

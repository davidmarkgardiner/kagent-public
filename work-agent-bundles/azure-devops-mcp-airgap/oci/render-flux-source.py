#!/usr/bin/env python3
"""Render Flux OCIRepository and Kustomization objects for a pinned artifact."""
import argparse
import json
from pathlib import Path
import re

BUNDLE = Path(__file__).resolve().parents[1]
REPO = BUNDLE.parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True, help='OCI repository URL without a tag')
    parser.add_argument('--digest', required=True, help='Registry manifest digest of the manifest artifact')
    parser.add_argument('--target-namespace', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--insecure-lab-registry', action='store_true',
                        help='Allow HTTP only for an isolated local test registry')
    args = parser.parse_args()
    if not re.fullmatch(r'oci://[a-zA-Z0-9.-]+(?::[0-9]+)?/[a-zA-Z0-9._/-]+', args.url):
        parser.error('Expected an OCI repository URL without a tag or digest')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', args.digest):
        parser.error('Expected the OCI artifact registry manifest digest')
    if not re.fullmatch(r'[a-z0-9]([-a-z0-9]*[a-z0-9])?', args.target_namespace):
        parser.error('Invalid target namespace')
    if args.output.resolve().is_relative_to(REPO):
        parser.error('Output must be outside the public repository')
    name = 'azure-devops-mcp'
    flux_namespace = 'flux-system'
    objects = [
        {'apiVersion': 'source.toolkit.fluxcd.io/v1', 'kind': 'OCIRepository',
         'metadata': {'name': name, 'namespace': flux_namespace},
         'spec': {'interval': '5m', 'url': args.url,
                  'ref': {'digest': args.digest},
                  **({'insecure': True} if args.insecure_lab_registry else {})}},
        {'apiVersion': 'kustomize.toolkit.fluxcd.io/v1', 'kind': 'Kustomization',
         'metadata': {'name': name, 'namespace': flux_namespace},
         'spec': {'interval': '5m', 'path': './', 'prune': False,
                  'targetNamespace': args.target_namespace,
                  'sourceRef': {'kind': 'OCIRepository', 'name': name}}},
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'apiVersion': 'v1', 'kind': 'List',
                                       'items': objects}, indent=2) + '\n')
    print(f'Prepared Flux source in {args.output}')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Render namespace-scoped AKS-MCP RBAC from the shared collector inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / "fox-mesh/namespaces.json"


def role_binding(namespace: str) -> dict:
    return {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "RoleBinding",
        "metadata": {
            "name": "cluster-health-investigator-read",
            "namespace": namespace,
            "labels": {"app.kubernetes.io/part-of": "cluster-health-assessment"},
        },
        "roleRef": {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "ClusterRole",
            "name": "cluster-health-investigator-namespace-read",
        },
        "subjects": [
            {
                "kind": "ServiceAccount",
                "name": "{{AKS_MCP_SERVICE_ACCOUNT_NAME}}",
                "namespace": "{{AKS_MCP_SERVICE_ACCOUNT_NAMESPACE}}",
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    namespaces = json.loads(SCOPE.read_text(encoding="utf-8"))["namespaces"]
    documents = [role_binding(namespace) for namespace in namespaces]
    args.output.write_text(
        yaml.safe_dump_all(documents, sort_keys=False, explicit_start=True),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

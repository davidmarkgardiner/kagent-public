#!/usr/bin/env python3
"""Read-only Azure readiness probe; prints no tenant, subscription or object IDs."""

import json
import subprocess
import sys


def az(*args):
    result = subprocess.run(["az", *args], text=True, capture_output=True)
    if result.returncode:
        return None
    return result.stdout


def main():
    account_raw = az("account", "show", "--output", "json")
    if account_raw is None:
        print("azure_login=unavailable")
        return 2
    account = json.loads(account_raw)
    print("azure_login=available")
    print(f"principal_type={account.get('user', {}).get('type', 'unknown')}")
    aks_raw = az("aks", "list", "--query", "length(@)", "-o", "tsv")
    print(f"aks_cluster_count={aks_raw.strip() if aks_raw is not None else 'unavailable'}")
    graph_raw = az(
        "rest", "--method", "GET", "--url",
        "https://graph.microsoft.com/v1.0/applications/microsoft.graph.agentIdentityBlueprint?$top=1",
        "--output", "json",
    )
    if graph_raw is None:
        print("graph_blueprint_read=unavailable_or_denied")
    else:
        try:
            json.loads(graph_raw)
            print("graph_blueprint_read=available")
        except json.JSONDecodeError:
            print("graph_blueprint_read=unexpected_response")
    return 0


if __name__ == "__main__":
    sys.exit(main())

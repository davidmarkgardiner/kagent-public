#!/usr/bin/env python3
"""Idempotently provision an isolated Entra Agent ID blueprint pilot.

Uses the current Azure CLI login and Microsoft Graph v1.0. Writes a private
0600 receipt outside this public repo. Does not create Azure compute or AKS.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from generate import PUBLIC_REPO


GRAPH = "https://graph.microsoft.com/v1.0"
MARKER = "kagent-public-agent-id-poc"


class ProvisionError(Exception):
    pass


def azure(*args, body=None):
    command = ["az", *args, "--output", "json", "--only-show-errors"]
    if body is not None:
        command.extend(["--headers", "Content-Type=application/json", "--body", json.dumps(body)])
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        codes = re.findall(r"(?:AADSTS\d+|Authorization_RequestDenied|Forbidden|BadRequest)", result.stderr)
        suffix = f" ({codes[0]})" if codes else ""
        raise ProvisionError(f"Azure call failed: {' '.join(args[:3])}{suffix}; no raw response printed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProvisionError("Azure returned a non-JSON response") from exc


def graph_get(path):
    return azure("rest", "--method", "GET", "--url", f"{GRAPH}{path}")


def graph_post(path, body):
    return azure("rest", "--method", "POST", "--url", f"{GRAPH}{path}", body=body)


def graph_items(path):
    url = f"{GRAPH}{path}"
    items = []
    for _ in range(10):
        page = azure("rest", "--method", "GET", "--url", url)
        items.extend(page.get("value", []))
        url = page.get("@odata.nextLink")
        if not url:
            return items
    raise ProvisionError("Graph collection exceeded ten pages; refusing an ambiguous lookup")


def private_state_dir(path):
    path = path.resolve()
    if path == PUBLIC_REPO or PUBLIC_REPO in path.parents:
        raise ProvisionError("state directory must be outside the public repository")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.stat().st_mode & 0o077:
        raise ProvisionError("state directory must not be accessible by group or others")
    return path


def load_state(path):
    if not path.exists():
        return {}
    if path.stat().st_mode & 0o077:
        raise ProvisionError("existing state file must have mode 0600")
    return json.loads(path.read_text())


def save_state(path, state):
    temp = path.with_suffix(".tmp")
    descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(state, stream, indent=2, sort_keys=True)
        stream.write("\n")
    os.replace(temp, path)


def find_unique(items, display_name, kind):
    matches = [item for item in items if item.get("displayName") == display_name]
    if len(matches) > 1:
        raise ProvisionError(f"multiple {kind} objects have the PoC name; stop for review")
    return matches[0] if matches else None


def provision(state_dir, name):
    state_path = state_dir / "state.json"
    state = load_state(state_path)
    account = azure("account", "show")
    subscriptions = azure("account", "list")
    if len(subscriptions) != 1:
        raise ProvisionError("expected exactly one accessible Azure subscription")
    if account.get("user", {}).get("type") != "user":
        raise ProvisionError("this pilot expects the reviewed interactive user login")
    tenant = account["tenantId"]
    subscription = account["id"]
    if state and (state.get("tenantId") != tenant or state.get("subscriptionId") != subscription or state.get("name") != name):
        raise ProvisionError("private receipt belongs to a different account or PoC name")
    state.update({"name": name, "tenantId": tenant, "subscriptionId": subscription})
    save_state(state_path, state)

    sponsor = azure("ad", "signed-in-user", "show")["id"]
    sponsor_ref = f"{GRAPH}/users/{sponsor}"

    blueprints = graph_items("/applications/microsoft.graph.agentIdentityBlueprint?$top=100")
    blueprint = find_unique(blueprints, f"{name}-blueprint", "blueprint")
    if blueprint is None:
        blueprint = graph_post("/applications/microsoft.graph.agentIdentityBlueprint", {
            "displayName": f"{name}-blueprint",
            "sponsors@odata.bind": [sponsor_ref],
            "tags": [MARKER],
        })
        print("blueprint=created")
    else:
        if MARKER not in blueprint.get("tags", []):
            raise ProvisionError("same-named blueprint lacks the PoC marker; refusing adoption")
        print("blueprint=existing")
    if state.get("blueprintAppId") not in (None, blueprint["appId"]):
        raise ProvisionError("receipt blueprint differs from Graph")
    state["blueprintAppId"] = blueprint["appId"]
    state["blueprintObjectId"] = blueprint["id"]
    save_state(state_path, state)
    verified = graph_get(f"/applications/{blueprint['id']}/microsoft.graph.agentIdentityBlueprint")
    if verified.get("appId") != blueprint["appId"]:
        raise ProvisionError("blueprint Graph read-back failed")

    principals = graph_items("/servicePrincipals/microsoft.graph.agentIdentityBlueprintPrincipal?$top=100")
    matching_principals = [item for item in principals if item.get("appId") == blueprint["appId"]]
    if len(matching_principals) > 1:
        raise ProvisionError("multiple blueprint principals found")
    if matching_principals:
        principal = matching_principals[0]
        print("blueprint_principal=existing")
    else:
        principal = graph_post("/servicePrincipals/microsoft.graph.agentIdentityBlueprintPrincipal", {
            "appId": blueprint["appId"],
        })
        print("blueprint_principal=created")
    state["blueprintPrincipalObjectId"] = principal["id"]
    save_state(state_path, state)
    verified = graph_get(f"/servicePrincipals/{principal['id']}/microsoft.graph.agentIdentityBlueprintPrincipal")
    if verified.get("appId") != blueprint["appId"]:
        raise ProvisionError("blueprint principal Graph read-back failed")

    agents = graph_items("/servicePrincipals/microsoft.graph.agentIdentity?$top=100")
    child = find_unique(agents, f"{name}-mcp-agent", "Agent ID")
    if child is None:
        child = graph_post("/servicePrincipals/microsoft.graph.agentIdentity", {
            "displayName": f"{name}-mcp-agent",
            "agentIdentityBlueprintId": blueprint["appId"],
            "sponsors@odata.bind": [sponsor_ref],
        })
        print("child_agent_id=created")
    else:
        if child.get("agentIdentityBlueprintId") != blueprint["appId"]:
            raise ProvisionError("same-named Agent ID belongs to another blueprint")
        print("child_agent_id=existing")
    if state.get("agentObjectId") not in (None, child["id"]):
        raise ProvisionError("receipt Agent ID differs from Graph")
    child_principal = graph_get(f"/servicePrincipals/{child['id']}?$select=id,appId,servicePrincipalType")
    if child_principal.get("servicePrincipalType") != "ServiceIdentity" or not child_principal.get("appId"):
        raise ProvisionError("child Agent ID lacks the expected service-principal identity")
    state["agentObjectId"] = child["id"]
    state["agentAppId"] = child_principal["appId"]
    save_state(state_path, state)
    verified = graph_get(f"/servicePrincipals/{child['id']}/microsoft.graph.agentIdentity")
    if verified.get("agentIdentityBlueprintId") != blueprint["appId"]:
        raise ProvisionError("child Agent ID Graph read-back failed")
    print("GRAPH_IDENTITY_POC_OK: blueprint, principal, and child read back")
    print(f"private_receipt={state_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--name", default="kagent-public-agentid-poc-20260924")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]{8,48}", args.name):
        parser.error("--name must be a short lowercase PoC key")
    try:
        provision(private_state_dir(args.state_dir), args.name)
    except (OSError, KeyError, ValueError, ProvisionError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()

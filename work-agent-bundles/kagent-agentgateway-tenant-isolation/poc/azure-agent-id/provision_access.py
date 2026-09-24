#!/usr/bin/env python3
"""Add a dedicated PoC API role and UAMI trust to a provisioned Agent ID.

Requires provision_graph.py first. Real identifiers stay in a private receipt.
This creates no cluster, workload, or Kubernetes federation credential.
"""

import argparse
import json
import re
import subprocess
import uuid
from pathlib import Path
from urllib.parse import quote

from provision_graph import (
    MARKER,
    ProvisionError,
    azure,
    find_unique,
    graph_get,
    graph_items,
    graph_post,
    GRAPH,
    load_state,
    private_state_dir,
    save_state,
)


ROLE_VALUE = "team-event.mcp.use"
FEDERATION_AUDIENCE = "api://AzureADTokenExchange"


def graph_patch(path, body):
    result = subprocess.run(
        ["az", "rest", "--method", "PATCH", "--url", f"{GRAPH}{path}",
         "--headers", "Content-Type=application/json", "--body", json.dumps(body),
         "--output", "none", "--only-show-errors"],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise ProvisionError("Graph application update failed; raw response withheld")


def require_match(actual, expected, label):
    if actual != expected:
        raise ProvisionError(f"{label} read-back differs from the PoC receipt")


def provision(state_dir, location):
    state_path = state_dir / "state.json"
    state = load_state(state_path)
    required = ("name", "tenantId", "subscriptionId", "blueprintObjectId", "agentObjectId")
    if any(not state.get(key) for key in required):
        raise ProvisionError("run provision_graph.py with this private state directory first")
    account = azure("account", "show")
    require_match(account.get("tenantId"), state["tenantId"], "tenant")
    require_match(account.get("id"), state["subscriptionId"], "subscription")

    name = state["name"]
    api_name = f"{name}-test-api"
    role_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{MARKER}/{name}/{ROLE_VALUE}"))
    display_filter = quote(f"displayName eq '{api_name}'", safe="")
    apps = graph_items(f"/applications?$filter={display_filter}&$select=id,appId,displayName,tags,appRoles,api")
    app = find_unique(apps, api_name, "test API application")
    if app is None:
        app = graph_post("/applications", {
            "displayName": api_name,
            "signInAudience": "AzureADMyOrg",
            "tags": [MARKER],
            "api": {"requestedAccessTokenVersion": 2},
            "appRoles": [{
                "id": role_id,
                "allowedMemberTypes": ["Application"],
                "displayName": "Use PoC team event MCP API",
                "description": "Access the isolated PoC API as an agent workload",
                "isEnabled": True,
                "value": ROLE_VALUE,
            }],
        })
        print("test_api_app=created")
    else:
        if MARKER not in app.get("tags", []):
            raise ProvisionError("same-named API app lacks the PoC marker; refusing adoption")
        print("test_api_app=existing")
    if state.get("apiAppObjectId") not in (None, app["id"]):
        raise ProvisionError("receipt API application differs from Graph")
    app = graph_get(f"/applications/{app['id']}?$select=id,appId,displayName,tags,appRoles,api,identifierUris")
    roles = [role for role in app.get("appRoles", []) if role.get("value") == ROLE_VALUE]
    if len(roles) != 1 or roles[0].get("id") != role_id or not roles[0].get("isEnabled"):
        raise ProvisionError("test API role read-back failed")
    if app.get("api", {}).get("requestedAccessTokenVersion") != 2:
        raise ProvisionError("test API does not request v2 access tokens")
    api_uri = f"api://{app['appId']}"
    if api_uri not in app.get("identifierUris", []):
        if app.get("identifierUris"):
            raise ProvisionError("PoC API already has another identifier URI; refusing replacement")
        graph_patch(f"/applications/{app['id']}", {"identifierUris": [api_uri]})
        print("test_api_identifier_uri=created")
    else:
        print("test_api_identifier_uri=existing")
    app = graph_get(f"/applications/{app['id']}?$select=id,appId,identifierUris")
    if app.get("identifierUris") != [api_uri]:
        raise ProvisionError("test API identifier URI read-back failed")
    state.update({"apiAppObjectId": app["id"], "apiAppId": app["appId"], "apiRoleId": role_id})
    save_state(state_path, state)

    app_filter = quote(f"appId eq '{app['appId']}'", safe="")
    principals = graph_items(f"/servicePrincipals?$filter={app_filter}&$select=id,appId,displayName")
    if len(principals) > 1:
        raise ProvisionError("multiple test API service principals found")
    if principals:
        principal = principals[0]
        print("test_api_principal=existing")
    else:
        principal = graph_post("/servicePrincipals", {"appId": app["appId"]})
        print("test_api_principal=created")
    require_match(principal.get("appId"), app["appId"], "API principal appId")
    state["apiPrincipalObjectId"] = principal["id"]
    save_state(state_path, state)

    assignments = graph_items(f"/servicePrincipals/{state['agentObjectId']}/appRoleAssignments")
    matches = [assignment for assignment in assignments
               if assignment.get("resourceId") == principal["id"] and assignment.get("appRoleId") == role_id]
    if len(matches) > 1:
        raise ProvisionError("duplicate child Agent ID app-role assignments found")
    if matches:
        print("agent_app_role=existing")
    else:
        graph_post(f"/servicePrincipals/{state['agentObjectId']}/appRoleAssignments", {
            "principalId": state["agentObjectId"],
            "resourceId": principal["id"],
            "appRoleId": role_id,
        })
        print("agent_app_role=created")
    assignments = graph_items(f"/servicePrincipals/{state['agentObjectId']}/appRoleAssignments")
    if not any(item.get("resourceId") == principal["id"] and item.get("appRoleId") == role_id
               for item in assignments):
        raise ProvisionError("Agent ID app-role assignment read-back failed")

    group_name = f"rg-{name}"
    group = azure("group", "show", "--name", group_name) if azure("group", "exists", "--name", group_name) else None
    if group is None:
        group = azure("group", "create", "--name", group_name, "--location", location,
                      "--tags", f"purpose={MARKER}")
        print("identity_resource_group=created")
    else:
        if group.get("tags", {}).get("purpose") != MARKER:
            raise ProvisionError("same-named resource group lacks the PoC marker; refusing adoption")
        print("identity_resource_group=existing")
    require_match(group.get("name", "").lower(), group_name.lower(), "resource group name")
    state["identityResourceGroup"] = group_name
    save_state(state_path, state)

    identity_name = f"id-{name}"
    existing = azure("identity", "list", "--resource-group", group_name)
    matches = [item for item in existing if item.get("name") == identity_name]
    if len(matches) > 1:
        raise ProvisionError("multiple same-named managed identities found")
    identity = matches[0] if matches else None
    if identity is None:
        identity = azure("identity", "create", "--resource-group", group_name,
                         "--name", identity_name, "--location", location,
                         "--tags", f"purpose={MARKER}")
        print("managed_identity=created")
    else:
        if identity.get("tags", {}).get("purpose") != MARKER:
            raise ProvisionError("same-named managed identity lacks the PoC marker; refusing adoption")
        print("managed_identity=existing")
    identity = azure("identity", "show", "--resource-group", group_name, "--name", identity_name)
    if identity.get("tags", {}).get("purpose") != MARKER or not identity.get("principalId"):
        raise ProvisionError("managed identity read-back failed")
    if state.get("managedIdentityResourceId") not in (None, identity["id"]):
        raise ProvisionError("receipt managed identity differs from Azure")
    state.update({
        "managedIdentityResourceId": identity["id"],
        "managedIdentityClientId": identity["clientId"],
        "managedIdentityPrincipalId": identity["principalId"],
    })
    save_state(state_path, state)

    fic_name = f"{name}-uami"
    issuer = f"https://login.microsoftonline.com/{state['tenantId']}/v2.0"
    fic_path = f"/applications/{state['blueprintObjectId']}/federatedIdentityCredentials"
    fics = graph_items(fic_path)
    fics = [fic for fic in fics if fic.get("name") == fic_name]
    if len(fics) > 1:
        raise ProvisionError("duplicate blueprint federation credentials found")
    if fics:
        fic = fics[0]
        print("blueprint_uami_federation=existing")
    else:
        fic = graph_post(fic_path, {
            "name": fic_name,
            "issuer": issuer,
            "subject": identity["principalId"],
            "audiences": [FEDERATION_AUDIENCE],
            "description": "Dedicated UAMI trust for the isolated Agent ID PoC",
        })
        print("blueprint_uami_federation=created")
    fic = graph_get(f"{fic_path}/{fic['id']}")
    require_match(fic.get("issuer"), issuer, "federation issuer")
    require_match(fic.get("subject"), identity["principalId"], "federation subject")
    require_match(fic.get("audiences"), [FEDERATION_AUDIENCE], "federation audience")
    state["blueprintFederationId"] = fic["id"]
    save_state(state_path, state)
    print("ACCESS_POC_OK: API role, Agent ID grant, UAMI, and blueprint federation read back")
    print(f"private_receipt={state_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--location", default="uksouth")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,25}", args.location):
        parser.error("--location must be a short Azure region name")
    try:
        provision(private_state_dir(args.state_dir), args.location)
    except (OSError, KeyError, ValueError, ProvisionError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()

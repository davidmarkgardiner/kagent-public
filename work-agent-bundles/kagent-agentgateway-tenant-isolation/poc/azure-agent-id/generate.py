#!/usr/bin/env python3
"""Validate an AACM-style result and render a private GitOps pilot overlay.

This does not call AACM or Azure. The example response is a proposed contract,
not a claim about AACM's actual API. Never write real IDs into this public repo.
"""

import argparse
import json
import re
import shutil
import sys
import uuid
from pathlib import Path


HERE = Path(__file__).resolve().parent
PUBLIC_REPO = HERE.parents[3]
BASE_AGENT = HERE.parents[1] / "teams" / "event" / "agent.yaml"
DNS_NAME = re.compile(r"^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$")


def fail(message):
    raise ValueError(message)


def check_id(value, field, demo):
    if not isinstance(value, str):
        fail(f"{field} must be a string")
    if demo and re.fullmatch(r"\{\{[A-Z_]+\}\}", value):
        return
    try:
        uuid.UUID(value)
    except ValueError:
        fail(f"{field} must be a UUID (or a placeholder with --demo)")


def check_name(value, field):
    if not isinstance(value, str) or len(value) > 63 or not DNS_NAME.fullmatch(value):
        fail(f"{field} must be a DNS-style name of at most 63 characters")


def validate(request, response, demo=False):
    if not isinstance(request, dict) or not isinstance(response, dict):
        fail("request and AACM result must be JSON objects")
    request_id = request.get("requestId")
    if not isinstance(request_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", request_id):
        fail("requestId must be a stable lowercase request key")
    if response.get("state") != "Ready":
        fail("AACM result is not Ready")
    if request.get("requestId") != response.get("requestId"):
        fail("AACM request ID does not match")
    if request.get("blueprintAppId") != response.get("blueprintAppId"):
        fail("AACM blueprint app ID does not match")
    for key in ("blueprintAppId",):
        check_id(request.get(key), key, demo)
    for key in ("agentAppId", "agentObjectId", "uamiClientId"):
        check_id(response.get(key), key, demo)
    if len({response["blueprintAppId"], response["agentAppId"], response["uamiClientId"]}) != 3:
        fail("blueprint, child Agent ID and UAMI client IDs must differ")
    agent = request.get("agent")
    if not isinstance(agent, dict):
        fail("agent must be an object")
    for key in ("namespace", "name", "serviceAccount"):
        check_name(agent.get(key), f"agent.{key}")
    if (agent["namespace"], agent["name"]) != ("team-event", "incident-adviser"):
        fail("this PoC is restricted to the team-event/incident-adviser pilot")
    subject = f"system:serviceaccount:{agent['namespace']}:{agent['serviceAccount']}"
    if response.get("serviceAccountSubject") != subject:
        fail("AACM federation subject does not match the pilot ServiceAccount")
    if request.get("mcpRole") != "team-event.mcp.use":
        fail("pilot MCP role does not match the gateway policy")
    if response.get("grantedRoles") != [request["mcpRole"]]:
        fail("AACM granted roles must be exactly the requested pilot MCP role")
    federation = response.get("federation", {})
    if not isinstance(federation, dict):
        fail("federation must be an object")
    if federation.get("serviceAccountToUami") is not True or federation.get("uamiToBlueprint") is not True:
        fail("both federation links must be reported Ready")
    return agent


def yaml_json(value):
    """JSON scalars and objects are also valid YAML values."""
    return json.dumps(value, sort_keys=True)


def render(request, response, out):
    agent = request["agent"]
    namespace = agent["namespace"]
    sa = agent["serviceAccount"]
    serviceaccount = (
        "apiVersion: v1\nkind: ServiceAccount\nmetadata:\n"
        f"  name: {sa}\n  namespace: {namespace}\n  annotations:\n"
        f"    azure.workload.identity/client-id: {yaml_json(response['uamiClientId'])}\n"
    )
    patch_ops = [
        ("/metadata/annotations", {
            "agent-id-poc.kagent.dev/blueprint-app-id": response["blueprintAppId"],
            "agent-id-poc.kagent.dev/agent-app-id": response["agentAppId"],
        }),
        ("/spec/declarative/deployment/serviceAccountName", sa),
        ("/spec/declarative/deployment/labels", {"azure.workload.identity/use": "true"}),
        ("/spec/declarative/deployment/env", [
            {"name": "AGENT_BLUEPRINT_APP_ID", "value": response["blueprintAppId"]},
            {"name": "AGENT_ID_APP_ID", "value": response["agentAppId"]},
        ]),
    ]
    patch = "".join(f"- op: add\n  path: {path}\n  value: {yaml_json(value)}\n" for path, value in patch_ops)
    kustomization = (
        "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\n"
        "resources:\n  - agent-base.yaml\n  - serviceaccount.yaml\n"
        "patches:\n  - target:\n      group: kagent.dev\n      version: v1alpha2\n"
        f"      kind: Agent\n      name: {agent['name']}\n      namespace: {namespace}\n"
        "    path: agent-identity-patch.yaml\n"
    )
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(BASE_AGENT, out / "agent-base.yaml")
    (out / "serviceaccount.yaml").write_text(serviceaccount)
    (out / "agent-identity-patch.yaml").write_text(patch)
    (out / "kustomization.yaml").write_text(kustomization)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--aacm-response", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--demo", action="store_true", help="allow placeholder IDs in example input")
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text())
        response = json.loads(args.aacm_response.read_text())
        validate(request, response, args.demo)
        out = args.out.resolve()
        if out == PUBLIC_REPO or PUBLIC_REPO in out.parents:
            fail("rendered identity IDs must be written outside the public repository")
        if out.exists():
            fail("output directory already exists; choose a fresh private path")
        render(request, response, out)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print("RENDER_OK: private pilot overlay created")


if __name__ == "__main__":
    main()

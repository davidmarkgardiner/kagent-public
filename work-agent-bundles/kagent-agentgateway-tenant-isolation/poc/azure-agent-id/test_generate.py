#!/usr/bin/env python3
"""Offline contract and GitOps-render checks for the AACM-style PoC."""

import json
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

from generate import HERE, render, validate


def fixture():
    request = json.loads((HERE / "request.example.json").read_text())
    response = json.loads((HERE / "aacm-response.example.json").read_text())
    replacements = {
        "{{BLUEPRINT_APP_ID}}": str(uuid.uuid5(uuid.NAMESPACE_DNS, "poc-blueprint")),
        "{{AGENT_APP_ID}}": str(uuid.uuid5(uuid.NAMESPACE_DNS, "poc-agent")),
        "{{AGENT_OBJECT_ID}}": str(uuid.uuid5(uuid.NAMESPACE_DNS, "poc-agent-object")),
        "{{UAMI_CLIENT_ID}}": str(uuid.uuid5(uuid.NAMESPACE_DNS, "poc-uami")),
    }
    for doc in (request, response):
        encoded = json.dumps(doc)
        for old, new in replacements.items():
            encoded = encoded.replace(old, new)
        doc.clear()
        doc.update(json.loads(encoded))
    return request, response


class GenerateTests(unittest.TestCase):
    def test_valid_contract_and_kustomize(self):
        request, response = fixture()
        validate(request, response)
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "overlay"
            render(request, response, out)
            result = subprocess.run(
                ["kubectl", "kustomize", str(out)],
                text=True, capture_output=True, check=True,
            )
            self.assertIn(f'azure.workload.identity/client-id: {response["uamiClientId"]}', result.stdout)
            self.assertIn('azure.workload.identity/use: "true"', result.stdout)
            self.assertIn("serviceAccountName: incident-adviser-id", result.stdout)
            self.assertIn(response["agentAppId"], result.stdout)
            self.assertNotIn("client_secret", result.stdout)

    def test_wrong_blueprint_is_rejected(self):
        request, response = fixture()
        response["blueprintAppId"] = str(uuid.uuid4())
        with self.assertRaisesRegex(ValueError, "blueprint app ID does not match"):
            validate(request, response)

    def test_wrong_federation_subject_is_rejected(self):
        request, response = fixture()
        response["serviceAccountSubject"] = "system:serviceaccount:team-chat:incident-adviser-id"
        with self.assertRaisesRegex(ValueError, "federation subject"):
            validate(request, response)

    def test_broader_role_grant_is_rejected(self):
        request, response = fixture()
        response["grantedRoles"].append("team-chat.mcp.use")
        with self.assertRaisesRegex(ValueError, "exactly the requested"):
            validate(request, response)

    def test_missing_trust_is_rejected(self):
        request, response = fixture()
        response["federation"]["uamiToBlueprint"] = False
        with self.assertRaisesRegex(ValueError, "both federation links"):
            validate(request, response)

    def test_placeholders_are_demo_only(self):
        request = json.loads((HERE / "request.example.json").read_text())
        response = json.loads((HERE / "aacm-response.example.json").read_text())
        validate(request, response, demo=True)
        with self.assertRaisesRegex(ValueError, "must be a UUID"):
            validate(request, response)

    def test_cli_refuses_output_inside_public_repo(self):
        forbidden = HERE / "never-write-generated-identities-here"
        self.assertFalse(forbidden.exists())
        result = subprocess.run(
            [
                "python3", str(HERE / "generate.py"), "--demo",
                "--request", str(HERE / "request.example.json"),
                "--aacm-response", str(HERE / "aacm-response.example.json"),
                "--out", str(forbidden),
            ],
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside the public repository", result.stderr)
        self.assertFalse(forbidden.exists())


if __name__ == "__main__":
    unittest.main()

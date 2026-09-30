"""Lab contract: UAMI scope and live JDBC properties/query through a fixture JAR."""

import asyncio
import base64
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("DENODO_HOST", "denodo.example.invalid")
os.environ.setdefault("DENODO_DATABASE", "synthetic")
os.environ.setdefault("DENODO_APPROVED_VIEW", "approved_namespace_inventory")
os.environ.setdefault("DENODO_RESOURCE_APP_ID", "dvp-resource-app-id")
os.environ.setdefault("AZURE_CLIENT_ID", "uami-client-id")
os.environ.setdefault("DENODO_JDBC_JAR", str(ROOT / "tests" / "fixture-driver.jar"))

import sys
sys.path.insert(0, str(ROOT / "adapter"))
import identity  # noqa: E402
import jdbc  # noqa: E402
import server  # noqa: E402
import verify_live  # noqa: E402
from fastmcp import Client  # noqa: E402


class LabTests(unittest.TestCase):
    @staticmethod
    def fixture_jwt(audience):
        payload = base64.urlsafe_b64encode(json.dumps({"aud": audience}).encode()).decode().rstrip("=")
        return f"header.{payload}.signature"

    def test_resource_scope_and_uami_selection(self):
        with patch.object(identity, "credential") as factory:
            factory.return_value.get_token.return_value.token = "lab-token"
            self.assertEqual(identity.access_token(), "lab-token")
            factory.return_value.get_token.assert_called_once_with(
                "dvp-resource-app-id/.default"
            )
        with patch.dict(os.environ, {"DENODO_IDENTITY_MODE": "managed_identity"}):
            with patch.object(identity, "ManagedIdentityCredential") as managed:
                identity._credential.cache_clear()
                identity.credential()
                managed.assert_called_once_with(client_id="uami-client-id")
        with patch.dict(os.environ, {
            "DENODO_IDENTITY_MODE": "workload_identity",
            "AZURE_TENANT_ID": "tenant-id",
            "AZURE_FEDERATED_TOKEN_FILE": "/var/run/secrets/azure/tokens/azure-identity-token",
        }):
            with patch.object(identity, "WorkloadIdentityCredential") as workload:
                identity._credential.cache_clear()
                identity.credential()
                identity.credential()
                workload.assert_called_once_with(
                    tenant_id="tenant-id",
                    client_id="uami-client-id",
                    token_file_path="/var/run/secrets/azure/tokens/azure-identity-token",
                )
        identity._credential.cache_clear()

    def test_jdbc_read_only_and_bounded_tools(self):
        with patch.object(jdbc, "access_token", return_value="lab-token"):
            count = server.get_namespace_count.fn()
            summary = server.get_namespace_summary.fn("payments")
        self.assertEqual(count["rows"], [{"namespace_count": 3}])
        self.assertEqual(summary["rows"][0]["namespace_name"], "payments")
        self.assertFalse(count["truncated"])
        self.assertFalse(summary["truncated"])

    def test_only_three_approved_tools(self):
        self.assertEqual(set(asyncio.run(server.mcp.get_tools())), {
            "get_inventory_data_product_details", "get_namespace_count", "get_namespace_summary"
        })

    def test_marker_only_verifier(self):
        import contextlib
        import io

        output = io.StringIO()
        with patch.object(identity, "access_token", return_value=self.fixture_jwt("dvp-resource-app-id")), \
             patch.object(jdbc, "access_token", return_value="lab-token"), \
             patch.object(verify_live, "access_token", return_value=self.fixture_jwt("dvp-resource-app-id")), \
             contextlib.redirect_stdout(output):
            verify_live.main()
        self.assertIn("DVP_DIRECT_GATES_PASS", output.getvalue())
        self.assertNotIn("lab-token", output.getvalue())

    def test_marker_verifier_rejects_wrong_audience(self):
        with self.assertRaisesRegex(RuntimeError, "DVP_TOKEN_AUDIENCE_MISMATCH"):
            verify_live.check_token_audience(self.fixture_jwt("other-resource"))
        with self.assertRaisesRegex(RuntimeError, "DVP_TOKEN_CLAIMS_UNREADABLE"):
            verify_live.check_token_audience("not-a-jwt")

    def test_mcp_client_invokes_jdbc_tool(self):
        async def invoke():
            async with Client(server.mcp) as client:
                return await client.call_tool("get_namespace_count")

        with patch.object(jdbc, "access_token", return_value="lab-token"):
            result = asyncio.run(invoke())
        self.assertFalse(result.is_error)
        self.assertEqual(result.structured_content["rows"], [{"namespace_count": 3}])

    def test_rejects_identifier_injection_and_budget_escalation(self):
        with patch.dict(os.environ, {"DENODO_APPROVED_VIEW": "v; DROP TABLE x"}):
            with self.assertRaises(ValueError):
                jdbc.approved_view()
        with patch.dict(os.environ, {"MCP_MAX_ROWS": "101"}):
            with self.assertRaises(ValueError):
                jdbc.query("SELECT 1")


if __name__ == "__main__":
    unittest.main()

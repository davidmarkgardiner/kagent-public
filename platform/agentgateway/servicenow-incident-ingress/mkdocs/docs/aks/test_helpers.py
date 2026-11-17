"""Offline checks: python3 -m unittest -v test_helpers.py (no cluster calls)."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import render
from smoke import assess


def fixture_values():
    values = json.loads((Path(__file__).parent / "values.example.json").read_text())
    for key, value in values.items():
        if isinstance(value, str) and "{{" in value:
            values[key] = "poc-" + key.lower().replace("_", "-")
    values["INGRESS_HOST"] = "incidents.example.com"
    values["BACKEND_A2A_PATH"] = "/api/a2a/test/agent/"
    return values


class RendererTests(unittest.TestCase):
    def test_routes_bind_discovered_targets_without_creating_platform(self):
        values = fixture_values()
        files = render.render(values)
        self.assertEqual(len(files), 4)
        self.assertIn(json.dumps(values["INGRESS_HOST"]), files["01-virtualservice.yaml"])
        self.assertIn(json.dumps(values["BACKEND_A2A_PATH"]), files["02-httproute.yaml"])
        self.assertIn(json.dumps(values["BACKEND_SERVICE_NAME"]), files["04-referencegrant.yaml"])
        self.assertIn('value: /incidents/triage/', files["02-httproute.yaml"])
        self.assertNotIn("{{", "".join(files.values()))
        self.assertNotIn("kind: Gateway\n", "".join(files.values()))
        self.assertNotIn("kind: Agent\n", "".join(files.values()))

    def test_same_namespace_omits_unneeded_grant(self):
        values = fixture_values()
        values["BACKEND_NAMESPACE"] = values["GATEWAY_NAMESPACE"]
        self.assertEqual(len(render.render(values)), 3)

    def test_unfilled_values_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Fill in"):
            render.render(json.loads((Path(__file__).parent / "values.example.json").read_text()))

    def test_wrong_ports_host_and_a2a_url_are_rejected(self):
        for key, value in [("BACKEND_SERVICE_PORT", True), ("GATEWAY_SERVICE_PORT", 0),
                           ("BACKEND_A2A_PATH", "https://other.example.com/"),
                           ("INGRESS_HOST", 'host\nkind: Secret'), ("REQUEST_TIMEOUT_SECONDS", 0)]:
            with self.subTest(key=key, value=value):
                values = fixture_values()
                values[key] = value
                with self.assertRaises(ValueError):
                    render.render(values)

    def test_values_cannot_silently_add_unknown_settings(self):
        values = fixture_values()
        values["TYPO_SERVICE_PORT"] = 123
        with self.assertRaisesRegex(ValueError, "Values keys differ"):
            render.render(values)

    def test_renderer_preserves_nonempty_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = root / "values.json"
            values.write_text(json.dumps(fixture_values()))
            output = root / "rendered"
            output.mkdir()
            sentinel = output / "existing.yaml"
            sentinel.write_text("preserve this")
            result = subprocess.run([sys.executable, str(Path(render.__file__)), "--values", str(values),
                                     "--out", str(output)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(), "preserve this")
            self.assertEqual(len(list(output.iterdir())), 1)


class ResponseTests(unittest.TestCase):
    def test_completed_agent_markers_are_required(self):
        response = {"result": {"id": "synthetic-task", "status": {"state": "completed"},
                               "artifacts": [{"parts": [{"kind": "text", "text": "INC-001 MARKER"}]}]}}
        self.assertEqual(assess(200, json.dumps(response), ["INC-001", "MARKER"])["task_state"], "completed")
        with self.assertRaisesRegex(ValueError, "marker"):
            assess(200, json.dumps(response), ["DIFFERENT_MARKER"])

    def test_http_success_does_not_hide_failed_or_unfinished_task(self):
        for state in ["failed", "submitted", "working"]:
            with self.subTest(state=state):
                with self.assertRaisesRegex(ValueError, "not proved"):
                    assess(200, json.dumps({"result": {"status": {"state": state}}}), [])

    def test_transport_rpc_and_empty_agent_response_fail(self):
        for code, response in [(503, {}), (200, {"error": {"code": -32600}}),
                               (200, {"result": {"status": {"state": "completed"}}}), (200, [])]:
            with self.subTest(code=code, response=response):
                with self.assertRaises(ValueError):
                    assess(code, json.dumps(response), [])


if __name__ == "__main__":
    unittest.main()

"""Check transfer rendering without a cluster or credential."""

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("work_renderer", ROOT / "render-work-bundle.py")
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class WorkRenderTests(unittest.TestCase):
    def test_suspended_stack_has_narrow_lease_and_no_secret(self):
        profile = renderer.profile_from(ROOT / "work-profile.example.json")
        objects = renderer.render(profile)
        self.assertNotIn("Secret", [item["kind"] for item in objects])
        self.assertEqual(len(objects), 19)
        cron = next(item for item in objects if item["kind"] == "CronJob")
        self.assertTrue(cron["spec"]["suspend"])
        pod = cron["spec"]["jobTemplate"]["spec"]["template"]["spec"]
        self.assertEqual(pod["serviceAccountName"], "sdlc-board-poller")
        self.assertEqual(pod["containers"][0]["image"], profile["python_image"])
        role = next(item for item in objects if item["kind"] == "Role")
        self.assertEqual(role["rules"], [{"apiGroups": ["coordination.k8s.io"],
                                           "resources": ["leases"],
                                           "resourceNames": ["sdlc-board-poller"],
                                           "verbs": ["get", "update"]}])
        policy = next(item for item in objects if item["kind"] == "NetworkPolicy")
        self.assertEqual(policy["spec"]["podSelector"]["matchLabels"],
                         {"app.kubernetes.io/name": "sdlc-gitlab-mcp"})
        self.assertEqual(policy["spec"]["ingress"][0]["ports"],
                         [{"protocol": "TCP", "port": 8080}])
        self.assertEqual(set(policy["spec"]["ingress"][0]["from"][0]["podSelector"]
                             ["matchExpressions"][0]["values"]),
                         {"sdlc-pm", "sdlc-builder", "sdlc-tester", "sdlc-reviewer"})
        pm = next(item for item in objects if item["kind"] == "Agent"
                  and item["metadata"]["name"] == "sdlc-pm")
        tool_names = [name for tool in pm["spec"]["declarative"]["tools"]
                      if tool["type"] == "McpServer"
                      for name in tool["mcpServer"]["toolNames"]]
        self.assertNotIn("gitlab_update_issue", tool_names)
        mcp_code = next(item for item in objects if item["kind"] == "ConfigMap"
                        and item["metadata"]["name"] == "sdlc-gitlab-mcp")["data"]["server.py"]
        self.assertIn('ALLOWED_FILES = set(["README.md", "package.json", "tests/calculator.test.mjs"])', mcp_code)

    def test_project_profile_reaches_mcp_and_poller(self):
        profile = renderer.profile_from(ROOT / "work-profile.example.json")
        profile["target_branch"] = "develop"
        profile["allowed_files"] = ["README.md"]
        objects = renderer.render(profile)
        mcp = next(item for item in objects if item["kind"] == "Deployment")
        mcp_env = {item["name"]: item.get("value") for item in mcp["spec"]["template"]["spec"]["containers"][0]["env"]}
        self.assertEqual(mcp_env["GITLAB_TARGET_BRANCH"], "develop")
        cron = next(item for item in objects if item["kind"] == "CronJob")
        env = {item["name"]: item.get("value") for item in cron["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]["env"]}
        self.assertEqual(env["GITLAB_TARGET_BRANCH"], "develop")
        self.assertEqual(json.loads(env["GITLAB_ALLOWED_FILES"]), ["README.md"])
        self.assertEqual(env["BOARD_LEASE_REQUIRED"], "true")

    def test_rejects_unsafe_file_profile(self):
        profile = renderer.profile_from(ROOT / "work-profile.example.json")
        profile["allowed_files"] = ["../secrets"]
        with self.assertRaises(ValueError):
            renderer.profile_from(self._write_profile(profile))

    def test_rejects_ci_file_profile(self):
        profile = renderer.profile_from(ROOT / "work-profile.example.json")
        profile["allowed_files"] = ["README.md", ".gitlab-ci.yml"]
        with self.assertRaisesRegex(ValueError, "CI configuration"):
            renderer.profile_from(self._write_profile(profile))

    def test_private_ca_and_proxy_reach_mcp_and_poller(self):
        profile = renderer.profile_from(ROOT / "work-profile.example.json")
        profile.update(ca_configmap="sandbox-ca", https_proxy="http://proxy.example.invalid:3128",
                       no_proxy="gitlab.example.invalid")
        objects = renderer.render(profile)
        mcp = next(item for item in objects if item["kind"] == "Deployment")
        cron = next(item for item in objects if item["kind"] == "CronJob")
        pods = [mcp["spec"]["template"]["spec"],
                cron["spec"]["jobTemplate"]["spec"]["template"]["spec"]]
        for pod in pods:
            container = pod["containers"][0]
            values = {item["name"]: item.get("value") for item in container["env"]}
            self.assertEqual(values["SSL_CERT_FILE"], "/etc/sdlc-ca/ca.crt")
            self.assertEqual(values["HTTPS_PROXY"], "http://proxy.example.invalid:3128")
            self.assertIn(".svc", values["NO_PROXY"])
            self.assertIn("gitlab.example.invalid", values["NO_PROXY"])
            self.assertIn("sdlc-extra-ca", [volume["name"] for volume in pod["volumes"]])

    def _write_profile(self, profile):
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as file:
            json.dump(profile, file)
            path = Path(file.name)
        self.addCleanup(path.unlink)
        return path


if __name__ == "__main__":
    unittest.main()

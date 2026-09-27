#!/usr/bin/env python3
"""Render a suspended, credential-free work canary from an explicit profile."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlparse

import yaml


ROOT = Path(__file__).resolve().parent
REQUIRED = {
    "project_path", "gitlab_api_url", "target_branch", "allowed_files",
    "model_name", "model_base_url", "model_client_secret_name",
    "model_client_secret_key", "pm_a2a_url", "python_image", "schedule",
    "allow_control_plane",
}


def endpoint(value, *, https_only=False):
    parsed = urlparse(value)
    if parsed.scheme not in (("https",) if https_only else ("http", "https")):
        raise ValueError("invalid endpoint scheme")
    if not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("endpoint must have a host and no credentials, query, or fragment")
    if "{{" in value or "}}" in value:
        raise ValueError("unresolved endpoint placeholder")
    return value


def profile_from(path):
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict) or set(data) != REQUIRED:
        raise ValueError(f"profile keys must be exactly {sorted(REQUIRED)}")
    strings = ("project_path", "target_branch", "model_name", "model_client_secret_name",
               "model_client_secret_key", "python_image", "schedule")
    if any(not isinstance(data[key], str) or not data[key] or "{{" in data[key]
           for key in strings):
        raise ValueError("profile has an empty value or unresolved placeholder")
    if not isinstance(data["allow_control_plane"], bool):
        raise ValueError("allow_control_plane must be a boolean")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+", data["project_path"]):
        raise ValueError("project_path must be group/project, with optional subgroups")
    if not re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", data["target_branch"]) or ".." in data["target_branch"]:
        raise ValueError("invalid target branch")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", data["model_name"]):
        raise ValueError("invalid model name")
    for key in ("model_client_secret_name", "model_client_secret_key"):
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,62}", data[key]):
            raise ValueError(f"invalid {key}")
    files = data["allowed_files"]
    if not isinstance(files, list) or not 1 <= len(files) <= 12:
        raise ValueError("allowed_files must have 1 to 12 distinct paths")
    if any(not isinstance(item, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", item)
           or ".." in item.split("/") for item in files):
        raise ValueError("allowed_files contains an unsafe path")
    if len(set(files)) != len(files):
        raise ValueError("allowed_files must have distinct paths")
    api = endpoint(data["gitlab_api_url"], https_only=True)
    if urlparse(api).path.rstrip("/") != "/api/v4":
        raise ValueError("gitlab_api_url must end in /api/v4")
    endpoint(data["model_base_url"])
    pm_url = endpoint(data["pm_a2a_url"])
    if not pm_url.endswith("/api/a2a/sdlc-rig/sdlc-pm/"):
        raise ValueError("pm_a2a_url must address the sdlc-rig PM A2A endpoint")
    if not re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", data["python_image"]):
        raise ValueError("python_image must be pinned by sha256 digest")
    if not re.fullmatch(r"[0-9*/,-]+(?: [0-9*/,-]+){4}", data["schedule"]):
        raise ValueError("schedule must be a five-field numeric cron expression")
    return data


def env(container, key, value):
    found = next((item for item in container["env"] if item["name"] == key), None)
    if found:
        found.pop("valueFrom", None)
        found["value"] = value
    else:
        container["env"].append({"name": key, "value": value})


def render(data):
    manifests = []
    foundation = list(yaml.safe_load_all((ROOT / "00-foundation.yaml").read_text()))
    foundation = [item for item in foundation if item["kind"] != "Secret"]
    model = next(item for item in foundation if item["kind"] == "ModelConfig")
    model["metadata"]["name"] = "sdlc-work-model"
    model["spec"]["model"] = data["model_name"]
    model["spec"]["apiKeySecret"] = data["model_client_secret_name"]
    model["spec"]["apiKeySecretKey"] = data["model_client_secret_key"]
    model["spec"]["openAI"]["baseUrl"] = data["model_base_url"]
    manifests.extend(foundation)

    for filename in ("10-a2a-agents.yaml", "20-delivery-workers.yaml"):
        for agent in yaml.safe_load_all((ROOT / filename).read_text()):
            spec = agent["spec"]["declarative"]
            spec["modelConfig"] = "sdlc-work-model"
            if agent["metadata"]["name"] in {"sdlc-builder", "sdlc-tester", "sdlc-reviewer"}:
                spec["systemMessage"] += (
                    "\nDeployment profile allowed paths: "
                    + ", ".join(sorted(data["allowed_files"]))
                    + ". Read or change no others.\n"
                )
            if not data["allow_control_plane"]:
                spec["deployment"].pop("tolerations", None)
            manifests.append(agent)

    command = [sys.executable, str(ROOT / "render-gitlab-mcp.py"),
               "--project-path", data["project_path"],
               "--gitlab-api-url", data["gitlab_api_url"],
               "--target-branch", data["target_branch"]]
    for item in data["allowed_files"]:
        command += ["--allowed-file", item]
    mcp = list(yaml.safe_load_all(subprocess.check_output(command, text=True)))
    for item in mcp:
        if item["kind"] == "Deployment":
            pod = item["spec"]["template"]["spec"]
            pod["containers"][0]["image"] = data["python_image"]
            if not data["allow_control_plane"]:
                pod.pop("tolerations", None)
    manifests.extend(mcp)

    manifests.append({"apiVersion": "v1", "kind": "ConfigMap",
                      "metadata": {"name": "sdlc-rig-settings", "namespace": "sdlc-rig"},
                      "data": {"project-path": data["project_path"]}})
    manifests.append({"apiVersion": "v1", "kind": "ConfigMap",
                      "metadata": {"name": "sdlc-board-poller-code", "namespace": "sdlc-rig"},
                      "data": {"board_poller.py": (ROOT / "board_poller.py").read_text()}})
    manifests.extend([
        {"apiVersion": "v1", "kind": "ServiceAccount",
         "metadata": {"name": "sdlc-board-poller", "namespace": "sdlc-rig"}},
        {"apiVersion": "coordination.k8s.io/v1", "kind": "Lease",
         "metadata": {"name": "sdlc-board-poller", "namespace": "sdlc-rig"},
         "spec": {"leaseDurationSeconds": 240}},
        {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "Role",
         "metadata": {"name": "sdlc-board-poller-lease", "namespace": "sdlc-rig"},
         "rules": [{"apiGroups": ["coordination.k8s.io"], "resources": ["leases"],
                    "resourceNames": ["sdlc-board-poller"], "verbs": ["get", "update"]}]},
        {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding",
         "metadata": {"name": "sdlc-board-poller-lease", "namespace": "sdlc-rig"},
         "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role",
                     "name": "sdlc-board-poller-lease"},
         "subjects": [{"kind": "ServiceAccount", "name": "sdlc-board-poller",
                       "namespace": "sdlc-rig"}]},
    ])
    cron = yaml.safe_load((ROOT / "30-board-cronjob.yaml").read_text())
    cron["spec"]["suspend"] = True
    cron["spec"]["schedule"] = data["schedule"]
    pod = cron["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    pod["containers"][0]["image"] = data["python_image"]
    pod["serviceAccountName"] = "sdlc-board-poller"
    pod["automountServiceAccountToken"] = True
    if not data["allow_control_plane"]:
        pod.pop("tolerations", None)
    container = pod["containers"][0]
    for key, value in (
        ("GITLAB_API_URL", data["gitlab_api_url"]),
        ("GITLAB_TARGET_BRANCH", data["target_branch"]),
        ("GITLAB_ALLOWED_FILES", json.dumps(sorted(data["allowed_files"]))),
        ("PM_A2A_URL", data["pm_a2a_url"]),
        ("BOARD_LEASE_REQUIRED", "true"),
    ):
        env(container, key, value)
    manifests.append(cron)
    return manifests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output", help="output YAML path; default stdout")
    args = parser.parse_args()
    content = yaml.safe_dump_all(render(profile_from(args.profile)), sort_keys=False)
    if args.output:
        Path(args.output).write_text(content)
    else:
        sys.stdout.write(content)


if __name__ == "__main__":
    main()

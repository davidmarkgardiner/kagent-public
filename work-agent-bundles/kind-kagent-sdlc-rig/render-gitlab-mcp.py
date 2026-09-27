#!/usr/bin/env python3
"""Render the existing fixed-project GitLab MCP for the isolated SDLC rig.

The project path is supplied at deployment time and never written to this repo.
The source MCP keeps its fixed file allowlist, agentic/ branch restriction, and
absence of merge/delete/settings tools.
"""

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

import yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-path", required=True)
    parser.add_argument("--gitlab-api-url", default="https://gitlab.com/api/v4")
    parser.add_argument("--target-branch", default="main")
    parser.add_argument("--allowed-file", action="append")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+", args.project_path):
        parser.error("supply a real sandbox project path at deployment time")
    api_url = args.gitlab_api_url.rstrip("/")
    parsed = urlparse(api_url)
    if (parsed.scheme != "https" or not parsed.netloc or parsed.path != "/api/v4"
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        parser.error("GitLab API URL must be an HTTPS /api/v4 endpoint without credentials")
    if not re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", args.target_branch) or ".." in args.target_branch:
        parser.error("invalid target branch")
    allowed_files = args.allowed_file or [
        "README.md", "package.json", "tests/calculator.test.mjs", ".gitlab-ci.yml"
    ]
    if len(set(allowed_files)) != len(allowed_files) or not 1 <= len(allowed_files) <= 12:
        parser.error("provide 1 to 12 distinct allowed files")
    if any(not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", path)
           or ".." in path.split("/") for path in allowed_files):
        parser.error("allowed files must be safe relative paths")

    source = Path(__file__).resolve().parent / "vendor" / "gitlab-delivery-mcp.yaml"
    resources = list(yaml.safe_load_all(source.read_text()))
    for resource in resources:
        resource["metadata"]["name"] = "sdlc-gitlab-mcp"
        resource["metadata"]["namespace"] = "sdlc-rig"
        resource["metadata"]["labels"] = {
            "app.kubernetes.io/name": "sdlc-gitlab-mcp",
            "app.kubernetes.io/part-of": "sdlc-rig",
        }
        kind = resource["kind"]
        if kind == "ConfigMap":
            server = resource["data"]["server.py"]
            old_validation = '    path = item.get("path", item.get("file_path", ""))'
            new_validation = (
                '    if not isinstance(item, dict):\n'
                '      raise ValueError("each file must be an object with path and content")\n'
                + old_validation
            )
            old_schema = '"files": {"type": "array"}'
            new_schema = (
                '"files": {"type": "array", "items": {"type": "object", '
                '"required": ["path", "content"], "properties": '
                '{"path": {"type": "string"}, "content": {"type": "string"}}}}'
            )
            if server.count(old_validation) != 1 or server.count(old_schema) != 1:
                raise RuntimeError("upstream GitLab MCP code changed; inspect adapter")
            resource["data"]["server.py"] = server.replace(
                old_validation, new_validation
            ).replace(old_schema, new_schema)
            server = resource["data"]["server.py"]
            old_error = (
                '      response = {"jsonrpc": "2.0", "id": request_id, '
                '"error": {"code": -32000, "message": str(exc)}}'
            )
            new_error = (
                '      response = {"jsonrpc": "2.0", "id": request_id, '
                '"result": {"content": [{"type": "text", '
                '"text": "Tool error: " + str(exc)}], "isError": True}}'
            )
            if server.count(old_error) != 1:
                raise RuntimeError("upstream MCP error response changed")
            server = server.replace(old_error, new_error)
            old_files = (
                'ALLOWED_FILES = {"README.md", "package.json", "index.html", '
                '"app.js", "tests/calculator.test.mjs", ".gitlab-ci.yml"}'
            )
            old_path_schema = (
                '"branch": {"type": "string"}, '
                '"path": {"type": "string"}'
            )
            if server.count(old_files) != 1 or server.count(old_path_schema) != 1:
                raise RuntimeError("upstream MCP file profile changed")
            new_files = "ALLOWED_FILES = set(" + json.dumps(sorted(allowed_files)) + ")"
            new_path_schema = (
                '"branch": {"type": "string"}, '
                '"path": {"type": "string", "enum": ' + json.dumps(sorted(allowed_files)) + "}"
            )
            server = server.replace(
                old_files, new_files
            ).replace(old_path_schema, new_path_schema)
            old_order = (
                '    paths.add(path)\n'
                '    action = "update" if file_exists(path, ref) else "create"'
            )
            new_order = (
                '    if path not in ALLOWED_FILES or path in paths:\n'
                '      raise ValueError("file path is outside the approved profile or repeated")\n'
                '    paths.add(path)\n'
                '    action = "update" if file_exists(path, ref) else "create"'
            )
            if server.count(old_order) != 1:
                raise RuntimeError("upstream GitLab MCP file validation order changed")
            server = server.replace(old_order, new_order)
            old_api = 'API = "https://gitlab.com/api/v4"'
            new_api = 'API = os.environ.get("GITLAB_API_URL", "https://gitlab.com/api/v4").rstrip("/")'
            if server.count(old_api) != 1:
                raise RuntimeError("upstream GitLab API URL changed")
            server = server.replace(old_api, new_api)
            server = server.replace("approved calculator profile", "approved file profile")
            server = server.replace("approved calculator file set", "approved file set")
            server = server.replace("approved calculator file", "approved file")
            server = server.replace("Create one allow-listed agentic branch from main.",
                                    "Create one allow-listed agentic branch from the configured target branch.")
            old_title = '"title": "Draft: " + title'
            new_title = (
                '"title": title if title.lower().startswith("draft: ") '
                'else "Draft: " + title'
            )
            if server.count(old_title) != 1:
                raise RuntimeError("upstream draft MR title behavior changed")
            resource["data"]["server.py"] = server.replace(old_title, new_title)
        elif kind == "Deployment":
            spec = resource["spec"]
            spec["selector"]["matchLabels"] = {"app.kubernetes.io/name": "sdlc-gitlab-mcp"}
            pod = spec["template"]
            pod["metadata"]["labels"] = {"app.kubernetes.io/name": "sdlc-gitlab-mcp"}
            pod["spec"]["nodeSelector"] = {"sdlc-rig.kagent.dev/worker": "true"}
            pod["spec"]["automountServiceAccountToken"] = False
            pod["spec"]["tolerations"] = [{
                "key": "node-role.kubernetes.io/control-plane",
                "operator": "Exists",
                "effect": "NoSchedule",
            }]
            for item in pod["spec"]["containers"][0]["env"]:
                if item["name"] == "GITLAB_PROJECT_PATH":
                    item["value"] = args.project_path
                elif item["name"] == "GITLAB_TARGET_BRANCH":
                    item["value"] = args.target_branch
                elif item["name"] == "GITLAB_TOKEN":
                    item["valueFrom"]["secretKeyRef"] = {
                        "name": "gitlab-project-token", "key": "token"
                    }
            pod["spec"]["containers"][0]["env"].append({"name": "GITLAB_API_URL", "value": api_url})
            pod["spec"]["volumes"][0]["configMap"]["name"] = "sdlc-gitlab-mcp"
        elif kind == "Service":
            resource["spec"]["selector"] = {"app.kubernetes.io/name": "sdlc-gitlab-mcp"}
        elif kind == "RemoteMCPServer":
            resource["spec"]["url"] = "http://sdlc-gitlab-mcp.sdlc-rig.svc.cluster.local:8080/mcp"
            resource["spec"]["description"] = (
                "Fixed sandbox GitLab tools; no merge, delete, or settings endpoint."
            )
    yaml.safe_dump_all(resources, sys.stdout, sort_keys=False)


if __name__ == "__main__":
    main()

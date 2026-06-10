#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${ROOT}/../.." && pwd)"

echo "== SRE first-contact demo verification =="

python3 - <<'PY' "${ROOT}"
import pathlib
import sys
import yaml

root = pathlib.Path(sys.argv[1])
required = [
    "prompts/01-sre-intake.md",
    "prompts/02-build-agents-and-tests.md",
    "prompts/03-run-demo-and-evaluate.md",
    "profiles/checkout-api.application-profile.yaml",
    "failure-modes/checkout-api.failure-modes.yaml",
    "requests/checkout-triage-agent-request.yaml",
    "requests/checkout-remediation-agent-request.yaml",
    "expected/sre-first-contact-agent.yaml",
    "expected/checkout-triage-agent.yaml",
    "expected/checkout-remediation-agent.yaml",
    "expected/checkout-toolgrants.yaml",
    "chaos/checkout-api-pod-delete.chaostest.yaml",
    "eval/checkout-api-demo-evidence-contract.yaml",
]

for rel in required:
    path = root / rel
    if not path.exists():
        raise SystemExit(f"MISSING {rel}")

yaml_paths = [
    *root.joinpath("profiles").glob("*.yaml"),
    *root.joinpath("failure-modes").glob("*.yaml"),
    *root.joinpath("requests").glob("*.yaml"),
    *root.joinpath("expected").glob("*.yaml"),
    *root.joinpath("chaos").glob("*.yaml"),
    *root.joinpath("eval").glob("*.yaml"),
]

for path in yaml_paths:
    with path.open(encoding="utf-8") as handle:
        docs = [doc for doc in yaml.safe_load_all(handle) if doc]
    if not docs:
        raise SystemExit(f"EMPTY_YAML {path}")
    for doc in docs:
        print(f"YAML_OK {path.relative_to(root)} {doc.get('kind')}/{doc.get('metadata', {}).get('name')}")

print("SRE_FIRST_CONTACT_YAML_OK: yes")
PY

python3 "${REPO_ROOT}/chaos/reliability/scripts/validate-reliability-configs.py" \
  "${ROOT}/chaos/checkout-api-pod-delete.chaostest.yaml"

python3 - <<'PY' "${ROOT}/expected"
import pathlib
import sys
import yaml

root = pathlib.Path(sys.argv[1])
forbidden = {"k8s_delete_resource", "k8s_exec", "delete_resource", "exec", "add_observations"}
found = []
agent_tools = {}
grant_tools = {}

for path in root.glob("*.yaml"):
    with path.open(encoding="utf-8") as handle:
        docs = [doc for doc in yaml.safe_load_all(handle) if doc]
    for doc in docs:
        kind = doc.get("kind")
        resource_name = doc.get("metadata", {}).get("name")
        spec = doc.get("spec", {})
        if kind == "ToolGrant":
            agent_ref = spec.get("agentRef", {}).get("name")
            if agent_ref:
                grant_tools.setdefault(agent_ref, set()).update(spec.get("allowedToolNames", []))
        for tool_name in spec.get("allowedToolNames", []):
            if tool_name in forbidden:
                found.append((path, kind, tool_name))
        declarative = spec.get("declarative", {})
        for tool in declarative.get("tools", []):
            names = tool.get("mcpServer", {}).get("toolNames", [])
            if kind == "Agent" and resource_name:
                agent_tools.setdefault(resource_name, set()).update(names)
            for tool_name in names:
                if tool_name in forbidden:
                    found.append((path, kind, tool_name))

if found:
    for path, kind, name in found:
        print(f"FORBIDDEN_TOOL {path} {kind} {name}")
    raise SystemExit(1)

print("FORBIDDEN_TOOLS_ABSENT: yes")

missing_grants = []
for agent, tools in sorted(agent_tools.items()):
    missing = tools - grant_tools.get(agent, set())
    if missing:
        missing_grants.append((agent, sorted(missing)))

if missing_grants:
    for agent, missing in missing_grants:
        print(f"TOOLGRANT_MISSING {agent} {','.join(missing)}")
    raise SystemExit(1)

print("TOOLGRANT_COVERS_AGENT_TOOLS: yes")
PY

python3 - <<'PY' "${ROOT}/eval/checkout-api-demo-evidence-contract.yaml"
import sys
import yaml

with open(sys.argv[1], encoding="utf-8") as handle:
    data = yaml.safe_load(handle)

markers = data.get("spec", {}).get("requiredMarkers", [])
hard_failures = data.get("spec", {}).get("hardFailures", [])

if len(markers) < 10:
    raise SystemExit("EVIDENCE_CONTRACT_TOO_SMALL")
if not hard_failures:
    raise SystemExit("HARD_FAILURES_MISSING")

print("EVIDENCE_CONTRACT_READY: yes")
PY

echo "SRE_FIRST_CONTACT_VERIFY: passed"

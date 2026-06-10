#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEMO_DIR="${ROOT}/demos/byo-agent-showcase"

echo "== BYO agent showcase verification =="

python3 - <<'PY'
from pathlib import Path
import yaml

demo = Path("demos/byo-agent-showcase")
paths = sorted((demo / "requests").glob("*.yaml")) + sorted((demo / "expected").glob("*.yaml"))
dangerous = {"k8s_delete_resource", "k8s_execute_command"}

for path in paths:
    docs = [doc for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")) if doc]
    if not docs:
        raise SystemExit(f"empty YAML: {path}")
    for doc in docs:
        kind = doc.get("kind")
        name = doc.get("metadata", {}).get("name")
        print(f"YAML_OK {path} {kind}/{name}")
        if kind == "Agent":
            tools = doc.get("spec", {}).get("declarative", {}).get("tools", [])
            for tool in tools:
                names = tool.get("mcpServer", {}).get("toolNames", [])
                if not names:
                    raise SystemExit(f"Agent {name} has empty toolNames in {path}")
                blocked = dangerous.intersection(names)
                if blocked:
                    raise SystemExit(f"Agent {name} has forbidden tools: {sorted(blocked)}")
        if kind == "ToolGrant":
            allowed = set(doc.get("spec", {}).get("allowedToolNames", []))
            blocked = dangerous.intersection(allowed)
            if blocked:
                raise SystemExit(f"ToolGrant {name} has forbidden tools: {sorted(blocked)}")

print("FORBIDDEN_TOOLS_ABSENT: yes")
PY

if command -v kubectl >/dev/null 2>&1; then
  kubectl kustomize "${DEMO_DIR}/expected" >/tmp/byo-agent-showcase.rendered.yaml
  echo "KUSTOMIZE_RENDERED: yes"
elif command -v kustomize >/dev/null 2>&1; then
  kustomize build "${DEMO_DIR}/expected" >/tmp/byo-agent-showcase.rendered.yaml
  echo "KUSTOMIZE_RENDERED: yes"
else
  echo "KUSTOMIZE_RENDERED: skipped (kubectl/kustomize missing)"
fi

echo "BYO_AGENT_SHOWCASE_VERIFY: passed"

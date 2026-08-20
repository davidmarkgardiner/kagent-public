#!/usr/bin/env sh
set -eu

root="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
repo="$(CDPATH='' cd -- "$root/../../.." && pwd)"

command -v kubectl >/dev/null
command -v python3 >/dev/null

created_registry=false
created_values=false
if [ ! -f "$root/cluster-registry.private.md" ]; then
  cp "$root/cluster-registry.template.md" "$root/cluster-registry.private.md"
  created_registry=true
fi
if [ ! -f "$root/work-values.env" ]; then
  cp "$root/work-values.env.template" "$root/work-values.env"
  created_values=true
fi
cleanup() {
  if [ "$created_registry" = true ]; then
    unlink "$root/cluster-registry.private.md"
  fi
  if [ "$created_values" = true ]; then
    unlink "$root/work-values.env"
  fi
}
trap cleanup EXIT HUP INT TERM

rendered="$(mktemp)"
kubectl kustomize "$root" >"$rendered"
python3 "$repo/scripts/validate-agent-cr.py" "$rendered" \
  --type triage --catalog "$root/tool-catalog.md"

python3 - "$rendered" <<'PY'
import sys
import yaml

docs = list(yaml.safe_load_all(open(sys.argv[1], encoding="utf-8")))
agent = next(doc for doc in docs if isinstance(doc, dict) and doc.get("kind") == "Agent")
config_maps = [doc for doc in docs if isinstance(doc, dict) and doc.get("kind") == "ConfigMap"]
tools = agent["spec"]["declarative"]["tools"]
assert len(tools) == 1
assert tools[0]["type"] == "McpServer"
assert tools[0]["mcpServer"]["toolNames"] == ["call_az", "call_kubectl"]
message = agent["spec"]["declarative"]["systemMessage"]
for required in (
    "BLOCKED_TARGET_CONTEXT",
    "--subscription <resolved-subscription-id>",
    "--context <resolved-kube-context>",
    "Never use `az account set`",
    "# GitLab issue draft",
):
    assert required in message, required
assert len(config_maps) == 2
assert all(item["metadata"]["namespace"] == agent["metadata"]["namespace"] for item in config_maps)
print("AKS_MULTI_SUBSCRIPTION_AGENT_CONTRACT_OK")
PY

unlink "$rendered"
"$repo/scripts/public-safe-scan.sh" "$root"
echo "AKS_MULTI_SUBSCRIPTION_TRIAGE_VERIFY_OK"

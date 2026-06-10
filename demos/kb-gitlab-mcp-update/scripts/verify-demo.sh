#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEMO_DIR="${ROOT}/demos/kb-gitlab-mcp-update"

echo "== KB GitLab MCP update demo verification =="

python3 - <<'PY' "${ROOT}" "${DEMO_DIR}"
from pathlib import Path
import re
import sys
import yaml

root = Path(sys.argv[1])
demo = Path(sys.argv[2])

required = [
    "README.md",
    "prompts/01-create-kb-docs-via-gitlab-mcp.md",
    "prompts/02-reindex-and-querydoc-proof.md",
    "prompts/03-triage-agent-kb-lookup.md",
    "requests/kb-update-request.yaml",
    "expected/platform-kb-author-agent.yaml",
    "expected/kb-update-evidence-contract.yaml",
    "expected/platform-knowledge-agent-query-contract.yaml",
]

kb_docs = [
    "docs/platform-kb/agents/kagent-triage-v2-overview.md",
    "docs/platform-kb/agents/gitlab-mcp-kb-update-loop.md",
    "docs/platform-kb/agents/querydoc-knowledge-agent.md",
    "docs/platform-kb/agents/triage-agent-kb-lookup.md",
]

for rel in required:
    path = demo / rel
    if not path.exists():
        raise SystemExit(f"MISSING {path.relative_to(root)}")
    print(f"FOUND {path.relative_to(root)}")

for rel in kb_docs:
    path = root / rel
    if not path.exists():
        raise SystemExit(f"MISSING {rel}")
    text = path.read_text(encoding="utf-8")
    if not text.startswith("# "):
        raise SystemExit(f"KB_DOC_MISSING_TITLE {rel}")
    print(f"KB_DOC_OK {rel}")

index = (root / "docs/platform-kb/INDEX.md").read_text(encoding="utf-8")
for rel in kb_docs:
    if rel not in index:
        raise SystemExit(f"INDEX_MISSING_LINK {rel}")
print("KB_INDEX_LINKS_OK: yes")

yaml_paths = sorted((demo / "requests").glob("*.yaml")) + sorted((demo / "expected").glob("*.yaml"))
for path in yaml_paths:
    docs = [doc for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")) if doc]
    if not docs:
        raise SystemExit(f"EMPTY_YAML {path.relative_to(root)}")
    for doc in docs:
        print(f"YAML_OK {path.relative_to(root)} {doc.get('kind')}/{doc.get('metadata', {}).get('name')}")

contract = yaml.safe_load((demo / "expected/kb-update-evidence-contract.yaml").read_text(encoding="utf-8"))
markers = contract["spec"]["requiredMarkers"]
for marker in [
    "KAGENT_MCP: called",
    "GITLAB_BRANCH: created",
    "GITLAB_FILE: created_or_updated",
    "KB_INDEX_UPDATED: yes",
    "GITLAB_MR: created",
    "GITLAB_MR_NOTE: created",
    "QUERYDOC_REINDEXED: yes",
    "KB_CITED_HIT: yes",
    "NO_RELEVANT_DOCS: yes",
    "TRIAGE_KB_LOOKUP: called",
    "KB_CITATION_USED_IN_TRIAGE: yes",
]:
    if marker not in markers:
        raise SystemExit(f"MARKER_MISSING {marker}")
print("EVIDENCE_MARKERS_OK: yes")

agent_docs = list(yaml.safe_load_all((demo / "expected/platform-kb-author-agent.yaml").read_text(encoding="utf-8")))
forbidden = {"k8s_delete_resource", "k8s_exec", "delete_resource", "exec", "k8s_execute_command"}
for doc in agent_docs:
    if not doc:
        continue
    kind = doc.get("kind")
    spec = doc.get("spec", {})
    if kind == "Agent":
        for tool in spec.get("declarative", {}).get("tools", []):
            names = set(tool.get("mcpServer", {}).get("toolNames", []))
            blocked = names & forbidden
            if blocked:
                raise SystemExit(f"FORBIDDEN_AGENT_TOOL {sorted(blocked)}")
    if kind == "ToolGrant":
        allowed = set(spec.get("allowedToolNames", []))
        blocked = allowed & forbidden
        if blocked:
            raise SystemExit(f"FORBIDDEN_TOOLGRANT_TOOL {sorted(blocked)}")
print("FORBIDDEN_TOOLS_ABSENT: yes")

leak_pattern = re.compile(
    r"(Bearer\s+[A-Za-z0-9._-]+|token=|password|secret:|"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|"
    r"10\.[0-9]{1,3}\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)",
    re.IGNORECASE,
)
scan_paths = [
    path for path in demo.rglob("*")
    if path.relative_to(demo).as_posix() != "scripts/verify-demo.sh"
] + [root / rel for rel in kb_docs] + [root / "docs/platform-kb/INDEX.md"]
hits = []
for path in scan_paths:
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        if leak_pattern.search(text):
            hits.append(str(path.relative_to(root)))
if hits:
    raise SystemExit("PUBLIC_SAFETY_HITS " + ", ".join(hits))
print("PUBLIC_SAFE_SCAN_OK: yes")
PY

echo "KB_GITLAB_MCP_UPDATE_VERIFY: passed"

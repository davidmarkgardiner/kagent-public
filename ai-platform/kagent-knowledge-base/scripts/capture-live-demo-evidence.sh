#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
POC_DIR="${ROOT}/ai-platform/kagent-knowledge-base"
OUT="${POC_DIR}/evidence/LIVE-DEMO-EVIDENCE.md"
A2A_JSON="${POC_DIR}/evidence/a2a-platform-knowledge-response.json"
A2A_RAW="${POC_DIR}/evidence/a2a-platform-knowledge-response.raw"

mkdir -p "${POC_DIR}/evidence"

kubectl -n kagent run live-a2a-platform-agent --rm -i --restart=Never --image=curlimages/curl:8.10.1 --command -- \
  sh -c 'cat > /tmp/payload.json <<'"'"'EOF'"'"'
{"jsonrpc":"2.0","id":"live-demo","method":"message/send","params":{"message":{"messageId":"msg-live-demo","role":"user","parts":[{"kind":"text","text":"Using the platform knowledge base, how do I secure my pod? Cite the source path."}]}}}
EOF
curl -sS -X POST http://platform-knowledge-agent.kagent.svc.cluster.local:8080/ -H "Content-Type: application/json" --data @/tmp/payload.json' \
  > "${A2A_RAW}"
python3 - "${A2A_RAW}" "${A2A_JSON}" <<'PY'
import json
import sys

raw = open(sys.argv[1], "r", encoding="utf-8").read()
start = raw.find("{")
if start < 0:
    raise SystemExit("no JSON object found in A2A response")
obj, _ = json.JSONDecoder().raw_decode(raw[start:])
with open(sys.argv[2], "w", encoding="utf-8") as f:
    json.dump(obj, f, indent=2)
    f.write("\n")
PY

{
  echo "# Platform KB Live Demo Evidence"
  echo
  echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Workspace: ${ROOT}"
  echo
  echo "## Cluster"
  echo
  echo '```text'
  kubectl config current-context
  kubectl -n kagent get deploy platform-kb-querydoc platform-knowledge-agent
  kubectl -n kagent get svc platform-kb-querydoc platform-knowledge-agent
  kubectl -n kagent get pvc platform-kb-data
  kubectl -n kagent get cronjob platform-kb-indexer
  kubectl -n kagent get modelconfig platform-kb-openai
  kubectl -n kagent get remotemcpserver platform-kb-querydoc
  kubectl -n kagent get agent platform-knowledge-agent
  echo '```'
  echo
  echo "## Querydoc Health"
  echo
  echo '```text'
  kubectl -n kagent run live-querydoc-health --rm -i --restart=Never --image=curlimages/curl:8.10.1 --command -- \
    sh -c 'curl -fsS http://platform-kb-querydoc.kagent.svc.cluster.local:8080/health && echo' 2>/dev/null
  echo '```'
  echo
  echo "## Agent Card"
  echo
  echo '```json'
  kubectl -n kagent run live-agent-card --rm -i --restart=Never --image=curlimages/curl:8.10.1 --command -- \
    sh -c 'curl -fsS http://platform-knowledge-agent.kagent.svc.cluster.local:8080/.well-known/agent-card.json' 2>/dev/null
  echo
  echo '```'
  echo
  echo "## A2A End-to-End Query"
  echo
  echo "Question:"
  echo
  echo '```text'
  echo "Using the platform knowledge base, how do I secure my pod? Cite the source path."
  echo '```'
  echo
  echo "The full JSON-RPC response is stored in \`evidence/a2a-platform-knowledge-response.json\`."
  echo
  echo "Evidence markers:"
  echo
  echo '```text'
  python3 - "${A2A_JSON}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    payload = json.load(f)

result = payload["result"]
print(f"task_state={result['status']['state']}")

tool_calls = []
tool_sources = []
final_text = ""
for item in result.get("history", []):
    for part in item.get("parts", []):
        data = part.get("data")
        if isinstance(data, dict) and data.get("name") == "query_documentation":
            if "args" in data:
                tool_calls.append(data["args"])
            response = data.get("response", {})
            for content in response.get("content", []):
                text = content.get("text", "")
                if "file://platform-kb/aks/pod-security.md" in text:
                    tool_sources.append("file://platform-kb/aks/pod-security.md")
        if part.get("kind") == "text" and "Secure Pods on the Shared AKS Platform" in part.get("text", ""):
            final_text = part["text"]

print(f"tool_calls={tool_calls}")
print(f"retrieved_sources={sorted(set(tool_sources))}")
if final_text:
    print("final_answer_excerpt=" + final_text[:500].replace("\\n", " "))
PY
  echo '```'
} > "${OUT}"

echo "Wrote ${OUT}"

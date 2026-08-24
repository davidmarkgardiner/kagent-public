#!/usr/bin/env bash

# Offline/static gate only. This script intentionally does not invoke kubectl,
# Helm, TokenRequest, or the live orchestrator.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

required_files=(
  README.md
  config/server.toml
  evidence/example-summary.json
  fixtures/expected-summary.json
  manifests/isolation.yaml
  manifests/namespace.yaml
  manifests/reader-rbac.yaml
  manifests/server.yaml
  manifests/smoke-client.yaml
  scripts/credentials.sh
  scripts/lib.sh
  scripts/live-poc.sh
  scripts/mcp-client.py
  scripts/preflight.sh
  scripts/rbac-diagnostics.py
  scripts/scan-evidence.py
  scripts/teardown.sh
  scripts/verify-rbac.sh
  values.yaml
)
for path in "${required_files[@]}"; do
  [[ -s "${BUNDLE_DIR}/${path}" ]] || {
    printf 'verify: missing required file: %s\n' "${path}" >&2
    exit 1
  }
done

for script in "${BUNDLE_DIR}"/scripts/*.sh; do
  bash -n "${script}"
  grep -F 'set -euo pipefail' "${script}" >/dev/null
done

python3 - "${BUNDLE_DIR}" <<'PY'
import json
import pathlib
import subprocess
import sys
import tomllib
import yaml

root = pathlib.Path(sys.argv[1])
poc_namespace = "kubernetes-mcp-cross-cluster-poc"
poc_rbac_name = "kubernetes-mcp-cross-cluster-poc-reader"
reader_name = "kubernetes-mcp-cross-cluster-reader"
runtime_uid = 65532
runtime_gid = 65532

manifest_docs = []
for path in sorted((root / "manifests").glob("*.yaml")) + [root / "values.yaml"]:
    with path.open("r", encoding="utf-8") as stream:
        documents = list(yaml.safe_load_all(stream))
    if not documents or any(document is None for document in documents):
        raise SystemExit(f"empty YAML document: {path.name}")
    if path.parent.name == "manifests":
        manifest_docs.extend(documents)

namespace = next(item for item in manifest_docs if item["kind"] == "Namespace")
if namespace["metadata"]["name"] != poc_namespace:
    raise SystemExit("POC namespace drifted")
for item in manifest_docs:
    metadata = item.get("metadata", {})
    if "namespace" in metadata and metadata["namespace"] != poc_namespace:
        raise SystemExit(f"manifest namespace drifted: {item['kind']}/{metadata.get('name')}")

lib_text = (root / "scripts/lib.sh").read_text(encoding="utf-8")
for declaration in {
    f'POC_NAMESPACE="{poc_namespace}"',
    f'POC_RBAC_NAME="{poc_rbac_name}"',
    f'READER_NAME="{reader_name}"',
}:
    if declaration not in lib_text:
        raise SystemExit(f"runtime POC identity drifted: {declaration}")
client_text = (root / "scripts/mcp-client.py").read_text(encoding="utf-8")
expected_endpoint = f'ENDPOINT = "http://kubernetes-mcp-server.{poc_namespace}.svc:8080/mcp"'
if expected_endpoint not in client_text:
    raise SystemExit("fixed in-cluster MCP endpoint drifted")

config = tomllib.loads((root / "config/server.toml").read_text(encoding="utf-8"))
expected_tools = {
    "configuration_contexts_list", "events_list", "namespaces_list",
    "pods_get", "pods_list", "pods_list_in_namespace", "pods_log",
    "resources_get", "resources_list",
}
if config.get("toolsets") != ["core", "config"] or set(config.get("enabled_tools", [])) != expected_tools:
    raise SystemExit("server tool allowlist drifted")
for forbidden in {
    "configuration_view", "pods_exec", "pods_delete", "pods_run",
    "resources_create_or_update", "resources_delete", "resources_scale",
}:
    if forbidden in config["enabled_tools"] or forbidden not in config["disabled_tools"]:
        raise SystemExit(f"unsafe tool posture: {forbidden}")
if config.get("read_only") is not True or config.get("cluster_provider_strategy") != "kubeconfig":
    raise SystemExit("server access posture drifted")

server_docs = list(yaml.safe_load_all((root / "manifests/server.yaml").read_text(encoding="utf-8")))
deployment = next(item for item in server_docs if item["kind"] == "Deployment")
service = next(item for item in server_docs if item["kind"] == "Service")
pod_spec = deployment["spec"]["template"]["spec"]
container = pod_spec["containers"][0]
server_resources = {
    "requests": {"cpu": "1m", "memory": "64Mi"},
    "limits": {"cpu": "200m", "memory": "256Mi"},
}
if pod_spec.get("automountServiceAccountToken") is not False:
    raise SystemExit("MCP pod token automount must be false")
pod_security = pod_spec.get("securityContext", {})
if not (
    pod_security.get("runAsNonRoot") is True
    and pod_security.get("runAsUser") == runtime_uid
    and pod_security.get("runAsGroup") == runtime_gid
    and pod_security.get("seccompProfile", {}).get("type") == "RuntimeDefault"
):
    raise SystemExit("MCP pod numeric non-root security context drifted")
security = container.get("securityContext", {})
if not (
    security.get("allowPrivilegeEscalation") is False
    and security.get("readOnlyRootFilesystem") is True
    and security.get("runAsNonRoot") is True
    and security.get("runAsUser") == runtime_uid
    and security.get("runAsGroup") == runtime_gid
    and security.get("capabilities", {}).get("drop") == ["ALL"]
):
    raise SystemExit("MCP container security context drifted")
if container.get("resources") != server_resources:
    raise SystemExit("MCP resources drifted from the bounded POC values")
if "@sha256:" not in container["image"] or ":latest" in container["image"]:
    raise SystemExit("MCP image must be immutable")
if service["spec"].get("type") != "ClusterIP" or "externalIPs" in service["spec"]:
    raise SystemExit("MCP Service must remain ClusterIP-only")

values = yaml.safe_load((root / "values.yaml").read_text(encoding="utf-8"))
if values.get("resources") != server_resources:
    raise SystemExit("audited values resources drifted from the MCP manifest")
if values.get("podSecurityContext") != pod_security:
    raise SystemExit("audited values pod security context drifted from the MCP manifest")
if values.get("securityContext") != security:
    raise SystemExit("audited values container security context drifted from the MCP manifest")

smoke_docs = list(yaml.safe_load_all((root / "manifests/smoke-client.yaml").read_text(encoding="utf-8")))
smoke_pod = next(item for item in smoke_docs if item["kind"] == "Pod")
smoke_resources = {
    "requests": {"cpu": "1m", "memory": "24Mi"},
    "limits": {"cpu": "100m", "memory": "64Mi"},
}
smoke_spec = smoke_pod["spec"]
smoke_container = smoke_spec["containers"][0]
smoke_pod_security = smoke_spec.get("securityContext", {})
if not (
    smoke_pod_security.get("runAsNonRoot") is True
    and smoke_pod_security.get("runAsUser") == runtime_uid
    and smoke_pod_security.get("runAsGroup") == runtime_gid
    and smoke_pod_security.get("seccompProfile", {}).get("type") == "RuntimeDefault"
):
    raise SystemExit("smoke-client pod numeric non-root security context drifted")
smoke_security = smoke_container.get("securityContext", {})
if not (
    smoke_security.get("allowPrivilegeEscalation") is False
    and smoke_security.get("readOnlyRootFilesystem") is True
    and smoke_security.get("runAsNonRoot") is True
    and smoke_security.get("runAsUser") == runtime_uid
    and smoke_security.get("runAsGroup") == runtime_gid
    and smoke_security.get("capabilities", {}).get("drop") == ["ALL"]
):
    raise SystemExit("smoke-client container security context drifted")
if smoke_container.get("resources") != smoke_resources:
    raise SystemExit("smoke-client resources drifted from the bounded POC values")

all_kinds = []
for path in (root / "manifests").glob("*.yaml"):
    all_kinds.extend(item["kind"] for item in yaml.safe_load_all(path.read_text(encoding="utf-8")))
if any(kind in {"Ingress", "HTTPRoute"} for kind in all_kinds):
    raise SystemExit("external exposure manifest is forbidden")

rbac_docs = list(yaml.safe_load_all((root / "manifests/reader-rbac.yaml").read_text(encoding="utf-8")))
role = next(item for item in rbac_docs if item["kind"] == "ClusterRole")
binding = next(item for item in rbac_docs if item["kind"] == "ClusterRoleBinding")
reader = next(item for item in rbac_docs if item["kind"] == "ServiceAccount")
if role["metadata"]["name"] != poc_rbac_name or binding["metadata"]["name"] != poc_rbac_name:
    raise SystemExit("POC cluster-scoped RBAC name drifted")
if binding["roleRef"]["name"] != poc_rbac_name:
    raise SystemExit("POC ClusterRoleBinding roleRef drifted")
if reader["metadata"]["name"] != reader_name or binding["subjects"] != [{
    "kind": "ServiceAccount", "name": reader_name, "namespace": poc_namespace,
}]:
    raise SystemExit("POC reader identity drifted")
rules = role["rules"]
resources = {resource for rule in rules for resource in rule["resources"]}
required = {
    "namespaces", "nodes", "pods", "pods/status", "pods/log", "events",
    "deployments", "replicasets", "statefulsets", "daemonsets", "jobs", "cronjobs",
}
if not required.issubset(resources):
    raise SystemExit("reader RBAC is missing an accepted read resource")
if resources & {"secrets", "serviceaccounts", "roles", "rolebindings", "clusterroles", "clusterrolebindings", "pods/exec", "serviceaccounts/token"}:
    raise SystemExit("reader RBAC exposes a forbidden resource")
if any(set(rule["verbs"]) - {"get", "list", "watch"} for rule in rules):
    raise SystemExit("reader RBAC contains a write verb")

isolation_docs = list(yaml.safe_load_all((root / "manifests/isolation.yaml").read_text(encoding="utf-8")))
if not any(item["spec"].get("podSelector") == {} and item["spec"].get("policyTypes") == ["Ingress"] for item in isolation_docs):
    raise SystemExit("default-deny ingress policy is missing")

generated = subprocess.run(
    [sys.executable, str(root / "scripts/mcp-client.py"), "--self-test"],
    check=True,
    capture_output=True,
    text=True,
).stdout
expected = (root / "fixtures/expected-summary.json").read_text(encoding="utf-8")
if json.loads(generated) != json.loads(expected):
    raise SystemExit("deterministic client fixture drifted")
summary = json.loads((root / "evidence/example-summary.json").read_text(encoding="utf-8"))
if summary.get("alternatingRequests", 0) < 20 or summary.get("crossoverCount") != 0:
    raise SystemExit("bounded example evidence is incomplete")
PY

python3 "${BUNDLE_DIR}/scripts/scan-evidence.py" --self-test >/dev/null
python3 "${BUNDLE_DIR}/scripts/rbac-diagnostics.py" self-test >/dev/null

if rg -q '(:latest|kind: (Ingress|HTTPRoute)|type: (LoadBalancer|NodePort))' \
  "${BUNDLE_DIR}/config" "${BUNDLE_DIR}/manifests" "${BUNDLE_DIR}/values.yaml"; then
  printf 'verify: unsafe exposure or mutable image reference detected\n' >&2
  exit 1
fi

if rg -q '(https?://|BEGIN [A-Z ]*PRIVATE KEY|BEGIN CERTIFICATE|certificate-authority-data|client-certificate-data|client-key-data|kind-homelab|proxmox-k8s|rawPrompt|kubeconfig:)' \
  "${BUNDLE_DIR}/evidence" "${BUNDLE_DIR}/fixtures"; then
  printf 'verify: retained evidence contains a forbidden value shape\n' >&2
  exit 1
fi

grep -F 'trap finish EXIT INT TERM' "${BUNDLE_DIR}/scripts/live-poc.sh" >/dev/null
grep -F -- '--duration=10m' "${BUNDLE_DIR}/scripts/credentials.sh" >/dev/null
grep -F 'create token' "${BUNDLE_DIR}/scripts/credentials.sh" >/dev/null
grep -F 'configuration_contexts_list' "${BUNDLE_DIR}/scripts/mcp-client.py" >/dev/null
grep -F 'range(1, 21)' "${BUNDLE_DIR}/scripts/mcp-client.py" >/dev/null
grep -F 'scan-evidence.py' "${BUNDLE_DIR}/scripts/live-poc.sh" >/dev/null
grep -F 'default/kubectl-mcp UID unchanged' "${BUNDLE_DIR}/scripts/teardown.sh" >/dev/null

printf 'verify: PASS (offline bundle, manifests, tool surface, RBAC, client fixture, evidence, teardown)\n'

#!/usr/bin/env python3
"""Read-only Prometheus exporter for kagent fleet inventory and lifecycle evals."""

from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
ARGO_NAMESPACE = os.environ.get("ARGO_NAMESPACE", "argo")
CLUSTER_NAME = os.environ.get("CLUSTER_NAME", "{{CLUSTER_NAME}}")
PORT = int(os.environ.get("PORT", "8080"))


def api_base() -> str:
    host = os.environ["KUBERNETES_SERVICE_HOST"]
    port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
    return f"https://{host}:{port}"


def token() -> str:
    with open(TOKEN_PATH, encoding="utf-8") as handle:
        return handle.read().strip()


def ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=CA_PATH)


def request(path: str) -> dict:
    req = urllib.request.Request(
        api_base() + path,
        headers={"Authorization": f"Bearer {token()}"},
    )
    with urllib.request.urlopen(req, context=ssl_context(), timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def request_text(path: str) -> str:
    req = urllib.request.Request(
        api_base() + path,
        headers={"Authorization": f"Bearer {token()}"},
    )
    with urllib.request.urlopen(req, context=ssl_context(), timeout=10) as response:
        return response.read().decode("utf-8", errors="replace")


def label_value(value: object) -> str:
    text = str(value or "")
    return text.replace("\\", "\\\\").replace("\n", " ").replace('"', '\\"')


def labels(**items: object) -> str:
    return "{" + ",".join(f'{key}="{label_value(value)}"' for key, value in items.items()) + "}"


def metric(name: str, value: object, **label_items: object) -> str:
    return f"{name}{labels(**label_items)} {value}"


def ready_condition(item: dict) -> int:
    for condition in item.get("status", {}).get("conditions", []):
        if condition.get("type") == "Ready" and condition.get("status") == "True":
            return 1
    return 0


def infer_capability(name: str, labels_map: dict) -> str:
    explicit = labels_map.get("reliability.platform/capability") or labels_map.get("capability")
    if explicit:
        return explicit
    lowered = name.lower()
    for keyword, capability in [
        ("grafana", "observability"),
        ("promql", "observability"),
        ("observability", "observability"),
        ("chaos", "chaos"),
        ("network", "networking"),
        ("gitops", "gitops"),
        ("gitlab", "gitlab"),
        ("knowledge", "knowledge"),
        ("trace", "tracing"),
        ("remediation", "remediation"),
        ("triage", "triage"),
    ]:
        if keyword in lowered:
            return capability
    return "general"


def infer_role(name: str, labels_map: dict) -> str:
    for key in ("role", "reliability.platform/role", "platform.com/type"):
        if labels_map.get(key):
            return labels_map[key]
    lowered = name.lower()
    if "commander" in lowered or "coordinator" in lowered or "orchestrator" in lowered:
        return "orchestrator"
    if "specialist" in lowered:
        return "specialist"
    if "review" in lowered:
        return "reviewer"
    if "remediation" in lowered:
        return "remediation"
    if "triage" in lowered:
        return "triage"
    return "agent"


def env_tier(labels_map: dict) -> str:
    return labels_map.get("reliability.platform/env-tier") or labels_map.get("env_tier") or "unknown"


def workflow_agent(workflow_name: str) -> str:
    if workflow_name == "chaos-test-lifecycle":
        return "chaos-test-manager"
    if "smart-triage" in workflow_name:
        return "smart-triage-incident-commander"
    return workflow_name


def workflow_failure_mode(workflow: dict) -> str:
    labels_map = workflow.get("metadata", {}).get("labels", {})
    test = labels_map.get("reliability.platform/test", "")
    if "pod-delete" in test:
        return "pod-delete"
    return labels_map.get("failure_mode") or labels_map.get("failure-mode") or "unknown"


def workflow_env_tier(workflow: dict) -> str:
    return env_tier(workflow.get("metadata", {}).get("labels", {}))


def workflow_short_name(workflow: dict) -> str:
    labels_map = workflow.get("metadata", {}).get("labels", {})
    return labels_map.get("app.kubernetes.io/name") or workflow.get("metadata", {}).get("generateName", "workflow").rstrip("-")


def parse_eval_log(log: str) -> tuple[float | None, int | None]:
    match = re.search(r"score=([0-9]+(?:\.[0-9]+)?)\s+passed=(true|false)", log)
    if not match:
        return None, None
    return float(match.group(1)), 1 if match.group(2) == "true" else 0


def workflow_eval_score(workflow: dict) -> tuple[float | None, int | None]:
    name = workflow.get("metadata", {}).get("name")
    if not name:
        return None, None
    selector = urllib.parse.quote(f"workflows.argoproj.io/workflow={name}")
    try:
        pods = request(f"/api/v1/namespaces/{ARGO_NAMESPACE}/pods?labelSelector={selector}")
    except urllib.error.HTTPError:
        return None, None
    for pod in pods.get("items", []):
        pod_name = pod.get("metadata", {}).get("name", "")
        if "evaluate-lifecycle" not in pod_name:
            continue
        try:
            log = request_text(f"/api/v1/namespaces/{ARGO_NAMESPACE}/pods/{pod_name}/log?container=main")
        except urllib.error.HTTPError:
            continue
        score, passed = parse_eval_log(log)
        if score is not None:
            return score, passed
    return None, None


def render_metrics() -> str:
    lines = [
        "# HELP kagent_agent_info Kagent Agent inventory record. Value is always 1.",
        "# TYPE kagent_agent_info gauge",
        "# HELP kagent_agent_ready Kagent Agent readiness as observed from the Ready condition.",
        "# TYPE kagent_agent_ready gauge",
    ]

    agents = request("/apis/kagent.dev/v1alpha2/agents")
    for item in agents.get("items", []):
        metadata = item.get("metadata", {})
        name = metadata.get("name", "unknown")
        namespace = metadata.get("namespace", "unknown")
        labels_map = metadata.get("labels", {})
        base = {
            "cluster": CLUSTER_NAME,
            "namespace": namespace,
            "agent": name,
            "role": infer_role(name, labels_map),
            "capability": infer_capability(name, labels_map),
            "env_tier": env_tier(labels_map),
        }
        lines.append(metric("kagent_agent_info", 1, **base))
        lines.append(metric("kagent_agent_ready", ready_condition(item), **base))

    lines += [
        "# HELP kagent_incident_received_total Incidents received by agent workflow.",
        "# TYPE kagent_incident_received_total counter",
        "# HELP kagent_incident_triaged_total Incidents with completed triage evidence.",
        "# TYPE kagent_incident_triaged_total counter",
        "# HELP kagent_remediation_attempted_total Remediation attempts made through approved workflow paths.",
        "# TYPE kagent_remediation_attempted_total counter",
        "# HELP kagent_remediation_verified_total Remediation attempts with successful post-action verification.",
        "# TYPE kagent_remediation_verified_total counter",
        "# HELP kagent_hitl_pending Human approvals currently pending for agent workflows.",
        "# TYPE kagent_hitl_pending gauge",
        "# HELP agent_lifecycle_eval_score Incident lifecycle eval score normalized from 0 to 1.",
        "# TYPE agent_lifecycle_eval_score gauge",
        "# HELP agent_lifecycle_eval_passed Whether an incident lifecycle eval passed.",
        "# TYPE agent_lifecycle_eval_passed gauge",
        "# HELP agent_lifecycle_eval_hard_failures Incident lifecycle eval hard failure count.",
        "# TYPE agent_lifecycle_eval_hard_failures gauge",
    ]

    workflows = request(f"/apis/argoproj.io/v1alpha1/namespaces/{ARGO_NAMESPACE}/workflows")
    for workflow in workflows.get("items", []):
        metadata = workflow.get("metadata", {})
        workflow_name = workflow_short_name(workflow)
        if workflow_name not in {"chaos-test-lifecycle", "smart-triage-fanout"}:
            continue
        status = workflow.get("status", {})
        phase = status.get("phase", "")
        labels_map = metadata.get("labels", {})
        agent = workflow_agent(workflow_name)
        base = {
            "cluster": CLUSTER_NAME,
            "namespace": metadata.get("namespace", ARGO_NAMESPACE),
            "agent": agent,
            "workflow_name": workflow_name,
            "run_id": metadata.get("name", "unknown"),
            "failure_mode": workflow_failure_mode(workflow),
            "env_tier": workflow_env_tier(workflow),
        }
        lines.append(metric("kagent_incident_received_total", 1, **base))
        lines.append(metric("kagent_incident_triaged_total", 1 if phase in {"Succeeded", "Failed", "Error"} else 0, **base))
        lines.append(metric("kagent_remediation_attempted_total", 1 if phase in {"Succeeded", "Failed"} else 0, **base))
        lines.append(metric("kagent_remediation_verified_total", 1 if phase == "Succeeded" else 0, **base))
        lines.append(metric("kagent_hitl_pending", 1 if phase in {"Suspended", "Pending"} else 0, cluster=CLUSTER_NAME, namespace=metadata.get("namespace", ARGO_NAMESPACE), workflow_name=workflow_name, run_id=metadata.get("name", "unknown"), approval_type="remediation", env_tier=workflow_env_tier(workflow)))

        score, passed = workflow_eval_score(workflow)
        if score is None:
            continue
        score_labels = {
            "cluster": CLUSTER_NAME,
            "namespace": metadata.get("namespace", ARGO_NAMESPACE),
            "agent": agent,
            "case_id": labels_map.get("reliability.platform/test", "unknown"),
            "run_id": metadata.get("name", "unknown"),
            "workflow_name": workflow_name,
            "env_tier": workflow_env_tier(workflow),
        }
        lines.append(metric("agent_lifecycle_eval_score", score, **score_labels))
        lines.append(metric("agent_lifecycle_eval_passed", passed, **score_labels))
        lines.append(metric("agent_lifecycle_eval_hard_failures", 0 if passed else 1, **score_labels))

    lines.append("")
    return "\n".join(lines)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/healthz":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok\n")
            return
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        try:
            payload = render_metrics().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:  # pragma: no cover - surfaced through /metrics
            payload = f"exporter_error{{error=\"{label_value(type(exc).__name__)}\"}} 1\n".encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {fmt % args}")


def main() -> int:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"serving kagent fleet metrics on :{PORT}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

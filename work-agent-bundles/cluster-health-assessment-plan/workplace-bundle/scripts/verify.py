#!/usr/bin/env python3
"""Offline acceptance gates for the workplace deployment bundle."""

from __future__ import annotations

import json
import fnmatch
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT.parent


def run(*command: str, cwd: Path | None = None) -> str:
    return subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True).stdout


def documents(path: Path) -> list[dict]:
    return [item for item in yaml.safe_load_all(path.read_text(encoding="utf-8")) if isinstance(item, dict)]


def pod_specs(document: dict):
    kind = document.get("kind")
    spec = document.get("spec") or {}
    if kind == "Deployment":
        yield spec.get("template", {}).get("spec", {})
    elif kind == "CronJob":
        yield spec.get("jobTemplate", {}).get("spec", {}).get("template", {}).get("spec", {})
    elif kind == "WorkflowTemplate":
        for template in spec.get("templates", []):
            script = template.get("script")
            if script:
                yield {"containers": [script]}


def validate_agent() -> None:
    agent_docs = documents(ROOT / "manager/agent.yaml")
    agents = [item for item in agent_docs if item.get("kind") == "Agent"]
    if len(agents) != 1 or agents[0].get("apiVersion") != "kagent.dev/v1alpha2":
        raise SystemExit("expected one kagent.dev/v1alpha2 Agent")
    agent = agents[0]
    labels = agent.get("metadata", {}).get("labels", {})
    declarative = agent.get("spec", {}).get("declarative", {})
    if labels.get("platform.com/type") != "triage" or not labels.get("platform.com/team"):
        raise SystemExit("Agent team/type labels are missing")
    tools = []
    for entry in declarative.get("tools", []):
        tools.extend((entry.get("mcpServer") or {}).get("toolNames") or [])
    if tools != ["call_kubectl"]:
        raise SystemExit("Agent must expose only the approved call_kubectl tool")
    if "CRITICAL: always use exact namespace" not in declarative.get("systemMessage", ""):
        raise SystemExit("Agent namespace/target prompt anchor is missing")
    if "gitlab" in json.dumps(agent).lower():
        raise SystemExit("Agent must not contain a GitLab tool or instruction")


def validate_access_boundary(
    worker_docs: list[dict], manager_docs: list[dict], namespaces: list[str], values: dict
) -> None:
    routes = [item for item in manager_docs if item.get("kind") == "HTTPRoute"]
    policies = [item for item in manager_docs if item.get("kind") == "AgentgatewayPolicy"]
    grants = [item for item in manager_docs if item.get("kind") == "ReferenceGrant"]
    if len(routes) != 1 or len(policies) != 1 or len(grants) != 1:
        raise SystemExit("expected one HTTPRoute, AgentgatewayPolicy and ReferenceGrant")
    route = routes[0]
    route_spec = route.get("spec", {})
    parent_refs = route_spec.get("parentRefs") or []
    rules = route_spec.get("rules") or []
    if len(parent_refs) != 1 or parent_refs[0] != {
        "group": "gateway.networking.k8s.io",
        "kind": "Gateway",
        "name": values["AGENTGATEWAY_GATEWAY_NAME"],
        "namespace": values["AGENTGATEWAY_NAMESPACE"],
        "sectionName": values["AGENTGATEWAY_LISTENER_NAME"],
    }:
        raise SystemExit("agentgateway route parent is not the approved Gateway")
    if route_spec.get("hostnames") != [
        "{}.{}.svc.cluster.local".format(values["AGENTGATEWAY_SERVICE_NAME"], values["AGENTGATEWAY_NAMESPACE"])
    ]:
        raise SystemExit("agentgateway route is not pinned to the internal Service hostname")
    if len(rules) != 1:
        raise SystemExit("agentgateway route must contain exactly one rule")
    rule = rules[0]
    matches = rule.get("matches") or []
    backend_refs = rule.get("backendRefs") or []
    if len(matches) != 1 or len(backend_refs) != 1:
        raise SystemExit("agentgateway route must contain one match and one backend")
    match = matches[0]
    if (
        match.get("method") != "POST"
        or match.get("path", {}).get("type") != "Exact"
        or match.get("path", {}).get("value") != "/a2a/cluster-health/"
    ):
        raise SystemExit("agentgateway route is not fixed to the cluster-health POST path")
    expected_filters = [
        {
            "type": "URLRewrite",
            "urlRewrite": {
                "path": {
                    "type": "ReplaceFullPath",
                    "replaceFullPath": "/api/a2a/kagent/cluster-health-investigator/",
                }
            },
        },
        {
            "type": "RequestHeaderModifier",
            "requestHeaderModifier": {"remove": ["Authorization"]},
        },
    ]
    if rule.get("filters") != expected_filters:
        raise SystemExit("agentgateway route filters differ from fixed rewrite and credential removal")
    if backend_refs[0] != {
        "group": "",
        "kind": "Service",
        "name": values["KAGENT_CONTROLLER_SERVICE_NAME"],
        "namespace": values["KAGENT_NAMESPACE"],
        "port": 8083,
    }:
        raise SystemExit("agentgateway route backend differs from the one controller Service")
    traffic = policies[0].get("spec", {}).get("traffic", {})
    if traffic.get("jwtAuthentication", {}).get("mode") != "Strict":
        raise SystemExit("agentgateway JWT authentication must be Strict")
    if policies[0].get("spec", {}).get("targetRefs") != [{
        "group": "gateway.networking.k8s.io", "kind": "HTTPRoute",
        "name": "cluster-health-investigator-a2a",
    }]:
        raise SystemExit("agentgateway policy is not attached only to the health route")
    providers = traffic.get("jwtAuthentication", {}).get("providers") or []
    if providers != [{
        "issuer": values["MANAGER_OIDC_ISSUER"],
        "audiences": [values["AGENTGATEWAY_AUDIENCE"]],
        "jwks": {"remote": {"jwksUri": values["MANAGER_OIDC_JWKS_URI"]}},
    }]:
        raise SystemExit("agentgateway JWT issuer, audience or JWKS differs from values")
    expressions = traffic.get("authorization", {}).get("policy", {}).get("matchExpressions") or []
    expected_subject = "system:serviceaccount:argo-events:cluster-health-investigation-workflow"
    expected_expression = 'jwt.sub == "{}"'.format(expected_subject)
    if traffic.get("authorization", {}).get("action") != "Allow" or expressions != [expected_expression]:
        raise SystemExit("agentgateway authorization must allow only the workflow ServiceAccount subject")
    grant_spec = grants[0].get("spec", {})
    if grant_spec.get("from") != [{
        "group": "gateway.networking.k8s.io", "kind": "HTTPRoute",
        "namespace": values["AGENTGATEWAY_NAMESPACE"],
    }] or grant_spec.get("to") != [{
        "group": "", "kind": "Service", "name": values["KAGENT_CONTROLLER_SERVICE_NAME"],
    }]:
        raise SystemExit("ReferenceGrant is broader than the one controller Service")

    approved = [
        item for item in manager_docs
        if item.get("kind") == "ConfigMap" and item.get("metadata", {}).get("name") == "cluster-health-approved-namespaces"
    ]
    if len(approved) != 1:
        raise SystemExit("approved namespace ConfigMap is missing")
    approved_namespaces = json.loads(approved[0]["data"]["namespaces.json"])["namespaces"]
    if approved_namespaces != namespaces:
        raise SystemExit("manager approved namespaces drift from the collector scope")

    bindings = [
        item for item in worker_docs
        if item.get("kind") == "RoleBinding"
        and item.get("metadata", {}).get("name") == "cluster-health-investigator-read"
    ]
    if sorted(item["metadata"]["namespace"] for item in bindings) != sorted(namespaces):
        raise SystemExit("MCP namespace RoleBindings drift from the collector scope")
    for binding in bindings:
        if binding.get("roleRef") != {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "ClusterRole",
            "name": "cluster-health-investigator-namespace-read",
        }:
            raise SystemExit("MCP RoleBinding points at an unexpected role")
        subjects = binding.get("subjects") or []
        if subjects != [{
            "kind": "ServiceAccount",
            "name": values["AKS_MCP_SERVICE_ACCOUNT_NAME"],
            "namespace": values["AKS_MCP_SERVICE_ACCOUNT_NAMESPACE"],
        }]:
            raise SystemExit("MCP RoleBinding subject is not one dedicated ServiceAccount")

    read_roles = [
        item for item in worker_docs
        if item.get("kind") == "ClusterRole"
        and item.get("metadata", {}).get("name") == "cluster-health-investigator-namespace-read"
    ]
    if len(read_roles) != 1:
        raise SystemExit("MCP namespace-read ClusterRole is missing")
    actual_namespace_rules = {
        (tuple(rule.get("apiGroups") or []), tuple(rule.get("resources") or []), tuple(rule.get("verbs") or []))
        for rule in read_roles[0].get("rules", [])
    }
    expected_namespace_rules = {
        (("",), ("pods", "pods/log", "services", "endpoints", "events", "persistentvolumeclaims"), ("get", "list", "watch")),
        (("apps",), ("deployments", "daemonsets", "replicasets", "statefulsets"), ("get", "list", "watch")),
        (("batch",), ("jobs", "cronjobs"), ("get", "list", "watch")),
        (("autoscaling",), ("horizontalpodautoscalers",), ("get", "list", "watch")),
        (("policy",), ("poddisruptionbudgets",), ("get", "list", "watch")),
        (("metrics.k8s.io",), ("pods",), ("get", "list")),
    }
    if read_roles[0].get("aggregationRule") or actual_namespace_rules != expected_namespace_rules or any(
        rule.get("nonResourceURLs") or rule.get("resourceNames") for rule in read_roles[0].get("rules", [])
    ):
        raise SystemExit("MCP namespace role differs from the exact read-only allowlist")

    node_roles = [
        item for item in worker_docs
        if item.get("kind") == "ClusterRole"
        and item.get("metadata", {}).get("name") == "cluster-health-investigator-node-read"
    ]
    node_bindings = [
        item for item in worker_docs
        if item.get("kind") == "ClusterRoleBinding"
        and item.get("metadata", {}).get("name") == "cluster-health-investigator-node-read"
    ]
    expected_node_rules = {
        (("",), ("nodes",), ("get", "list", "watch")),
        (("metrics.k8s.io",), ("nodes",), ("get", "list")),
    }
    if len(node_roles) != 1 or node_roles[0].get("aggregationRule") or {
        (tuple(rule.get("apiGroups") or []), tuple(rule.get("resources") or []), tuple(rule.get("verbs") or []))
        for rule in node_roles[0].get("rules", [])
    } != expected_node_rules or any(
        rule.get("nonResourceURLs") or rule.get("resourceNames") for rule in node_roles[0].get("rules", [])
    ):
        raise SystemExit("MCP node role differs from the exact node-read allowlist")
    expected_subject = [{
        "kind": "ServiceAccount",
        "name": values["AKS_MCP_SERVICE_ACCOUNT_NAME"],
        "namespace": values["AKS_MCP_SERVICE_ACCOUNT_NAMESPACE"],
    }]
    if (
        len(node_bindings) != 1
        or node_bindings[0].get("subjects") != expected_subject
        or node_bindings[0].get("roleRef") != {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "ClusterRole",
            "name": "cluster-health-investigator-node-read",
        }
    ):
        raise SystemExit("MCP node binding subject differs from the dedicated ServiceAccount")
    target_bindings = [
        document
        for document in worker_docs
        if document.get("kind") in {"RoleBinding", "ClusterRoleBinding"}
        and any(
            subject == expected_subject[0]
            for subject in (document.get("subjects") or [])
        )
    ]
    if len(target_bindings) != len(namespaces) + 1:
        raise SystemExit("rendered manifests contain an unexpected additional MCP ServiceAccount binding")

    manager_text = json.dumps(manager_docs)
    if "/var/run/secrets/agentgateway/token" not in manager_text:
        raise SystemExit("workflow does not send its projected agentgateway JWT")
    if "kagent-controller.kagent" in manager_text:
        raise SystemExit("workflow retains a direct kagent-controller bypass URL")
    if "cluster-health-approved-namespaces" not in manager_text or "--slurpfile approved" not in manager_text:
        raise SystemExit("workflow does not fail closed on namespace scope")
    sensors = [item for item in manager_docs if item.get("kind") == "Sensor"]
    if len(sensors) != 1 or sensors[0].get("spec", {}).get("template", {}).get("serviceAccountName") != "cluster-health-sensor":
        raise SystemExit("Sensor does not use its dedicated trigger ServiceAccount")
    sensor_roles = [
        item for item in manager_docs
        if item.get("kind") == "Role" and item.get("metadata", {}).get("name") == "cluster-health-sensor"
    ]
    if len(sensor_roles) != 1:
        raise SystemExit("dedicated Sensor Role is missing")
    for sensor_rule in sensor_roles[0].get("rules", []):
        if sensor_rule.get("resources") != ["workflows"] or set(sensor_rule.get("verbs") or []) - {"create", "get"}:
            raise SystemExit("Sensor Role exceeds Workflow create/get")
    ingress_policies = [
        item for item in manager_docs
        if item.get("kind") == "NetworkPolicy"
        and item.get("metadata", {}).get("name") == "cluster-health-kagent-a2a-ingress"
    ]
    if len(ingress_policies) != 1:
        raise SystemExit("kagent controller ingress boundary is missing")
    if ingress_policies[0].get("spec", {}).get("podSelector", {}).get("matchLabels") != {
        "app.kubernetes.io/name": "kagent",
        "app.kubernetes.io/component": "controller",
    }:
        raise SystemExit("kagent controller policy selects unexpected pods")
    peers = (ingress_policies[0].get("spec", {}).get("ingress") or [{}])[0].get("from") or []
    expected_peers = [
        {
            "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": values["AGENTGATEWAY_NAMESPACE"]}},
            "podSelector": {"matchLabels": {
                "gateway.networking.k8s.io/gateway-name": values["AGENTGATEWAY_GATEWAY_NAME"]
            }},
        },
        {
            "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": values["KAGENT_NAMESPACE"]}},
            "podSelector": {"matchLabels": {"kagent": "cluster-health-investigator"}},
        },
    ]
    if peers != expected_peers:
        raise SystemExit("kagent controller ingress peers differ from gateway and investigator")
    agent_policies = [
        item for item in manager_docs
        if item.get("kind") == "NetworkPolicy"
        and item.get("metadata", {}).get("name") == "cluster-health-agent-runtime-ingress"
    ]
    if len(agent_policies) != 1 or agent_policies[0].get("spec", {}).get("podSelector", {}).get("matchLabels") != {
        "kagent": "cluster-health-investigator"
    }:
        raise SystemExit("generated agent runtime ingress boundary is missing")
    agent_ingress = (agent_policies[0].get("spec", {}).get("ingress") or [])
    expected_agent_ingress = [{
        "from": [{"podSelector": {"matchLabels": {
            "app.kubernetes.io/name": "kagent",
            "app.kubernetes.io/component": "controller",
        }}}],
        "ports": [{"protocol": "TCP", "port": 8080}],
    }]
    if agent_ingress != expected_agent_ingress:
        raise SystemExit("agent runtime ingress differs from the one controller path")

    mcp_policies = [
        item for item in worker_docs
        if item.get("kind") == "NetworkPolicy"
        and item.get("metadata", {}).get("name") == "cluster-health-aks-mcp"
    ]
    if len(mcp_policies) != 1:
        raise SystemExit("dedicated AKS-MCP network boundary is missing")
    mcp_policy = mcp_policies[0]
    if mcp_policy.get("metadata", {}).get("namespace") != values["AKS_MCP_SERVICE_ACCOUNT_NAMESPACE"]:
        raise SystemExit("AKS-MCP network boundary is in an unexpected namespace")
    if mcp_policy.get("spec", {}).get("podSelector", {}).get("matchLabels") != {
        "app.kubernetes.io/instance": values["AKS_MCP_INSTANCE_LABEL"]
    }:
        raise SystemExit("AKS-MCP network boundary selects an unexpected instance")
    mcp_ingress = mcp_policy.get("spec", {}).get("ingress") or []
    expected_mcp_ingress = [{
        "from": [
            {
                "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": values["KAGENT_NAMESPACE"]}},
                "podSelector": {"matchLabels": {"kagent": "cluster-health-investigator"}},
            },
            {
                "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": values["KAGENT_NAMESPACE"]}},
                "podSelector": {"matchLabels": {
                    "app.kubernetes.io/name": "kagent",
                    "app.kubernetes.io/component": "controller",
                }},
            },
        ],
        "ports": [{"protocol": "TCP", "port": int(values["AKS_MCP_PORT"])}],
    }]
    if mcp_ingress != expected_mcp_ingress:
        raise SystemExit("AKS-MCP ingress differs from the one investigator path")


def public_safe_scan() -> None:
    patterns = []
    for line in (BUNDLE / "public-safe-scan.allowlist").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    unsafe = re.compile(
        r"192\.168\.|10\.[0-9]|172\.(?:1[6-9]|2[0-9]|3[0-1])\."
        r"|redpanda\.redpanda|PRIVATE-TOKEN|password=|[Bb]earer |token=|secret:"
        r"|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    )
    hits = []
    pinned_evidence = {
        "workplace-bundle/evidence/authenticated-front-door-final-review.md":
            "1774ede38f22f5cda37f04f26bcc29a0a82535aebe1f582cea0dfcc8f8bfcf33",
        "workplace-bundle/evidence/authenticated-front-door-repair-review.md":
            "324077cec1785f8f2aca44fe01302343e4be2c27ac37136e899356a8f65ca0d9",
    }
    for path in BUNDLE.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(BUNDLE).as_posix()
        if relative in pinned_evidence:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != pinned_evidence[relative]:
                hits.append(relative + ":sha256")
            continue
        if any(fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch("x/" + relative, pattern) for pattern in patterns):
            continue
        try:
            text_value = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text_value.splitlines(), 1):
            if unsafe.search(line):
                hits.append("{}:{}".format(relative, number))
    if hits:
        raise SystemExit("public-safety scan hits: " + ", ".join(hits[:20]))


def main() -> int:
    run(sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "runtime"), "-p", "test_*.py", "-v")
    run(sys.executable, str(BUNDLE / "fox-mesh/verify.py"))
    validate_agent()

    schema = json.loads((BUNDLE / "contracts/alert.schema.json").read_text(encoding="utf-8"))
    fixture_values = json.loads((ROOT / "fixtures/test-values.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(json.loads((ROOT / "fixtures/sample-alert.json").read_text(encoding="utf-8")), schema)

    with tempfile.TemporaryDirectory() as directory:
        rejected_output = Path(directory) / "rendered"
        injection_cases = {
            "AGENTGATEWAY_AUDIENCE": "api://health'\n- https://kubernetes.default.svc",
            "MANAGER_OIDC_ISSUER": "https://issuer.example.invalid/'\nmode: permissive",
            "MCP_CLUSTER_TARGET": 'worker-a" or true or "',
        }
        for name, malicious_value in injection_cases.items():
            malicious_values = dict(fixture_values)
            malicious_values[name] = malicious_value
            malicious_path = Path(directory) / (name.lower() + ".json")
            malicious_path.write_text(json.dumps(malicious_values), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/render.py"), "--values", str(malicious_path),
                 "--output-dir", str(rejected_output)],
                text=True, capture_output=True,
            )
            if result.returncode == 0:
                raise SystemExit("renderer accepted value injection through " + name)

    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        run(sys.executable, str(ROOT / "scripts/render.py"),
            "--values", str(ROOT / "fixtures/test-values.json"), "--output-dir", str(output))
        worker = (output / "worker.yaml").read_text(encoding="utf-8")
        manager = (output / "manager.yaml").read_text(encoding="utf-8")
        combined = worker + manager
        if re.search(r"\{\{[A-Z0-9_]+\}\}", combined):
            raise SystemExit("rendered workplace manifests retain placeholders")
        if ":latest" in combined:
            raise SystemExit("rendered workplace manifests contain latest")
        images = re.findall(r"^\s*image:\s*['\"]?([^'\"\s]+)", combined, re.MULTILINE)
        if not images or any("@sha256:" not in image for image in images):
            raise SystemExit("every rendered image must be pinned by digest")

        worker_docs = documents(output / "worker.yaml")
        manager_docs = documents(output / "manager.yaml")
        fox = [item for item in worker_docs if item.get("kind") == "Deployment" and item.get("metadata", {}).get("name", "").startswith("fox-monitor-")]
        namespaces = json.loads((BUNDLE / "fox-mesh/namespaces.json").read_text())["namespaces"]
        expected_fox = len(namespaces)
        if len(fox) != expected_fox:
            raise SystemExit("Fox deployment count does not match namespace contract")
        if any(item.get("spec", {}).get("strategy", {}).get("type") != "Recreate" for item in fox):
            raise SystemExit("Fox deployments must use Recreate to prevent duplicate namespace writers")
        validate_access_boundary(worker_docs, manager_docs, namespaces, fixture_values)

        for document in worker_docs + manager_docs:
            for spec in pod_specs(document):
                for container in spec.get("containers", []):
                    resources = container.get("resources") or {}
                    security = container.get("securityContext") or {}
                    if not resources.get("requests") or not resources.get("limits"):
                        raise SystemExit("container lacks requests/limits: {}".format(document.get("metadata", {}).get("name")))
                    if "ephemeral-storage" not in resources["requests"] or "ephemeral-storage" not in resources["limits"]:
                        raise SystemExit("container lacks ephemeral-storage bounds: {}".format(document.get("metadata", {}).get("name")))
                    if security.get("allowPrivilegeEscalation") is not False:
                        raise SystemExit("container permits privilege escalation: {}".format(document.get("metadata", {}).get("name")))
                    if security.get("readOnlyRootFilesystem") is not True:
                        raise SystemExit("container root filesystem is writable: {}".format(document.get("metadata", {}).get("name")))
                    if "ALL" not in (security.get("capabilities", {}).get("drop") or []):
                        raise SystemExit("container does not drop all capabilities: {}".format(document.get("metadata", {}).get("name")))

        if "cluster-health.fox.raw.disabled" not in worker or "127.0.0.1:1" not in worker:
            raise SystemExit("Fox raw publication does not fail safe")
        bridge_roles = [
            item for item in worker_docs
            if item.get("kind") == "Role" and item.get("metadata", {}).get("name") == "cluster-health-alert-bridge"
        ]
        if len(bridge_roles) != 1:
            raise SystemExit("alert bridge Role is missing or ambiguous")
        if any("create" in (rule.get("verbs") or []) for rule in bridge_roles[0].get("rules", [])):
            raise SystemExit("alert bridge must not create arbitrary ConfigMaps")
        if "type: disk" in worker:
            raise SystemExit("Vector disk buffering is forbidden until runtime drain is proven")
        if "sasl_ssl" not in worker or "enable.idempotence" not in worker:
            raise SystemExit("Vector Kafka TLS/SASL/idempotence guardrails are missing")
        if "insecureSkipVerify: true" in manager:
            raise SystemExit("manager Kafka TLS verification is disabled")
        if "kind: Sensor" not in manager or "kind: EventSource" not in manager:
            raise SystemExit("manager event path is incomplete")
        if "dataKey: body.dispatch.workflow_name" not in manager or "dest: metadata.name" not in manager:
            raise SystemExit("manager workflow replay-dedupe binding is missing")
        if "generateName: cluster-health-investigation-" in manager:
            raise SystemExit("manager workflow uses a replay-unsafe generated name")
        if 'name: DAILY_REPORT_HOUR_UTC' not in worker or 'name: DAILY_REPORT_MINUTE_UTC' not in worker:
            raise SystemExit("worker daily dispatch controls are missing")
        if 'name: write-gitlab-summary' not in manager or 'false == true' not in manager:
            raise SystemExit("GitLab summary writer is missing or not default-disabled in fixture")
        if '/app/gitlab_summary_writer.py' not in manager:
            raise SystemExit("GitLab summary writer entrypoint is missing")
        if "gitlab_summary_writer.py" not in (ROOT / "images/assessor/Dockerfile").read_text():
            raise SystemExit("assessor image does not contain the GitLab writer")
        workflows = [item for item in manager_docs if item.get("kind") == "WorkflowTemplate"]
        if len(workflows) != 1:
            raise SystemExit("expected one cluster-health WorkflowTemplate")
        templates = workflows[0].get("spec", {}).get("templates", [])
        entrypoint = [item for item in templates if item.get("name") == "investigate"]
        if len(entrypoint) != 1:
            raise SystemExit("workflow investigate entrypoint is missing or ambiguous")
        steps = [step for group in entrypoint[0].get("steps", []) for step in group]
        agent_steps = [step for step in steps if step.get("name") == "call-agent"]
        if len(agent_steps) != 1 or "when" in agent_steps[0]:
            raise SystemExit("validated agent step must run unconditionally to keep output references resolvable")
        writer_templates = [item for item in templates if item.get("name") == "write-gitlab-summary"]
        if len(writer_templates) != 1 or "GITLAB_TOKEN" not in json.dumps(writer_templates[0]):
            raise SystemExit("GitLab token is not confined to the fixed writer template")
        if "GITLAB_TOKEN" in json.dumps([item for item in templates if item.get("name") != "write-gitlab-summary"]):
            raise SystemExit("a non-writer Workflow template can access the GitLab token")
        for forbidden in ("PRIVATE-TOKEN", "kind: Secret", "create-gitlab", "api/v4/projects"):
            if forbidden in combined:
                raise SystemExit("bundle crosses the no-ticket/no-secret boundary: " + forbidden)

        enabled_values = dict(fixture_values)
        enabled_values["GITLAB_WRITE_ENABLED"] = "true"
        enabled_values["GITLAB_API_URL"] = "https://gitlab.example.invalid:8443"
        enabled_values["GITLAB_PORT"] = "8443"
        enabled_values["KAFKA_BOOTSTRAP"] = "kafka.example.invalid:19092"
        enabled_values["KAFKA_PORT"] = "19092"
        enabled_values["AGENTGATEWAY_PORT"] = "18080"
        enabled_values["AGENTGATEWAY_TARGET_PORT"] = "18081"
        enabled_values["AKS_MCP_PORT"] = "18000"
        enabled_values["KAGENT_A2A_URL"] = (
            "http://agentgateway-proxy.agentgateway-system.svc.cluster.local:18080/"
            "a2a/cluster-health/"
        )
        enabled_path = output / "gitlab-enabled-values.json"
        enabled_path.write_text(json.dumps(enabled_values), encoding="utf-8")
        enabled_output = output / "gitlab-enabled"
        run(sys.executable, str(ROOT / "scripts/render.py"),
            "--values", str(enabled_path), "--output-dir", str(enabled_output))
        enabled_worker = (enabled_output / "worker.yaml").read_text(encoding="utf-8")
        enabled_manager = (enabled_output / "manager.yaml").read_text(encoding="utf-8")
        for expected in ("true == true", "port: 8443", "port: 19092", "port: 18081"):
            if expected not in enabled_manager:
                raise SystemExit("enabled/non-default manager value did not render: " + expected)
        if "port: 18000" not in enabled_worker:
            raise SystemExit("non-default AKS-MCP port did not render")
        for sentinel in ("port: 31443", "port: 9092", "port: 38080"):
            if sentinel in enabled_manager:
                raise SystemExit("manager egress sentinel/default port remained after render: " + sentinel)
        if "port: 38000" in enabled_worker:
            raise SystemExit("AKS-MCP network sentinel port remained after render")
        if "port: 19092" not in enabled_worker or "port: 9092" in enabled_worker:
            raise SystemExit("non-default worker Kafka egress port did not render")

    for script in sorted((ROOT / "scripts").glob("*.sh")):
        run("bash", "-n", str(script))
    with tempfile.TemporaryDirectory() as directory:
        generated_rbac = Path(directory) / "mcp-rolebindings.yaml"
        run(sys.executable, str(ROOT / "scripts/render-mcp-rbac.py"), "--output", str(generated_rbac))
        if generated_rbac.read_text(encoding="utf-8") != (ROOT / "worker/mcp-rolebindings.yaml").read_text(encoding="utf-8"):
            raise SystemExit("checked-in MCP RoleBindings drift from namespaces.json")
    public_safe_scan()
    print("Workplace cluster-health bundle verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

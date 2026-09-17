#!/usr/bin/env python3
"""Render public-key platform manifests and create disposable lab JWTs outside Git."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "platform/contracts/tenants.json"
RENDERED = ROOT / ".rendered"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def mint(private_key: Path, kid: str, claims: dict) -> str:
    header = {"alg": "RS256", "kid": kid, "typ": "JWT"}
    signing_input = ".".join(
        b64url(json.dumps(part, separators=(",", ":"), sort_keys=True).encode())
        for part in (header, claims)
    )
    signature = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", str(private_key)],
        input=signing_input.encode(),
        check=True,
        capture_output=True,
    ).stdout
    return f"{signing_input}.{b64url(signature)}"


def metadata(name: str, namespace: str | None = None, labels: dict | None = None) -> dict:
    result = {"name": name}
    if namespace:
        result["namespace"] = namespace
    if labels:
        result["labels"] = labels
    return result


def namespace(name: str, discover: bool = False, restricted: bool = True) -> dict:
    labels = {"tenant-isolation.agentgateway.dev/discover": str(discover).lower()}
    if restricted:
        labels.update({
            "pod-security.kubernetes.io/enforce": "restricted",
            "pod-security.kubernetes.io/audit": "restricted",
            "pod-security.kubernetes.io/warn": "restricted",
        })
    return {"apiVersion": "v1", "kind": "Namespace", "metadata": metadata(name, labels=labels)}


def role_objects(ns: str) -> list[dict]:
    role_name = "application-editor"
    role = {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "Role",
        "metadata": metadata(role_name, ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "rules": [
            {"apiGroups": [""], "resources": ["configmaps", "secrets", "services", "serviceaccounts", "pods", "pods/log"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
            {"apiGroups": ["apps"], "resources": ["deployments", "statefulsets"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
            {"apiGroups": ["batch"], "resources": ["jobs", "cronjobs"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
            {"apiGroups": ["kagent.dev"], "resources": ["agents"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
            {"apiGroups": ["kagent.dev"], "resources": ["agents/status", "remotemcpservers", "modelconfigs"], "verbs": ["get", "list", "watch"]},
        ],
    }
    sa = {"apiVersion": "v1", "kind": "ServiceAccount", "metadata": metadata(f"{ns}-admin", ns)}
    binding = {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "RoleBinding",
        "metadata": metadata(role_name, ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "subjects": [{"kind": "ServiceAccount", "name": f"{ns}-admin", "namespace": ns}],
        "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": role_name},
    }
    return [sa, role, binding]


def default_deny(ns: str) -> dict:
    return {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": metadata("default-deny", ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": {"podSelector": {}, "policyTypes": ["Ingress", "Egress"]},
    }


def dns_egress(ns: str) -> dict:
    return {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": metadata("allow-dns", ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": {
            "podSelector": {},
            "policyTypes": ["Egress"],
            "egress": [{
                "to": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "kube-system"}}}],
                "ports": [{"protocol": "UDP", "port": 53}, {"protocol": "TCP", "port": 53}],
            }],
        },
    }


def validate_contract(contract: dict) -> None:
    required_root = {
        "issuer", "gatewayNamespace", "gatewayName", "gatewayClassName",
        "kagentNamespace", "kagentService", "rogueNamespace", "substrateDemo", "tenants",
    }
    missing = required_root - contract.keys()
    if missing:
        raise ValueError(f"contract is missing root fields: {sorted(missing)}")
    if not isinstance(contract["tenants"], list) or not contract["tenants"]:
        raise ValueError("contract.tenants must be a non-empty list")

    required_substrate = {
        "name", "namespace", "agent", "service", "servicePort", "gatewayPort",
        "a2aAudience", "callerSubject", "tenantClaim",
    }
    substrate_missing = required_substrate - contract["substrateDemo"].keys()
    if substrate_missing:
        raise ValueError(f"contract.substrateDemo is missing fields: {sorted(substrate_missing)}")
    for field in ("servicePort", "gatewayPort"):
        if not isinstance(contract["substrateDemo"][field], int) or not 1 <= contract["substrateDemo"][field] <= 65535:
            raise ValueError(f"substrateDemo.{field} must be a TCP port")

    required_tenant = {
        "name", "namespace", "agent", "mcpService", "mcpTool", "a2aPort",
        "mcpPort", "a2aAudience", "mcpAudience", "callerSubject", "runtimeSubject",
    }
    unique_fields = ("name", "namespace", "agent", "a2aPort", "mcpPort", "a2aAudience", "mcpAudience")
    for tenant in contract["tenants"]:
        tenant_missing = required_tenant - tenant.keys()
        if tenant_missing:
            raise ValueError(f"tenant is missing fields: {sorted(tenant_missing)}")
        for field in ("a2aPort", "mcpPort"):
            if not isinstance(tenant[field], int) or not 1 <= tenant[field] <= 65535:
                raise ValueError(f"{tenant['name']}.{field} must be a TCP port")
        if tenant["namespace"] == contract["rogueNamespace"]:
            raise ValueError("a legitimate tenant cannot use rogueNamespace")
    for field in unique_fields:
        values = [tenant[field] for tenant in contract["tenants"]]
        if len(values) != len(set(values)):
            raise ValueError(f"tenant field must be unique: {field}")
    tenant_ports = [tenant[field] for tenant in contract["tenants"] for field in ("a2aPort", "mcpPort")]
    if contract["substrateDemo"]["gatewayPort"] in tenant_ports:
        raise ValueError("substrateDemo.gatewayPort must be unique")


def gateway(root: dict) -> dict:
    listeners = []
    for tenant in root["tenants"]:
        for capability in ("a2a", "mcp"):
            listeners.append({
                "name": f'{tenant["name"]}-{capability}',
                "protocol": "HTTP",
                "port": tenant[f"{capability}Port"],
                "allowedRoutes": {"namespaces": {"from": "Same"}},
            })
    listeners.append({
        "name": "substrate-a2a",
        "protocol": "HTTP",
        "port": root["substrateDemo"]["gatewayPort"],
        "allowedRoutes": {"namespaces": {"from": "Same"}},
    })
    return {
        "apiVersion": "gateway.networking.k8s.io/v1",
        "kind": "Gateway",
        "metadata": metadata(root["gatewayName"], root["gatewayNamespace"], {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": {"gatewayClassName": root["gatewayClassName"], "listeners": listeners},
    }


def route(name: str, section: str, backend: dict, rewrite: str | None = None) -> dict:
    rule: dict = {"matches": [{"path": {"type": "PathPrefix", "value": "/"}}], "backendRefs": [backend]}
    if rewrite:
        rule["filters"] = [{"type": "URLRewrite", "urlRewrite": {"path": {"type": "ReplaceFullPath", "replaceFullPath": rewrite}}}]
    return {
        "apiVersion": "gateway.networking.k8s.io/v1",
        "kind": "HTTPRoute",
        "metadata": metadata(name, "tenant-gateway-system", {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": {
            "parentRefs": [{"name": "tenant-gateway", "sectionName": section}],
            "rules": [rule],
        },
    }


def jwt_policy(name: str, route_name: str, issuer: str, audience: str, jwks: str, claims: list[str], preserve: bool, tool: str | None = None) -> dict:
    spec: dict = {
        "targetRefs": [{"group": "gateway.networking.k8s.io", "kind": "HTTPRoute", "name": route_name}],
        "traffic": {
            "jwtAuthentication": {
                "mode": "Strict",
                "preserveToken": preserve,
                "providers": [{"issuer": issuer, "audiences": [audience], "jwks": {"inline": jwks}}],
            },
            "authorization": {"action": "Require", "policy": {"matchExpressions": claims}},
        },
    }
    if tool:
        spec["backend"] = {"mcp": {"authorization": {"action": "Allow", "policy": {"matchExpressions": [f'mcp.tool.name == "{tool}"']}}}}
    return {
        "apiVersion": "agentgateway.dev/v1alpha1",
        "kind": "AgentgatewayPolicy",
        "metadata": metadata(name, "tenant-gateway-system", {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": spec,
    }


def team_platform(contract: dict, root: dict, jwks: str) -> list[dict]:
    ns = contract["namespace"]
    short = contract["name"]
    backend_name = f"{short}-mcp"
    mcp_url = f'http://{root["gatewayName"]}.{root["gatewayNamespace"]}.svc.cluster.local:{contract["mcpPort"]}/mcp'
    backend = {
        "apiVersion": "agentgateway.dev/v1alpha1",
        "kind": "AgentgatewayBackend",
        "metadata": metadata(backend_name, ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": {
            "mcp": {
                "failureMode": "FailClosed",
                "sessionRouting": "Stateful",
                "targets": [{"name": f"{short}-tools", "static": {"backendRef": {"name": contract["mcpService"]}, "port": 8080, "path": "/mcp", "protocol": "StreamableHTTP"}}],
            }
        },
    }
    grant_backend = {
        "apiVersion": "gateway.networking.k8s.io/v1beta1",
        "kind": "ReferenceGrant",
        "metadata": metadata("allow-platform-mcp-route", ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": {
            "from": [{"group": "gateway.networking.k8s.io", "kind": "HTTPRoute", "namespace": root["gatewayNamespace"]}],
            "to": [{"group": "agentgateway.dev", "kind": "AgentgatewayBackend", "name": backend_name}],
        },
    }
    remote = {
        "apiVersion": "kagent.dev/v1alpha2",
        "kind": "RemoteMCPServer",
        "metadata": metadata("tenant-mcp", ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": {
            "description": f"Platform-authenticated {short} MCP route",
            "url": mcp_url,
            "protocol": "STREAMABLE_HTTP",
            "timeout": "30s",
            "headersFrom": [{"name": "Authorization", "valueFrom": {"type": "Secret", "name": "tenant-mcp-runtime-token", "key": "authorization"}}],
            "allowedNamespaces": {"from": "Same"},
        },
    }
    model = {
        "apiVersion": "kagent.dev/v1alpha2",
        "kind": "ModelConfig",
        "metadata": metadata("tenant-model", ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": {
            "provider": "OpenAI",
            "model": "kimi-for-coding",
            "apiKeySecret": "tenant-model-key",
            "apiKeySecretKey": "api-key",
            "openAI": {"baseUrl": "http://ai-gateway.agentgateway-system.svc.cluster.local/kimi/v1"},
        },
    }
    a2a_route_name = f"{short}-a2a"
    mcp_route_name = f"{short}-mcp"
    a2a_route = route(
        a2a_route_name,
        f"{short}-a2a",
        {"name": root["kagentService"], "namespace": root["kagentNamespace"], "port": 8083},
        f'/api/a2a/{ns}/{contract["agent"]}/',
    )
    mcp_route = route(
        mcp_route_name,
        f"{short}-mcp",
        {"group": "agentgateway.dev", "kind": "AgentgatewayBackend", "name": backend_name, "namespace": ns},
    )
    a2a_claims = [
        f'jwt.tenant == "{ns}"',
        'jwt.purpose == "a2a"',
        f'jwt.sub == "{contract["callerSubject"]}"',
    ]
    mcp_claims = [
        f'jwt.tenant == "{ns}"',
        'jwt.purpose == "mcp"',
        f'jwt.sub == "{contract["runtimeSubject"]}"',
    ]
    policies = [
        jwt_policy(f"{short}-a2a-auth", a2a_route_name, root["issuer"], contract["a2aAudience"], jwks, a2a_claims, True),
        jwt_policy(f"{short}-mcp-auth", mcp_route_name, root["issuer"], contract["mcpAudience"], jwks, mcp_claims, False, contract["mcpTool"]),
    ]
    netpols = [
        default_deny(ns),
        dns_egress(ns),
        {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": metadata("allow-gateway-to-mcp", ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
            "spec": {
                "podSelector": {"matchLabels": {"tenant-isolation.agentgateway.dev/component": "mcp"}},
                "policyTypes": ["Ingress"],
                "ingress": [{
                    "from": [{
                        "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": root["gatewayNamespace"]}},
                        "podSelector": {"matchLabels": {"gateway.networking.k8s.io/gateway-name": root["gatewayName"]}},
                    }],
                    "ports": [{"protocol": "TCP", "port": 8080}],
                }],
            },
        },
        {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": metadata("allow-kagent-to-agent", ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
            "spec": {
                "podSelector": {"matchLabels": {"app.kubernetes.io/managed-by": "kagent"}},
                "policyTypes": ["Ingress"],
                "ingress": [{
                    "from": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": root["kagentNamespace"]}}}],
                    "ports": [{"protocol": "TCP", "port": 8080}],
                }],
            },
        },
        {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": metadata("allow-agent-egress", ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
            "spec": {
                "podSelector": {"matchLabels": {"app.kubernetes.io/managed-by": "kagent"}},
                "policyTypes": ["Egress"],
                "egress": [
                    {
                        "to": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": root["kagentNamespace"]}}}],
                        "ports": [{"protocol": "TCP", "port": 8083}],
                    },
                    {
                        "to": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": root["gatewayNamespace"]}}}],
                        "ports": [{"protocol": "TCP", "port": contract["mcpPort"]}],
                    },
                    {
                        "to": [{
                            "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "agentgateway-system"}},
                            "podSelector": {"matchLabels": {"gateway.networking.k8s.io/gateway-name": "ai-gateway"}},
                        }],
                        "ports": [{"protocol": "TCP", "port": 80}],
                    },
                    {
                        "to": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "kube-system"}}}],
                        "ports": [{"protocol": "UDP", "port": 53}, {"protocol": "TCP", "port": 53}],
                    },
                ],
            },
        },
    ]
    if short == "event":
        netpols.extend([{
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": metadata("allow-event-adapter-egress", ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
            "spec": {
                "podSelector": {"matchLabels": {"tenant-isolation.agentgateway.dev/component": "event-adapter"}},
                "policyTypes": ["Egress"],
                "egress": [{
                    "to": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": root["gatewayNamespace"]}}}],
                    "ports": [{"protocol": "TCP", "port": contract["a2aPort"]}],
                }],
            },
        }, {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": metadata("allow-event-source-to-adapter", ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
            "spec": {
                "podSelector": {"matchLabels": {"tenant-isolation.agentgateway.dev/component": "event-adapter"}},
                "policyTypes": ["Ingress"],
                "ingress": [{
                    "from": [{"podSelector": {"matchLabels": {"tenant-isolation.agentgateway.dev/component": "event-source"}}}],
                    "ports": [{"protocol": "TCP", "port": 8080}],
                }],
            },
        }, {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": metadata("allow-event-source-egress", ns, {"tenant-isolation.agentgateway.dev/owner": "platform"}),
            "spec": {
                "podSelector": {"matchLabels": {"tenant-isolation.agentgateway.dev/component": "event-source"}},
                "policyTypes": ["Egress"],
                "egress": [{
                    "to": [{"podSelector": {"matchLabels": {"tenant-isolation.agentgateway.dev/component": "event-adapter"}}}],
                    "ports": [{"protocol": "TCP", "port": 8080}],
                }],
            },
        }])
    return [backend, grant_backend, remote, model, a2a_route, mcp_route, *policies, *netpols]


def substrate_platform(root: dict, jwks: str) -> list[dict]:
    substrate = root["substrateDemo"]
    route_name = "substrate-a2a"
    substrate_route = route(
        route_name,
        route_name,
        {"name": substrate["service"], "namespace": substrate["namespace"], "port": substrate["servicePort"]},
        f'/api/a2a-sandboxes/{substrate["namespace"]}/{substrate["agent"]}/',
    )
    claims = [
        f'jwt.tenant == "{substrate["tenantClaim"]}"',
        'jwt.purpose == "a2a"',
        f'jwt.sub == "{substrate["callerSubject"]}"',
    ]
    policy = jwt_policy(
        "substrate-a2a-auth",
        route_name,
        root["issuer"],
        substrate["a2aAudience"],
        jwks,
        claims,
        True,
    )
    grant = {
        "apiVersion": "gateway.networking.k8s.io/v1beta1",
        "kind": "ReferenceGrant",
        "metadata": metadata("allow-platform-substrate-a2a-route", substrate["namespace"], {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": {
            "from": [{"group": "gateway.networking.k8s.io", "kind": "HTTPRoute", "namespace": root["gatewayNamespace"]}],
            "to": [{"group": "", "kind": "Service", "name": substrate["service"]}],
        },
    }
    return [substrate_route, policy, grant]


def admission_policy(team_namespaces: list[str]) -> list[dict]:
    policy = {
        "apiVersion": "admissionregistration.k8s.io/v1",
        "kind": "ValidatingAdmissionPolicy",
        "metadata": metadata("tenant-agent-reference-boundaries"),
        "spec": {
            "failurePolicy": "Fail",
            "matchConstraints": {
                "resourceRules": [
                    {"apiGroups": ["kagent.dev"], "apiVersions": ["v1alpha2"], "operations": ["CREATE", "UPDATE"], "resources": ["agents", "remotemcpservers"]},
                    {"apiGroups": ["apps"], "apiVersions": ["v1"], "operations": ["CREATE", "UPDATE"], "resources": ["deployments"]},
                    {"apiGroups": [""], "apiVersions": ["v1"], "operations": ["CREATE", "UPDATE"], "resources": ["pods"]},
                ]
            },
            "validations": [
                {
                    "expression": "object.kind != 'RemoteMCPServer' || object.spec.allowedNamespaces.from == 'Same'",
                    "message": "RemoteMCPServer references must remain in the same namespace",
                },
                {
                    "expression": "object.kind != 'Agent' || !has(object.spec.declarative) || !has(object.spec.declarative.tools) || object.spec.declarative.tools.all(t, t.type != 'McpServer' || !has(t.mcpServer.namespace) || t.mcpServer.namespace == object.metadata.namespace)",
                    "message": "Agent MCP references must remain in the Agent namespace",
                },
                {
                    "expression": "object.kind != 'Agent' || object.spec.type == 'Declarative'",
                    "message": "The shared platform kagent lane permits Declarative Agents only",
                },
                {
                    "expression": "object.kind != 'Deployment' || (((!has(object.metadata.labels) || !('app.kubernetes.io/managed-by' in object.metadata.labels) || object.metadata.labels['app.kubernetes.io/managed-by'] != 'kagent') && (!has(object.spec.template.metadata.labels) || !('app.kubernetes.io/managed-by' in object.spec.template.metadata.labels) || object.spec.template.metadata.labels['app.kubernetes.io/managed-by'] != 'kagent')) || request.userInfo.username == 'system:serviceaccount:tenant-kagent-system:tenant-kagent-controller')",
                    "message": "Only the platform kagent controller may create kagent-managed Deployments",
                },
                {
                    "expression": "object.kind != 'Pod' || !has(object.metadata.labels) || !('app.kubernetes.io/managed-by' in object.metadata.labels) || object.metadata.labels['app.kubernetes.io/managed-by'] != 'kagent' || request.userInfo.username == 'system:serviceaccount:kube-system:replicaset-controller'",
                    "message": "Only the ReplicaSet controller may create kagent-managed Pods",
                },
            ],
        },
    }
    binding = {
        "apiVersion": "admissionregistration.k8s.io/v1",
        "kind": "ValidatingAdmissionPolicyBinding",
        "metadata": metadata("tenant-agent-reference-boundaries"),
        "spec": {
            "policyName": "tenant-agent-reference-boundaries",
            "validationActions": ["Deny", "Audit"],
            "matchResources": {
                "namespaceSelector": {"matchExpressions": [{"key": "kubernetes.io/metadata.name", "operator": "In", "values": team_namespaces}]}
            },
        },
    }
    return [policy, binding]


def make_objects(contract: dict, jwks: str) -> list[dict]:
    tenant_namespaces = [tenant["namespace"] for tenant in contract["tenants"]]
    team_namespaces = [*tenant_namespaces, contract["rogueNamespace"]]
    items: list[dict] = [
        namespace(contract["gatewayNamespace"], True, False),
        namespace(contract["kagentNamespace"], True, False),
        namespace(contract["substrateDemo"]["namespace"], True, False),
        *[namespace(name, True) for name in tenant_namespaces],
        namespace(contract["rogueNamespace"], False),
        gateway(contract),
    ]
    for ns in team_namespaces:
        items.extend(role_objects(ns))
    for tenant in contract["tenants"]:
        items.extend(team_platform(tenant, contract, jwks))
    items.extend(substrate_platform(contract, jwks))
    items.extend([default_deny(contract["rogueNamespace"]), dns_egress(contract["rogueNamespace"])])
    items.append({
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": metadata("allow-rogue-to-gateway-only", contract["rogueNamespace"], {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": {
            "podSelector": {},
            "policyTypes": ["Egress"],
            "egress": [{
                "to": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": contract["gatewayNamespace"]}}}],
                "ports": [
                    *[{"protocol": "TCP", "port": tenant[f"{capability}Port"]} for tenant in contract["tenants"] for capability in ("a2a", "mcp")],
                    {"protocol": "TCP", "port": contract["substrateDemo"]["gatewayPort"]},
                ],
            }],
        },
    })
    items.append({
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": metadata("allow-agent-to-kagent-session", contract["kagentNamespace"], {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": {
            "podSelector": {"matchLabels": {"app.kubernetes.io/component": "controller", "app.kubernetes.io/instance": "tenant-kagent", "app.kubernetes.io/name": "kagent"}},
            "policyTypes": ["Ingress"],
            "ingress": [{
                "from": [{
                    "namespaceSelector": {"matchExpressions": [{"key": "kubernetes.io/metadata.name", "operator": "In", "values": tenant_namespaces}]},
                    "podSelector": {"matchLabels": {"app.kubernetes.io/managed-by": "kagent"}},
                }],
                "ports": [{"protocol": "TCP", "port": 8083}],
            }],
        },
    })
    items.append({
        "apiVersion": "gateway.networking.k8s.io/v1beta1",
        "kind": "ReferenceGrant",
        "metadata": metadata("allow-tenant-a2a-routes", contract["kagentNamespace"], {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": {
            "from": [{"group": "gateway.networking.k8s.io", "kind": "HTTPRoute", "namespace": contract["gatewayNamespace"]}],
            "to": [{"group": "", "kind": "Service", "name": contract["kagentService"]}],
        },
    })
    items.append({
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": metadata("allow-gateway-to-kagent-a2a", contract["kagentNamespace"], {"tenant-isolation.agentgateway.dev/owner": "platform"}),
        "spec": {
            "podSelector": {"matchLabels": {"app.kubernetes.io/component": "controller", "app.kubernetes.io/instance": "tenant-kagent", "app.kubernetes.io/name": "kagent"}},
            "policyTypes": ["Ingress"],
            "ingress": [{
                "from": [{
                    "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": contract["gatewayNamespace"]}},
                    "podSelector": {"matchLabels": {"gateway.networking.k8s.io/gateway-name": contract["gatewayName"]}},
                }],
                "ports": [{"protocol": "TCP", "port": 8083}],
            }],
        },
    })
    items.extend(admission_policy(team_namespaces))
    return items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["red"], default="red")
    args = parser.parse_args()
    del args

    contract = json.loads(CONTRACT_PATH.read_text())
    validate_contract(contract)
    run_dir = Path(tempfile.mkdtemp(prefix="kagent-tenant-isolation-"))
    private_key = run_dir / "jwt-signing-key.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private_key)], check=True, capture_output=True)
    os.chmod(private_key, 0o600)
    modulus_hex = subprocess.run(["openssl", "rsa", "-in", str(private_key), "-noout", "-modulus"], check=True, capture_output=True, text=True).stdout.strip().split("=", 1)[1]
    jwk = {"kty": "RSA", "e": "AQAB", "use": "sig", "kid": "red-lab-1", "alg": "RS256", "n": b64url(bytes.fromhex(modulus_hex))}
    jwks = json.dumps({"keys": [jwk]}, separators=(",", ":"))

    now = int(time.time())
    tokens: dict[str, str] = {}
    for tenant in contract["tenants"]:
        for capability in ("a2a", "mcp"):
            claims = {
                "iss": contract["issuer"],
                "aud": tenant[f"{capability}Audience"],
                "sub": tenant["callerSubject" if capability == "a2a" else "runtimeSubject"],
                "tenant": tenant["namespace"],
                "purpose": capability,
                "iat": now,
                "exp": now + 1800,
            }
            tokens[f'{tenant["name"]}_{capability}'] = mint(private_key, "red-lab-1", claims)
            rogue_claims = dict(claims, sub="system:serviceaccount:team-rogue:rogue", tenant="team-rogue")
            tokens[f'rogue_{tenant["name"]}_{capability}'] = mint(private_key, "red-lab-1", rogue_claims)
    substrate = contract["substrateDemo"]
    substrate_claims = {
        "iss": contract["issuer"],
        "aud": substrate["a2aAudience"],
        "sub": substrate["callerSubject"],
        "tenant": substrate["tenantClaim"],
        "purpose": "a2a",
        "iat": now,
        "exp": now + 1800,
    }
    tokens["substrate_a2a"] = mint(private_key, "red-lab-1", substrate_claims)
    tokens["rogue_substrate_a2a"] = mint(
        private_key,
        "red-lab-1",
        dict(substrate_claims, sub="system:serviceaccount:team-rogue:rogue", tenant="team-rogue"),
    )
    tokens["wrong_audience"] = mint(private_key, "red-lab-1", {
        "iss": contract["issuer"], "aud": "urn:kagent-lab:wrong", "sub": "wrong", "tenant": "team-rogue", "purpose": "a2a", "iat": now, "exp": now + 1800,
    })
    tokens["expired"] = mint(private_key, "red-lab-1", {
        "iss": contract["issuer"], "aud": contract["tenants"][0]["a2aAudience"], "sub": contract["tenants"][0]["callerSubject"], "tenant": "team-event", "purpose": "a2a", "iat": now - 3600, "exp": now - 60,
    })
    (run_dir / "tokens.json").write_text(json.dumps(tokens, indent=2) + "\n")
    os.chmod(run_dir / "tokens.json", 0o600)

    RENDERED.mkdir(exist_ok=True)
    output = {"apiVersion": "v1", "kind": "List", "items": make_objects(contract, jwks)}
    (RENDERED / "platform.json").write_text(json.dumps(output, indent=2) + "\n")
    (ROOT / ".run-dir").write_text(str(run_dir) + "\n")
    print(f"Rendered public manifests to {RENDERED / 'platform.json'}")
    print(f"Disposable private material is outside the repository at {run_dir}")


if __name__ == "__main__":
    main()

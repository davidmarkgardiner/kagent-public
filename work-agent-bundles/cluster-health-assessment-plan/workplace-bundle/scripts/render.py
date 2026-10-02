#!/usr/bin/env python3
"""Render placeholder-free worker and manager manifests from reviewed values."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import subprocess
import urllib.parse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
IMAGE = re.compile(r"^[a-zA-Z0-9._:/-]+@sha256:[0-9a-f]{64}$")
DNS_LABEL = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
AUDIENCE = re.compile(r"^api://[A-Za-z0-9._-]+$")
SAFE_HTTPS_URL = re.compile(
    r"^https://[A-Za-z0-9.-]+(?::[0-9]+)?(?:/[A-Za-z0-9._~%/-]+)*/?$"
)


REQUIRED = {
    "AGENTGATEWAY_AUDIENCE", "AGENTGATEWAY_GATEWAY_NAME", "AGENTGATEWAY_LISTENER_NAME", "AGENTGATEWAY_NAMESPACE",
    "AGENTGATEWAY_PORT", "AGENTGATEWAY_SERVICE_NAME", "AGENTGATEWAY_TARGET_PORT",
    "AKS_MCP_INSTANCE_LABEL", "AKS_MCP_PORT", "AKS_MCP_SERVER_NAME",
    "AKS_MCP_SERVICE_ACCOUNT_NAME", "AKS_MCP_SERVICE_ACCOUNT_NAMESPACE",
    "ASSESSOR_IMAGE", "CLUSTER_HEALTH_ALERT_TOPIC",
    "CLUSTER_HEALTH_CONSUMER_GROUP", "CLUSTER_ID", "CRITICAL_NAMESPACES",
    "FOX_IMAGE", "GITLAB_API_URL", "GITLAB_CREDENTIALS_SECRET",
    "GITLAB_EGRESS_CIDR", "GITLAB_PORT", "GITLAB_PROJECT_ID",
    "GITLAB_WRITE_ENABLED", "KAFKA_BOOTSTRAP", "KAFKA_CREDENTIALS_SECRET",
    "KAFKA_EGRESS_CIDR", "KAGENT_A2A_URL", "KAGENT_CONTROLLER_SERVICE_NAME",
    "KAGENT_MODEL_CONFIG", "KAGENT_NAMESPACE", "KAFKA_PORT",
    "KUBERNETES_API_CIDR", "MANAGER_KUBERNETES_API_CIDR", "MCP_CLUSTER_TARGET",
    "MANAGER_OIDC_ISSUER", "MANAGER_OIDC_JWKS_URI",
    "PROMETHEUS_NAMESPACE", "EXPECTED_NAMESPACE_COUNT", "SOURCE_GENERATION",
    "TOOLBOX_IMAGE", "VECTOR_IMAGE",
}


def validate(values: dict) -> None:
    missing = sorted(REQUIRED - values.keys())
    extra = sorted(values.keys() - REQUIRED)
    if missing or extra:
        raise ValueError("values keys differ: missing={} extra={}".format(missing, extra))
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise ValueError("every value must be a non-empty string")
    for name, value in values.items():
        if len(value) > 2048 or any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("{} contains a control character or is too long".format(name))
        if any(character in value for character in ("'", '"', "\\")):
            raise ValueError("{} contains a forbidden quote or escape character".format(name))
    if any(TOKEN.search(value) for value in values.values()):
        raise ValueError("values file still contains placeholder tokens")
    for name in ("ASSESSOR_IMAGE", "FOX_IMAGE", "TOOLBOX_IMAGE", "VECTOR_IMAGE"):
        if not IMAGE.fullmatch(values[name]):
            raise ValueError("{} must be an immutable image@sha256 reference".format(name))
    for name in ("GITLAB_EGRESS_CIDR", "KAFKA_EGRESS_CIDR", "KUBERNETES_API_CIDR", "MANAGER_KUBERNETES_API_CIDR"):
        ipaddress.ip_network(values[name], strict=False)
    for name in (
        "AGENTGATEWAY_GATEWAY_NAME", "AGENTGATEWAY_LISTENER_NAME", "AGENTGATEWAY_NAMESPACE", "AGENTGATEWAY_SERVICE_NAME",
        "AKS_MCP_INSTANCE_LABEL", "AKS_MCP_SERVER_NAME", "AKS_MCP_SERVICE_ACCOUNT_NAME", "AKS_MCP_SERVICE_ACCOUNT_NAMESPACE",
        "GITLAB_CREDENTIALS_SECRET", "KAFKA_CREDENTIALS_SECRET", "KAGENT_CONTROLLER_SERVICE_NAME",
        "PROMETHEUS_NAMESPACE", "KAGENT_NAMESPACE",
    ):
        if not DNS_LABEL.fullmatch(values[name]):
            raise ValueError("{} must be a Kubernetes DNS label".format(name))
    for name in ("CLUSTER_ID", "MCP_CLUSTER_TARGET"):
        if not DNS_LABEL.fullmatch(values[name]):
            raise ValueError("{} must be a Kubernetes DNS label".format(name))
    if not values["KAGENT_A2A_URL"].endswith("/"):
        raise ValueError("KAGENT_A2A_URL must include the required trailing slash")
    for name, lower, upper in (("AGENTGATEWAY_PORT", 1, 65535), ("AGENTGATEWAY_TARGET_PORT", 1, 65535), ("AKS_MCP_PORT", 1, 65535), ("GITLAB_PORT", 1, 65535), ("KAFKA_PORT", 1, 65535), ("EXPECTED_NAMESPACE_COUNT", 1, 1000)):
        if not values[name].isdigit() or not lower <= int(values[name]) <= upper:
            raise ValueError("{} must be an integer from {} to {}".format(name, lower, upper))
    scope = json.loads((ROOT.parent / "fox-mesh/namespaces.json").read_text(encoding="utf-8"))
    actual_count = len(scope.get("namespaces", []))
    if int(values["EXPECTED_NAMESPACE_COUNT"]) != actual_count:
        raise ValueError(
            "EXPECTED_NAMESPACE_COUNT {} does not match namespaces.json count {}".format(
                values["EXPECTED_NAMESPACE_COUNT"], actual_count
            )
        )
    parsed_a2a = urllib.parse.urlparse(values["KAGENT_A2A_URL"])
    expected_host = "{}.{}.svc.cluster.local".format(
        values["AGENTGATEWAY_SERVICE_NAME"], values["AGENTGATEWAY_NAMESPACE"]
    )
    if parsed_a2a.scheme not in {"http", "https"} or not parsed_a2a.hostname:
        raise ValueError("KAGENT_A2A_URL must be an HTTP(S) service URL")
    if parsed_a2a.hostname != expected_host:
        raise ValueError("KAGENT_A2A_URL must target the configured agentgateway Service")
    if parsed_a2a.port != int(values["AGENTGATEWAY_PORT"]):
        raise ValueError("KAGENT_A2A_URL port must match AGENTGATEWAY_PORT")
    if parsed_a2a.path != "/a2a/cluster-health/":
        raise ValueError("KAGENT_A2A_URL must use the fixed cluster-health gateway route")
    for name in ("MANAGER_OIDC_ISSUER", "MANAGER_OIDC_JWKS_URI"):
        parsed = urllib.parse.urlparse(values[name])
        if (
            parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or not SAFE_HTTPS_URL.fullmatch(values[name])
        ):
            raise ValueError("{} must be a simple HTTPS URL without credentials, query or fragment".format(name))
    if not AUDIENCE.fullmatch(values["AGENTGATEWAY_AUDIENCE"]):
        raise ValueError("AGENTGATEWAY_AUDIENCE must be one dedicated api:// identifier")
    brokers = [item.strip() for item in values["KAFKA_BOOTSTRAP"].split(",")]
    if not brokers or any(not re.fullmatch(r"[A-Za-z0-9.-]+:[0-9]+", item) for item in brokers):
        raise ValueError("KAFKA_BOOTSTRAP must be a comma-separated host:port list")
    if any(int(item.rsplit(":", 1)[1]) != int(values["KAFKA_PORT"]) for item in brokers):
        raise ValueError("every KAFKA_BOOTSTRAP broker must use KAFKA_PORT")
    gitlab = urllib.parse.urlparse(values["GITLAB_API_URL"])
    if gitlab.scheme != "https" or not gitlab.hostname or gitlab.path not in {"", "/"}:
        raise ValueError("GITLAB_API_URL must be an HTTPS origin without a path")
    if (gitlab.port or 443) != int(values["GITLAB_PORT"]):
        raise ValueError("GITLAB_API_URL port must match GITLAB_PORT")
    if values["GITLAB_WRITE_ENABLED"] not in {"true", "false"}:
        raise ValueError("GITLAB_WRITE_ENABLED must be true or false")
    if ":latest" in " ".join(values.values()):
        raise ValueError("floating latest tags are forbidden")


def render(component: str, values: dict) -> str:
    generated = subprocess.run(
        ["kubectl", "kustomize", str(ROOT / component)],
        check=True, text=True, capture_output=True,
    ).stdout
    for name in ("ASSESSOR_IMAGE", "FOX_IMAGE", "VECTOR_IMAGE"):
        generated = generated.replace("{{{{{}}}}}:workplace".format(name), values[name])
    generated = re.sub(
        r"(^\s*(?:-\s*)?port:\s*)9092(\s*$)",
        lambda match: match.group(1) + values["KAFKA_PORT"] + match.group(2),
        generated,
        flags=re.MULTILINE,
    )
    generated = re.sub(
        r"(^\s*(?:-\s*)?port:\s*)38080(\s*$)",
        lambda match: match.group(1) + values["AGENTGATEWAY_TARGET_PORT"] + match.group(2),
        generated,
        flags=re.MULTILINE,
    )
    generated = re.sub(
        r"(^\s*(?:-\s*)?port:\s*)38000(\s*$)",
        lambda match: match.group(1) + values["AKS_MCP_PORT"] + match.group(2),
        generated,
        flags=re.MULTILINE,
    )
    generated = re.sub(
        r"(^\s*(?:-\s*)?port:\s*)31443(\s*$)",
        lambda match: match.group(1) + values["GITLAB_PORT"] + match.group(2),
        generated,
        flags=re.MULTILINE,
    )
    for name, value in values.items():
        generated = generated.replace("{{{{{}}}}}".format(name), value)
    unresolved = sorted(set(TOKEN.findall(generated)))
    if unresolved:
        raise ValueError("unresolved placeholders in {}: {}".format(component, unresolved))
    if ":latest" in generated:
        raise ValueError("rendered manifest contains a floating latest tag")
    return generated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--values", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    values = json.loads(args.values.read_text(encoding="utf-8"))
    if not isinstance(values, dict):
        raise ValueError("values file must contain one JSON object")
    validate(values)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for component in ("worker", "manager"):
        target = args.output_dir / (component + ".yaml")
        target.write_text(render(component, values), encoding="utf-8")
        print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

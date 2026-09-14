#!/usr/bin/env python3
"""Fail-closed schema validation for bounded homelab proof evidence."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


HOST_ALIAS = "red-homelab"
TARGET_ALIAS = "proxmox-homelab"
ALIASES = {HOST_ALIAS, TARGET_ALIAS}
EXPECTED_TOOLS = {
    "configuration_contexts_list",
    "events_list",
    "namespaces_list",
    "pods_get",
    "pods_list",
    "pods_list_in_namespace",
    "pods_log",
    "resources_get",
    "resources_list",
}
BLOCKED_TOOLS = {
    "configuration_view",
    "pods_exec",
    "resources_create_or_update",
    "resources_delete",
    "resources_scale",
}
FORBIDDEN_TEXT = re.compile(
    r"https?://|BEGIN [A-Z ]*(?:PRIVATE KEY|CERTIFICATE)|"
    r"certificate-authority-data|client-certificate-data|client-key-data|"
    r"kind-homelab|proxmox-k8s|rawPrompt|kubeconfig:",
    re.IGNORECASE,
)
MAX_FILE_BYTES = 64 * 1024


class EvidenceError(ValueError):
    """Evidence does not match the bounded public-safe contract."""


def require_exact_keys(value: Any, expected: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise EvidenceError(f"{name} keys do not match the bounded schema")
    return value


def validate_contexts(value: Any) -> None:
    if value != [
        {"alias": HOST_ALIAS, "nodeCount": 1},
        {"alias": TARGET_ALIAS, "nodeCount": 3},
    ]:
        raise EvidenceError("context evidence drifted")


def validate_client(value: Any) -> None:
    document = require_exact_keys(
        value,
        {
            "schema",
            "status",
            "contexts",
            "toolNames",
            "blockedTools",
            "requests",
            "crossoverCount",
        },
        "client evidence",
    )
    if document["schema"] != "homelab-cross-cluster-mcp/v1" or document["status"] != "PASS":
        raise EvidenceError("client proof did not pass")
    validate_contexts(document["contexts"])
    if set(document["toolNames"]) != EXPECTED_TOOLS or len(document["toolNames"]) != len(EXPECTED_TOOLS):
        raise EvidenceError("client tool allowlist drifted")
    blocked = document["blockedTools"]
    if not isinstance(blocked, list) or {
        item.get("tool") for item in blocked if isinstance(item, dict)
    } != BLOCKED_TOOLS:
        raise EvidenceError("blocked tool evidence drifted")
    if any(
        set(item) != {"tool", "status"} or item["status"] != "REJECTED"
        for item in blocked
        if isinstance(item, dict)
    ) or len(blocked) != len(BLOCKED_TOOLS):
        raise EvidenceError("a blocked tool was not rejected")
    requests = document["requests"]
    if not isinstance(requests, list) or len(requests) != 20:
        raise EvidenceError("client request evidence must contain exactly 20 entries")
    for sequence, item in enumerate(requests, start=1):
        request = require_exact_keys(item, {"sequence", "context", "nodeCount", "status"}, "request")
        expected_alias = HOST_ALIAS if sequence % 2 else TARGET_ALIAS
        expected_count = 1 if expected_alias == HOST_ALIAS else 3
        if request != {
            "sequence": sequence,
            "context": expected_alias,
            "nodeCount": expected_count,
            "status": "PASS",
        }:
            raise EvidenceError("client request sequence or routing result drifted")
    if document["crossoverCount"] != 0:
        raise EvidenceError("client proof recorded a context crossover")


def expected_rbac_checks() -> set[tuple[str, str]]:
    checks: set[str] = set()
    readable = [
        "namespaces",
        "nodes",
        "pods",
        "pods_status",
        "events",
        "deployments.apps",
        "replicasets.apps",
        "statefulsets.apps",
        "daemonsets.apps",
        "jobs.batch",
        "cronjobs.batch",
    ]
    for verb in ("get", "list", "watch"):
        checks.update(f"{verb}_{resource}_yes" for resource in readable)
    checks.add("get_pods_log_yes")
    checks.update(
        f"get_{resource}_no"
        for resource in (
            "secrets",
            "serviceaccounts",
            "roles.rbac.authorization.k8s.io",
            "rolebindings.rbac.authorization.k8s.io",
            "clusterroles.rbac.authorization.k8s.io",
            "clusterrolebindings.rbac.authorization.k8s.io",
        )
    )
    checks.update({"create_serviceaccounts_token_no", "create_pods_exec_no"})
    for verb in ("create", "update", "patch", "delete"):
        checks.update(f"{verb}_{resource}_no" for resource in ("pods", "deployments.apps", "jobs.batch"))
    return {(alias, check) for alias in ALIASES for check in checks}


def validate_rbac(value: Any) -> None:
    document = require_exact_keys(value, {"schema", "status", "checks"}, "RBAC evidence")
    if document["schema"] != "homelab-cross-cluster-rbac/v1" or document["status"] != "PASS":
        raise EvidenceError("RBAC proof did not pass")
    checks = document["checks"]
    if not isinstance(checks, list):
        raise EvidenceError("RBAC checks are malformed")
    observed: set[tuple[str, str]] = set()
    for item in checks:
        check = require_exact_keys(item, {"context", "check", "status"}, "RBAC check")
        if check["context"] not in ALIASES or check["status"] != "PASS":
            raise EvidenceError("RBAC check contains an unsafe value")
        observed.add((check["context"], check["check"]))
    expected = expected_rbac_checks()
    if observed != expected or len(checks) != len(expected):
        raise EvidenceError("RBAC evidence is incomplete or duplicated")


def validate_runtime(value: Any) -> None:
    expected = {
        "schema": "homelab-cross-cluster-proof/v1",
        "status": "PASS",
        "contexts": [
            {"alias": HOST_ALIAS, "nodeCount": 1},
            {"alias": TARGET_ALIAS, "nodeCount": 3},
        ],
        "alternatingRequests": 20,
        "crossoverCount": 0,
        "toolSurface": "allowlist-only",
        "rbac": "positive-and-negative-checks-passed",
        "endpoint": "ClusterIP-only",
        "teardownVerified": True,
        "defaultKubectlMcpUidUnchanged": True,
        "networkPolicyLimitation": "KindNet manifest present; enforcement not claimed",
    }
    if value != expected:
        raise EvidenceError("runtime summary drifted from the bounded schema")


VALIDATORS = {
    "client-summary.json": validate_client,
    "rbac-summary.json": validate_rbac,
    "runtime-summary.json": validate_runtime,
}


def scan_directory(directory: pathlib.Path) -> None:
    files = {path.name: path for path in directory.iterdir() if path.is_file()}
    if set(files) != set(VALIDATORS):
        raise EvidenceError("evidence directory contains missing or unexpected files")
    for name, validator in VALIDATORS.items():
        path = files[name]
        if path.stat().st_size > MAX_FILE_BYTES:
            raise EvidenceError(f"{name} exceeds the bounded size limit")
        raw = path.read_text(encoding="utf-8")
        if FORBIDDEN_TEXT.search(raw):
            raise EvidenceError(f"{name} contains a forbidden sensitive value shape")
        validator(json.loads(raw))


def self_test() -> None:
    requests = [
        {
            "sequence": sequence,
            "context": HOST_ALIAS if sequence % 2 else TARGET_ALIAS,
            "nodeCount": 1 if sequence % 2 else 3,
            "status": "PASS",
        }
        for sequence in range(1, 21)
    ]
    client = {
        "schema": "homelab-cross-cluster-mcp/v1",
        "status": "PASS",
        "contexts": [
            {"alias": HOST_ALIAS, "nodeCount": 1},
            {"alias": TARGET_ALIAS, "nodeCount": 3},
        ],
        "toolNames": sorted(EXPECTED_TOOLS),
        "blockedTools": [{"tool": tool, "status": "REJECTED"} for tool in sorted(BLOCKED_TOOLS)],
        "requests": requests,
        "crossoverCount": 0,
    }
    rbac = {
        "schema": "homelab-cross-cluster-rbac/v1",
        "status": "PASS",
        "checks": [
            {"context": alias, "check": check, "status": "PASS"}
            for alias, check in sorted(expected_rbac_checks())
        ],
    }
    runtime = {
        "schema": "homelab-cross-cluster-proof/v1",
        "status": "PASS",
        "contexts": client["contexts"],
        "alternatingRequests": 20,
        "crossoverCount": 0,
        "toolSurface": "allowlist-only",
        "rbac": "positive-and-negative-checks-passed",
        "endpoint": "ClusterIP-only",
        "teardownVerified": True,
        "defaultKubectlMcpUidUnchanged": True,
        "networkPolicyLimitation": "KindNet manifest present; enforcement not claimed",
    }
    validate_client(client)
    validate_rbac(rbac)
    validate_runtime(runtime)
    leaked = dict(runtime)
    leaked["endpoint"] = "https://private.example.invalid"
    try:
        validate_runtime(leaked)
    except EvidenceError:
        return
    raise EvidenceError("self-test accepted an unexpected endpoint")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_dir", nargs="?", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            if args.evidence_dir is not None:
                raise EvidenceError("self-test does not accept an evidence directory")
            self_test()
        elif args.evidence_dir is None or not args.evidence_dir.is_dir():
            raise EvidenceError("an existing evidence directory is required")
        else:
            scan_directory(args.evidence_dir)
    except (EvidenceError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"evidence scan: FAIL ({exc})", file=sys.stderr)
        return 1
    print("evidence scan: PASS (strict bounded schemas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

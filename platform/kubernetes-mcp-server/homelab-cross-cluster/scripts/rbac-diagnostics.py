#!/usr/bin/env python3
"""Render only bounded, public-safe RBAC diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from typing import NoReturn


HOST_ALIAS = "red-homelab"
TARGET_ALIAS = "proxmox-homelab"
ALIASES = {HOST_ALIAS, TARGET_ALIAS}
ACTUAL_RESULTS = {"allow", "deny", "error"}


class DiagnosticError(ValueError):
    """A diagnostic value is outside the exact public-safe contract."""


def expected_check_ids() -> set[str]:
    readable = (
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
    )
    checks = {
        f"{verb}_{resource}_yes"
        for verb in ("get", "list", "watch")
        for resource in readable
    }
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
    checks.update(
        f"{verb}_{resource}_no"
        for verb in ("create", "update", "patch", "delete")
        for resource in ("pods", "deployments.apps", "jobs.batch")
    )
    return checks


CHECK_IDS = expected_check_ids()
EXPECTED_CHECK_COUNT = len(CHECK_IDS) * len(ALIASES)


def compact_json(value: dict[str, object]) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def render_check(
    check: str,
    context: str,
    expected: str,
    actual: str,
    result: str,
) -> str:
    if check not in CHECK_IDS:
        raise DiagnosticError("check identifier is not allowlisted")
    if context not in ALIASES:
        raise DiagnosticError("context alias is not allowlisted")
    if expected not in {"allow", "deny"}:
        raise DiagnosticError("expected status is not allowlisted")
    expected_suffix = "yes" if expected == "allow" else "no"
    if not check.endswith(f"_{expected_suffix}"):
        raise DiagnosticError("check identifier and expected status disagree")
    if actual not in ACTUAL_RESULTS:
        raise DiagnosticError("actual status is not allowlisted")
    computed = "PASS" if actual == expected else "FAIL"
    if result != computed:
        raise DiagnosticError("reported check result is inconsistent")
    return "RBAC_DIAGNOSTIC: " + compact_json(
        {
            "actual": actual,
            "check": check,
            "context": context,
            "expected": expected,
            "result": result,
        }
    )


def render_overall(checks: int, failures: int, result: str) -> str:
    if checks != EXPECTED_CHECK_COUNT:
        raise DiagnosticError("overall check count is not the exact bounded matrix")
    if failures < 0 or failures > checks:
        raise DiagnosticError("overall failure count is invalid")
    computed = "PASS" if failures == 0 else "FAIL"
    if result != computed:
        raise DiagnosticError("reported overall result is inconsistent")
    return "RBAC_RESULT: " + compact_json(
        {"checks": checks, "failures": failures, "result": result}
    )


def expect_rejected(value: str) -> None:
    try:
        render_check("get_namespaces_yes", HOST_ALIAS, "allow", value, "FAIL")
    except DiagnosticError:
        return
    raise DiagnosticError("self-test accepted a forbidden diagnostic value")


def self_test() -> None:
    expected = (
        'RBAC_DIAGNOSTIC: {"actual":"deny","check":"get_namespaces_yes",'
        '"context":"red-homelab","expected":"allow","result":"FAIL"}'
    )
    if render_check("get_namespaces_yes", HOST_ALIAS, "allow", "deny", "FAIL") != expected:
        raise DiagnosticError("self-test diagnostic rendering drifted")
    if render_overall(EXPECTED_CHECK_COUNT, 1, "FAIL") != (
        f'RBAC_RESULT: {{"checks":{EXPECTED_CHECK_COUNT},"failures":1,"result":"FAIL"}}'
    ):
        raise DiagnosticError("self-test overall rendering drifted")

    forbidden_shapes = {
        "credential": "client" + "_secret=example-value",
        "token": "ey" + "JhbGciOiJub25lIn0.example.signature",
        "url": "ht" + "tps://private.example.invalid",
        "pem": "-----BEGIN " + "PRIVATE KEY-----",
        "kubeconfig": "apiVersion: v1\n" + "clusters:",
        "secret": "se" + "cret=example-value",
        "authorization-header": "Authori" + "zation: Bearer example-value",
    }
    for value in forbidden_shapes.values():
        expect_rejected(value)


def fail(message: str) -> NoReturn:
    print(f"rbac diagnostic rejected: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--check", required=True)
    check_parser.add_argument("--context", required=True)
    check_parser.add_argument("--expected", required=True)
    check_parser.add_argument("--actual", required=True)
    check_parser.add_argument("--result", required=True)

    overall_parser = subparsers.add_parser("overall")
    overall_parser.add_argument("--checks", required=True, type=int)
    overall_parser.add_argument("--failures", required=True, type=int)
    overall_parser.add_argument("--result", required=True)

    subparsers.add_parser("self-test")
    args = parser.parse_args()
    try:
        if args.command == "check":
            print(render_check(args.check, args.context, args.expected, args.actual, args.result))
        elif args.command == "overall":
            print(render_overall(args.checks, args.failures, args.result))
        else:
            self_test()
    except DiagnosticError as exc:
        fail(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Capture a bounded, public-safe receipt for one existing kagent A2A route."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "kagent-a2a-trajectory-receipt/v1"
TARGET_SCHEMA_VERSION = "kagent-a2a-readonly-targets/v1"
MAX_RESPONSE_BYTES = 4096
MAX_TIMEOUT_SECONDS = 300
SAFE_DNS_NAME = re.compile(r"^[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?$")
SAFE_MARKER = re.compile(r"^[A-Z][A-Z0-9_:-]{2,79}$")
WRITE_TOOL = re.compile(
    r"(?i)(?:^|_)(apply|create|delete|edit|exec|patch|replace|restart|scale|sync|"
    r"update|write|rollout|cordon|drain)(?:_|$)"
)
CREDENTIAL = re.compile(
    r"(?is)(bearer\s+[A-Za-z0-9._~+/=-]+|-----BEGIN [A-Z ]*PRIVATE KEY-----.*?"
    r"-----END [A-Z ]*PRIVATE KEY-----|\b(?:password|passwd|client_secret|"
    r"access_token|refresh_token|api[_-]?key|auth[_-]?token|token)\s*[:=]\s*\S+)"
)
KUBECONFIG_OR_SECRET = re.compile(
    r"(?i)((?:certificate-authority-data|client-certificate-data|client-key-data|"
    r"current-context)\s*:\s*\S+|kind\s*:\s*secret\b)"
)
PRIVATE_ENDPOINT = re.compile(
    r"(?i)(https?://\S+|\b(?:10|127)\.(?:\d{1,3}\.){2}\d{1,3}\b|"
    r"\b192\.168\.(?:\d{1,3}\.)\d{1,3}\b|\b172\.(?:1[6-9]|2\d|3[01])\."
    r"(?:\d{1,3}\.)\d{1,3}\b|\b(?:[a-z0-9-]+\.)+(?:internal|local)\b)"
)
PROMPT_INJECTION = re.compile(
    r"(?i)(ignore (?:all |the )?(?:previous|prior) instructions|reveal (?:the )?"
    r"system prompt|system prompt|act as (?:an? )?(?:admin|root)|execute the "
    r"following command|disregard (?:all |the )?(?:previous|prior) instructions)"
)


class ReceiptError(ValueError):
    """A fail-closed receipt precondition was not met."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def validate_name(value: str, option: str) -> str:
    if not SAFE_DNS_NAME.fullmatch(value):
        raise ReceiptError(f"invalid_{option}")
    return value


def safe_identity(value: str) -> str:
    return value if SAFE_DNS_NAME.fullmatch(value) else "invalid"


def load_target(path: Path, target_name: str, context: str, namespace: str, agent: str) -> dict[str, Any]:
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ReceiptError("invalid_target_registry") from None
    if registry.get("schema_version") != TARGET_SCHEMA_VERSION or not isinstance(registry.get("targets"), list):
        raise ReceiptError("invalid_target_registry")
    matches = [item for item in registry["targets"] if isinstance(item, dict) and item.get("name") == target_name]
    if len(matches) != 1:
        raise ReceiptError("target_not_allowlisted")
    target = matches[0]
    if target.get("read_only") is not True:
        raise ReceiptError("target_not_read_only")
    expected = (target.get("context_alias"), target.get("namespace"), target.get("agent"))
    if expected != (context, namespace, agent):
        raise ReceiptError("target_identity_mismatch")
    policies = target.get("agent_policies")
    if not isinstance(policies, dict) or agent not in policies:
        raise ReceiptError("invalid_target_registry")
    return target


def _condition_true(agent: dict[str, Any], condition_type: str) -> bool:
    conditions = agent.get("status", {}).get("conditions", [])
    return any(
        isinstance(item, dict) and item.get("type") == condition_type and item.get("status") == "True"
        for item in conditions
    )


def validate_agent_inventory(agent: dict[str, Any], policy: dict[str, Any], *, require_accepted: bool = True) -> list[str]:
    if not _condition_true(agent, "Ready") or (require_accepted and not _condition_true(agent, "Accepted")):
        raise ReceiptError("agent_not_ready")
    declared_tools = policy.get("tools")
    declared_delegates = policy.get("delegates")
    if not isinstance(declared_tools, list) or not isinstance(declared_delegates, list):
        raise ReceiptError("invalid_target_registry")
    if any(not isinstance(name, str) or WRITE_TOOL.search(name) for name in declared_tools):
        raise ReceiptError("write_capable_tool_denied")

    actual_tools: list[str] = []
    actual_delegates: list[str] = []
    tools = agent.get("spec", {}).get("declarative", {}).get("tools", [])
    if not isinstance(tools, list):
        raise ReceiptError("agent_inventory_malformed")
    for entry in tools:
        if not isinstance(entry, dict):
            raise ReceiptError("agent_inventory_malformed")
        if entry.get("type") == "McpServer":
            names = entry.get("mcpServer", {}).get("toolNames")
            if not isinstance(names, list) or any(not isinstance(name, str) for name in names):
                raise ReceiptError("unbounded_tool_inventory")
            actual_tools.extend(names)
        elif entry.get("type") == "Agent":
            name = entry.get("agent", {}).get("name")
            if not isinstance(name, str):
                raise ReceiptError("agent_inventory_malformed")
            actual_delegates.append(name)
        else:
            raise ReceiptError("unknown_tool_type")
    if sorted(set(actual_tools)) != sorted(set(declared_tools)):
        raise ReceiptError("tool_allowlist_mismatch")
    if sorted(set(actual_delegates)) != sorted(set(declared_delegates)):
        raise ReceiptError("delegate_allowlist_mismatch")
    if any(WRITE_TOOL.search(name) for name in actual_tools):
        raise ReceiptError("write_capable_tool_denied")
    return actual_delegates


def kubectl_agent(context: str, namespace: str, agent: str) -> dict[str, Any]:
    command = [
        "kubectl", "--context", context, "get", "agent", agent,
        "--namespace", namespace, "--output", "json",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise ReceiptError("agent_preflight_failed") from None
    if completed.returncode != 0:
        raise ReceiptError("agent_preflight_failed")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise ReceiptError("agent_inventory_malformed") from None
    if not isinstance(value, dict):
        raise ReceiptError("agent_inventory_malformed")
    return value


def preflight_target(target: dict[str, Any]) -> None:
    context = target["context_alias"]
    namespace = target["namespace"]
    policies = target["agent_policies"]
    pending = [target["agent"]]
    visited: set[str] = set()
    while pending:
        agent_name = pending.pop(0)
        if agent_name in visited:
            continue
        if len(visited) >= 8 or agent_name not in policies:
            raise ReceiptError("delegate_not_allowlisted")
        inventory = kubectl_agent(context, namespace, agent_name)
        if inventory.get("metadata", {}).get("name") != agent_name:
            raise ReceiptError("agent_identity_mismatch")
        pending.extend(validate_agent_inventory(
            inventory, policies[agent_name], require_accepted=agent_name == target["agent"],
        ))
        visited.add(agent_name)


def base_receipt(target_name: str, context: str, namespace: str, agent: str, elapsed_ms: int) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "target": safe_identity(target_name),
        "context_alias": safe_identity(context),
        "namespace": safe_identity(namespace),
        "agent": safe_identity(agent),
        "terminal_outcome": "FAIL",
        "failure_reason": "incomplete_evidence",
        "reply_source": "none",
        "elapsed_ms": min(max(0, elapsed_ms), (MAX_TIMEOUT_SECONDS + 20) * 1000),
        "expected_marker_match": False,
        "response_digest": None,
        "redaction_status": "not_needed",
        "truncation_status": "not_needed",
    }


def fail_receipt(target_name: str, context: str, namespace: str, agent: str,
                 reason: str, elapsed_ms: int = 0) -> dict[str, Any]:
    receipt = base_receipt(target_name, context, namespace, agent, elapsed_ms)
    receipt["failure_reason"] = reason
    return receipt


def evaluate_helper_result(target_name: str, context: str, namespace: str, agent: str,
                           marker: str, returncode: int, stdout: str,
                           measured_elapsed_ms: int) -> dict[str, Any]:
    if returncode != 0:
        reasons = {
            2: "target_not_found",
            3: "transport_failure",
            4: "timeout",
            5: "incomplete_response",
        }
        return fail_receipt(
            target_name, context, namespace, agent,
            reasons.get(returncode, "invocation_failure"), measured_elapsed_ms,
        )
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return fail_receipt(target_name, context, namespace, agent, "malformed_response", measured_elapsed_ms)
    if not isinstance(payload, dict):
        return fail_receipt(target_name, context, namespace, agent, "malformed_response", measured_elapsed_ms)
    reply = payload.get("text")
    reply_source = payload.get("reply_source")
    terminal_state = payload.get("terminal_state")
    elapsed_ms = payload.get("elapsed_ms")
    if (
        payload.get("ok") is not True
        or payload.get("agent") != agent
        or terminal_state != "completed"
        or not isinstance(reply, str)
        or not reply
        or reply_source not in {"artifact", "history-fallback"}
        or not isinstance(elapsed_ms, int)
        or isinstance(elapsed_ms, bool)
        or elapsed_ms < 0
        or elapsed_ms > MAX_TIMEOUT_SECONDS * 1000
    ):
        return fail_receipt(target_name, context, namespace, agent, "malformed_response", measured_elapsed_ms)

    receipt = base_receipt(target_name, context, namespace, agent, elapsed_ms)
    receipt["reply_source"] = reply_source
    reply_lines = reply.rstrip().splitlines()
    receipt["expected_marker_match"] = bool(reply_lines and reply_lines[-1].strip() == marker)
    encoded = reply.encode("utf-8")
    retained = encoded
    if len(encoded) > MAX_RESPONSE_BYTES:
        retained = encoded[:MAX_RESPONSE_BYTES]
        receipt["truncation_status"] = "applied"
    safe_text = retained.decode("utf-8", errors="ignore")
    sensitive = bool(CREDENTIAL.search(safe_text) or KUBECONFIG_OR_SECRET.search(safe_text) or PRIVATE_ENDPOINT.search(safe_text))
    injected = bool(PROMPT_INJECTION.search(safe_text))
    if sensitive or injected:
        receipt["redaction_status"] = "applied"
    safe_text = CREDENTIAL.sub("[REDACTED]", safe_text)
    safe_text = KUBECONFIG_OR_SECRET.sub("[REDACTED]", safe_text)
    safe_text = PRIVATE_ENDPOINT.sub("[REDACTED]", safe_text)
    safe_text = PROMPT_INJECTION.sub("[UNTRUSTED_INSTRUCTION]", safe_text)
    receipt["response_digest"] = "sha256:" + hashlib.sha256(safe_text.encode("utf-8")).hexdigest()

    if receipt["truncation_status"] == "applied":
        receipt["failure_reason"] = "response_truncated"
    elif sensitive:
        receipt["failure_reason"] = "sensitive_content_detected"
    elif injected:
        receipt["failure_reason"] = "prompt_injection_detected"
    elif not receipt["expected_marker_match"]:
        receipt["failure_reason"] = "marker_mismatch"
    else:
        receipt["terminal_outcome"] = "PASS"
        receipt["failure_reason"] = "none"
    return receipt


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    if not path.parent.is_dir():
        raise ReceiptError("output_directory_missing")
    document = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=".a2a-receipt-", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(document)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def positive_timeout(value: str) -> int:
    try:
        timeout = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be an integer") from exc
    if not 1 <= timeout <= MAX_TIMEOUT_SECONDS:
        raise argparse.ArgumentTypeError(f"timeout must be between 1 and {MAX_TIMEOUT_SECONDS}")
    return timeout


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, help="explicit kubectl context alias")
    parser.add_argument("--namespace", required=True, help="existing Agent namespace")
    parser.add_argument("--agent", required=True, help="existing read-only Agent name")
    parser.add_argument("--timeout", required=True, type=positive_timeout, help="A2A timeout in seconds (1-300)")
    parser.add_argument("--expected-marker", required=True, help="safe exact marker required in the terminal reply")
    parser.add_argument("--target", required=True, help="exact checked-in read-only target name")
    parser.add_argument("--output", required=True, type=Path, help="public-safe receipt output path")
    parser.add_argument("--allowlist", type=Path, default=root / "a2a-readonly-targets.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        context = validate_name(args.context, "context")
        namespace = validate_name(args.namespace, "namespace")
        agent = validate_name(args.agent, "agent")
        target_name = validate_name(args.target, "target")
        if not SAFE_MARKER.fullmatch(args.expected_marker):
            raise ReceiptError("invalid_expected_marker")
        target = load_target(args.allowlist, target_name, context, namespace, agent)
        preflight_target(target)
        helper = Path(__file__).resolve().parent.parents[2] / "scripts" / "kagent-a2a-invoke.sh"
        if not helper.is_file() or not os.access(helper, os.X_OK):
            raise ReceiptError("helper_unavailable")
    except ReceiptError as exc:
        receipt = fail_receipt(args.target, args.context, args.namespace, args.agent, exc.reason)
        try:
            write_receipt(args.output, receipt)
        except ReceiptError:
            return 2
        print(f"A2A_TRAJECTORY_RECEIPT_FAIL reason={exc.reason}", file=sys.stderr)
        return 1

    prompt = (
        f"Use only allow-listed read-only Kubernetes tools to report whether namespace {namespace} "
        "has any Pods outside Running or Succeeded. Do not read Secrets, credentials, tokens, "
        "kubeconfig data, or private endpoints. Do not create, update, patch, delete, exec, restart, "
        f"scale, deploy, or delegate beyond your configured read-only agents. End with {args.expected_marker}."
    )
    command = [
        str(helper), "--context", context, "--ns", namespace, "--agent", agent,
        "--timeout", str(args.timeout), "--text", prompt, "--json",
    ]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=args.timeout + 20, check=False,
        )
        measured_ms = round((time.monotonic() - started) * 1000)
        receipt = evaluate_helper_result(
            target_name, context, namespace, agent, args.expected_marker,
            completed.returncode, completed.stdout, measured_ms,
        )
    except subprocess.TimeoutExpired:
        measured_ms = round((time.monotonic() - started) * 1000)
        receipt = fail_receipt(target_name, context, namespace, agent, "wrapper_timeout", measured_ms)
    try:
        write_receipt(args.output, receipt)
    except ReceiptError as exc:
        print(f"A2A_TRAJECTORY_RECEIPT_FAIL reason={exc.reason}", file=sys.stderr)
        return 2
    if receipt["terminal_outcome"] != "PASS":
        print(f"A2A_TRAJECTORY_RECEIPT_FAIL reason={receipt['failure_reason']}", file=sys.stderr)
        return 1
    print(f"A2A_TRAJECTORY_RECEIPT_PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

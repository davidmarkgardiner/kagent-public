#!/usr/bin/env python3
"""Deterministic, bounded routing for the smart-triage SRE orchestrator POC."""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SPECIALISTS = (
    "kubernetes", "network", "grafana", "gitops", "knowledge",
    "deployment", "policy", "trace",
)
WRITE_WORDS = {
    "apply", "create", "delete", "edit", "exec", "patch", "replace",
    "restart", "scale", "sync", "rollout-undo", "cordon", "drain",
}
SAFE_ALIAS = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
SAFE_TOKEN = re.compile(r"[^A-Za-z0-9._-]")
SENSITIVE = re.compile(
    r"(?i)(bearer\s+[A-Za-z0-9._~+/=-]+|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\b(?:password|passwd|client_secret|access_token|refresh_token)\s*[:=]\s*\S+)"
)
INJECTION = re.compile(
    r"(?i)(ignore (?:all |the )?(?:previous|prior) instructions|system prompt|"
    r"act as (?:an? )?(?:admin|root)|execute the following command)"
)
DEFAULT_BUDGETS = {
    "ordinarySpecialistLimit": 3,
    "fullAuditSpecialistLimit": 8,
    "parallelismLimit": 3,
    "modelCallLimit": 9,
    "toolCallLimit": 10,
    "elapsedSecondsLimit": 180,
    "perSpecialistOutputBytes": 4096,
    "totalEvidenceBytes": 16384,
}


class OrchestratorError(ValueError):
    """The bounded orchestration contract was not satisfied."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_lifecycle(path: str):
    spec = importlib.util.spec_from_file_location("finding_lifecycle_contract", path)
    if not spec or not spec.loader:
        raise OrchestratorError("unable to load the finding lifecycle contract")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def truncate_text(text: str, limit: int, source: str) -> tuple[str, dict[str, Any] | None]:
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text, None
    retained = encoded[:limit].decode("utf-8", errors="ignore")
    marker = {
        "marker": "TOOL_OUTPUT_TRUNCATED",
        "source": source,
        "originalBytes": len(encoded),
        "retainedBytes": len(retained.encode("utf-8")),
        "requiredAction": "Narrow the resource, time window or query before retrying.",
    }
    return retained + "\n" + canonical_json(marker), marker


def extract_alert(envelope: dict[str, Any]) -> dict[str, Any]:
    alerts = envelope.get("alerts")
    if not isinstance(alerts, list) or not alerts or not isinstance(alerts[0], dict):
        raise OrchestratorError("alert payload must contain at least one alert object")
    firing = next((item for item in alerts if item.get("status") == "firing"), alerts[0])
    firing.setdefault("labels", {})
    firing.setdefault("annotations", {})
    if not isinstance(firing["labels"], dict) or not isinstance(firing["annotations"], dict):
        raise OrchestratorError("alert labels and annotations must be objects")
    return firing


def _target_values(alert: dict[str, Any]) -> dict[str, str]:
    labels = alert["labels"]
    return {
        "clusterAlias": str(labels.get("cluster_alias", "")),
        "subscriptionAlias": str(labels.get("subscription_alias", labels.get("subscription_scope", ""))),
        "resourceGroup": str(labels.get("resource_group", "")),
        "cluster": str(labels.get("cluster", "")),
        "kubeContext": str(labels.get("kube_context", "")),
        "environment": str(labels.get("environment", labels.get("env", ""))),
        "namespace": str(labels.get("namespace", "")),
        "stableWorkload": str(
            labels.get("workload", labels.get("deployment", labels.get("statefulset", labels.get("daemonset", ""))))
        ),
    }


def resolve_target(alert: dict[str, Any], registry: dict[str, Any], run_id: str) -> dict[str, Any]:
    supplied = _target_values(alert)
    targets = registry.get("targets", [])
    if not isinstance(targets, list):
        raise OrchestratorError("target registry targets must be an array")
    alias = supplied["clusterAlias"]
    candidates = [item for item in targets if item.get("clusterAlias") == alias] if alias else []
    if not alias:
        candidates = [
            item for item in targets
            if supplied["cluster"] and item.get("cluster") == supplied["cluster"]
            and (not supplied["subscriptionAlias"] or item.get("subscriptionAlias") == supplied["subscriptionAlias"])
        ]
    missing = []
    conflicts = []
    if len(candidates) != 1:
        if not alias and not supplied["cluster"]:
            missing.append("clusterAlias or exact cluster")
        elif not candidates:
            conflicts.append("target is not in the approved registry")
        else:
            conflicts.append("target matches more than one approved registry row")
        return {
            "status": "BLOCKED_TARGET_CONTEXT", "missing": missing, "conflicts": conflicts,
            "kubectlAllowed": False, "credentialPreparation": {"planned": False, "executed": False, "count": 0},
        }

    target = dict(candidates[0])
    required = (
        "clusterAlias", "subscriptionAlias", "subscriptionRef", "resourceGroup",
        "cluster", "kubeContext", "environment",
    )
    missing.extend(key for key in required if not str(target.get(key, "")).strip())
    for field in ("subscriptionAlias", "resourceGroup", "cluster", "kubeContext", "environment"):
        if supplied[field] and supplied[field] != target.get(field):
            conflicts.append(f"{field} conflicts with approved registry")
    namespace = supplied["namespace"]
    cluster_scoped = str(alert["labels"].get("cluster_scoped", "false")).lower() == "true"
    if not namespace and not cluster_scoped:
        missing.append("namespace")
    if namespace and target.get("namespaces") and namespace not in target["namespaces"]:
        conflicts.append("namespace is not approved for the target")
    workload = supplied["stableWorkload"]
    if not workload and not cluster_scoped:
        missing.append("stableWorkload")
    if missing or conflicts:
        return {
            "status": "BLOCKED_TARGET_CONTEXT", "missing": sorted(set(missing)),
            "conflicts": sorted(set(conflicts)), "kubectlAllowed": False,
            "credentialPreparation": {"planned": False, "executed": False, "count": 0},
        }
    safe_run = SAFE_TOKEN.sub("-", run_id)[:80]
    if not SAFE_ALIAS.fullmatch(str(target["clusterAlias"])):
        raise OrchestratorError("approved cluster alias is not path safe")
    kubeconfig = f"/tmp/aks-triage/{safe_run}.kubeconfig"
    target.update({
        "namespace": namespace or "cluster-scope",
        "stableWorkload": workload or "cluster",
        "clusterScoped": cluster_scoped,
        "kubeconfigPath": kubeconfig,
    })
    target.pop("namespaces", None)
    target["subscriptionId"] = "PROTECTED_RUNTIME_VALUE"
    return {
        "status": "TARGET_READY",
        "target": target,
        "kubectlAllowed": True,
        "credentialPreparation": {
            "planned": True,
            "executed": False,
            "count": 1,
            "mode": "REQUEST_SPECIFIC_PLAN",
            "command": [
                "az", "aks", "get-credentials", "--subscription", "PROTECTED_RUNTIME_VALUE",
                "--resource-group", target["resourceGroup"], "--name", target["cluster"],
                "--file", kubeconfig, "--overwrite-existing",
            ],
            "forbiddenArguments": ["--admin"],
        },
        "kubectlRequirements": {
            "kubeconfig": kubeconfig,
            "context": target["kubeContext"],
            "namespace": target["namespace"],
            "sharedCurrentContextChanged": False,
        },
    }


def route_specialists(alert: dict[str, Any], full_health_audit: bool = False) -> tuple[list[str], dict[str, str]]:
    if full_health_audit:
        return list(SPECIALISTS), {name: "explicit bounded full-health audit" for name in SPECIALISTS}
    labels, annotations = alert["labels"], alert["annotations"]
    signal = " ".join(str(value) for value in (
        labels.get("alertname", ""), labels.get("event_reason", ""), labels.get("reason", ""),
        labels.get("failure", ""), annotations.get("summary", ""), annotations.get("description", ""),
    )).lower()
    selected: list[str]
    reason: str
    if re.search(r"crashloop|oom|imagepull|backoff|notready|restart", signal):
        selected, reason = ["kubernetes", "grafana"], "pod/workload health plus bounded recent logs"
    elif re.search(r"failedschedul|scheduling|capacity|preempt|evict|nodepressure|replica|hpa", signal):
        selected, reason = ["kubernetes", "deployment", "grafana"], "placement, capacity and deployment evidence"
    elif re.search(r"certificate|workload.?identity|managed.?identity|token|login|failedmount", signal):
        selected, reason = ["policy", "kubernetes"], "identity and policy evidence without secret retrieval"
    elif re.search(r"cronjob|\bjob\b|missed.?schedule", signal):
        selected, reason = ["kubernetes", "deployment"], "Job/CronJob status and controller evidence"
    elif re.search(r"network|dns|connect|ingress|endpoint|hubble", signal):
        selected, reason = ["network", "kubernetes", "grafana"], "network path and corroborating workload evidence"
    elif re.search(r"flux|helm|gitops|deployment|rollout", signal):
        selected, reason = ["deployment", "gitops", "knowledge"], "deployment state and cited runbook context"
    else:
        selected, reason = ["kubernetes", "knowledge"], "minimum safe general triage"
    return selected, {name: reason for name in selected}


def finding_domain(alert: dict[str, Any]) -> str:
    signal = " ".join(str(value) for value in alert["labels"].values()).lower()
    if re.search(r"certificate|identity|token|login|failedmount", signal):
        return "identity"
    if re.search(r"schedul|capacity|preempt|evict", signal):
        return "scheduling"
    if re.search(r"network|dns|ingress|endpoint", signal):
        return "network"
    return "pod-health"


def build_finding(alert: dict[str, Any], target: dict[str, Any], run_id: str,
                  specialist: str, observed_at: str | None = None) -> dict[str, Any]:
    labels = alert["labels"]
    raw_reason = str(labels.get("event_reason", labels.get("reason", labels.get("alertname", "UnclassifiedSignal"))))
    reason = SAFE_TOKEN.sub("_", raw_reason)[:96] or "UnclassifiedSignal"
    severity = str(labels.get("severity", "warning")).lower()
    if severity not in {"info", "warning", "critical"}:
        severity = "warning"
    observed = observed_at or str(alert.get("startsAt", ""))
    if not observed or observed == "0001-01-01T00:00:00Z":
        observed = utc_now()
    observed_resource = str(labels.get("pod", labels.get("resource", target["stableWorkload"])))
    return {
        "schemaVersion": "smart-triage-finding/v1",
        "runId": f"{run_id}-{specialist}"[:128],
        "observedAt": observed,
        "observationStatus": "resolved" if alert.get("status") == "resolved" else "firing",
        "target": {
            "subscriptionScope": target["subscriptionAlias"],
            "cluster": target["clusterAlias"],
            "environment": target["environment"],
            "namespace": target["namespace"],
        },
        "resource": {
            "kind": "Deployment" if labels.get("deployment") else "Pod",
            "stableWorkload": target["stableWorkload"],
            "observedResource": observed_resource,
        },
        "finding": {
            "domain": finding_domain(alert),
            "reason": reason,
            "severity": severity,
            "confidence": "high" if labels.get("sre_outcome") else "medium",
            "summary": f"{specialist} evidence for {reason} on {target['stableWorkload']}.",
            "identityStatus": "canonical",
        },
        "evidence": [{
            "source": specialist,
            "reference": f"alert={reason}; workload={target['stableWorkload']}; bounded=true",
            "observedAt": observed,
        }],
        "provenance": {"agent": f"smart-triage-{specialist}-specialist", "tools": []},
        "recommendedActions": ["An authorised SRE should review the bounded evidence and verify current state."],
    }


def apply_sre_correction(finding: dict[str, Any], correction: dict[str, Any]) -> dict[str, Any]:
    """Apply only a trusted, sanitized offline SRE evaluation fixture."""
    if correction.get("source") != "sanitized-sre-feedback" or correction.get("trustedFixture") is not True:
        raise OrchestratorError("SRE correction must be a trusted sanitized fixture")
    if correction.get("sreOutcome") != "FALSE_POSITIVE":
        raise OrchestratorError("unsupported SRE correction outcome")
    match = correction.get("match", {})
    if (
        finding["resource"]["stableWorkload"] != match.get("stableWorkload")
        or finding["finding"]["reason"] != match.get("reason")
    ):
        raise OrchestratorError("SRE correction does not match the finding identity")
    amended = json.loads(json.dumps(finding))
    update = correction.get("correction", {})
    for field in ("severity", "confidence", "summary"):
        if field in update:
            amended["finding"][field] = update[field]
    return amended


def post_lifecycle(url: str, finding: dict[str, Any], timeout: int = 10) -> dict[str, Any]:
    if not url:
        return {
            "status": "STATE_UNAVAILABLE", "notify": True, "autoTicketAllowed": False,
            "ticketAction": "NONE", "marker": "STATE_UNAVAILABLE",
        }
    request = urllib.request.Request(
        url.rstrip("/") + "/v1/findings/evaluate",
        data=canonical_json(finding).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return {
            "status": "STATE_UNAVAILABLE", "notify": True, "autoTicketAllowed": False,
            "ticketAction": "NONE", "marker": "STATE_UNAVAILABLE",
        }


def _extract_a2a_text(payload: dict[str, Any]) -> str:
    result = payload.get("result", {})
    texts = []
    for artifact in result.get("artifacts", []) or []:
        for part in artifact.get("parts", []) or []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                texts.append(part["text"])
    if not texts:
        for part in result.get("status", {}).get("message", {}).get("parts", []) or []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                texts.append(part["text"])
    return "\n".join(texts)


def call_live_specialist(name: str, endpoint: str, finding: dict[str, Any], timeout: int) -> str:
    body = {
        "jsonrpc": "2.0",
        "id": f"selective-{finding['runId']}",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": f"msg-{finding['runId']}",
                "role": "user",
                "parts": [{
                    "kind": "text",
                    "text": "SELECTIVE_FINDING_JSON: Return only one JSON finding matching smart-triage-finding/v1. " + canonical_json(finding),
                }],
            },
        },
    }
    request = urllib.request.Request(
        endpoint, data=canonical_json(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return _extract_a2a_text(json.loads(response.read().decode("utf-8")))


def call_live_commander(endpoint: str, report: dict[str, Any], timeout: int) -> str:
    evidence = {
        "runId": report["runId"],
        "target": report.get("target", {}),
        "lifecycleDecision": report.get("lifecycleDecision", {}),
        "specialistResults": report.get("specialistResults", []),
    }
    body = {
        "jsonrpc": "2.0",
        "id": f"selective-commander-{report['runId']}",
        "method": "message/send",
        "params": {"message": {
            "messageId": f"msg-commander-{report['runId']}",
            "role": "user",
            "parts": [{"kind": "text", "text": (
                "Synthesize only this validated evidence. Label every conclusion PROVEN, LIKELY or UNKNOWN. "
                + canonical_json(evidence)
            )}],
        }},
    }
    request = urllib.request.Request(
        endpoint, data=canonical_json(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return _extract_a2a_text(json.loads(response.read().decode("utf-8")))


def dispatch(name: str, finding: dict[str, Any], mode: str, endpoints: dict[str, str],
             validate: Callable[[Any], Any], budgets: dict[str, int]) -> dict[str, Any]:
    started = time.monotonic()
    try:
        if mode == "fixture":
            raw = canonical_json(finding)
            call_status = "FIXTURE_VALIDATED"
        else:
            endpoint = endpoints.get(name, "")
            if not endpoint:
                raise OrchestratorError("selected specialist endpoint is not configured")
            raw = call_live_specialist(name, endpoint, finding, min(60, budgets["elapsedSecondsLimit"]))
            call_status = "A2A_COMPLETED"
        bounded, marker = truncate_text(raw, budgets["perSpecialistOutputBytes"], name)
        parsed = json.loads(bounded.split("\n", 1)[0])
        validate(parsed)
        return {
            "specialist": name, "status": call_status, "finding": parsed,
            "latencyMs": int((time.monotonic() - started) * 1000),
            "truncation": marker, "toolTrajectory": [],
        }
    except urllib.error.HTTPError as exc:
        status = "ACCESS_DENIED" if exc.code in {401, 403} else "SPECIALIST_FAILED"
        return {"specialist": name, "status": status, "error": f"HTTP {exc.code}", "latencyMs": int((time.monotonic() - started) * 1000)}
    except (TimeoutError, urllib.error.URLError) as exc:
        return {"specialist": name, "status": "SPECIALIST_TIMEOUT", "error": type(exc).__name__, "latencyMs": int((time.monotonic() - started) * 1000)}
    except Exception as exc:
        return {"specialist": name, "status": "SPECIALIST_CONTRACT_FAILED", "error": str(exc)[:300], "latencyMs": int((time.monotonic() - started) * 1000)}


def markdown_report(report: dict[str, Any]) -> str:
    target = report.get("target", {})
    lines = [
        "# GitLab issue report",
        "",
        f"Run ID: `{report['runId']}`",
        f"Status: `{report['status']}`",
        f"Lifecycle: `{report.get('lifecycleDecision', {}).get('status', 'NOT_EVALUATED')}`",
        f"Ticket action: `{report.get('lifecycleDecision', {}).get('ticketAction', 'NONE')}`",
        "",
        "## Routing",
        f"- Subscription alias: {target.get('subscriptionAlias', 'UNKNOWN')}",
        f"- Resource group: {target.get('resourceGroup', 'UNKNOWN')}",
        f"- Cluster: {target.get('clusterAlias', 'UNKNOWN')}",
        f"- Kube context: {target.get('kubeContext', 'UNKNOWN')}",
        f"- Namespace: {target.get('namespace', 'UNKNOWN')}",
        f"- Workload: {target.get('stableWorkload', 'UNKNOWN')}",
        "",
        "## Evidence conclusions",
    ]
    for result in report.get("specialistResults", []):
        status = "PROVEN" if result.get("finding") else "UNKNOWN"
        lines.append(f"- {status} `{result['specialist']}`: {result['status']}")
    if not report.get("specialistResults"):
        lines.append("- UNKNOWN: no specialist evidence was collected")
    lines.extend([
        "",
        "## Human boundary",
        "No remediation was executed. Existing human alerting remains active.",
    ])
    return "\n".join(lines) + "\n"


def run_orchestrator(envelope: dict[str, Any], registry: dict[str, Any], run_id: str,
                     lifecycle_url: str, mode: str, full_health_audit: bool,
                     lifecycle_module, endpoints: dict[str, str] | None = None,
                     budgets: dict[str, int] | None = None) -> dict[str, Any]:
    started = time.monotonic()
    budgets = dict(DEFAULT_BUDGETS if budgets is None else budgets)
    alert = extract_alert(envelope)
    target_result = resolve_target(alert, registry, run_id)
    base = {
        "schemaVersion": "smart-triage-orchestrator-report/v1",
        "runId": run_id,
        "existingHumanAlertPath": True,
        "budgets": budgets,
        "selectedSpecialists": [],
        "skippedSpecialists": list(SPECIALISTS),
        "specialistResults": [],
        "targetResolution": target_result,
        "security": {
            "authority": "read-only",
            "untrustedEvidence": True,
            "writeToolsAvailable": False,
            "secretValuesRequested": False,
            "promptInjectionDetected": bool(INJECTION.search(canonical_json(alert))),
            "credentialLikeInputDetected": bool(SENSITIVE.search(canonical_json(alert))),
        },
    }
    if target_result["status"] != "TARGET_READY":
        base.update({
            "status": "BLOCKED_TARGET_CONTEXT", "lifecycleDecision": {"status": "NOT_EVALUATED", "ticketAction": "NONE"},
            "metrics": {
                "specialistCalls": 0, "synthesisCalls": 0, "modelCalls": 0,
                "selectedPathCalls": 0, "unconditionalBaselinePathCalls": 9,
                "toolCalls": 0, "elapsedMs": int((time.monotonic() - started) * 1000),
            },
        })
        base["reportMarkdown"] = markdown_report(base)
        return base
    target = target_result["target"]
    base["target"] = target
    lifecycle_finding = build_finding(alert, target, run_id, "orchestrator")
    lifecycle_module.validate_finding(lifecycle_finding)
    lifecycle = post_lifecycle(lifecycle_url, lifecycle_finding)
    base["lifecycleDecision"] = lifecycle
    if lifecycle.get("notify") is False:
        base.update({
            "status": "UNCHANGED_SUPPRESSED",
            "metrics": {
                "specialistCalls": 0, "synthesisCalls": 0, "modelCalls": 0,
                "selectedPathCalls": 0, "unconditionalBaselinePathCalls": 9,
                "toolCalls": 0, "elapsedMs": int((time.monotonic() - started) * 1000),
            },
        })
        base["reportMarkdown"] = markdown_report(base)
        return base
    selected, routing_reasons = route_specialists(alert, full_health_audit)
    limit = budgets["fullAuditSpecialistLimit"] if full_health_audit else budgets["ordinarySpecialistLimit"]
    if len(selected) > limit:
        selected = selected[:limit]
    base["selectedSpecialists"] = selected
    base["skippedSpecialists"] = [name for name in SPECIALISTS if name not in selected]
    base["routingReasons"] = routing_reasons
    endpoints = endpoints or {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=budgets["parallelismLimit"]) as executor:
        futures = {
            executor.submit(
                dispatch, name, build_finding(alert, target, run_id, name), mode,
                endpoints, lifecycle_module.validate_finding, budgets,
            ): name for name in selected
        }
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    results.sort(key=lambda item: selected.index(item["specialist"]))
    total_evidence = canonical_json(results)
    bounded, total_marker = truncate_text(total_evidence, budgets["totalEvidenceBytes"], "total-evidence")
    if total_marker:
        # Preserve structured status while refusing to put oversized evidence into synthesis.
        results = [{"specialist": "evidence-boundary", "status": "SPECIALIST_CONTRACT_FAILED", "truncation": total_marker}]
    base["specialistResults"] = results
    incomplete = any(item["status"] not in {"FIXTURE_VALIDATED", "A2A_COMPLETED"} for item in results)
    if mode == "fixture":
        commander = {"status": "FIXTURE_DETERMINISTIC", "output": "Synthesis derived only from validated fixture findings."}
    else:
        try:
            endpoint = endpoints.get("commander", "")
            if not endpoint:
                raise OrchestratorError("incident commander endpoint is not configured")
            commander_text = call_live_commander(endpoint, base, min(60, budgets["elapsedSecondsLimit"]))
            commander_output, commander_truncation = truncate_text(
                commander_text, budgets["totalEvidenceBytes"], "incident-commander"
            )
            commander = {"status": "A2A_COMPLETED", "output": commander_output, "truncation": commander_truncation}
        except Exception as exc:
            commander = {"status": "SYNTHESIS_UNAVAILABLE", "error": str(exc)[:300]}
            incomplete = True
    base["commanderSynthesis"] = commander
    base["status"] = "PARTIAL_EVIDENCE" if incomplete else "VALIDATED_REPORT"
    elapsed = int((time.monotonic() - started) * 1000)
    base["metrics"] = {
        "specialistCalls": len(selected),
        "synthesisCalls": 1,
        "modelCalls": 0 if mode == "fixture" else len(selected) + 1,
        "selectedPathCalls": len(selected) + 1,
        "unconditionalBaselinePathCalls": len(SPECIALISTS) + 1,
        "toolCalls": sum(len(item.get("toolTrajectory", [])) for item in results),
        "parallelismLimit": budgets["parallelismLimit"],
        "elapsedMs": elapsed,
        "lowerThanUnconditionalFanout": len(selected) + 1 < len(SPECIALISTS) + 1,
    }
    base["conclusions"] = [
        {
            "status": "PROVEN" if item.get("finding") else "UNKNOWN",
            "specialist": item["specialist"],
            "evidenceBoundary": None if item.get("finding") else item.get("status"),
        } for item in results
    ]
    base["reportMarkdown"] = markdown_report(base)
    return base


def write_outputs(report: dict[str, Any], output_dir: str) -> None:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (directory / "report.md").write_text(report["reportMarkdown"], encoding="utf-8")
    (directory / "status.txt").write_text(report["status"] + "\n", encoding="utf-8")
    (directory / "selected.json").write_text(canonical_json(report["selectedSpecialists"]) + "\n", encoding="utf-8")
    (directory / "metrics.json").write_text(canonical_json(report["metrics"]) + "\n", encoding="utf-8")
    (directory / "lifecycle-decision.json").write_text(canonical_json(report["lifecycleDecision"]) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run"])
    parser.add_argument("--alert-file")
    parser.add_argument("--alert-env", default="ALERT_PAYLOAD")
    parser.add_argument("--registry", required=True)
    parser.add_argument("--lifecycle-module", required=True)
    parser.add_argument("--lifecycle-url", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mode", choices=["fixture", "live"], default="fixture")
    parser.add_argument("--full-health-audit", action="store_true")
    parser.add_argument("--endpoints-json", default="{}")
    parser.add_argument("--output-dir", required=True)
    arguments = parser.parse_args()
    if arguments.alert_file:
        envelope = json.loads(Path(arguments.alert_file).read_text(encoding="utf-8"))
    else:
        envelope = json.loads(os.environ.get(arguments.alert_env, "{}"))
    registry = json.loads(Path(arguments.registry).read_text(encoding="utf-8"))
    lifecycle = load_lifecycle(arguments.lifecycle_module)
    report = run_orchestrator(
        envelope, registry, arguments.run_id, arguments.lifecycle_url,
        arguments.mode, arguments.full_health_audit, lifecycle,
        endpoints=json.loads(arguments.endpoints_json),
    )
    write_outputs(report, arguments.output_dir)
    print(canonical_json({
        "status": report["status"], "selected": report["selectedSpecialists"],
        "lifecycle": report["lifecycleDecision"].get("status"), "metrics": report["metrics"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

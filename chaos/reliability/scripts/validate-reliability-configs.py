#!/usr/bin/env python3
"""Validate public-safe ChaosTest and ReliabilitySuite config objects."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


LOWER_ENVS = {"dev", "test", "staging"}
ALLOWED_EXPERIMENTS = {"pod-delete", "pod-cpu-hog", "pod-network-latency"}


def fail(path: Path, message: str) -> str:
    return f"{path}: {message}"


def validate_chaos_test(path: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    metadata = data.get("metadata", {})
    labels = metadata.get("labels", {})
    spec = data.get("spec", {})
    target = spec.get("target", {})
    experiment = spec.get("experiment", {})
    safety = spec.get("safety", {})
    selector_labels = target.get("selector", {}).get("matchLabels", {})

    if data.get("apiVersion") != "reliability.platform.example/v1alpha1":
        errors.append(fail(path, "ChaosTest apiVersion must be reliability.platform.example/v1alpha1"))
    if data.get("kind") != "ChaosTest":
        errors.append(fail(path, "kind must be ChaosTest"))
    if labels.get("reliability.platform/env-tier") not in LOWER_ENVS:
        errors.append(fail(path, "metadata env-tier must be dev, test, or staging"))
    if target.get("environment") not in LOWER_ENVS:
        errors.append(fail(path, "target.environment must be dev, test, or staging"))
    if target.get("environment") == "production" or labels.get("reliability.platform/env-tier") == "production":
        errors.append(fail(path, "production chaos is excluded in v1"))
    if not target.get("namespace"):
        errors.append(fail(path, "target.namespace is required"))
    if selector_labels.get("reliability.platform/chaos-optin") != "true":
        errors.append(fail(path, 'target selector must include reliability.platform/chaos-optin: "true"'))
    if experiment.get("provider") != "litmus":
        errors.append(fail(path, "experiment.provider must be litmus"))
    if experiment.get("type") not in ALLOWED_EXPERIMENTS:
        errors.append(fail(path, f"experiment.type must be one of {sorted(ALLOWED_EXPERIMENTS)}"))
    if safety.get("requiresHITL") is not True:
        errors.append(fail(path, "safety.requiresHITL must be true"))
    if not safety.get("abortConditions"):
        errors.append(fail(path, "safety.abortConditions must not be empty"))
    if not safety.get("rollback"):
        errors.append(fail(path, "safety.rollback is required"))
    if spec.get("eval", {}).get("benchmark") != 8:
        errors.append(fail(path, "eval.benchmark must be 8 for the v1 benchmark model"))
    if spec.get("learning", {}).get("memoryUpdatePolicy") != "curator-only":
        errors.append(fail(path, "memory updates must be curator-only"))
    if spec.get("learning", {}).get("kbUpdatePolicy") != "hitl-gated-mr":
        errors.append(fail(path, "KB updates must be hitl-gated-mr"))

    return errors


def validate_reliability_suite(path: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    spec = data.get("spec", {})
    tiers = set(spec.get("environmentTiers", []))

    if data.get("apiVersion") != "reliability.platform.example/v1alpha1":
        errors.append(fail(path, "ReliabilitySuite apiVersion must be reliability.platform.example/v1alpha1"))
    if data.get("kind") != "ReliabilitySuite":
        errors.append(fail(path, "kind must be ReliabilitySuite"))
    if not tiers:
        errors.append(fail(path, "environmentTiers must not be empty"))
    if not tiers.issubset(LOWER_ENVS):
        errors.append(fail(path, "environmentTiers must be limited to dev, test, and staging"))
    if spec.get("scoring", {}).get("benchmark") != 8:
        errors.append(fail(path, "scoring.benchmark must be 8"))
    below = spec.get("reporting", {}).get("reviewManagerRouting", {}).get("belowBenchmark")
    if below != "review-manager-agent":
        errors.append(fail(path, "below-benchmark routing must target review-manager-agent"))
    if spec.get("schedulePolicy", {}).get("maxConcurrent", 0) < 1:
        errors.append(fail(path, "schedulePolicy.maxConcurrent must be at least 1"))

    return errors


def validate_chaos_engine(path: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    metadata = data.get("metadata", {})
    labels = metadata.get("labels", {})
    spec = data.get("spec", {})
    appinfo = spec.get("appinfo", {})
    experiments = spec.get("experiments", [])
    experiment_names = {item.get("name") for item in experiments if isinstance(item, dict)}

    if data.get("apiVersion") != "litmuschaos.io/v1alpha1":
        errors.append(fail(path, "ChaosEngine apiVersion must be litmuschaos.io/v1alpha1"))
    if data.get("kind") != "ChaosEngine":
        errors.append(fail(path, "kind must be ChaosEngine"))
    if labels.get("reliability.platform/env-tier") not in LOWER_ENVS:
        errors.append(fail(path, "ChaosEngine env-tier must be dev, test, or staging"))
    if metadata.get("namespace") != appinfo.get("appns"):
        errors.append(fail(path, "ChaosEngine spec.appinfo.appns must match metadata.namespace"))
    if "production" in {metadata.get("namespace"), appinfo.get("appns"), labels.get("reliability.platform/env-tier")}:
        errors.append(fail(path, "production ChaosEngine targets are excluded in v1"))
    if "reliability.platform/chaos-optin=true" not in appinfo.get("applabel", ""):
        errors.append(fail(path, "ChaosEngine applabel must include reliability.platform/chaos-optin=true"))
    if not experiment_names:
        errors.append(fail(path, "ChaosEngine must declare at least one experiment"))
    if not experiment_names.issubset(ALLOWED_EXPERIMENTS):
        errors.append(fail(path, f"ChaosEngine experiments must be limited to {sorted(ALLOWED_EXPERIMENTS)}"))
    if spec.get("chaosServiceAccount") != "k8s-chaos-admin":
        errors.append(fail(path, "ChaosEngine chaosServiceAccount must be k8s-chaos-admin for the first demo"))

    return errors


def load_docs(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [doc for doc in yaml.safe_load_all(handle) if doc]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    checked = 0
    for path in args.paths:
        for doc in load_docs(path):
            checked += 1
            kind = doc.get("kind")
            if kind == "ChaosTest":
                errors.extend(validate_chaos_test(path, doc))
            elif kind == "ReliabilitySuite":
                errors.extend(validate_reliability_suite(path, doc))
            elif kind == "ChaosEngine":
                errors.extend(validate_chaos_engine(path, doc))
            else:
                errors.append(fail(path, f"unsupported kind {kind!r}"))

    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        return 1

    print(f"RELIABILITY_CONFIG_VALID: yes checked={checked}")
    print("OUTPUT_SANITIZED: yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

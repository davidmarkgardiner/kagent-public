#!/usr/bin/env python3
"""
Kagent Chaos Eval POC
Runs chaos scenarios, scores infrastructure recovery, reports findings.
No embedded credentials in code. Sensitive values come from environment variables or Kubernetes objects.
"""

import subprocess
import time
import datetime
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTING_DIR = REPO_ROOT / "observability" / "agent-evals" / "scripts"
sys.path.insert(0, str(REPORTING_DIR))

from reporting import render_chaos_recovery_markdown, utc_now_iso, write_json, write_markdown

LANGFUSE_HOST = "http://langfuse-web.kagent.svc.cluster.local:3000"
NAMESPACE     = "kagent"

def run(cmd, timeout=60):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def log(msg):
    print(f"[{datetime.datetime.utcnow().isoformat()}] {msg}", flush=True)

# Scenario 1: Pod restart resilience
def scenario_pod_restart():
    log("SCENARIO 1: pod restart resilience - killing k8s-agent")
    t0 = time.time()
    run(f"kubectl delete pod -n {NAMESPACE} -l app=k8s-agent --force --grace-period=0 2>/dev/null || true")
    # Poll until pod is Running again
    for _ in range(30):
        out, _, rc = run(f"kubectl get pods -n {NAMESPACE} -l app=k8s-agent --no-headers 2>/dev/null | grep Running")
        if rc == 0 and out:
            break
        time.sleep(5)
    recovery_s = time.time() - t0
    log(f"  recovered in {recovery_s:.1f}s")
    return {
        "scenario": "pod_restart",
        "recovery_seconds": round(recovery_s, 1),
        "workflow_stability": 1.0 if recovery_s < 30 else (0.7 if recovery_s < 60 else 0.4),
        "notes": f"k8s-agent restarted and recovered in {recovery_s:.0f}s"
    }

# Scenario 2: Scale-to-zero resilience
def scenario_scale_zero():
    log("SCENARIO 2: scale-to-zero - chaos-triage-agent to 0 replicas, then restore")
    run(f"kubectl scale deployment chaos-triage-agent -n {NAMESPACE} --replicas=0")
    time.sleep(10)
    run(f"kubectl scale deployment chaos-triage-agent -n {NAMESPACE} --replicas=1")
    t0 = time.time()
    for _ in range(24):
        out, _, rc = run(f"kubectl get pods -n {NAMESPACE} -l app=chaos-triage-agent --no-headers 2>/dev/null | grep Running")
        if rc == 0 and out:
            break
        time.sleep(5)
    recovery_s = time.time() - t0
    log(f"  recovered in {recovery_s:.1f}s")
    return {
        "scenario": "scale_zero_restore",
        "recovery_seconds": round(recovery_s, 1),
        "workflow_stability": 1.0 if recovery_s < 45 else 0.6,
        "notes": f"chaos-triage-agent scaled to 0 then restored in {recovery_s:.0f}s"
    }

# Scenario 3: ClickHouse temporary outage
def scenario_clickhouse_outage():
    log("SCENARIO 3: ClickHouse outage - scale to 0 for 20s, restore")
    run(f"kubectl scale deployment clickhouse -n {NAMESPACE} --replicas=0")
    time.sleep(20)
    run(f"kubectl scale deployment clickhouse -n {NAMESPACE} --replicas=1")
    t0 = time.time()
    for _ in range(24):
        out, _, rc = run(f"kubectl get pods -n {NAMESPACE} -l app=clickhouse --no-headers 2>/dev/null | grep Running")
        if rc == 0 and out:
            break
        time.sleep(5)
    recovery_s = time.time() - t0
    # Check langfuse-web still alive after CH restored
    web_out, _, web_rc = run(f"kubectl get pods -n {NAMESPACE} -l app.kubernetes.io/component=web --no-headers 2>/dev/null | grep Running")
    langfuse_ok = web_rc == 0 and bool(web_out)
    log(f"  ClickHouse recovered in {recovery_s:.1f}s, Langfuse web ok={langfuse_ok}")
    return {
        "scenario": "clickhouse_outage",
        "recovery_seconds": round(recovery_s, 1),
        "workflow_stability": 1.0 if (recovery_s < 60 and langfuse_ok) else 0.5,
        "notes": f"ClickHouse 20s outage, recovered in {recovery_s:.0f}s, Langfuse ok={langfuse_ok}"
    }

# Recovery score
def compute_recovery_score(results):
    stabilities = [r["workflow_stability"] for r in results]
    avg_stability = sum(stabilities) / len(stabilities)
    score = round(avg_stability, 3)
    return score, avg_stability

def build_recovery_result(results, recovery_score, avg_stability):
    return {
        "schemaVersion": "agent-evals.kagent-public/v1alpha1",
        "kind": "ChaosRecoveryEvalResult",
        "completed_at": utc_now_iso(),
        "namespace": NAMESPACE,
        "recovery_score": recovery_score,
        "workflow_stability_avg": round(avg_stability, 3),
        "passed": recovery_score >= 0.7,
        "scenarios": results,
        "notes": [
            "This score measures infrastructure recovery only.",
            "Agent diagnosis quality is scored separately by observability/agent-evals.",
        ],
    }

if __name__ == "__main__":
    log("Starting chaos eval POC")
    results = []
    results.append(scenario_pod_restart())
    results.append(scenario_scale_zero())
    results.append(scenario_clickhouse_outage())

    recovery_score, avg_stability = compute_recovery_score(results)
    result = build_recovery_result(results, recovery_score, avg_stability)
    report = render_chaos_recovery_markdown(result)

    log(f"Recovery score: {recovery_score}")
    print("\n" + report)

    # Save report to the current directory unless explicitly overridden.
    report_dir = os.getenv("CHAOS_EVAL_REPORT_DIR", ".")
    os.makedirs(report_dir, exist_ok=True)
    report_stem = f"chaos-recovery-eval-{datetime.datetime.utcnow().strftime('%Y-%m-%d')}"
    report_path = os.path.join(
        report_dir,
        f"{report_stem}.md",
    )
    json_path = os.path.join(report_dir, f"{report_stem}.json")
    write_markdown(report_path, report)
    write_json(json_path, result)
    log(f"Markdown report saved to {report_path}")
    log(f"JSON report saved to {json_path}")

    # Exit non-zero if unhealthy
    sys.exit(0 if result["passed"] else 1)

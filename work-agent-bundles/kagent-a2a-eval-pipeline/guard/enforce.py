#!/usr/bin/env python3
"""Guard enforcement: apply a block policy that propose.py wrote, but only when it is definitely bad, and with hard limits.

Chosen design (owner decision, 24 Nov 2026): a definite offender is blocked immediately and the policy is applied directly to the cluster, as a failsafe.
Because that is a real power, every call is gated, and nothing here is automatic unless the caller passes --auto-apply AND --context:

- only signals in rules.yaml `autoApply.signals` (default: forbidden_tool, a deterministic tool-outside-allowlist result); token burn and the rest stay ticket-only;
- the policy file is RE-VALIDATED here, independently of propose.py: one named HTTPRoute, action Deny, one `jwt.sub` identifier, the allowed namespace, a guard-deny- name;
- the never-block list is checked again; a hard cap on active guard blocks (`autoApply.maxActiveBlocks`) stops a runaway Guard from blocking the fleet;
- a per-hour cap and a kill switch (`guard-enforce.disabled` file or GUARD_ENFORCE_DISABLED=1);
- server dry-run first, then apply, then read back; every decision is one ledger line; a block stays until a person runs `release` (it never expires by itself).
`release` removes only policies this tool applied. Exit: 0 ok | 1 something refused | 3 bad input.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

SUBJECT = re.compile(r"^[A-Za-z0-9._:@/-]{1,128}$")
NAME = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
EXPR = re.compile(r'^jwt\.sub == "([A-Za-z0-9._:@/-]{1,128})"$')
LABEL = "app.kubernetes.io/managed-by"
OWNER = "guard-proposal"


def kubectl(ctx: str, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["kubectl", "--context", ctx, *args], capture_output=True, text=True, input=stdin)


def validate(pol: dict[str, Any], rules: dict[str, Any]) -> tuple[str | None, str]:
    """Return (subject or None, reason). Independent of propose.py on purpose."""
    try:
        md, spec = pol["metadata"], pol["spec"]
        if pol.get("kind") != "AgentgatewayPolicy" or pol.get("apiVersion") != "agentgateway.dev/v1alpha1":
            return None, "not an AgentgatewayPolicy v1alpha1"
        if not str(md.get("name", "")).startswith("guard-deny-") or not NAME.match(md["name"]):
            return None, "name must be guard-deny-<slug>"
        if md.get("namespace") != rules.get("policyNamespace"):
            return None, "namespace is not the allowed policy namespace"
        if (md.get("labels") or {}).get(LABEL) != OWNER:
            return None, "missing the guard managed-by label"
        refs = spec["targetRefs"]
        if len(refs) != 1 or refs[0].get("kind") != "HTTPRoute" or not NAME.match(str(refs[0].get("name", ""))):
            return None, "must target exactly one named HTTPRoute"
        if set(spec) != {"targetRefs", "traffic"} or set(spec["traffic"]) != {"authorization"}:
            return None, "unexpected fields in spec"
        auth = spec["traffic"]["authorization"]
        exprs = auth["policy"]["matchExpressions"]
        if auth.get("action") != "Deny" or len(exprs) != 1 or set(auth) != {"action", "policy"} or set(auth["policy"]) != {"matchExpressions"}:
            return None, "must be a single-expression Deny"
        m = EXPR.match(exprs[0])
        if not m or not SUBJECT.match(m.group(1)):
            return None, "expression is not exactly jwt.sub == \"<plain identifier>\""
        subject = m.group(1)
    except (KeyError, TypeError, AttributeError):
        return None, "policy is malformed"
    deny = [str(n).lower() for n in rules.get("neverBlock") or []]
    for n in (subject, refs[0]["name"], md["name"]):
        low = n.lower()
        if any(low == d or low.startswith(d + "-") for d in deny):
            return None, f"{n!r} is on the never-block list"
    return subject, "ok"


def ledger_append(path: Path | None, rec: dict[str, Any]) -> None:
    if path:
        with open(path, "a") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")


def recent_applies(path: Path | None, now: float, window: int = 3600) -> int:
    n = 0
    if path and path.exists():
        for line in path.read_text().splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("outcome") == "applied" and now - d.get("epoch", 0) < window:
                n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply")
    a.add_argument("--proposals", type=Path, required=True, help="the proposals.json that propose.py wrote (its policy files sit beside it)")
    a.add_argument("--rules", type=Path, default=Path(__file__).with_name("rules.yaml"))
    a.add_argument("--context"); a.add_argument("--auto-apply", action="store_true"); a.add_argument("--ledger", type=Path); a.add_argument("--now", type=float)
    r = sub.add_parser("release")
    r.add_argument("--context", required=True); r.add_argument("--namespace", required=True); r.add_argument("--name", required=True); r.add_argument("--ledger", type=Path); r.add_argument("--now", type=float)
    args = ap.parse_args()
    now = args.now if args.now is not None else time.time()

    if args.cmd == "release":
        g = kubectl(args.context, "-n", args.namespace, "get", "agentgatewaypolicies.agentgateway.dev", args.name, "-o", "json")
        if g.returncode != 0:
            print(json.dumps({"outcome": "not_found", "detail": g.stderr.strip()[:200]})); return 1
        if (json.loads(g.stdout)["metadata"].get("labels") or {}).get(LABEL) != OWNER:
            print(json.dumps({"outcome": "refused_not_guard_managed"})); return 1
        d = kubectl(args.context, "-n", args.namespace, "delete", "agentgatewaypolicies.agentgateway.dev", args.name)
        ledger_append(args.ledger, {"epoch": now, "policy": args.name, "outcome": "released" if d.returncode == 0 else "release_failed"})
        print(json.dumps({"outcome": "released" if d.returncode == 0 else "release_failed", "detail": (d.stdout + d.stderr).strip()[:200]}))
        return 0 if d.returncode == 0 else 1

    if not args.auto_apply or not args.context:
        print(json.dumps({"outcome": "refused", "reason": "needs --auto-apply and an explicit --context; nothing was applied"})); return 1
    try:
        rules = yaml.safe_load(args.rules.read_text())
        props = json.loads(args.proposals.read_text())["results"]
    except (OSError, ValueError, KeyError, yaml.YAMLError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr); return 3
    cfg = rules.get("autoApply") or {}
    out, rc = [], 0
    kill = os.environ.get("GUARD_ENFORCE_DISABLED") == "1" or (args.proposals.parent / "guard-enforce.disabled").exists()
    for p in props:
        rec: dict[str, Any] = {"epoch": now, "finding": p.get("finding"), "signal": p.get("signal"), "agent": p.get("agent")}
        def done(outcome: str, reason: str = "") -> None:
            nonlocal rc
            rec.update(outcome=outcome, reason=reason); out.append(rec); ledger_append(args.ledger, rec)
            rc = rc or (0 if outcome == "applied" or outcome == "skipped_not_a_block" else 1)
        if not p.get("policy_file"):
            done("skipped_not_a_block"); continue
        if kill:
            done("refused", "kill switch"); continue
        if p.get("signal") not in (cfg.get("signals") or []):
            done("refused", f"signal {p.get('signal')!r} is not in autoApply.signals (ticket only)"); continue
        try:
            pol = yaml.safe_load((args.proposals.parent / p["policy_file"]).read_text())
        except (OSError, yaml.YAMLError):
            done("refused", "policy file unreadable"); continue
        subject, why = validate(pol, rules)
        if not subject:
            done("refused", f"re-validation failed: {why}"); continue
        ns, name = pol["metadata"]["namespace"], pol["metadata"]["name"]
        rec.update(policy=name, subject=subject, route=pol["spec"]["targetRefs"][0]["name"])
        if recent_applies(args.ledger, now) >= int(cfg.get("maxAppliesPerHour", 2)):
            done("refused", "hourly apply cap reached; a person must decide"); continue
        lst = kubectl(args.context, "-n", ns, "get", "agentgatewaypolicies.agentgateway.dev", "-l", f"{LABEL}={OWNER}", "-o", "json")
        if lst.returncode != 0:
            done("refused", "cannot count existing guard blocks; failing closed"); continue
        active = [i for i in json.loads(lst.stdout).get("items", []) if (i["metadata"].get("annotations") or {}).get("guard.kagent.dev/applied") == "true"]
        if len(active) >= int(cfg.get("maxActiveBlocks", 3)):
            done("refused", f"{len(active)} guard blocks are already active (cap {cfg.get('maxActiveBlocks', 3)}); a person must review"); continue
        pol["metadata"]["annotations"].update({"guard.kagent.dev/applied": "true", "guard.kagent.dev/applied-at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                                               "guard.kagent.dev/review-by": (datetime.fromtimestamp(now, timezone.utc) + timedelta(days=int(cfg.get("reviewDays", 1)))).isoformat(),
                                               "guard.kagent.dev/note": "Applied automatically by the Guard for a definite offence. Never expires by itself: a person reviews, fixes, then runs `enforce.py release`."})
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tf:
            yaml.safe_dump(pol, tf, sort_keys=False); path = tf.name
        dry = kubectl(args.context, "apply", "--dry-run=server", "-f", path)
        if dry.returncode != 0:
            done("refused", "server dry-run rejected it: " + dry.stderr.strip()[:200]); continue
        ap_ = kubectl(args.context, "apply", "-f", path)
        chk = kubectl(args.context, "-n", ns, "get", "agentgatewaypolicies.agentgateway.dev", name, "-o", "name")
        if ap_.returncode != 0 or chk.returncode != 0:
            done("failed", "apply or read-back failed: " + (ap_.stderr + chk.stderr).strip()[:200]); continue
        done("applied", "definite offence; blocked until a person releases it")
    print(json.dumps({"results": out}, indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main())

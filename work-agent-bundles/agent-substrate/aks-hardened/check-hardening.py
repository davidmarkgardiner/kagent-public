#!/usr/bin/env python3
"""Offline hardening check for rendered Kubernetes manifests.

Reads multi-document YAML on stdin (for example `helm template ... | ./check-hardening.py`)
and checks every container and init container in every pod template for:

  - readOnlyRootFilesystem: true
  - allowPrivilegeEscalation: false and capabilities.drop [ALL]
  - runAsNonRoot: true and a RuntimeDefault/Localhost seccomp profile (pod or container)
  - cpu and memory requests and limits
  - no capabilities added other than NET_BIND_SERVICE

Workloads that are privileged by design (atelet) are listed as needing a policy exception
instead of failing, but they must still have a read-only root filesystem and limits.
WorkerPool objects must set spec.template.resources, because their pods are generated
by atecontroller and cannot be patched.

Exit status is 1 when any check fails. Requires python3 with PyYAML.
"""
import sys

import yaml

POD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "ReplicaSet"}
EXCEPTION_ALLOWED = {("DaemonSet", "atelet"), ("DaemonSet", "substrate-atelet")}


def pod_spec(doc):
    kind = doc.get("kind")
    if kind == "Pod":
        return doc.get("spec") or {}
    if kind == "CronJob":
        return doc["spec"]["jobTemplate"]["spec"]["template"].get("spec") or {}
    if kind in POD_KINDS:
        return doc["spec"]["template"].get("spec") or {}
    return None


def has_limits(resources):
    missing = []
    for section in ("requests", "limits"):
        for res in ("cpu", "memory"):
            if not (resources or {}).get(section, {}).get(res):
                missing.append(f"{section}.{res}")
    return missing


def check(doc):
    kind, name = doc.get("kind"), doc["metadata"]["name"]
    spec = pod_spec(doc)
    failures, notes = [], []
    if spec is None:
        if kind == "WorkerPool":
            tmpl = (doc.get("spec") or {}).get("template") or {}
            missing = has_limits(tmpl.get("resources"))
            if missing:
                failures.append(f"spec.template.resources missing {', '.join(missing)}")
            notes.append("worker pods are privileged by design: needs a policy exception")
        return failures, notes

    pod_sc = spec.get("securityContext") or {}
    privileged_workload = False
    for field in ("hostNetwork", "hostPID", "hostIPC"):
        if spec.get(field):
            failures.append(f"pod uses {field}")
    host_paths = [v["name"] for v in spec.get("volumes") or [] if "hostPath" in v]

    for group in ("initContainers", "containers"):
        for c in spec.get(group) or []:
            where = f"{group[:-1]} {c['name']}"
            sc = c.get("securityContext") or {}
            privileged = bool(sc.get("privileged"))
            privileged_workload |= privileged
            if sc.get("readOnlyRootFilesystem") is not True:
                failures.append(f"{where}: readOnlyRootFilesystem is not true")
            missing = has_limits(c.get("resources"))
            if missing:
                failures.append(f"{where}: resources missing {', '.join(missing)}")
            host_ports = [p["hostPort"] for p in c.get("ports") or [] if p.get("hostPort")]
            if privileged:
                notes.append(f"{where}: privileged, hostPorts {host_ports or 'none'}")
                continue
            if host_ports:
                failures.append(f"{where}: hostPort {host_ports}")
            if sc.get("allowPrivilegeEscalation") is not False:
                failures.append(f"{where}: allowPrivilegeEscalation is not false")
            caps = sc.get("capabilities") or {}
            if "ALL" not in (caps.get("drop") or []):
                failures.append(f"{where}: capabilities.drop does not include ALL")
            extra = [a for a in caps.get("add") or [] if a != "NET_BIND_SERVICE"]
            if extra:
                failures.append(f"{where}: adds capabilities {extra}")
            if not (sc.get("runAsNonRoot") or pod_sc.get("runAsNonRoot")):
                failures.append(f"{where}: runAsNonRoot not set")
            if sc.get("runAsUser", pod_sc.get("runAsUser")) == 0:
                failures.append(f"{where}: runAsUser is 0")
            seccomp = (sc.get("seccompProfile") or pod_sc.get("seccompProfile") or {}).get("type")
            if seccomp not in ("RuntimeDefault", "Localhost"):
                failures.append(f"{where}: seccompProfile is {seccomp or 'unset'}")

    if host_paths:
        if privileged_workload:
            notes.append(f"hostPath volumes {host_paths}")
        else:
            failures.append(f"hostPath volumes {host_paths}")
    if privileged_workload:
        if (kind, name) in EXCEPTION_ALLOWED:
            notes.insert(0, "privileged by design: needs a policy exception")
        else:
            failures.append("privileged container outside the expected exception list")
    return failures, notes


def main():
    docs = [d for d in yaml.safe_load_all(sys.stdin) if isinstance(d, dict) and d.get("kind")]
    failed = 0
    checked = 0
    for doc in docs:
        if pod_spec(doc) is None and doc.get("kind") != "WorkerPool":
            continue
        checked += 1
        failures, notes = check(doc)
        label = f"{doc['kind']}/{doc['metadata']['name']}"
        if failures:
            failed += 1
            print(f"FAIL {label}")
            for f in failures:
                print(f"     - {f}")
        elif notes:
            print(f"EXCEPTION {label}")
        else:
            print(f"PASS {label}")
        for n in notes:
            print(f"     * {n}")
    print(f"HARDENING_CHECK: {'FAIL' if failed else 'PASS'} ({checked} workloads, {failed} failing)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

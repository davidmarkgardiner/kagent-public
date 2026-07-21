#!/usr/bin/env python3
"""validate-agent-cr.py — mechanical lint for kagent Agent CRDs.

Runs the BYOA validation checklist (agents/skills/byoa-agent-builder/SKILL.md)
as static YAML assertions instead of a remembered prose list. The
security-relevant check — no write tools on a triage agent — is enforced
mechanically here.

Usage:
    scripts/validate-agent-cr.py FILE... [--type triage|remediation]
                                 [--catalog PATH] [--json]

The agent type is read from the ``platform.com/type`` label unless --type is
given. Exit code 0 when every check passes on every file, 1 otherwise.
"""

import argparse
import json
import pathlib
import re
import sys

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = REPO_ROOT / "agents/skills/byoa-agent-builder/references/tool-catalog.md"

WRITE_TOOLS = {
    "k8s_apply_manifest",
    "k8s_patch_resource",
    "k8s_delete_resource",
    "k8s_create_resource",
    "k8s_execute_command",
}
CORE_WRITE_TOOLS = {"k8s_apply_manifest", "k8s_patch_resource"}
ANCHOR_RE = re.compile(r"CRITICAL: always use exact namespace")


def load_catalog(path):
    """Extract tool names from the markdown catalog tables (| `name` | ...)."""
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`([a-z0-9_]+)`\s*\|", line)
        if m:
            names.add(m.group(1))
    return names


def check(results, name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok), "detail": detail})


def validate_agent(doc, agent_type, catalog):
    results = []
    meta = doc.get("metadata") or {}
    labels = meta.get("labels") or {}
    spec = doc.get("spec") or {}
    declarative = spec.get("declarative") or {}

    check(results, "kind-agent",
          doc.get("apiVersion") == "kagent.dev/v1alpha2" and doc.get("kind") == "Agent",
          f"apiVersion={doc.get('apiVersion')!r} kind={doc.get('kind')!r}")

    if agent_type is None:
        agent_type = labels.get("platform.com/type")
    check(results, "type-known", agent_type in ("triage", "remediation"),
          f"type={agent_type!r} (from --type or platform.com/type label)")

    check(results, "label-team", bool(labels.get("platform.com/team")),
          "metadata.labels['platform.com/team'] present")
    check(results, "label-type", bool(labels.get("platform.com/type")),
          "metadata.labels['platform.com/type'] present")

    tools = []
    for tool in declarative.get("tools") or []:
        mcp = tool.get("mcpServer") or {}
        tools.extend(mcp.get("toolNames") or [])
    check(results, "tools-nonempty", bool(tools), f"{len(tools)} tool name(s)")

    unknown = sorted(set(tools) - catalog) if catalog else []
    check(results, "tools-in-catalog", not unknown,
          f"unknown tools: {unknown}" if unknown else "all tool names in catalog")

    writes = sorted(set(tools) & WRITE_TOOLS)
    if agent_type == "triage":
        check(results, "triage-no-write-tools", not writes,
              f"write tools present on triage agent: {writes}" if writes else "no write tools")
    elif agent_type == "remediation":
        missing = sorted(CORE_WRITE_TOOLS - set(tools))
        check(results, "remediation-core-writes", not missing,
              f"missing core write tools: {missing}" if missing else "core write tools present")

    skills = (declarative.get("a2aConfig") or {}).get("skills") or []
    check(results, "a2a-skills", len(skills) >= 1, f"{len(skills)} a2aConfig.skills entries")

    check(results, "modelConfig-not-deprecated",
          "modelConfig" in declarative and "modelConfigRef" not in declarative,
          "modelConfig used (modelConfigRef is deprecated)")

    check(results, "systemMessage-not-systemPrompt",
          "systemMessage" in declarative and "systemPrompt" not in declarative,
          "systemMessage used (systemPrompt is not a valid field)")

    anchors = len(ANCHOR_RE.findall(declarative.get("systemMessage") or ""))
    check(results, "namespace-anchor", anchors >= 1,
          f"{anchors} 'CRITICAL: always use exact namespace' line(s) in systemMessage")

    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", metavar="FILE")
    parser.add_argument("--type", choices=("triage", "remediation"), default=None,
                        help="override the platform.com/type label")
    parser.add_argument("--catalog", type=pathlib.Path, default=DEFAULT_CATALOG,
                        help=f"tool catalog markdown (default: {DEFAULT_CATALOG})")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    catalog = set()
    if args.catalog.is_file():
        catalog = load_catalog(args.catalog)
    else:
        print(f"WARN tool catalog not found: {args.catalog} — skipping catalog check",
              file=sys.stderr)

    report = []
    failed = 0
    for name in args.files:
        path = pathlib.Path(name)
        if not path.is_file():
            report.append({"file": name, "error": "file not found"})
            failed += 1
            continue
        try:
            docs = [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8"))
                    if isinstance(d, dict)]
        except yaml.YAMLError as exc:
            report.append({"file": name, "error": f"YAML parse error: {exc}"})
            failed += 1
            continue
        agents = [d for d in docs if d.get("kind") == "Agent"]
        if not agents:
            report.append({"file": name, "error": "no Agent document found"})
            failed += 1
            continue
        for doc in agents:
            results = validate_agent(doc, args.type, catalog)
            agent_name = (doc.get("metadata") or {}).get("name", "?")
            report.append({"file": name, "agent": agent_name, "results": results})
            failed += sum(1 for r in results if not r["ok"])

    if args.as_json:
        json.dump({"failed_checks": failed, "files": report}, sys.stdout, indent=2)
        print()
    else:
        for entry in report:
            if "error" in entry:
                print(f"FAIL {entry['file']}: {entry['error']}")
                continue
            print(f"== {entry['file']} ({entry['agent']})")
            for r in entry["results"]:
                status = "PASS" if r["ok"] else "FAIL"
                print(f"{status} {r['check']}: {r['detail']}")
        print(f"{failed} failed check(s)")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

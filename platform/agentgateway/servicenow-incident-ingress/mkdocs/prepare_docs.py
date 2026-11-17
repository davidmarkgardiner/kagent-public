#!/usr/bin/env python3
"""Prepare the MkDocs copy from an explicit list of public handoff sources."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

PROJECT = Path(__file__).resolve().parent
BUNDLE = PROJECT.parent
LINK = re.compile(r"(\[[^\]]+\]\()([^)]+)(\))")
DIAGRAMS = {
    "ad772d18d0e753709b63ae1f8ffa7f675d9268bd9d44dc47bb41715a375e4954": (
        "ServiceNow JSON + Entra token\n  -> Istio HTTPS / JWT and role checks\n"
        "  -> VirtualService\n  -> agentgateway Service / HTTPRoute / JSON-to-A2A policy\n"
        "  -> approved A2A entry point\n  -> selected agent"
    ),
    "6ca79005657abffc5127f607b27196ad117135f75a1b2c0efa52577f890a1ae4": (
        "ServiceNow raw incident JSON -> Istio ingress / VirtualService\n"
        "  -> agentgateway listener / HTTPRoute / body policy\n"
        "  -> kagent controller A2A endpoint -> selected read-only triage agent"
    ),
    "bd998b2a81baa48655c0da0e6fc0543dc4582cbcfb8098dd86cc361f45d2f43f": (
        "Proxmox synthetic JSON client -> loopback port-forward\n"
        "  -> agentgateway 1.7.0 -> A2A -> kagent 0.10.4 Go agent\n"
        "  -> existing model gateway -> real DeepSeek API\nNo Argo in this tested path."
    ),
}


def expected_files():
    manifest = json.loads((PROJECT / "public-files.json").read_text())
    sources = {(BUNDLE / source).resolve(): target for source, target in manifest.items()}
    expected = {}
    for source, target in sources.items():
        if not source.is_file():
            raise ValueError("Missing public input: " + str(source))
        destination = Path(target)
        if destination.is_absolute() or ".." in destination.parts:
            raise ValueError("Destination must remain inside docs/: " + target)
        content = source.read_text()
        if source.suffix == ".md" and destination.suffix == ".md":
            def replace_link(match):
                link = match.group(2)
                if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", link) or link.startswith("#"):
                    return match.group(0)
                path, separator, anchor = link.partition("#")
                resolved = (source.parent / path).resolve()
                if resolved.is_dir():
                    resolved = resolved / "README.md"
                if resolved not in sources:
                    raise ValueError("Unlisted linked file: " + str(resolved))
                relative = os.path.relpath(sources[resolved], start=destination.parent).replace(os.sep, "/")
                return match.group(1) + relative + (separator + anchor if separator else "") + match.group(3)
            content = LINK.sub(replace_link, content)
            if "```mermaid" in content:
                def replace_diagram(match):
                    digest = hashlib.sha256(match.group(1).encode()).hexdigest()
                    if digest not in DIAGRAMS:
                        raise ValueError("Changed Mermaid diagram: review and update its text equivalent in prepare_docs.py")
                    return "```text\n" + DIAGRAMS[digest] + "\n```"
                content = re.sub(r"```mermaid\n(.*?)\n```", replace_diagram, content, flags=re.S)
            if target == "skill.md":
                content = re.sub(r"\A---\n.*?\n---\n", "", content, count=1, flags=re.S)
                content = "Raw portable entrypoint: [SKILL.md.txt](downloads/skill/SKILL.md.txt).\n\n" + content
        expected[target] = content
    skill = BUNDLE / "skills/mkdocs-work-agent/SKILL.md"
    expected["downloads/skill/SKILL.md.txt"] = skill.read_text()
    downloads = ["# Downloads", "", "Public examples and sanitized receipts are bundled with this site.",
                 "The YAML templates still need rendering and target validation; downloads do not deploy anything.", ""]
    for target in sorted(expected):
        if not target.endswith(".md"):
            downloads.append(f"- [{target}]({target})")
    downloads += ["", "The raw skill entrypoint uses a `.txt` suffix so MkDocs serves the source unchanged.",
                  "Remove the final `.txt` from downloaded `.md.txt` filenames when importing, and preserve `agents/` and `assets/` from",
                  "the bundled skill downloads. The canonical GitHub skill folder already has the right names.", ""]
    expected["downloads.md"] = "\n".join(downloads)
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check freshness without writing")
    args = parser.parse_args()
    expected = expected_files()
    docs = PROJECT / "docs"
    actual = {str(p.relative_to(docs)) for p in docs.rglob("*") if p.is_file()}
    unknown = actual - expected.keys()
    if unknown:
        raise ValueError("Unmanaged files in generated docs/; preserve and inspect: " + str(sorted(unknown)))
    stale = [path for path, content in expected.items()
             if not (docs / path).exists() or (docs / path).read_text() != content]
    if args.check:
        if stale:
            parser.exit(1, "Stale generated files: " + ", ".join(stale) + "\n")
        print(f"PASS: {len(expected)} generated public files are current")
        return
    for path, content in expected.items():
        output = docs / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content)
    print(f"Prepared {len(expected)} public files in {docs}")


if __name__ == "__main__":
    main()

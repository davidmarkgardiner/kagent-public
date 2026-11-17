#!/usr/bin/env python3
"""Render the AKS PoC templates locally. No network calls or cluster changes."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
TOKEN = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
NAME = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")


def render(values):
    expected = set(json.loads((ROOT / "values.example.json").read_text()))
    if set(values) != expected:
        raise ValueError("Values keys differ: " + str(sorted(set(values) ^ expected)))
    for key, value in values.items():
        if isinstance(value, str) and (not value or "{{" in value or "}}" in value):
            raise ValueError("Fill in " + key)
        if key.endswith("_PORT"):
            if type(value) is not int or not 1 <= value <= 65535:
                raise ValueError("Invalid port: " + key)
        elif key == "REQUEST_TIMEOUT_SECONDS":
            if type(value) is not int or not 1 <= value <= 300:
                raise ValueError("Timeout must be an integer from 1 to 300")
        elif not isinstance(value, str):
            raise ValueError("Expected string: " + key)
        elif key == "VIRTUALSERVICE_API_VERSION":
            if value not in ("networking.istio.io/v1", "networking.istio.io/v1beta1"):
                raise ValueError("Unsupported Istio API version")
        elif key == "INGRESS_HOST":
            if len(value) > 253 or any(len(part) > 63 or not NAME.fullmatch(part) for part in value.split(".")):
                raise ValueError("Use a DNS hostname without scheme, port, or wildcard")
        elif key == "BACKEND_A2A_PATH":
            if value != "/" and not re.fullmatch(r"/[A-Za-z0-9._~%/-]+/", value):
                raise ValueError("A2A path must be an absolute path ending in /, with no query")
        elif len(value) > 63 or not NAME.fullmatch(value):
            raise ValueError("Invalid Kubernetes name: " + key)

    mapped = dict(values)
    mapped["ISTIO_GATEWAY_REF"] = values["ISTIO_GATEWAY_NAMESPACE"] + "/" + values["ISTIO_GATEWAY_NAME"]
    mapped["GATEWAY_SERVICE_DNS"] = values["GATEWAY_SERVICE_NAME"] + "." + values["GATEWAY_NAMESPACE"] + ".svc.cluster.local"
    mapped["GATEWAY_TIMEOUT"] = str(values["REQUEST_TIMEOUT_SECONDS"]) + "s"
    mapped["ISTIO_TIMEOUT"] = str(values["REQUEST_TIMEOUT_SECONDS"] + 5) + "s"
    files = {}
    for template in sorted((ROOT / "templates").glob("*.yaml")):
        if template.name == "04-referencegrant.yaml" and values["BACKEND_NAMESPACE"] == values["GATEWAY_NAMESPACE"]:
            continue
        files[template.name] = TOKEN.sub(lambda match: json.dumps(mapped[match.group(1)]), template.read_text())
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--values", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("rendered"))
    args = parser.parse_args()
    files = render(json.loads(args.values.read_text()))
    if args.out.exists() and any(args.out.iterdir()):
        parser.error("Output folder is not empty; use a new folder to avoid stale grants")
    args.out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (args.out / name).write_text(content)
    print(f"Rendered {len(files)} YAML files in {args.out}; no cluster changes made")


if __name__ == "__main__":
    main()

"""Render a separate Vector manifest; never overwrite the source bundle.

Shadow retains the original Kafka sink. Cutover removes it and sends all
eligible normalized signals to admission, before repeat suppression.
"""
import argparse
from pathlib import Path

import yaml


def render(source, uri, cutover=False):
    docs = list(yaml.safe_load_all(source))
    changed = 0
    for doc in docs:
        if not doc or doc.get("kind") != "ConfigMap" or "vector.yaml" not in doc.get("data", {}):
            continue
        config = yaml.safe_load(doc["data"]["vector.yaml"])
        if "incident_signals" not in config.get("transforms", {}):
            raise ValueError("expected normalized incident_signals transform")
        sinks = config["sinks"]
        kafka_sinks = [name for name, spec in sinks.items() if spec.get("type") == "kafka"]
        if not kafka_sinks:
            raise ValueError("expected direct Kafka sink to replace")
        if cutover:
            for name in kafka_sinks:
                del sinks[name]
        sinks["admission"] = {
            "type": "http", "inputs": ["incident_signals"], "uri": uri,
            "method": "post", "encoding": {"codec": "json"},
            "framing": {"method": "newline_delimited"},
            "batch": {"max_events": 1, "timeout_secs": 1},
            "auth": {"strategy": "bearer", "token": "${ADMISSION_AUTH_KEY}"},
            "buffer": {"type": "memory", "max_events": 1000, "when_full": "block"},
            "request": {"timeout_secs": 20},
            "healthcheck": {"enabled": False},
        }
        doc["data"]["vector.yaml"] = yaml.safe_dump(config, sort_keys=False, width=120)
        changed += 1
    if changed != 1:
        raise ValueError("expected exactly one Vector configuration")
    for doc in docs:
        if not doc or doc.get("kind") != "Deployment":
            continue
        for container in doc["spec"]["template"]["spec"]["containers"]:
            if container.get("name") == "vector":
                env = container.setdefault("env", [])
                env[:] = [e for e in env if e["name"] != "ADMISSION_AUTH_KEY"]
                env.append({"name": "ADMISSION_AUTH_KEY", "valueFrom": {
                    "secretKeyRef": {"name": "namespace-alert-admission", "key": "auth-key"}}})
    return yaml.safe_dump_all(docs, sort_keys=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--uri", required=True)
    parser.add_argument("--cutover", action="store_true")
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve() or args.output.exists():
        parser.error("output must be a new file distinct from source")
    args.output.write_text(render(args.source.read_text(), args.uri, args.cutover))

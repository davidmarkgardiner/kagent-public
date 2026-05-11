#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


NODEPORT_MIN = 30000
NODEPORT_MAX = 32767
ISO_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"WARN: {msg}", file=sys.stderr)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"Missing file: {path}")
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON in {path}: {e}")


def parse_updated(updated: str) -> None:
    # Expect canonical RFC3339-with-Z, e.g. 2026-02-07T10:30:00Z
    if not ISO_Z_RE.match(updated):
        warn(f'"updated" is not in canonical Z form: {updated!r} (expected YYYY-MM-DDTHH:MM:SSZ)')
        return
    # Ensure it parses
    datetime.strptime(updated, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "references" / "services.json"
    data = load_json(path)

    if not isinstance(data, dict):
        fail("Root JSON must be an object.")

    updated = data.get("updated")
    if not isinstance(updated, str):
        fail('Missing or invalid "updated" (must be a string).')
    parse_updated(updated)

    clusters = data.get("clusters")
    if not isinstance(clusters, dict):
        fail('Missing or invalid "clusters" (must be an object).')

    services = data.get("services")
    if not isinstance(services, dict):
        fail('Missing or invalid "services" (must be an object).')

    seen_ports: dict[int, str] = {}
    seen_urls: dict[str, str] = {}

    def check_service(svc: dict, group: str) -> None:
        if not isinstance(svc, dict):
            fail(f"Service entry in {group} must be an object.")

        name = svc.get("name")
        if not isinstance(name, str) or not name.strip():
            fail(f"Service in {group} is missing a valid 'name'.")

        url = svc.get("url")
        ip = svc.get("ip")
        port = svc.get("port")
        node_port = svc.get("nodePort")
        namespace = svc.get("namespace")

        if url is not None and not (isinstance(url, str) and url.strip()):
            fail(f"{group}/{name}: 'url' must be a non-empty string or null.")
        if ip is not None and not (isinstance(ip, str) and ip.strip()):
            fail(f"{group}/{name}: 'ip' must be a non-empty string.")
        if port is not None and not isinstance(port, int):
            fail(f"{group}/{name}: 'port' must be an int when present.")

        if node_port is not None and not isinstance(node_port, int):
            fail(f"{group}/{name}: 'nodePort' must be an int when present.")

        # If it looks like a K8s-exposed service, require namespace + nodePort.
        if namespace is not None and not (isinstance(namespace, str) and namespace.strip()):
            fail(f"{group}/{name}: 'namespace' must be a non-empty string when present.")

        if node_port is not None:
            if not (NODEPORT_MIN <= node_port <= NODEPORT_MAX):
                fail(f"{group}/{name}: nodePort {node_port} out of range [{NODEPORT_MIN}, {NODEPORT_MAX}].")
            prev = seen_ports.get(node_port)
            if prev:
                fail(f"Duplicate nodePort {node_port}: {prev} and {group}/{name}")
            seen_ports[node_port] = f"{group}/{name}"

        if url:
            prev = seen_urls.get(url)
            if prev:
                fail(f"Duplicate url {url!r}: {prev} and {group}/{name}")
            seen_urls[url] = f"{group}/{name}"

        # Heuristics: if a service has nodePort it should probably have namespace.
        if node_port is not None and not namespace:
            warn(f"{group}/{name}: has nodePort but no namespace.")

    for group, entries in services.items():
        if not isinstance(entries, list):
            fail(f"services.{group} must be a list.")
        for svc in entries:
            check_service(svc, group)

    print(f"OK: {path} (checked groups={len(services)}, nodePorts={len(seen_ports)}, urls={len(seen_urls)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

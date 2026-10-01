"""Read-only Kubernetes topology snapshot and bounded relationship queries."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

CORE = ("namespaces", "deployments", "replicasets", "statefulsets", "daemonsets",
        "pods", "services", "endpointslices", "ingresses")
OPTIONAL = ("gateways.gateway.networking.k8s.io", "httproutes.gateway.networking.k8s.io",
            "agentgatewaybackends.agentgateway.dev", "virtualservices.networking.istio.io")


def collect(context, knowledge=None):
    if not context or context == "current":
        raise ValueError("an explicit Kubernetes context is required")
    resources, errors = [], []
    for kind in CORE + OPTIONAL:
        command = ["kubectl", "--context", context, "--request-timeout=10s", "get", kind,
                   "--all-namespaces", "-o", "json"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
        if result.returncode:
            if kind in OPTIONAL and ("doesn't have a resource type" in result.stderr or
                                     "the server could not find" in result.stderr):
                continue
            errors.append(f"{kind}: Kubernetes API read failed")
            continue
        resources.extend(json.loads(result.stdout).get("items", []))
    return build_graph(context, resources, errors, knowledge)


def node_id(kind, namespace, name):
    return f"{kind}:{namespace}/{name}" if namespace else f"{kind}:{name}"


def health(item):
    kind, spec, status = item.get("kind"), item.get("spec") or {}, item.get("status") or {}
    if kind == "Pod":
        if status.get("phase") in ("Failed", "Unknown"):
            return "unhealthy"
        if status.get("phase") == "Succeeded":
            return "healthy"
        conditions = status.get("conditions") or []
        ready = next((c.get("status") for c in conditions if c.get("type") == "Ready"), None)
        return "healthy" if ready == "True" else "unhealthy" if ready == "False" else "unknown"
    if kind in ("Deployment", "StatefulSet", "ReplicaSet"):
        desired = spec.get("replicas", 1)
        ready = status.get("readyReplicas", 0)
        return "healthy" if ready >= desired else "unhealthy"
    if kind == "DaemonSet":
        desired = status.get("desiredNumberScheduled")
        ready = status.get("numberReady", 0)
        return "healthy" if desired is not None and ready >= desired else "unhealthy" if desired is not None else "unknown"
    return "unknown"


def build_graph(context, resources, errors=None, knowledge=None):
    errors = errors or []
    graph = {"context": context, "observed_at": datetime.now(timezone.utc).isoformat(),
             "complete": not errors, "errors": errors, "nodes": [], "edges": []}
    nodes, edges, uids = {}, {}, {}

    def add_node(identifier, kind, name, namespace="", state="unknown", **detail):
        nodes[identifier] = {"id": identifier, "kind": kind, "name": name,
                             "namespace": namespace, "health": state, **detail}

    def add_edge(source, target, relation, evidence):
        if source in nodes and target in nodes:
            key = (source, target, relation)
            edges[key] = {"source": source, "target": target, "relation": relation,
                          "evidence": evidence}

    cluster_id = node_id("Cluster", "", context)
    add_node(cluster_id, "Cluster", context)
    for item in resources:
        meta = item.get("metadata") or {}
        kind, name, ns = item.get("kind"), meta.get("name"), meta.get("namespace", "")
        if not kind or not name or kind == "EndpointSlice":
            continue
        identifier = node_id(kind, ns, name)
        add_node(identifier, kind, name, ns, health(item))
        if meta.get("uid"):
            uids[meta["uid"]] = identifier
    for item in resources:
        meta = item.get("metadata") or {}
        kind, name, ns = item.get("kind"), meta.get("name"), meta.get("namespace", "")
        identifier = node_id(kind, ns, name) if kind and name else ""
        if identifier not in nodes:
            continue
        if kind == "Namespace":
            add_edge(cluster_id, identifier, "CONTAINS", "Kubernetes namespace")
        elif ns:
            add_edge(node_id("Namespace", "", ns), identifier, "CONTAINS", "metadata.namespace")
        for owner in meta.get("ownerReferences") or []:
            parent = uids.get(owner.get("uid"))
            if parent:
                add_edge(parent, identifier, "OWNS", "metadata.ownerReferences.uid")

    # EndpointSlice targetRef is the observed Service backend. A label match alone
    # does not prove that a Pod currently receives traffic from the Service.
    ready_by_service = {}
    for item in resources:
        if item.get("kind") != "EndpointSlice":
            continue
        meta = item.get("metadata") or {}
        ns = meta.get("namespace", "")
        service = (meta.get("labels") or {}).get("kubernetes.io/service-name")
        if not service:
            continue
        service_id = node_id("Service", ns, service)
        ready_by_service.setdefault(service_id, 0)
        for endpoint in item.get("endpoints") or []:
            if endpoint.get("conditions", {}).get("ready") is not False:
                ready_by_service[service_id] += 1
            target = endpoint.get("targetRef") or {}
            if target.get("kind") != "Pod" or not target.get("name"):
                continue
            pod_id = node_id("Pod", target.get("namespace") or ns, target["name"])
            add_edge(service_id, pod_id, "BACKED_BY",
                     "EndpointSlice.targetRef; ready=" + str(endpoint.get("conditions", {}).get("ready")))
    for item in resources:
        if item.get("kind") != "Service":
            continue
        meta, spec = item.get("metadata") or {}, item.get("spec") or {}
        identifier = node_id("Service", meta.get("namespace", ""), meta.get("name", ""))
        if identifier in nodes:
            count = ready_by_service.get(identifier, 0)
            nodes[identifier]["ready_endpoints"] = count
            if spec.get("selector"):
                nodes[identifier]["health"] = ("unknown" if any(e.startswith("endpointslices:") for e in errors)
                                                else "healthy" if count else "unhealthy")
            nodes[identifier]["dns"] = f"{meta.get('name')}.{meta.get('namespace')}.svc.cluster.local"

    for item in resources:
        kind, meta, spec = item.get("kind"), item.get("metadata") or {}, item.get("spec") or {}
        ns, name = meta.get("namespace", ""), meta.get("name", "")
        source = node_id(kind, ns, name) if kind and name else ""
        if kind == "Ingress":
            for rule in spec.get("rules") or []:
                for path in ((rule.get("http") or {}).get("paths") or []):
                    service = (((path.get("backend") or {}).get("service") or {}).get("name"))
                    if service:
                        add_edge(source, node_id("Service", ns, service), "ROUTES_TO", "Ingress.spec.rules")
        if kind == "HTTPRoute":
            for parent in spec.get("parentRefs") or []:
                if parent.get("name") and parent.get("kind", "Gateway") == "Gateway":
                    add_edge(node_id("Gateway", parent.get("namespace") or ns, parent["name"]),
                             source, "ATTACHES", "HTTPRoute.spec.parentRefs")
            for rule in spec.get("rules") or []:
                for backend in rule.get("backendRefs") or []:
                    if backend.get("name") and backend.get("kind", "Service") in ("Service", "AgentgatewayBackend"):
                        add_edge(source, node_id(backend.get("kind", "Service"),
                                                 backend.get("namespace") or ns, backend["name"]),
                                 "ROUTES_TO", "HTTPRoute.spec.rules.backendRefs")
        if kind == "AgentgatewayBackend":
            for target in (spec.get("mcp") or {}).get("targets") or []:
                backend = ((target.get("static") or {}).get("backendRef") or {})
                if backend.get("name"):
                    add_edge(source, node_id("Service", backend.get("namespace") or ns,
                                              backend["name"]), "ROUTES_TO",
                             "AgentgatewayBackend.spec.mcp.targets.static.backendRef")
        if kind == "VirtualService":
            for route_kind in ("http", "tcp", "tls"):
                for rule in spec.get(route_kind) or []:
                    for route in rule.get("route") or []:
                        host = ((route.get("destination") or {}).get("host") or "").lower()
                        parts = host.split(".")
                        if len(parts) == 1:
                            service_ns, service_name = ns, parts[0]
                        elif len(parts) >= 5 and parts[2:5] == ["svc", "cluster", "local"]:
                            service_name, service_ns = parts[0], parts[1]
                        elif len(parts) == 2:
                            service_name, service_ns = parts
                        else:
                            continue
                        add_edge(source, node_id("Service", service_ns, service_name), "ROUTES_TO",
                                 f"VirtualService.spec.{route_kind}.route.destination.host")

    for entry in knowledge or []:
        target = entry.get("resource_id")
        kind = entry.get("kind")
        path = entry.get("path")
        if target not in nodes or kind not in ("Runbook", "Skill", "Knowledge") or not path:
            continue
        guide_id = node_id(kind, "", path)
        add_node(guide_id, kind, Path(path).name, path=path, state="unknown")
        add_edge(target, guide_id, "HAS_GUIDANCE", "curated knowledge mapping")

    for node in list(nodes.values()):
        if node["kind"] != "Namespace":
            continue
        members = [nodes[edge["target"]] for edge in edges.values()
                   if edge["source"] == node["id"] and edge["relation"] == "CONTAINS"
                   and nodes[edge["target"]]["kind"] in ("Namespace", "Deployment", "StatefulSet",
                                                         "DaemonSet", "Pod", "Service")]
        states = [member["health"] for member in members]
        node["health"] = ("unknown" if errors else "unhealthy" if "unhealthy" in states
                          else "healthy" if states and all(s == "healthy" for s in states)
                          else "unknown")
    namespace_states = [n["health"] for n in nodes.values() if n["kind"] == "Namespace"]
    nodes[cluster_id]["health"] = ("unknown" if errors else "unhealthy" if "unhealthy" in namespace_states
                                   else "healthy" if namespace_states and all(s == "healthy" for s in namespace_states)
                                   else "unknown")
    graph["nodes"] = sorted(nodes.values(), key=lambda n: n["id"])
    graph["edges"] = sorted(edges.values(), key=lambda e: (e["source"], e["target"], e["relation"]))
    return graph


def neighborhood(graph, identifier, depth=1, limit=50, include_containment=False):
    if depth not in (1, 2, 3) or limit < 1 or limit > 100:
        raise ValueError("depth must be 1..3 and limit 1..100")
    nodes = {node["id"]: node for node in graph["nodes"]}
    if identifier not in nodes:
        return {"status": "not_found", "id": identifier, "items": [], "truncated": False,
                "observed_at": graph["observed_at"], "complete": graph["complete"]}
    seen, frontier, found = {identifier}, {identifier}, []
    for distance in range(1, depth + 1):
        next_frontier = set()
        for edge in graph["edges"]:
            if edge["relation"] == "CONTAINS" and not include_containment:
                continue
            if edge["source"] in frontier or edge["target"] in frontier:
                other = edge["target"] if edge["source"] in frontier else edge["source"]
                if other not in seen and other not in next_frontier:
                    next_frontier.add(other)
                    found.append({"node": nodes[other], "distance": distance,
                                  "relation": edge["relation"], "evidence": edge["evidence"]})
        seen |= next_frontier
        frontier = next_frontier
        if not frontier:
            break
    found.sort(key=lambda x: (x["distance"], x["node"]["id"]))
    return {"status": "found", "id": identifier, "items": found[:limit],
            "truncated": len(found) > limit, "observed_at": graph["observed_at"],
            "complete": graph["complete"]}

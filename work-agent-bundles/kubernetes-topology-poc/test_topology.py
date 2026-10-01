import unittest

from topology import build_graph, neighborhood


def obj(kind, name, namespace=None, uid=None, spec=None, status=None, labels=None, owners=None, endpoints=None):
    meta = {"name": name}
    if namespace:
        meta["namespace"] = namespace
    if uid:
        meta["uid"] = uid
    if labels:
        meta["labels"] = labels
    if owners:
        meta["ownerReferences"] = owners
    result = {"kind": kind, "metadata": meta, "spec": spec or {}, "status": status or {}}
    if endpoints is not None:
        result["endpoints"] = endpoints
    return result


class TopologyBehavior(unittest.TestCase):
    def setUp(self):
        self.items = [
            obj("Namespace", "product", uid="ns-1"),
            obj("Deployment", "catalog", "product", uid="dep-1", spec={"replicas": 1},
                status={"readyReplicas": 1}),
            obj("ReplicaSet", "catalog-rs", "product", uid="rs-1", spec={"replicas": 1},
                status={"readyReplicas": 1}, owners=[{"uid": "dep-1"}]),
            obj("Pod", "catalog-pod", "product", uid="pod-1", owners=[{"uid": "rs-1"}],
                status={"phase": "Running", "conditions": [{"type": "Ready", "status": "True"}]}),
            obj("Service", "catalog", "product", uid="svc-1", spec={"selector": {"app": "catalog"}}),
            obj("EndpointSlice", "catalog-slice", "product",
                labels={"kubernetes.io/service-name": "catalog"},
                endpoints=[{"targetRef": {"kind": "Pod", "name": "catalog-pod"},
                            "conditions": {"ready": True}}]),
            obj("Gateway", "public", "product"),
            obj("HTTPRoute", "catalog", "product", spec={"parentRefs": [{"name": "public"}],
                "rules": [{"backendRefs": [{"name": "catalog"}]}]}),
            obj("VirtualService", "catalog", "product", spec={"http": [
                {"route": [{"destination": {"host": "catalog.product.svc.cluster.local"}}]}]}),
        ]

    def test_live_relationships_and_bounded_query(self):
        graph = build_graph("kind-demo", self.items, knowledge=[
            {"resource_id": "Service:product/catalog", "kind": "Runbook", "path": "docs/example.md"}])
        edges = {(e["source"], e["target"], e["relation"]) for e in graph["edges"]}
        self.assertIn(("Deployment:product/catalog", "ReplicaSet:product/catalog-rs", "OWNS"), edges)
        self.assertIn(("Service:product/catalog", "Pod:product/catalog-pod", "BACKED_BY"), edges)
        self.assertIn(("Gateway:product/public", "HTTPRoute:product/catalog", "ATTACHES"), edges)
        self.assertIn(("VirtualService:product/catalog", "Service:product/catalog", "ROUTES_TO"), edges)
        self.assertIn(("Service:product/catalog", "Runbook:docs/example.md", "HAS_GUIDANCE"), edges)
        self.assertEqual("healthy", next(n["health"] for n in graph["nodes"] if n["id"] == "Service:product/catalog"))
        query = neighborhood(graph, "Service:product/catalog", depth=2)
        self.assertEqual("found", query["status"])
        self.assertIn("Runbook:docs/example.md", [x["node"]["id"] for x in query["items"]])
        self.assertNotIn("Namespace:product", [x["node"]["id"] for x in query["items"]])

    def test_empty_service_and_partial_read_are_not_green(self):
        empty = self.items[:5]
        graph = build_graph("kind-demo", empty)
        self.assertEqual("unhealthy", next(n["health"] for n in graph["nodes"] if n["id"] == "Service:product/catalog"))
        partial = build_graph("kind-demo", empty, errors=["endpointslices: Kubernetes API read failed"])
        self.assertFalse(partial["complete"])
        self.assertEqual("unknown", next(n["health"] for n in partial["nodes"] if n["id"] == "Service:product/catalog"))
        self.assertEqual("unknown", next(n["health"] for n in partial["nodes"] if n["id"] == "Cluster:kind-demo"))


if __name__ == "__main__":
    unittest.main()

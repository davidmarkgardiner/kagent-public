# Kubernetes topology lab

**Status:** Local, read-only proof on a disposable kind cluster. No workplace
cluster, Azure resource, or production database is connected. This bundle
builds a Kubernetes relationship snapshot, serves a clickable namespace map,
and exposes bounded queries through both HTTP and MCP. It does not claim to
measure application health or live network traffic.

**Tool decision update:** An [in-cluster Radar evaluation](RADAR-EVALUATION.md)
covered the standard Kubernetes topology UI, watch-based collection, and
read-only MCP query path with an existing Apache-2.0 tool. Treat this custom
collector and viewer as a comparison fixture; assess Radar's identified gaps
before expanding this code.

## Tool choice

| Tool | Good at | Boundary for this use case |
|---|---|---|
| [Radar](https://github.com/skyhook-io/radar) | Open source in-cluster Kubernetes topology UI, watch-based inventory, and built-in read-only MCP tools. | Best current trial candidate; the lab found a missing `AgentgatewayBackend` route hop and no curated guidance edges. |
| [Headlamp Map and Projects](https://headlamp.dev/docs/latest/learn/projects/) | Open source Kubernetes UI with namespace, resource, project, and multi-cluster navigation. Its [map extension API](https://headlamp.dev/docs/latest/development/plugins/functionality/extending-the-map/) can add custom kinds. | Alternative human UI. Built-in MCP client support currently requires the Desktop app; agents would need a separate MCP service. |
| [Cilium Hubble UI](https://docs.cilium.io/en/stable/observability/hubble/index.html) | Observed service-to-service flows, DNS, and a traffic service map when Cilium/Hubble is installed. | Add for actual communication evidence. A Service selector or route declaration does not prove a request flowed. |
| [Kiali](https://kiali.io/docs/features/topology/) | Istio traffic topology and mesh configuration. | Strong if the fleet uses Istio; not a general Kubernetes inventory map. |
| This lab viewer | One small snapshot and agent tool contract over Kubernetes API objects. | Comparison fixture for checking specific relationship coverage and health caveats. |

**Recommended direction:** Evaluate Radar first for the standard topology UI,
watch-based inventory, and bounded MCP reads. Headlamp remains an alternative
human UI, but its built-in MCP client currently requires Headlamp Desktop;
that does not fit a headless in-cluster deployment. Add only the relationship
or guidance functionality the evaluation shows is missing. Keep Git and
querydoc authoritative for approved runbook, skill, and KB content.

## What the lab maps

```text
Cluster → Namespace → Gateway → HTTPRoute → AgentgatewayBackend → Service
                   └── Istio VirtualService → Service
                   └── Deployment → ReplicaSet → Pod ← EndpointSlice/Service
                   └── StatefulSet / DaemonSet → Pod
Service → curated Runbook / Skill / Knowledge reference
```

Edges have an evidence field. `OWNS` comes from owner UID, `BACKED_BY` from
EndpointSlice `targetRef`, `ROUTES_TO` from Ingress/HTTPRoute, Istio
VirtualService, or an AgentgatewayBackend target, and `HAS_GUIDANCE` from an
explicit local mapping.
Service DNS names are derived from Kubernetes naming rules; this proof does
not query CoreDNS. It does not infer application-to-application dependencies
from labels. Hubble or traces are needed to substantiate those edges.

## Run against the disposable lab

Use an explicit non-production context. The viewer binds to localhost and
does not have authentication or user-specific RBAC.

```bash
python3 work-agent-bundles/kubernetes-topology-poc/app.py \
  --context {{KUBE_CONTEXT}} \
  --knowledge work-agent-bundles/kubernetes-topology-poc/knowledge.example.json \
  --port 8765
```

Open http://127.0.0.1:8765/ in a browser. The server polls the Kubernetes
API every 30 seconds; the browser refreshes every 15 seconds. Click a
namespace, then a resource to see its Kubernetes relationships and source.
The example guidance mapping only matches the synthetic
`neo4j-memory-lab/demo-inventory` Service; edit or omit it for another lab.

Get the same graph as JSON, or make one bounded agent-style query:

```bash
python3 work-agent-bundles/kubernetes-topology-poc/app.py \
  --context {{KUBE_CONTEXT}} --once > /tmp/kubernetes-topology.json

python3 work-agent-bundles/kubernetes-topology-poc/app.py \
  --context {{KUBE_CONTEXT}} --query 'Service:{{NAMESPACE}}/{{SERVICE_NAME}}' \
  --depth 2
```

The local HTTP equivalents are `GET /api/graph` and
`GET /api/neighbors?id=Service%3A...&depth=2`. Neighbor queries exclude
namespace containment to prevent a two-hop lookup from returning an entire
namespace. They cap depth at three and results at 100; the MCP tool uses 50.

For MCP, install the pinned major release in an isolated environment and run
the read-only server locally:

```bash
uv venv /tmp/kubernetes-topology-venv
uv pip install --python /tmp/kubernetes-topology-venv/bin/python \
  -r work-agent-bundles/kubernetes-topology-poc/requirements.txt
KUBE_CONTEXT={{KUBE_CONTEXT}} \
KUBE_TOPOLOGY_KNOWLEDGE=work-agent-bundles/kubernetes-topology-poc/knowledge.example.json \
  /tmp/kubernetes-topology-venv/bin/python \
  work-agent-bundles/kubernetes-topology-poc/mcp_server.py
```

Its local Streamable HTTP endpoint is http://127.0.0.1:8766/mcp and exposes
`find_connections` and `find_namespace_health`. The MCP service makes a fresh
Kubernetes read on each call. No agent or gateway is wired to it yet. A remote
deployment needs dedicated read-only list/watch RBAC, an authenticated
gateway, per-tenant scoping, and a measured cache/refresh design.

## Health meaning and next build step

Green here means **tracked Kubernetes objects currently report ready**, and
selector-based Services have a ready EndpointSlice target. Red means a tracked
object is not ready. Amber means the tracked data does not support a health
conclusion or an API read failed. Empty namespaces are amber. Green does not
assert that customers can reach a service, that DNS resolves, that requests
meet an SLO, or that the entire fleet is healthy.

For fleet scale, replace per-request `kubectl` calls with Kubernetes
informers/watch streams per cluster, a bounded queue, a snapshot/version
checkpoint, and a central read model. Use stable workload identities across
pod churn. Aggregate health from readiness *and* explicit alert/SLO sources,
show source and freshness on every edge, and mark disconnected clusters
unknown. Headlamp can use its Map source API for the human view; the same read
model can back fixed MCP tools such as `find_connections`, `find_dependents`,
and `find_guidance`. Evaluate PostgreSQL tables, PostgreSQL+AGE, and Neo4j
only after representative multi-hop workloads and update rates are measured.

## Verification

```bash
python3 -m unittest discover -s work-agent-bundles/kubernetes-topology-poc -p 'test_*.py'
bash scripts/public-safe-scan.sh work-agent-bundles/kubernetes-topology-poc
```

The lab test checks ownership, Service→Pod endpoints, Gateway routes,
guidance references, bounded queries, and incomplete-read health. The live
kind proof and browser inspection should be recorded separately from these
offline tests.

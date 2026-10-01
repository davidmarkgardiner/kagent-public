# Radar in-cluster topology evaluation

**Date:** 2026-09-30
**Scope:** disposable kind lab only; Radar chart and image `1.15.0`. No AKS,
workplace cluster, production database, ingress, or external identity was used.

## Result

Radar is an Apache-2.0 alternative to most of this bundle's custom collector,
viewer, and MCP server. Its Helm deployment in the lab was Ready, the browser
showed a clickable namespace topology, and its built-in read-only MCP endpoint
returned Kubernetes relationships. A kagent `RemoteMCPServer` accepted and
discovered the tools, and a temporary Agent became Ready. An A2A prompt could
not reach tool use because the lab ModelConfig's upstream model returned a
five-hour quota-limit response. Thus conversational kagent tool use remains
**unproven**; MCP transport and kagent discovery are verified separately.

## What was actually checked

| Check | Observation |
|---|---|
| Deployment | Helm chart `radar` 1.15.0 installed in an isolated `radar-eval` namespace; one Pod Ready. No ingress. Access was through localhost port-forward. |
| Permissions | Rendered ClusterRole used `get/list/watch` for inventory and `create` for SelfSubjectAccessReview. It did not grant patch Deployment or read Secret in the tested configuration. Optional Helm writes, pod exec/logs, port-forward, traffic Secret, RBAC and webhook viewing were disabled. |
| Browser | Radar's Overview and Topology pages loaded. Namespace filtering showed the lab Gateway, HTTPRoute, Services, workloads, Pods, ConfigMaps, and ServiceAccounts, with edges and click-through resource navigation. |
| API | Before adding the temporary Agent, `/api/topology` returned 101 nodes and 72 edges. The counts change with cluster activity and namespace selection. It showed a Service `exposes` Deployment edge and a Gateway `routes-to` HTTPRoute edge. |
| Refresh | A temporary Service was created and then deleted in the isolated namespace; both changes appeared in `/api/topology` on the first poll (under 0.03 seconds after each `kubectl` command returned). This shows watch updates in this small lab, not fleet-scale latency. |
| MCP | `/mcp-readonly` negotiated MCP protocol `2025-03-26`, listed 25 tools with no write tools, and `get_neighborhood` for a known Service returned the Service, backing Deployment, `exposes` edge, and `truncated:false`. `get_topology` and `get_neighborhood` were present. |
| kagent | `RemoteMCPServer` Accepted=True and discovered 25 tools. The temporary Agent had only `get_neighborhood` and `get_topology` in its allowlist; the project verification helper reported Accepted, Ready, and API-listed. The A2A call failed upstream on model quota before any graph-tool response. |

## Gaps to resolve before choosing it for the fleet

1. In this lab, Radar mapped Gateway to HTTPRoute but did not show the next
   hop when the HTTPRoute backend was an `AgentgatewayBackend`. The Kubernetes
   HTTPRoute had an accepted, resolved backend reference. Our custom fixture
   explicitly maps `HTTPRoute → AgentgatewayBackend → Service`; a Radar upstream
   integration or a small extension would be required for this use case.
2. Radar does not represent our curated runbook, skill, or knowledge references
   as graph nodes. Those can remain in a separate approved knowledge service;
   joining them to Kubernetes identities is still design work.
3. Radar's Helm chart documents a **single replica** with an in-memory informer
   cache. This evaluation covers one small cluster. It does not prove a shared
   multi-cluster query plane, high availability, or the proposed fleet scale.
4. The lab had no metrics-server; Radar's health endpoint reported the metrics
   API was not discovered. Its visible readiness/issues should not be described
   as an application SLO or live service-traffic verdict. Live traffic requires
   a configured observation source, such as Hubble or Istio.
5. The lab's no-auth Service was ClusterIP only and locally port-forwarded.
   Production requires an authenticated, namespace-scoped UI and MCP route,
   fixed read-tool allowlists, and a review of Radar's RBAC and response bounds.

**Decision:** Pause new custom collector and viewer development. Test Radar's
missing `AgentgatewayBackend` hop and guidance lookup against a representative
cluster. Re-run the kagent A2A test when the lab model is available. Only build
the smallest extension needed after those checks.

## Repeatable lab setup

The local evaluation used the official chart source and explicit context.
Values were held outside Git. Use a disposable cluster only; render and review
the RBAC before installation.

```bash
helm repo add skyhook https://skyhook-io.github.io/helm-charts
helm repo update skyhook
helm template radar-eval skyhook/radar --version 1.15.0 \
  --namespace radar-eval -f {{REVIEWED_VALUES_FILE}} > /tmp/radar-eval-rendered.yaml
kubectl --context {{KUBE_CONTEXT}} apply --dry-run=server \
  -f /tmp/radar-eval-rendered.yaml
helm --kube-context {{KUBE_CONTEXT}} upgrade --install radar-eval \
  skyhook/radar --version 1.15.0 --namespace radar-eval \
  --create-namespace -f {{REVIEWED_VALUES_FILE}} --wait
kubectl --context {{KUBE_CONTEXT}} -n radar-eval \
  port-forward service/radar-eval 19280:9280
```

Then open `http://127.0.0.1:19280/`. In the test values, set
`usageReporting.enabled=false`, `auth.mode=none`, `ingress.enabled=false`,
`mcp.enabled=true`, and disable unneeded RBAC options as described above.
`auth.mode=none` was acceptable only because this lab used a localhost
port-forward and a disposable cluster.

Sources: [Radar repository](https://github.com/skyhook-io/radar),
[MCP guide](https://github.com/skyhook-io/radar/blob/main/docs/mcp.md),
[in-cluster guide](https://github.com/skyhook-io/radar/blob/main/docs/in-cluster.md).

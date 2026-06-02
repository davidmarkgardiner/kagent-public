# Workload To Release Mapping

This public-safe mapping documents how the deployment-state specialist resolves
an incident workload to deployment metadata during the demo.

| Namespace | Workload | Controller | Application / release |
|---|---|---|---|
| `demo-payments` | `checkout-api` | `synthetic-flux` | `checkout-api` |

Work environments should replace this with the authoritative mapping source:
Flux labels, Argo CD application labels, Helm release annotations, Backstage,
CMDB, or repo metadata.

# Chaos Engineering POCs

This directory compares two event-driven chaos engineering paths for local
validation clusters and future AKS production use.

| Area | Chaos Mesh POC | LitmusChaos POC |
| --- | --- | --- |
| Install complexity | Smaller controller footprint; experiments are CRDs and controllers. | ChaosCenter plus `litmus-core` plus experiment charts; more components but includes UI and catalog integration. |
| Argo native-ness | Integrates through Kubernetes events or custom webhooks. | Stronger fit: Litmus uses Argo-era workflow patterns and emits CRDs that Argo Events can watch directly. |
| Experiment catalog | Good Kubernetes-native fault set. | Larger ChaosHub catalog with Kubernetes, cloud, network, and application experiments. |
| AKS compatibility | Good for Kubernetes-native pod, network, DNS, and stress experiments. | Good for AKS and broader Azure/cloud experiments; needs RBAC and runtime socket settings validated per node pool. |
| Operational model | Lightweight and direct for cluster-local chaos. | Richer platform experience with ChaosCenter, reusable experiment hub, and event-driven triage hooks. |
| Recommendation | Keep as the lightweight Kubernetes-native baseline. | Prefer for production-path evaluation because it has ChaosCenter, a larger catalog, and cleaner Argo Events/kagent handoff. |

## Current Layout

```text
chaos/
|-- litmus/
|   |-- WORK-INSTALL.md
|   |-- experiments/
|   |-- manifests/
|   |-- values/
|   |-- run-demo.sh
|   `-- README.md
`-- README.md
```

## Current Lift-And-Shift Path

Use [`litmus/WORK-INSTALL.md`](litmus/WORK-INSTALL.md) for the ring-fenced
cluster install handoff. It links the exact Litmus Helm chart versions, values
files, image mirror list, RBAC review points, kagent/Argo Events integration,
validation commands, and local evidence captured from the demo run.

Add the Chaos Mesh POC under `chaos/chaos-mesh/` when MIL-143 lands in this repository.

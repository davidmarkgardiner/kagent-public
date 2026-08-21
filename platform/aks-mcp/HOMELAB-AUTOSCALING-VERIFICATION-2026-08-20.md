# AKS-MCP autoscaling verification — 2026-08-20

## Outcome

The chart's native HPA path passed server-side dry-run against the existing
`red` homelab. The KEDA Prometheus control loop, failure fallback, recovery,
and the full target schema passed in a disposable kind cluster. No work AKS
cluster was accessed and no existing homelab resource was changed.

This proves the Kubernetes and KEDA wiring. It does not prove the work
Prometheus query, Azure workload identities, real AKS-MCP multi-replica
traffic, Azure API throttling, or AKS node capacity.

## Static and chart gates

| Check | Result |
|---|---|
| `helm lint platform/aks-mcp/chart` | Passed: one chart linted, zero failed |
| `platform/aks-mcp/scripts/verify-autoscaling.sh` | Passed all default, HPA, KEDA, VPA Off, and invalid-combination assertions |
| Default render | One Deployment; no HPA, ScaledObject, or VPA |
| HPA render | One native HPA; no ScaledObject; optional VPA remained `Off` |
| AKS target render | One ScaledObject, TriggerAuthentication, VPA, and PDB; no separately rendered HPA |
| Public-safety scan | `{"clean":true,"hits":0}` |
| `git diff --check` | Passed |

The render test also proved that the chart rejects:

- an unknown or combined autoscaling mode;
- KEDA mode without a Prometheus endpoint and query;
- horizontal autoscaling with `app.transport=stdio`; and
- any VPA update mode other than `Off`.

## Existing `red` homelab

Observed server version: Kubernetes `v1.32.2`.

Observed capabilities:

- native `autoscaling/v2` HPA: present;
- native `policy/v1` PDB: present;
- resource metrics API: absent;
- KEDA ScaledObject/TriggerAuthentication CRDs: absent; and
- VPA CRD: absent.

The native target was rendered without chart-created RBAC and with the default
ServiceAccount, then submitted using server-side dry-run. The API accepted the
Service, Deployment, HPA, and PDB. Because the metrics API is absent, `red`
could validate the HPA schema but could not run the CPU control loop.

## Disposable KEDA control-loop test

The test used:

- a fresh kind Kubernetes `v1.35.0` cluster named
  `aks-mcp-autoscaling-test`;
- KEDA chart/application `2.18.2`;
- a dummy Deployment named `aks-mcp`, initially at two replicas; and
- a synthetic Prometheus HTTP query endpoint returning one value of `100` for
  the chart query `vector(100)`.

The chart-rendered ScaledObject used a threshold of `10`, a minimum of `2`, and
a maximum of `10`.

### Scale-up result

KEDA reported:

```text
Ready=True:ScaledObjectReady
Active=True:ScalerActive
Fallback=False:NoFallbackFound
health=Happy
```

KEDA created `HorizontalPodAutoscaler/keda-hpa-aks-mcp`. The chart's bounded
scale-up policy increased the target gradually, ultimately reaching:

```text
Deployment/aks-mcp desired=10 ready=10
```

The initial two-minute wait found eight replicas because the policy permits at
most 100 percent or two additional pods per 60 seconds. A subsequent bounded
wait reached ten. This was expected behavior, not a scaler error.

### Metric-failure and recovery result

The synthetic Prometheus Deployment was scaled to zero. After repeated failed
queries, KEDA reported:

```text
Ready=True:ScaledObjectReady
Active=False:ScalerNotActive
Fallback=True:FallbackExists
health=Failing failures=5
```

The HPA remained at ten during this short observation because the target
configuration deliberately has a 600-second scale-down stabilization window.
The test therefore proves fallback detection, not the eventual reduction to
the configured fallback of two replicas.

After the endpoint was restored, KEDA recovered without intervention:

```text
Ready=True:ScaledObjectReady
Active=True:ScalerActive
Fallback=False:NoFallbackFound
health=Happy failures=0
```

### Full target schema result

The current upstream VPA v1 CRD was added only to the disposable cluster. The
complete `values-autoscaling-aks.yaml` render then passed server-side dry-run
for all of these resources:

```text
PodDisruptionBudget
ServiceAccount
Secret
ClusterRole
ClusterRoleBinding
Service
Deployment
ScaledObject
TriggerAuthentication
VerticalPodAutoscaler
```

The disposable kind cluster and all of its test resources were deleted after
the evidence was captured.

## Remaining AKS acceptance gates

Before work deployment, the owning team still needs to prove:

1. the installed AKS managed KEDA version accepts the same fields;
2. the selected Azure Managed Prometheus endpoint and PromQL return one numeric
   result for idle, steady, and loaded AKS-MCP traffic;
3. the dedicated KEDA UAMI can read only the intended Monitor workspace;
4. two real AKS-MCP `v0.0.16` pods can concurrently serve initialize and tool
   calls through the actual kagent route;
5. scale-up improves queueing/latency without increasing Azure or Kubernetes
   API throttling; and
6. scale-down to two does not terminate an active MCP call.

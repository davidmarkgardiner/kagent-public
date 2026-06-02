# Grafana Alloy and VPA Guidance

This note documents the recommended Vertical Pod Autoscaler posture for Grafana
Alloy collectors running on AKS clusters.

## TLDR

Do not run Grafana Alloy with VPA `Auto` as the default production posture.

Use VPA in `Off` mode first to observe recommendations, then set bounded
requests and limits through the normal GitOps path. If automation is required,
prefer `Initial` or `InPlaceOrRecreate` on AKS versions that support it, with
explicit `minAllowed` and `maxAllowed` values.

The reason is simple: Alloy is observability plumbing. In AKS, VPA `Auto` is
deprecated and currently behaves like `Recreate`, so it can evict the Alloy pod
when recommendations change. That may create gaps in log or metric collection,
especially for singleton collectors or collectors using local pod storage.

## Recommendation

Treat VPA as a sizing advisor for Alloy, not as an unbounded automatic control
loop.

Recommended default:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: alloy-vpa
  namespace: monitoring
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: alloy
  updatePolicy:
    updateMode: "Off"
```

After several days of representative traffic, including a busy period or
incident-like log volume, review the VPA recommendation and update the Alloy
resource settings through the deployment manifest or Helm values.

If automatic updates are required:

- Use `Initial` when the goal is to size new pods without disrupting running
  collectors.
- Use `InPlaceOrRecreate` only on AKS versions that support in-place pod resize,
  and still expect eviction fallback in some cases.
- Avoid `Auto`; it is deprecated and currently behaves like `Recreate`.
- Set `minAllowed` and `maxAllowed` so recommendations cannot drift too low
  during quiet periods or too high after an incident.
- Consider `controlledValues: RequestsOnly` if limits should remain manually
  controlled.

Example bounded policy:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: alloy-vpa
  namespace: monitoring
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: alloy
  updatePolicy:
    updateMode: "Initial"
  resourcePolicy:
    containerPolicies:
      - containerName: alloy
        controlledResources:
          - cpu
          - memory
        controlledValues: RequestsOnly
        minAllowed:
          cpu: 50m
          memory: 128Mi
        maxAllowed:
          cpu: 1
          memory: 1Gi
```

Adjust the bounds for the target cluster and telemetry volume before applying.

## Why Alloy Is Different

Alloy is not a stateless application endpoint where a short pod recycle is
usually harmless. It can be responsible for:

- tailing Kubernetes pod logs;
- scraping Prometheus endpoints;
- scraping kubelet or cAdvisor metrics;
- forwarding telemetry to Loki, Mimir, Prometheus, Grafana Cloud, EventHub, or
  another downstream system;
- storing local positions, WAL data, or component state depending on the
  deployment mode and configuration.

For this repo, Alloy is part of the kagent and agentgateway observability path.
It tails logs, scrapes metrics, and remote-writes telemetry for dashboards and
alerts. That makes stability and predictable rollout behavior more important
than automatically minimizing pod requests.

## Expected Resource Variability

Alloy resource usage can change over time, but the changes are usually tied to
observable inputs rather than something VPA understands semantically:

- log ingestion rate;
- number of active metrics series;
- scrape interval;
- number of pods, nodes, and files being tailed;
- label cardinality;
- downstream latency or backpressure;
- incident bursts and noisy workloads.

VPA only sees CPU and memory history. It does not understand dropped samples,
collection gaps, log checkpoint behavior, or the operational importance of the
collector.

## Risks With VPA Auto

Using VPA `Auto` or `Recreate` for Alloy can introduce these issues:

- collection gaps while the pod is evicted and recreated;
- duplicate or missed log/event handling if state is local to the pod;
- request inflation after noisy incidents, which can make future scheduling
  harder;
- request reduction after quiet periods, followed by throttling or OOM risk
  during the next burst;
- disruption to singleton collectors where another pod does not cover the gap;
- harder incident analysis if the telemetry collector changed size or restarted
  during the same incident being investigated.

## Operational Pattern

1. Deploy Alloy with explicit requests and limits.
2. Add VPA in `Off` mode for recommendations only.
3. Observe recommendations across normal and busy windows.
4. Compare VPA recommendations with Alloy self-metrics, Loki/Mimir delivery,
   restart history, throttling, and OOM events.
5. Update resources through GitOps.
6. Keep bounded VPA automation only where the disruption behavior is acceptable.

## Checks Before Enabling Automation

Before moving beyond `Off`, confirm:

- the target AKS version and VPA version;
- whether `InPlaceOrRecreate` is supported;
- whether the Alloy collector is a singleton, Deployment, DaemonSet, or
  StatefulSet;
- whether Alloy uses local pod storage for positions or WAL data;
- whether a PodDisruptionBudget exists and is meaningful for the controller;
- whether the node pool has room for the maximum allowed recommendation;
- whether alerting covers Alloy restarts, OOM kills, throttling, and failed
  remote-write or export delivery.

## Teams Message

Hi team,

Short version: I would not put the Grafana Alloy collector on VPA `Auto` as the
default setting.

On AKS, VPA `Auto` is deprecated and currently behaves like `Recreate`, so it
can evict and restart the Alloy pod when recommendations change. Because Alloy
is collecting logs and metrics for Grafana, that restart can create collection
gaps or make incident timelines harder to trust.

The better posture is:

- run VPA in `Off` mode first and use it for recommendations;
- review sizing after a representative traffic window;
- set explicit bounded requests and limits through GitOps;
- only use `Initial` or `InPlaceOrRecreate` if we want automation and the AKS
  version plus collector setup can tolerate it;
- always set min and max bounds.

So VPA is useful here, but mainly as a sizing advisor. I would avoid leaving
Alloy on unbounded `Auto`, especially for singleton collectors or anything that
stores local collection state.

## References

- [AKS Vertical Pod Autoscaler](https://learn.microsoft.com/en-us/azure/aks/vertical-pod-autoscaler)
- [Kubernetes Vertical Pod Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/vertical-pod-autoscale/)
- [Grafana Alloy resource usage guidance](https://grafana.com/docs/alloy/latest/set-up/estimate-resource-usage/)
- [Grafana Alloy collector reference](https://grafana.com/docs/grafana-cloud/monitor-infrastructure/kubernetes-monitoring/configuration/helm-chart-config/helm-chart/collector-reference/)

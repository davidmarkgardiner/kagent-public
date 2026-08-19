# AKS 1.35 and 1.36 Efficiency Priorities

## Context and Assumptions

This recommendation is for a platform that:

- uses many Kyverno mutation policies;
- uses AKS node auto-provisioning (NAP);
- hosts a large number of namespaces across a fleet of clusters;
- is introducing Vertical Pod Autoscaler (VPA) to reduce compute cost; and
- wants to improve platform efficiency without weakening reliability or tenant controls.

The phrases "cavernal mutations" and "no-dot provisioner" in the source request are interpreted as **Kyverno mutations** and **node auto-provisioning**. Confirm those interpretations before turning this guidance into an implementation backlog.

## Verdict: Pick These Three

| Priority | Capability | Version | Why it fits this platform |
| --- | --- | --- | --- |
| 1 | CEL-based `MutatingAdmissionPolicy` | Kubernetes 1.36, stable upstream and enabled by default upstream | Move simple, deterministic Kyverno mutations into the API server to reduce admission network hops, webhook latency, certificates, service dependencies, and failure surface. |
| 2 | In-place Pod resize with VPA `InPlaceOrRecreate` | Resize is stable in Kubernetes 1.35; AKS supports VPA `InPlaceOrRecreate` on 1.34+ | The most direct route to lower node cost: improve requests without routinely evicting Pods, then let NAP bin-pack and consolidate underused nodes. |
| 3 | Pressure Stall Information (PSI) metrics | Kubernetes 1.36, stable and locked enabled upstream | Use CPU, memory, and I/O stall time to reduce unjustified resource padding while detecting noisy-neighbour pressure that ordinary utilisation misses. |

These features reinforce one another:

```text
lower admission overhead
        +
better workload requests from VPA
        +
contention evidence from PSI
        ↓
safer bin-packing and NAP consolidation
        ↓
fewer node-hours at an evidence-backed reliability level
```

Version upgrades do not produce savings automatically. The savings occur only when policies are migrated safely, resource requests become more accurate, NAP is allowed to consolidate capacity, and the resulting node-hours or VM spend actually decline.

## 1. Replace Simple Kyverno Mutations with CEL Admission Policies

### Why This Is the Best 1.36 Platform-Efficiency Feature

Kubernetes 1.36 makes `MutatingAdmissionPolicy` stable. Policies run in the API-server admission path using Common Expression Language (CEL), rather than requiring every matching request to make a network call to a mutating webhook.

For a fleet with many namespaces and a high volume of object creation and update, this can reduce:

- admission webhook calls and aggregate latency;
- Kyverno admission-controller CPU and memory consumption;
- webhook TLS certificate and Service lifecycle work;
- failure modes caused by network, DNS, endpoint, or webhook availability;
- fleet-wide operational overhead for simple defaulting rules.

### Good First Migration Candidates

Start with deterministic rules that only need the incoming object and static or parameterized platform data, for example:

- adding standard ownership, cost-centre, environment, or support labels;
- adding annotations used by platform automation;
- applying a default security context;
- setting a default topology spread, scheduling preference, or toleration;
- applying a standard resource field where the ownership model is unambiguous.

### Keep These in Kyverno

Do not treat CEL policies as a wholesale Kyverno replacement. Retain Kyverno where a policy depends on:

- image verification or supply-chain features;
- policy reports and Kyverno-specific audit workflows;
- generate or cleanup behaviour;
- external or cross-resource context not available to the CEL policy;
- complex mutation that is clearer and safer in the existing engine;
- an established exception, testing, or policy-distribution workflow that CEL cannot yet reproduce.

### Migration Experiment

1. Inventory Kyverno mutation policies by request volume, p95 latency, failure rate, complexity, and dependency type.
2. Select three to five high-volume, low-complexity policies.
3. Reproduce them as CEL policies in a non-production 1.36 cluster.
4. Build a golden corpus containing normal objects, malformed objects, exemptions, server-side apply, patch, update, dry-run, and deletion paths.
5. Compare mutated output field by field and test idempotency.
6. Run only one mutator as the owner of each field; avoid overlapping Kyverno and CEL mutation in production.
7. Canary by cluster cohort, with an immediate rollback path to the original Kyverno rule.

### Success Measures

- admission p50, p95, and p99 latency;
- Kyverno admission-controller CPU and memory;
- webhook timeouts, denials, fail-open events, and unavailable endpoints;
- API request throughput during namespace and workload bursts;
- mutation parity and policy-exception parity;
- operational incidents and certificate rotations attributable to mutation webhooks.

## 2. Use Stable In-Place Resize to Make VPA and NAP Work Together

### Why This Is the Best Direct Cost Opportunity

Kubernetes 1.35 makes in-place CPU and memory resize stable. AKS documents `InPlaceOrRecreate` as the preferred VPA mode when a restart-free update is possible, with Pod recreation as the fallback.

The cost chain is:

1. VPA learns that a workload request is larger than its observed need.
2. VPA reduces the request in place where supported, avoiding routine eviction and recreation.
3. The scheduler and NAP see more accurate resource requests.
4. Pods can fit on fewer or better-matched nodes.
5. NAP consolidation removes empty or underutilised nodes or replaces them with less expensive variants.

NAP provisions from Pod requests, not from wishful utilisation targets. VPA therefore improves the input that drives NAP's SKU selection, scheduling, and consolidation decisions.

### Scale Constraint

Microsoft currently documents optimal AKS VPA support for up to **1,000 Pods per cluster associated with VPA objects**. VPA component memory—especially recommender memory—grows with the number of tracked Pods. A platform with thousands of namespaces should not enable VPA indiscriminately across every workload.

Use cohorts such as:

- high-cost, stable Linux services with visibly inflated requests;
- workloads without JVM memory-sizing ambiguity;
- workloads that do not use static CPU Manager, static Memory Manager, or swap;
- workloads whose HPA does not use the same CPU or memory signal;
- workloads with a tested PodDisruptionBudget for the fallback recreate path.

### Rollout Sequence

1. Start with VPA `Off` mode to collect recommendations without changing workloads.
2. Collect enough representative peak, weekday, weekend, deployment, and batch-cycle data.
3. Add minimum and maximum resource policies so outlier recommendations cannot create unschedulable Pods or consume a namespace unfairly.
4. Review conflicts with `LimitRange`, `ResourceQuota`, HPA, KEDA, PDB, and Kyverno resource mutation.
5. Move a small cohort to `InPlaceOrRecreate`.
6. Observe resize conditions, deferred resizes, fallbacks to recreation, OOM events, throttling, latency, and application behaviour.
7. Confirm that lower requests produce actual NAP consolidation and lower node-hours.
8. Expand only while VPA recommender and updater performance remain within a defined scale envelope.

### Important Guardrails

- Do not use VPA and HPA on the same CPU or memory metrics. Use HPA/KEDA with application or external demand metrics if VPA owns CPU or memory sizing.
- Memory limit reduction uses a best-effort safety check and can still expose applications to risk; canary it separately from CPU changes.
- Java and Python runtimes may not adapt safely to all in-place memory changes. Microsoft specifically documents JVM-based workloads as unsupported by AKS VPA.
- Treat Pod recreation as an expected fallback, not an exceptional impossibility.
- Preserve enough spare capacity and disruption budget for NAP consolidation and VPA fallback actions.

### Success Measures

- requested CPU and memory versus p95 and p99 usage;
- VPA recommendation acceptance and in-place success rate;
- fallback recreation and failed or deferred resize rate;
- OOM, CPU throttling, latency, saturation, and error budgets;
- NAP NodeClaim count, VM SKU mix, consolidation actions, and disruption rate;
- allocatable capacity, stranded capacity, idle cost, node-hours, and Azure compute spend;
- VPA recommender, updater, and admission-controller memory and CPU.

The primary financial gate should be **cost per unit of useful workload**, not merely a higher node utilisation percentage.

## 3. Use PSI to Right-Size Without Flying Blind

### Why PSI Is Useful

Traditional utilisation says how busy a resource is. Pressure Stall Information says how much time workloads lose because CPU, memory, or I/O is contended. Kubernetes 1.36 exposes stable PSI signals at node, Pod, and container level through the kubelet Summary API and `/metrics/cadvisor`.

This helps a high-density, multi-tenant platform distinguish:

- a highly utilised but healthy node from a node where workloads are stalling;
- safe bin-packing from harmful noisy-neighbour contention;
- CPU shortage from memory reclaim or I/O saturation;
- an overprovisioned request from headroom that is actually protecting latency.

PSI should improve the evidence used to set VPA bounds and NAP consolidation policy. It should not be wired directly into automated eviction or provisioning until its relationship with application service levels is understood.

### Requirements and Limits

- Linux kernel 4.20 or later;
- cgroup v2;
- PSI enabled in the node OS;
- a Prometheus-compatible path scraping kubelet cAdvisor metrics or an approved Summary API collector;
- Windows nodes omit these metrics.

Confirm that the selected AKS node image and Azure monitoring path expose the required series before declaring PSI available across the fleet.

### Adoption Experiment

1. Enable collection on one representative 1.36 Linux cluster without adding automated actions.
2. Dashboard CPU, memory, and I/O `some` and `full` pressure alongside workload latency, errors, throttling, OOM, eviction, node utilisation, and NAP events.
3. Establish workload-specific relationships between sustained pressure and service-level degradation.
4. Use those results to set VPA minimums and maximums, resource-quota headroom, and NAP consolidation guardrails.
5. Alert on sustained pressure windows rather than brief spikes.

### Success Measures

- percentage of nodes and Pods with valid PSI data;
- sustained pressure correlated with application latency or errors;
- noisy-neighbour incidents detected before outage;
- reduction in unnecessary request headroom without SLO regression;
- lower node-hours while pressure and application error budgets remain acceptable.

## Ingest Kubernetes 1.35 and 1.36 Separately

The versions should enter the platform backlog as separate capability increments rather than one combined "upgrade value" epic.

### Kubernetes 1.35 Ingestion

| Capability | Decision | Work item |
| --- | --- | --- |
| In-place Pod CPU and memory resize, stable | Adopt through a bounded VPA trial. | Prove `Off` to `InPlaceOrRecreate`, fallback behaviour, workload compatibility, and realised NAP savings. |
| Pod `generation` and `observedGeneration`, stable | Adopt where custom controllers need reliable acknowledgement of Pod updates. | Update controller and dashboard logic; use the fields to distinguish desired from observed resize state. |
| Native storage-version migration, beta | Evaluate for object-dense upgrade operations. | Measure migration load, conflicts, API latency, and recovery on a representative non-production cluster. |
| `PreferSameNode` and `PreferSameZone`, stable | Evaluate for chatty services. | Measure latency, resilience, and Azure cross-zone data-transfer effects before standardising. |
| Job `managedBy`, stable | Adopt only if the platform uses multi-cluster batch dispatch such as MultiKueue. | Keep out of the general workload baseline otherwise. |

### Kubernetes 1.36 Ingestion

| Capability | Decision | Work item |
| --- | --- | --- |
| CEL mutating admission policies, stable | Prioritise. | Migrate a small set of high-volume, deterministic Kyverno mutations and compare admission cost and correctness. |
| PSI metrics, stable | Prioritise. | Establish Linux/cgroup v2 availability, metrics ingestion, SLO correlation, and dashboards. |
| Fine-grained kubelet authorization, stable | Adopt as a security-efficiency improvement. | Remove unnecessary `nodes/proxy` access from monitoring and support identities after compatibility testing. |
| User namespaces for Pods, stable | Evaluate for multi-tenant defence in depth. | Test node OS, runtime, storage, security agent, and workload compatibility. |
| Mutable CSI volume attachment limits, stable | Adopt through managed-driver compatibility testing. | Measure reduction in stale-limit scheduling failures on storage-heavy clusters. |
| Server-side sharded list and watch, alpha | Watch only. | Do not plan production use unless AKS explicitly exposes the API-server feature gate and the feature reaches an acceptable maturity level. |

## Ninety-Day Evaluation Plan

### Days 0-30: Baseline and Selection

- confirm that the source terms mean Kyverno and NAP;
- capture admission, VPA, NAP, workload, node, and Azure cost baselines;
- inventory mutation rules and select CEL candidates;
- select a VPA workload cohort below the documented scale envelope;
- verify PSI prerequisites and metrics-path compatibility.

### Days 31-60: Non-Production Proof

- run Kyverno-versus-CEL mutation parity and load tests;
- run VPA in recommendation-only mode, then canary `InPlaceOrRecreate`;
- collect PSI and correlate it with application SLOs;
- test NAP consolidation after requests decrease;
- exercise rollback, PDB, quota, HPA/KEDA, and webhook failure paths.

### Days 61-90: Controlled Production Canary

- promote one CEL mutation cohort with a rollback window;
- promote selected VPA workloads within strict resource bounds;
- retain PSI as an observability signal, not an automatic actuator;
- compare node-hours and cost per useful workload against the baseline;
- decide whether to expand, amend, or stop each capability independently.

## Go/No-Go Scorecard

| Capability | Go when | Stop or amend when |
| --- | --- | --- |
| CEL mutations | Mutation parity is complete and admission latency or Kyverno footprint materially improves. | Field ownership overlaps, exception behaviour differs, or API-server admission errors increase. |
| VPA plus NAP | Requests fall safely and node-hours or VM spend declines without SLO regression. | Recommender scale, resize failures, recreation, OOM, throttling, or disruption exceeds budget. |
| PSI | Coverage is reliable and sustained pressure predicts service impact. | Metrics are absent, too costly, or do not correlate with actionable outcomes. |

## References

- [Kubernetes 1.36 Mutating Admission Policy](https://kubernetes.io/docs/reference/access-authn-authz/mutating-admission-policy/)
- [Kubernetes 1.35 in-place Pod resize GA](https://kubernetes.io/blog/2025/12/19/kubernetes-v1-35-in-place-pod-resize-ga/)
- [AKS Vertical Pod Autoscaler](https://learn.microsoft.com/azure/aks/vertical-pod-autoscaler)
- [AKS node auto-provisioning](https://learn.microsoft.com/azure/aks/node-auto-provisioning)
- [AKS cost-optimisation best practices](https://learn.microsoft.com/azure/aks/best-practices-cost)
- [Kubernetes 1.36 PSI metrics GA](https://kubernetes.io/blog/2026/05/12/kubernetes-v1-36-psi-metrics-ga/)
- [Kubernetes server-side sharded list and watch](https://kubernetes.io/blog/2026/05/06/kubernetes-v1-36-server-side-sharded-list-and-watch/)
- [AKS supported versions and managed component changes](https://learn.microsoft.com/azure/aks/supported-kubernetes-versions)

## Evidence Boundary

This is a prioritisation and evaluation document based on upstream Kubernetes and Microsoft AKS documentation available on 19 August 2026. It does not prove that a feature is enabled in the target subscriptions, regions, cluster modes, node images, or monitoring stack. It does not record a production mutation migration, VPA rollout, NAP saving, PSI ingestion, or scale test. Each outcome requires evidence from representative target clusters.

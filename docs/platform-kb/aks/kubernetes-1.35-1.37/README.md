# AKS Kubernetes 1.35, 1.36, and 1.37 for Large Multi-Tenant Platforms

## Executive Summary

For a platform team hosting thousands of namespaces across a fleet of AKS clusters, Kubernetes 1.36 is the stronger target for new clusters and staged upgrades. Its most relevant improvements are stable CEL-based mutating admission policies, stable user namespaces, fine-grained kubelet authorization, Pressure Stall Information (PSI), safer impersonation, and controller-staleness safeguards.

Kubernetes 1.35 remains an important stepping stone. It brings stable in-place Pod resource resizing and Pod generation tracking, plus beta native storage-version migration. These improve workload rightsizing and controller correctness in object-dense clusters.

Kubernetes 1.37 is a forward-looking evaluation target, not the current production recommendation. As of 19 August 2026, its upstream release is planned for 26 August 2026; Microsoft schedules AKS preview for September 2026 and AKS general availability for October 2026. The announced feature set can still change before the upstream release.

None of these releases, by itself, proves that a cluster can safely host a particular number of namespaces. Namespace density remains a measured scale-envelope decision involving API object count and churn, admission latency, watch traffic, controller queues, scheduler throughput, network policy scale, identity boundaries, and recovery objectives.

## Recommendation

1. Use AKS 1.36 as the target baseline for new clusters when the required region and AKS configuration support it.
2. Upgrade existing supported non-LTS clusters one minor version at a time.
3. Canary 1.36 on representative clusters before a staged fleet rollout.
4. Track 1.37 in a separate evaluation lane, then reassess after the final upstream release notes, AKS preview component matrix, regional availability, and workload compatibility evidence exist.
5. Prioritize stable and beta capabilities that AKS actually exposes; do not build a production dependency on upstream alpha feature gates.
6. Treat upstream feature maturity and AKS product availability as separate gates.

As of 19 August 2026, Microsoft lists AKS 1.35 and 1.36 as generally available. Community support is listed through March 2027 for 1.35 and June 2027 for 1.36. With AKS long-term support enabled, the listed dates extend to March 2028 and June 2028 respectively. Microsoft's planned dates for AKS 1.37 are October 2027 for community end of life and October 2028 for LTS end of life, subject to the version reaching AKS GA as scheduled.

## Three Priorities for the Current Platform

For a platform that uses many Kyverno mutations, AKS node auto-provisioning, large numbers of namespaces, and VPA for cost reduction, prioritize these three capabilities:

1. **CEL-based mutating admission policies in Kubernetes 1.36.** Move simple, deterministic, high-volume Kyverno mutations into the API server. This can reduce webhook calls, admission latency, controller resources, certificate management, and webhook availability dependencies. Keep image verification, reporting, generate/cleanup behaviour, external context, and complex rules in Kyverno.
2. **Stable in-place Pod resize from Kubernetes 1.35 with AKS VPA `InPlaceOrRecreate`.** Let VPA improve CPU and memory requests without routinely restarting Pods, then allow node auto-provisioning to bin-pack and consolidate underused nodes. Measure realised node-hours and VM spend; lower requests alone are not proof of savings. Microsoft currently documents optimal AKS VPA support for up to 1,000 VPA-managed Pods per cluster, so use selected workload cohorts rather than enabling it indiscriminately across every namespace.
3. **Stable Pressure Stall Information metrics in Kubernetes 1.36.** Use CPU, memory, and I/O stall time to distinguish safe utilisation from harmful contention. PSI provides evidence for reducing unjustified resource padding while protecting workloads from noisy neighbours. Validate Linux, cgroup v2, node-image, and metrics-pipeline support before relying on it.

Together, these capabilities provide a practical efficiency loop: reduce admission overhead, improve resource requests, use PSI to protect the reliability boundary, and allow node auto-provisioning to turn freed capacity into fewer node-hours.

See [AKS 1.35 and 1.36 efficiency priorities](../kubernetes-1.35-1.36-efficiency-priorities/README.md) for the migration experiments, separate version-ingestion tables, 90-day evaluation plan, success metrics, and go/no-go gates.

## Highest-Value Capabilities

| Capability | Version and maturity | Platform value at fleet scale | Adoption note |
| --- | --- | --- | --- |
| Stable Metrics API | 1.37, planned stable upstream | Moves the widely used `metrics.k8s.io` API behind HPA and `kubectl top` from beta to `v1`, providing a durable API contract for platform integrations. | No major functional change is expected. Inventory clients pinned to `v1beta1` and wait for the final release and AKS component matrix. |
| Rootless kubelet using a user namespace | 1.37, planned beta upstream | Reduces host-level privilege for a critical node component and could limit the impact of a kubelet vulnerability. | Treat as research until AKS explicitly documents node-image and support availability; customers do not configure the managed AKS node architecture solely from upstream feature status. |
| Volume health monitor API | 1.37, planned alpha upstream | Proposes machine-readable PVC, Pod, and CSINode storage-health signals for automated diagnosis and remediation. | Evaluation only. It requires CSI driver support, is alpha, and was reset to alpha after an earlier implementation. |
| Mutating admission policies using CEL | 1.36, stable upstream | Replaces many simple mutation webhooks with declarative API-server policy, reducing network hops, certificate management, latency, and webhook failure modes. | Inventory existing webhooks and confirm AKS exposure before migration. Keep complex external lookups in webhooks. |
| User namespaces for Pods | 1.36, stable upstream | Maps container root to an unprivileged host user, adding defence in depth for multi-tenant nodes. | Validate the selected AKS node OS, container runtime, storage drivers, security tooling, and workload compatibility. |
| Fine-grained kubelet API authorization | 1.36, stable upstream | Lets monitoring and diagnostic components avoid broad `nodes/proxy` access. This reduces the blast radius of fleet-wide observability identities. | Re-test metrics, log, and support tooling with least-privilege RBAC. |
| Pressure Stall Information | 1.36, stable upstream | Distinguishes a merely busy node from CPU, memory, or I/O contention. This is useful for detecting noisy neighbours and tuning shared node pools. | Confirm that the node OS exposes PSI and that the chosen metrics pipeline collects actionable signals. |
| Constrained impersonation | 1.36, beta upstream | Allows support services and platform controllers to impersonate tenants without automatically inheriting every permission available to the tenant. | Confirm AKS enablement and test existing support, proxy, and automation identities. |
| Controller staleness mitigation | 1.36, beta upstream | Helps controllers avoid acting on stale cached state, which becomes more important as object counts, watch lag, and reconciliation concurrency grow. | Test custom controllers against 1.36 client libraries and observe cache freshness and work queues. |
| Strict IP and CIDR validation | 1.36, beta upstream | Rejects malformed IP data earlier, reducing confusing Service and NetworkPolicy behaviour across tenant-generated resources. | Audit stored objects and manifests before enforcement to find values accepted by older versions. |
| Mixed-version API-server proxy | 1.36, beta upstream | Reduces incorrect `404` responses while highly available API servers temporarily run different versions during a control-plane upgrade. | This improves an upgrade path; it does not replace canaries, compatibility tests, or staged rollout. |
| Mutable CSI volume attachment limits | 1.36, stable upstream | Keeps scheduler storage-capacity information current without component restarts, reducing avoidable scheduling failures. | Benefit depends on CSI driver support and the AKS-managed driver versions. |
| Volume group snapshots | 1.36, stable upstream | Enables crash-consistent recovery points across groups of PVCs. | Requires compatible CSI snapshot support; validate Azure Disk and Azure Files behaviour separately. |
| In-place Pod CPU and memory resize | 1.35, stable upstream | Enables less disruptive rightsizing and can improve utilisation of long-running and stateful workloads. | Validate application, autoscaler, metrics, and policy behaviour before automating resize. |
| Native storage-version migration | 1.35, beta upstream | Replaces fragile bulk read/write loops with control-plane migration logic, valuable in clusters containing large numbers of API objects and Secrets. | Establish etcd and API-server performance guardrails and test migration load on a representative canary. |
| Pod `generation` and `observedGeneration` | 1.35, stable upstream | Gives controllers a reliable signal that a kubelet has observed a Pod specification update. | Update custom controller logic and dashboards to use the signal where appropriate. |
| `PreferSameNode` and `PreferSameZone` Service traffic distribution | 1.35, stable upstream | Can reduce latency and cross-zone traffic cost for suitable services. | Model resilience carefully; a routing preference is not an availability guarantee. |
| Job `managedBy` | 1.35, stable upstream | Supports clean delegation of Job synchronization to systems such as MultiKueue for multi-cluster batch dispatch. | Relevant when the platform operates a batch or AI scheduling service. |
| Pod certificates | 1.35, beta upstream | Offers a native building block for rotated workload certificates and mTLS without distributing long-lived bearer credentials. | Confirm AKS signer integration and operational ownership before replacing cert-manager or SPIFFE/SPIRE. |

## Capabilities to Evaluate, Not Standardize Yet

Kubernetes 1.35 and 1.36 introduce alpha workload-aware scheduling features including the Workload API, PodGroups, gang scheduling, workload-aware preemption, and tighter Dynamic Resource Allocation integration. These can reduce partial placement and wasted capacity for distributed AI, HPC, and batch workloads.

They should remain evaluation-only for this platform until they reach an acceptable maturity level and AKS explicitly exposes the required feature gates. AKS customers do not control the managed control plane in the same way as a self-managed Kubernetes deployment.

Similarly, external ServiceAccount token signing is stable upstream in 1.36 but requires control-plane integration. Do not assume it is configurable in AKS without explicit Microsoft documentation or a validated AKS capability.

Kubernetes 1.37 as a whole belongs in this evaluation category until it has shipped upstream and the target AKS region exposes a suitable preview or GA patch. Preview clusters should not carry production tenants or become the only evidence source for platform compatibility.

## Kubernetes 1.37 Watchlist

### Potential Benefits

- A stable `metrics.k8s.io/v1` API gives platform tooling a durable resource-metrics contract after nearly nine years of beta usage.
- Rootless kubelet beta could materially improve node defence in depth if AKS adopts and supports it in its managed node images.
- The redesigned volume health monitor could eventually make storage failures machine-readable and automatable across large fleets.

### Announced Migration Risks

- `kubectl run --filename` and `kubectl run -f` are planned for deprecation. Search platform scripts, documentation, CI jobs, and tenant examples for these forms.
- Static Pods can no longer reference Secrets or ConfigMaps. Audit any custom static-Pod node bootstrap or security tooling.
- `kube-proxy` IPVS mode begins its deprecation path, with disablement planned for 1.40 and removal planned for 1.43. Confirm the networking mode in every fleet cohort and create a migration plan where IPVS remains.
- cgroup v1 is already on a removal path. Confirm all supported node images use cgroup v2 and eliminate temporary `failCgroupV1: false` dependencies.
- SELinux volume relabeling is planned to become GA and enabled by default when the CSI driver opts in. Pods with different SELinux labels sharing a volume on the same node may fail to start unless compatibility is addressed.
- Microsoft states that Windows Server 2022 node pools are not supported with Kubernetes 1.37 and later. Fleets containing Windows workloads require a separate node OS migration decision before adopting 1.37.

### Promotion Preconditions

Do not promote 1.37 into the production baseline until all of the following are true:

1. Kubernetes 1.37 has a final upstream release and changelog.
2. AKS publishes preview or GA component and breaking-change details for the exact target patch.
3. The target Azure regions expose the required AKS version.
4. CNI, CSI, policy, identity, ingress, service mesh, autoscaling, security, backup, and observability dependencies pass compatibility testing.
5. Linux cgroup, SELinux storage, kube-proxy, and any Windows node-pool implications have explicit owners and migration evidence.
6. A representative object-heavy canary passes the validation and failure tests in this document.

## What These Versions Do Not Solve

An upgrade does not remove the need to engineer and prove:

- tenant trust boundaries and the choice between namespace, node-pool, or cluster isolation;
- default-deny network policy and metadata-service protection;
- namespace quotas, object-count quotas, limit ranges, and Pod security controls;
- API Priority and Fairness behaviour for tenant and platform identities;
- admission webhook availability, timeouts, failure policy, and aggregate latency;
- CRD count, conversion webhook behaviour, and stored-version lifecycle;
- controller and informer memory use at the fleet's real object count;
- DNS, service, endpoint, and network-policy scale;
- observability cost and cardinality controls;
- restore, regional failure, and fleet rollback objectives.

AKS documents namespace isolation as appropriate for trusted internal tenants and stronger node-pool or cluster isolation for higher-risk boundaries. A namespace must not be treated as equivalent to a hard security boundary for mutually untrusted tenants.

## Canary Validation Plan

### 1. Establish a Representative Canary

Select at least one cluster with representative namespace count, API object density, admission stack, CRDs, policy engine, CNI, CSI, service mesh, autoscaling, and observability agents. A nearly empty technical canary is insufficient for a scale decision.

### 2. Capture the Pre-Upgrade Baseline

Record, at minimum:

- API-server request latency, error rate, throttling, and inflight saturation;
- admission webhook latency, rejection rate, timeout rate, and fail-open events;
- controller work-queue depth, retries, reconcile duration, and watch reconnects;
- scheduler pending Pods, scheduling latency, preemption, and unschedulable reasons;
- namespace provisioning and deletion duration;
- DNS latency and error rate;
- node CPU, memory, I/O pressure, eviction, and throttling signals;
- CNI address allocation and network-policy programming latency;
- CSI attach, mount, resize, and snapshot errors;
- platform controller memory and restart counts;
- tenant-facing availability and support-ticket rate.

### 3. Run Compatibility Gates

Validate the exact versions of:

- Azure CNI or Cilium and all network policies;
- Azure Disk, Azure Files, Blob CSI, and snapshot components in use;
- CoreDNS and custom DNS configuration;
- Gatekeeper, Azure Policy, Kyverno, or other admission components;
- service mesh and ingress or Gateway API implementations;
- KEDA, VPA, HPA, Cluster Autoscaler, and node auto-provisioning;
- custom operators, CRDs, conversion webhooks, and Kubernetes client libraries;
- security, monitoring, backup, and disaster-recovery agents.

Review Microsoft's AKS component and breaking-change table for the exact patch version before each rollout. Managed add-ons and node images can change independently of the upstream Kubernetes headline features.

### 4. Exercise Scale and Failure Paths

Run controlled tests for:

- burst namespace and workload creation at expected peak rates;
- mass list/watch reconnect after an API-server or controller disruption;
- webhook slowdown, unavailability, and certificate rotation;
- node drain, image update, zone loss, and Pod rescheduling;
- storage attachment exhaustion and snapshot or restore;
- tenant quota exhaustion and deliberately malformed IP/CIDR configuration;
- rollback of platform policies and application releases;
- upgrade progression while representative clients remain active.

### 5. Use Explicit Promotion Gates

Promote only when the canary remains within agreed error and latency budgets, no critical compatibility gaps remain, rollback has been exercised, and platform owners have durable evidence for the result. Roll out by fleet stage, with soak time and approval gates between representative cohorts.

## Suggested Adoption Sequence

1. Upgrade a representative non-production cluster to AKS 1.35 if required by the supported upgrade path.
2. Upgrade that canary to AKS 1.36 and complete compatibility and failure testing.
3. Introduce PSI-based dashboards before using PSI signals for automated decisions.
4. Reduce kubelet API permissions for monitoring components and verify their behaviour.
5. Trial user namespaces with selected compatible workloads.
6. Convert simple, deterministic mutation webhooks to CEL policies in a shadow or audit-first workflow.
7. Test constrained impersonation for tenant-support tooling if AKS exposes it.
8. Roll out AKS 1.36 through Fleet Manager stages: platform canary, low-risk clusters, representative production clusters, then the remaining fleet.
9. After upstream 1.37 ships, review the final changelog against this watchlist and update the compatibility inventory.
10. Use AKS 1.37 preview only for disposable evaluation clusters; begin production promotion assessment after AKS GA and regional rollout evidence exist.

## Decision Record

| Decision | Position |
| --- | --- |
| Default version for new clusters | Prefer AKS 1.36 after regional and dependency validation. |
| Existing fleet | Use canary-first, one-minor-at-a-time upgrades and staged Fleet Manager update runs. |
| Kubernetes 1.37 | Track as a forward-looking evaluation target; do not treat planned upstream or AKS dates as delivered capability. |
| Primary business case | Safer multi-tenancy and admission, better contention visibility, and more reliable controllers and upgrades. |
| Namespace-scale claim | Not established by version number; prove against representative object density and churn. |
| Alpha features | Evaluation only; no production dependency. |
| Upstream stable features | Still require explicit AKS, node OS, runtime, add-on, and workload compatibility checks. |

## References

- [Kubernetes 1.35 release announcement](https://kubernetes.io/blog/2025/12/17/kubernetes-v1-35-release/)
- [Kubernetes 1.36 release announcement](https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/)
- [Kubernetes 1.37 sneak peek](https://kubernetes.io/blog/2026/07/31/kubernetes-v1-37-sneak-peek/)
- [AKS supported Kubernetes versions and component changes](https://learn.microsoft.com/azure/aks/supported-kubernetes-versions)
- [AKS Windows node OS upgrade guidance](https://learn.microsoft.com/azure/aks/upgrade-windows-os)
- [AKS multi-tenancy concepts](https://learn.microsoft.com/azure/aks/concepts-multi-tenancy)
- [AKS cluster operator and developer best practices](https://learn.microsoft.com/azure/aks/best-practices)
- [Azure Kubernetes Fleet Manager](https://learn.microsoft.com/azure/kubernetes-fleet/)
- [Fleet Manager update orchestration](https://learn.microsoft.com/azure/kubernetes-fleet/concepts-update-orchestration)

## Evidence Boundary

This document is an architecture and adoption guide based on upstream Kubernetes release documentation and Microsoft AKS documentation available on 19 August 2026. Kubernetes 1.37 content is based on a pre-release upstream preview and Microsoft's published future AKS schedule, so it is provisional. This document does not record a live upgrade, performance test, feature-availability test, or production rollout. Those outcomes require evidence from the target AKS subscriptions, regions, cluster configurations, and workloads.

# AKS Node Auto-Provisioning Platform Guide

## Summary

Node auto-provisioning (NAP) is AKS-managed Karpenter. Instead of pre-selecting every user node pool size up front, the platform defines provisioning policies and NAP creates the right Linux nodes when pods are pending.

For this platform, NAP should be treated as a platform-owned capacity layer, not an application-team node-pool feature. Application teams influence placement through normal Kubernetes contracts: resource requests, limits, labels, tolerations, affinity, topology constraints, and disruption budgets. The platform owns the AKS cluster profile, `NodePool` and `AKSNodeClass` resources, subnet permissions, SKU guardrails, Spot policy, disruption policy, and monitoring.

Checked against Microsoft Learn on 2026-06-10. The main Microsoft NAP docs referenced here were last updated between 2026-04-14 and 2026-05-21.

## Call TLDR

NAP is useful when teams have varied or changing compute needs and the platform does not want to maintain many fixed-size node pools by hand.

The app-team message is simple:

- Set realistic CPU and memory requests. NAP provisions from pending pod requirements.
- Use approved labels, tolerations, and affinity only when the platform has published a matching capacity class.
- Do not ask for bespoke node pools for normal workloads. Ask for a capacity class only when there is a real requirement, such as GPU, memory-optimized, Spot-tolerant, zone-specific, or compliance-constrained compute.
- Make workloads disruption-safe with multiple replicas and `PodDisruptionBudget` where availability matters.
- Expect Linux only. Windows node pools are not supported by AKS NAP.

The platform-team message is:

- Enable NAP declaratively on the AKS `ManagedCluster`.
- Keep a stable system node pool for cluster/system components.
- Manage NAP `NodePool` and `AKSNodeClass` resources through Flux.
- Use policy to stop application namespaces from creating or mutating cluster-level NAP resources.
- Validate networking, subnet capacity, identity permissions, quotas, disruption behavior, and observability before production rollout.

## What NAP Is

NAP automatically deploys, configures, and manages Karpenter on AKS. NAP watches pending pod pressure and uses workload resource requirements to decide what VM shape can run the workload efficiently.

The key resources are:

| Resource | Owner | Purpose |
|---|---|---|
| AKS `ManagedCluster.nodeProvisioningProfile` | Platform | Turns NAP on or off for the cluster. |
| `NodePool` | Platform | Defines provisioning policy, scheduling constraints, capacity type, disruption behavior, limits, and weight. |
| `AKSNodeClass` | Platform | Defines Azure-specific node settings such as subnet selection. |
| `NodeClaim` | NAP/Karpenter | Represents provisioned nodes. Operators can inspect it, but should not hand-author it. |
| Workload pods | App team | Resource requests, affinity, tolerations, and topology constraints drive scheduling demand. |

## How We Use It In This Platform

The target platform path is GitOps first:

1. KRO renders an ASO `ManagedCluster`.
2. The `ManagedCluster` enables NAP through `spec.nodeProvisioningProfile`.
3. Flux bootstraps platform configuration onto the worker cluster.
4. The first worker-cluster Flux path applies platform-owned NAP configuration.
5. Application workloads land after the NAP capacity classes exist.

The current public KRO definition at `infra/kro-stack/definitions/uk8scluster-public.yaml` keeps NAP disabled:

```yaml
nodeProvisioningProfile:
  mode: Manual
  defaultNodePools: None
```

That means NAP is not active from this template as written. The companion Flux definition at `infra/kro-stack/definitions/uk8sfluxgitops.yaml` already models a first-class `napconfiguration` path:

```yaml
napconfiguration:
  path: environments/${schema.spec.environment}/napconfiguration/base
```

The intended production pattern is to make NAP an explicit platform decision in the cluster template, then keep NAP policy in Git under the environment's platform configuration. Do not let individual app teams enable NAP or create cluster-level NAP resources directly.

## Recommended Platform Shape

| Area | Recommendation |
|---|---|
| Cluster mode | Enable NAP only through the KRO/ASO `ManagedCluster` contract after server-side schema validation against the installed ASO CRD. |
| Default pools | Decide at cluster creation whether to use AKS-created default NAP pools or platform-authored pools. Avoid toggling this on live clusters without a tested migration plan. |
| System capacity | Keep a fixed system node pool for critical add-ons, DNS, CNI, Flux, monitoring agents, and cluster bootstrap. |
| App capacity | Use NAP `NodePool` resources for user workload classes such as general, memory, compute, Spot, GPU, or zone-constrained pools. |
| Access control | App teams can deploy pods and namespaced workload resources. Platform owns `NodePool`, `AKSNodeClass`, cluster identity permissions, and subnet access. |
| GitOps ordering | Reconcile NAP configuration before app workloads that depend on NAP-only capacity. |
| Observability | Enable AKS control-plane logs/metrics for NAP/Karpenter events and alert on unschedulable pods, quota exhaustion, provisioning failures, and unexpected disruption. |
| Rollout | Pilot in non-production with one or two clear capacity classes before replacing fixed user node pools broadly. |

## Application Team Contract

Application teams do not request nodes directly. They make their workloads schedulable.

Minimum workload expectations:

- Every container has CPU and memory `requests`.
- Production services have realistic `limits` where appropriate.
- Availability-sensitive services run more than one replica.
- Availability-sensitive services define a `PodDisruptionBudget`.
- Workloads avoid hard node affinity unless the platform has published the label as part of an approved capacity class.
- Workloads tolerate Spot only when they are interruption-tolerant.

Example workload shape:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{APP_NAME}}
  namespace: {{APP_NAMESPACE}}
spec:
  replicas: 3
  selector:
    matchLabels:
      app: {{APP_NAME}}
  template:
    metadata:
      labels:
        app: {{APP_NAME}}
    spec:
      containers:
        - name: app
          image: {{REGISTRY_HOST}}/{{IMAGE_NAME}}:{{IMAGE_TAG}}
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "1"
              memory: "1Gi"
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{APP_NAME}}
  namespace: {{APP_NAMESPACE}}
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: {{APP_NAME}}
```

If a team needs a specific capacity profile, capture the reason as an onboarding/platform request:

| Need | What to ask for | What the platform decides |
|---|---|---|
| Cheap interruptible workers | Spot-tolerant capacity class | Spot `NodePool`, taints, disruption policy, limits, and max cost exposure |
| Memory-heavy service | Memory-optimized capacity class | SKU families, memory limits, topology, and quota |
| GPU workload | GPU capacity class | GPU SKU availability, drivers, taints, quotas, and cost guardrails |
| Zone-sensitive service | Zone placement contract | Allowed zones, topology spread, subnet capacity, and failover expectations |
| Dedicated compliance boundary | Isolated capacity class | Whether node isolation is justified or namespace/policy isolation is enough |

## Example Platform NAP Policy Shape

This is a request/config example, not a complete installable production manifest. Validate the installed NAP CRDs and AKS version before applying in a real cluster.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general-on-demand
spec:
  weight: 50
  limits:
    cpu: "500"
    memory: 2000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
  template:
    spec:
      nodeClassRef:
        name: general
      requirements:
        - key: kubernetes.io/os
          operator: In
          values: ["linux"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: karpenter.azure.com/sku-family
          operator: In
          values: ["D", "F"]
---
apiVersion: karpenter.azure.com/v1beta1
kind: AKSNodeClass
metadata:
  name: general
spec:
  vnetSubnetID: "/subscriptions/{{AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{RESOURCE_GROUP}}/providers/Microsoft.Network/virtualNetworks/{{VNET_NAME}}/subnets/{{SUBNET_NAME}}"
```

For Spot capacity, prefer a separate, clearly named `NodePool` with taints and lower priority than required on-demand capacity. Do not mix Spot into the default path for ordinary production services unless the team explicitly tolerates interruption.

## Enablement Checklist

Before enabling NAP for a cluster:

- Confirm the cluster is not using AKS cluster autoscaler. AKS documents NAP and cluster autoscaler as mutually exclusive.
- Confirm the cluster uses a supported networking model. Azure CNI, Azure CNI Overlay, and Azure CNI Overlay with Cilium are supported; Calico network policy and dynamic IP allocation are not.
- Confirm the cluster uses managed identity, not service principal authentication.
- Confirm the cluster uses Standard Load Balancer for custom VNet clusters.
- Confirm the cluster is IPv4-only for NAP. IPv6 clusters are not supported.
- Confirm Windows capacity is out of scope for NAP.
- Confirm subnet CIDRs do not overlap pod or service CIDRs.
- Confirm subnet IP capacity and Azure VM family quota for the expected scale.
- Confirm the cluster identity has least-privilege subnet read/join permissions, or document why broader VNet permissions are temporarily accepted.
- Confirm maintenance windows for cluster upgrades and node OS image updates.
- Confirm app-critical workloads have PDBs and enough replicas before enabling consolidation.
- Confirm NAP/Karpenter control-plane logs and events are visible in the operations workspace.

## Operational Checks

Useful read-only checks during a pilot:

```bash
kubectl get nodepools
kubectl get aksnodeclasses
kubectl get nodeclaims
kubectl get nodes -l karpenter.sh/nodepool
kubectl get events --field-selector source=karpenter-events
kubectl get pods -A --field-selector=status.phase=Pending
```

In Azure Monitor / Log Analytics, Microsoft documents querying NAP events from the `AKSControlPlane` table:

```kusto
AKSControlPlane
| where Category == "karpenter-events"
```

## Disruption And Upgrades

NAP can remove, replace, or consolidate nodes when doing so improves placement or cost. It uses Karpenter-style disruption behavior and should respect disruption budgets. This is good for efficiency, but it means workload availability must be explicit.

Platform defaults should be conservative at first:

- Use `WhenEmpty` consolidation for the first pilot if teams are not yet disruption-ready.
- Move to `WhenEmptyOrUnderutilized` only after PDBs, replicas, and observability are proven.
- Define node OS maintenance windows. Microsoft recommends a weekly cadence and a maintenance window of at least four hours for reliable NAP node image rollouts.
- Remember that NAP can force a new image if the existing node image is older than 90 days.

## Risks And Caveats

| Risk | Control |
|---|---|
| Bad resource requests create bad capacity decisions | Require requests through policy and review high-risk workloads. |
| Quota exhaustion leaves pods pending | Pre-check Azure regional SKU quota and alert on unschedulable pods. |
| Subnet exhaustion blocks provisioning | Capacity-plan subnet IPs before scale tests. |
| Over-broad subnet permissions | Prefer scoped subnet read/join custom role where feasible. |
| Spot interruptions affect production | Separate Spot capacity, taint it, and require explicit tolerations. |
| Consolidation disrupts fragile apps | Start conservative, require PDBs, and monitor eviction behavior. |
| Live cluster toggles surprise workloads | Treat NAP enablement/default-pool changes as a change-controlled platform rollout. |
| Teams bypass platform policy | Admission policy should block app namespaces from owning NAP cluster resources. |

## Recommended Pilot

1. Pick a non-production AKS cluster using the same networking and identity model as the target platform.
2. Enable NAP through the KRO/ASO `ManagedCluster` path, not by hand.
3. Publish one `general-on-demand` NAP `NodePool` through Flux.
4. Deploy one stateless test workload with realistic requests and a PDB.
5. Confirm pending pods trigger NAP node creation.
6. Confirm scale-down and consolidation behavior during a quiet period.
7. Confirm logs, events, `NodeClaim` state, Azure quota, subnet usage, and cost visibility.
8. Add one optional class, such as Spot or memory-optimized, only after the general path is proven.
9. Document the approved labels, tolerations, and request process for application teams.

## Share Message

NAP is how we let AKS create the right Linux user nodes from workload demand instead of us hand-building lots of fixed node pools. It is managed Karpenter in AKS.

For app teams, the contract is Kubernetes-native: set accurate CPU and memory requests, use PDBs for availability, and only use approved selectors/tolerations when the platform has published a matching capacity class. Teams should not own node pools directly.

For the platform, NAP is enabled declaratively through KRO/ASO on the AKS `ManagedCluster`, then the platform-owned `NodePool` and `AKSNodeClass` resources are delivered by Flux before workloads. We keep system capacity separate, govern SKU/subnet/Spot/disruption policy centrally, and monitor Karpenter events, pending pods, quota, subnet capacity, and node churn.

The first pilot should be a non-production cluster with one general on-demand capacity class, realistic workload requests, PDBs, and control-plane NAP logs enabled. After that works, add specialized classes such as Spot, memory, GPU, or zone-constrained capacity.

## References

- Microsoft Learn: Overview of node auto-provisioning in AKS: https://learn.microsoft.com/en-us/azure/aks/node-auto-provisioning
- Microsoft Learn: Enable or disable node auto-provisioning in AKS: https://learn.microsoft.com/en-us/azure/aks/use-node-auto-provisioning
- Microsoft Learn: Configure node pools for node auto-provisioning in AKS: https://learn.microsoft.com/en-us/azure/aks/node-auto-provisioning-node-pools
- Microsoft Learn: NAP networking configuration: https://learn.microsoft.com/en-us/azure/aks/node-auto-provisioning-networking
- Microsoft Learn: NAP disruption policies: https://learn.microsoft.com/en-us/azure/aks/node-auto-provisioning-disruption
- Microsoft Learn: NAP node image updates: https://learn.microsoft.com/en-us/azure/aks/node-auto-provisioning-upgrade-image
- Microsoft Learn: `Microsoft.ContainerService/managedClusters` ARM schema: https://learn.microsoft.com/en-us/azure/templates/microsoft.containerservice/2025-08-01/managedclusters

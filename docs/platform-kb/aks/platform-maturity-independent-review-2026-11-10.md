# Independent review of AKS platform maturity questions

Reviewed against official documentation on **10 November 2026**.

This review separates public technical capabilities from questions that require internal evidence. It does not establish how any organisation's platform is configured or operated. Owner roles below are suggested routing destinations, not confirmed organisational responsibilities.

## Public technical findings

### 1. Azure CNI Overlay pod CIDR expansion

Microsoft documents in-place pod CIDR expansion for **Linux-only Azure CNI Overlay clusters**. The new CIDR must be a larger, contiguous superset containing the entire existing range. Shrinking, replacing the range, adding a disjoint range, IPv6 expansion, and updating multiple pod CIDRs are unsupported. Windows and mixed Linux/Windows clusters are excluded.

The documented operation uses `az aks update --pod-cidr` and requires Azure CLI **2.48.0 or later**. Microsoft says to verify reconciliation through `NodeNetworkConfig`. A successful Azure update response alone is insufficient. [Microsoft: expand Overlay pod CIDR](https://learn.microsoft.com/en-us/azure/aks/azure-cni-overlay-pod-expand)

Address planning still constrains expansion:

- Overlay allocates a fixed `/24` pod block per node. Include future nodes and upgrade surge capacity.
- The enlarged range must avoid conflicting node, service, and connected-network ranges.
- Supported pod ranges use RFC 1918 private or RFC 6598 shared address space. Proposed supernets must also avoid the AKS-reserved ranges listed in the CNI prerequisites.

[Microsoft: Overlay address planning](https://learn.microsoft.com/en-us/azure/aks/concepts-network-azure-cni-overlay), [CNI prerequisites and reserved ranges](https://learn.microsoft.com/en-us/azure/aks/concepts-network-cni-overview)

**Service IP capacity has separate rules.** Current Microsoft guidance says that, starting with Kubernetes **1.33**, service IP capacity can be extended using Kubernetes `ServiceCIDR` resources. This adds allocatable addresses. It does not automatically renumber existing Services or resolve an existing overlap. The service range must remain nonoverlapping, and Microsoft specifies an address block smaller than `/12`. [Microsoft: IP planning](https://learn.microsoft.com/en-us/azure/aks/concepts-network-ip-address-planning), [Kubernetes: extend Service IP ranges](https://kubernetes.io/docs/tasks/network/extend-service-ip-ranges/)

Microsoft's overlap troubleshooting article also says the cluster's original service CIDR cannot be changed after creation. It documents redeployment when an overlapping subnet cannot be removed or adjusted. Read that alongside the newer service-capacity extension guidance. Adding `ServiceCIDR` capacity differs from replacing the original range or renumbering existing Services. [Microsoft: service CIDR overlap](https://learn.microsoft.com/en-us/troubleshoot/azure/azure-kubernetes/error-codes/servicecidroverlapexistingsubnetscidr-error)

**Networking migration differs from expansion.** Microsoft documents forward-only migration from kubenet or Azure CNI Node Subnet to Overlay. Prerequisites include Kubernetes **1.27 or later**, no dynamic pod IP allocation, and network-policy restrictions. That migration reimages node pools and is irreversible. It is a different operation from enlarging an already-Overlay cluster. [Microsoft: supported networking migration paths](https://learn.microsoft.com/en-us/azure/aks/update-azure-cni)

A parallel cluster is a conditional engineering recommendation when the required change is unsupported in place, conflicts cannot be resolved, or migration disruption is unacceptable. Pod IP exhaustion alone no longer proves that a rebuild is necessary. Actual eligibility and migration choice **require internal owner confirmation**.

### 2. Azure role-assignment quotas and namespace access

The current documented limits are:

| Scope or resource | Limit |
|---|---:|
| Azure role assignments per subscription | **5,000** |
| Azure role assignments per management group | **500** |
| Azure custom role definitions per tenant | **5,000** |

The subscription assignment limit includes subscription, resource-group, and resource scopes. It is fixed and cannot be increased. Management-group assignments have their separate limit. Eligible assignments and assignments scheduled for the future are excluded from the subscription count. Custom role definitions have a separate quota. [Microsoft: Azure RBAC limits](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/azure-subscription-service-limits#azure-rbac-limits), [assignment-limit troubleshooting](https://learn.microsoft.com/en-us/azure/role-based-access-control/troubleshoot-limits)

AKS Azure RBAC supports cluster- and namespace-scoped assignments. Namespace assignments consume the subscription's shared assignment budget. There is no separate 5,000-assignment allowance for each cluster or namespace. [Microsoft: AKS authorization and namespace scopes](https://learn.microsoft.com/en-us/azure/aks/entra-id-authorization)

Supported alternatives and design considerations include:

- Assign roles to Entra groups when principals share the same permissions and scope. Distinct namespace scopes still need separate grants.
- Consider broader scopes only where the required access permits them. Cluster or inherited resource-group grants reduce assignment counts while expanding access.
- Consider Entra authentication with native Kubernetes RBAC. Namespace `RoleBinding` objects do not consume Azure role assignments. Select the authorization mode deliberately and retain lifecycle automation, audit, and access reviews. Adding bindings must not be assumed to bypass the configured Azure authorizer. Azure permissions needed to retrieve cluster credentials remain a separate concern.
- Remove obsolete grants and assess subscription separation where governance and isolation requirements justify it.

[Microsoft: assignment-quota remedies](https://learn.microsoft.com/en-us/azure/role-based-access-control/troubleshoot-limits), [Entra authentication with Kubernetes RBAC](https://learn.microsoft.com/en-us/azure/aks/kubernetes-rbac-entra-id)

Whether lower environments should change access models **requires internal owner confirmation**. Assignment pressure alone does not justify broader tenant access.

### 3. Federated identity credential limits and scaling patterns

The documented maximum is **20 federated identity credentials per application object or user-assigned managed identity**. It is not a per-cluster, subscription, or tenant-wide allowance. Configuring these credentials on a system-assigned managed identity is unsupported. [Microsoft: federation restrictions](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-considerations), [user-assigned identity trust](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-create-trust-user-assigned-managed-identity)

Conventional AKS federation matches issuer, subject, and audience. Different cluster issuers or namespace and service-account subjects generally need distinct credentials. Reusing a service-account name across clusters does not eliminate different issuers. Multiple pods using one service account do not each need another credential. AKS supports many service accounts referencing one Entra identity, subject to the credential limit. [Microsoft: federation matching](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-considerations), [AKS workload identity mappings](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)

| Pattern | Applicability and caveat |
|---|---|
| Reuse a service account | Appropriate only where workloads intentionally share an identity and trust boundary. It does not solve arbitrary distinct-subject growth. |
| Partition across user-assigned managed identities | Preserves application or environment boundaries and gives each identity its own credential budget. This changes the design from one identity to several. |
| AKS identity bindings | Microsoft documents sharing one identity across clusters and service accounts using **one AKS-managed federated credential per identity**. Kubernetes RBAC authorizes permitted subjects. |
| Flexible federated credential expressions | Current preview documentation lists GitHub, GitLab, and Terraform Cloud token support. It does not establish wildcard support for AKS service-account tokens. |

Identity bindings require compatible Azure Identity libraries and explicit `WorkloadIdentityCredential` opt-in. Current dedicated documentation excludes API server VNet-integrated clusters. Setup specifies Azure CLI **2.73.0 or later**. Validate applicable SDK versions, feature availability, and support status before selecting this approach. [Microsoft: identity bindings and SDK requirements](https://learn.microsoft.com/en-us/azure/aks/identity-bindings-concepts), [setup and limitations](https://learn.microsoft.com/en-us/azure/aks/identity-bindings), [flexible credential preview](https://learn.microsoft.com/en-us/entra/workload-id/workload-identities-flexible-federated-identity-credentials)

**Twenty is the documented service maximum, distinct from automation guardrails.** A lower local warning threshold is not another Azure quota. Concurrent credential creation under one user-assigned identity can also return HTTP 409. That concurrency restriction does not establish that the credential maximum was reached. [Microsoft: federation restrictions and concurrency](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-considerations)

Current counts, identity boundaries, and lifecycle ownership **require internal owner confirmation**.

### 4. Admission webhook outage behavior

For requests matching the webhook's configured rules:

| Failure policy | Effect when the webhook call errors or times out |
|---|---|
| `Ignore`, fail-open | Skip the failed webhook and continue admission processing. Other checks can still reject the request. |
| `Fail`, fail-closed | Reject the matching request. This is the default. |

A successfully returned explicit webhook denial rejects the request under either policy. The default timeout is ten seconds, configurable from one to thirty seconds. [Kubernetes: failure policy and timeouts](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/#failure-policy)

Scaling impact depends on the installed rules. A webhook matching workload updates or `/scale` updates can block a replica-count change. One matching Pod creation can let that change succeed but prevent controllers from creating the required pods. This can affect manual scaling, HPA, rollouts, and replacement after disruption. This is an inference from admission matching and controller behavior, not a claim about an installation. [Kubernetes: admission matching](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/#matching-requests-rules), [horizontal autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)

An admission outage does not itself terminate already-running pods or directly stop their existing traffic. Kubelet container restarts within an existing pod differ from creating a replacement pod. Broadly matched status updates and recovery operations can still affect availability indirectly. Fail-open mutation can admit pods without expected injection or defaults. [Kubernetes: Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), [webhook good practices](https://kubernetes.io/docs/concepts/cluster-administration/admission-webhooks-good-practices/)

Actual incident impact, matching rules, failure policies, and availability controls **require internal owner confirmation**.

## Internal questions and evidence routing

Every row below has the status **requires internal owner confirmation**. Ask owners for reviewed summaries, aggregates, attestations, or synthetic examples. Raw identifiers and non-public configuration remain in approved internal systems. This review does not require tenant IDs, subscription IDs, cluster names, hostnames, internal repository paths, workload identifiers, credentials, or configuration exports.

### Capacity, networking, and access

| Question | Owner role to ask | Evidence or data needed |
|---|---|---|
| What stops new tenant placement, and what is the validated capacity envelope? | Platform capacity lead; SRE | Placement criteria; requests versus allocatable resources; usage distributions; quota, IP, and access headroom; failure and maintenance reserves; dated largest-cluster measurements and load-test results. |
| What constrains pod and service growth, and has parallel migration been assessed? | AKS networking lead; platform architect | Owner-verified prefix lengths, utilization, overlap findings, growth forecast, versions and mode, supported-change assessment, and migration options covering data, ingress, rollback, downtime, and cost. Actual ranges remain internal. |
| Why was namespace access selected, and should lower environments differ? | IAM and security architect; AKS authorization owner | Decision record; authorization mechanisms and scopes; assignment counts and growth; group use; access reviews; comparison of isolation, audit, and administration. |
| What are federation counts, identity boundaries, and lifecycle responsibilities? | Workload identity or IAM owner | Counts per anonymized identity; issuer and subject cardinality; application and environment boundaries; creation, update, and retirement workflow; orphan checks; accountable role. |
| Have webhook outages affected deployment or scaling? | Admission-policy owner; SRE | Sanitized incident timeline; effective rules, selectors, failure policies, and timeouts; availability design; rejection and latency metrics; deployment, scale, and recovery outcomes. |
| Which issue consumes most effort, and which creates greatest future risk? | Operations lead; platform risk owner | Recent case summaries; toil measurements; incident frequency and severity; risk assessment; mitigation ownership and forecast. |

### Agentic operations and roadmap

| Question | Owner role to ask | Evidence or data needed |
|---|---|---|
| Which initiatives are committed or underway? | Platform product or roadmap owner | Accountable owner, users, scope, status, delivery date, dependencies, funding or capacity, and reusable shared services. Distinguish commitments from proposals. |
| Which three recurring tasks create most burden or risk? | Operations or SRE lead; task owners | Sanitized cases covering trigger, evidence, consulted systems, decisions, handoffs, outcome, hands-on time, and waiting time. |
| What have AI prototypes demonstrated? | Prototype lead; evaluation owner; operators | Evaluation method and dataset description; measured results; sanitized outputs; operator feedback; failure cases; adoption or non-progression rationale. |
| What should an assistant produce, when, and with what evidence? | Operational user or product owner; control owner | Output examples, triggers, required provenance and freshness, completeness rules, abstention and escalation conditions, and unacceptable-error examples. |
| Which sources are authoritative, and who resolves conflicts? | Domain data owners; platform architect | Source-of-truth matrix for ownership, desired and observed versions, dependencies, rollouts, incidents, capacity, and validation. Include precedence and dispute-resolution rules. |
| Which identifiers safely join records? | Data architect; inventory owners | Sanitized join contract using synthetic identifiers for cluster, namespace, workload, change or release, and incident entities. Include rename, recreation, retirement, duplicate, and reconciliation rules. |
| Which interfaces, identities, and data uses are approved? | Security and IAM; data governance; privacy | Approved API and export capabilities and permission profiles; tenant separation; classification, residency, retention, and approved AI-service rules. No credentials required. |
| How fresh, complete, and attributable are sources? | Source-system owners; data engineering | Update cadence and latency distributions; observation versus ingestion times; coverage; provenance; missing-data indicators; stale and incomplete examples. |
| Which observability integrations lose data or fail at scale? | Observability platform owner | Throughput and cardinality tests; drop, rejection, queue, and backpressure metrics; safe summaries of sampling and retention; reconciliation and alerting evidence. |
| What is the measured use-case baseline? | Operations analytics; service owners | Frequency, hands-on and waiting time, rework and error rate, staffing, and incident or audit impact. State the measurement window and label estimates. |
| What prerequisites already exist, and what is blocked? | Delivery and integration owners | Runbooks, access status, integration readiness, approvals, evaluation examples, support arrangements, blocker owner, and committed delivery dates. |
| Which steps require judgment rather than integration or rules? | Runbook owners; automation architect | Step-level task decomposition; existing scripts and rules; exception frequency; decision examples; comparison with deterministic automation. |
| What justifies adoption? | Business or service owner; security; evaluation lead | Baseline comparison; value and control criteria; evaluation responsibility; unacceptable failures; adoption and rollback gates; delivery and resource constraints. |

### Execution controls and resource efficiency

| Question | Owner role to ask | Evidence or data needed |
|---|---|---|
| Who reads, recommends, prepares, approves, and executes? | Runbook owner; change manager | Representative workflow; human and system responsibilities; permission boundaries and handoffs. |
| Which operations are prohibited or approval-dependent? | Security and control owners; production service owners | Action matrix by environment and target type, including tenant and shared resources, destructive operations, and security-sensitive changes. |
| How are approval boundaries enforced? | IAM and security engineering; change-platform owner | Permission design; approval bound to exact target, action, and parameters; expiry and revalidation; separation of duties; evidence that bypass attempts are denied. |
| What happens after stale context, target changes, partial execution, duplicates, or failures? | SRE; workflow owner; incident commander | Preconditions; target and version checks; idempotency; retry limits; partial-result handling; stop and takeover controls; recovery authorization and unavailable-approver procedure. |
| What audit evidence is retained and supported? | Audit and compliance; security logging; operations | Sanitized end-to-end example recording initiator, evidence, proposal, approval, parameters, result, and recovery. Include integrity, retention, redaction, and support ownership. |
| Which resource and cost signals are available? | FinOps; observability; Kubernetes platform owner | Sanitized samples from cloud cost tools, Azure, Kubernetes or OpenCost, monitoring, and autoscaling for cost, requests and usage, idle capacity, pending pods, scale events, and specialized pools. Include coverage and units. |
| Can costs be attributed by node pool, namespace, workload, and time? | FinOps; data engineering | Allocation method; ownership and tag coverage; time granularity; freshness and history; reconciliation; measured, allocated, and unallocated shared-cost treatment. |
| Which idle resources are intentional reserves? | Capacity and SRE; application owners | Reserve policy; recovery objectives; disruption and eviction tolerance; startup and scale-up latency; minimum capacity; workload constraints. |
| What previous optimizations helped or harmed? | FinOps; application performance owners | Before-and-after cost and service-level results normalized for demand; realized savings versus theoretical reduction; regressions, rollback, owner acceptance, and autoscaling conflicts. |
| Does post-build Istio correction limit proxy injection? | Service-mesh owner; platform build owner | Sanitized explanation and test results showing effective injection scope and coverage. If unconstrained, provide proxy counts, requests and usage, configuration size, push frequency, latency, failures, and largest-cluster trends. |

## Assumptions and version-sensitive caveats

- This review concerns AKS on Azure. The pod-expansion finding applies to Linux-only Azure CNI Overlay clusters.
- CLI prerequisites, Kubernetes capabilities, networking migration prerequisites, and SDK requirements are separate compatibility checks.
- Current documentation supports service-range extension from Kubernetes 1.33. Extension differs from replacing an overlapping original range or renumbering existing Services.
- Identity-binding availability and support must be checked for the intended cloud, cluster configuration, and client-library versions. Documentation of a feature does not prove compatibility with an existing platform.
- A parallel cluster, different authorization model, identity partition, or assistant workflow is a design option. None is an approved internal change.
- Public documentation cannot establish internal capacity, incident history, access models, roadmap commitments, approval boundaries, or savings outcomes.

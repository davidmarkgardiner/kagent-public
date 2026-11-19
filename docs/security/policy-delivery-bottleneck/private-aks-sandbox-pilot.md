# One protected AKS cluster for engineering proofs of concept

## The decision

Approve a 60-day pilot for **one private, non-production AKS cluster provisioned without the centrally enforced container and workload admission policies** in the agreed pilot scope. Agree the cluster scope with Azure Policy owners during provisioning, then let named engineers deploy and iterate through reviewed GitOps inside that scope. One approval establishes the operating boundary for the pilot.

Retain Azure resource controls for networking, identity, diagnostics and cost. Document any Kubernetes admission controls that are intrinsic to AKS or required by the platform. If the control plane team needs a specific compensating workload control, agree its intent, test coverage and ownership. Kyverno is an option for that agreed control, with routine changes delegated through GitOps.

## Why we’re asking

Inventory existing Kubernetes administrator roles and node access. Confirm effective roles and key custody as part of the design. Admission controls can still prevent workload misconfiguration and reduce risk from ordinary deployment identities. For the pilot, design on the assumption that a privileged identity or node might be compromised. Put the most important boundaries under owners outside the cluster.

The delivery issue is **time to first successful deployment**. A fast exception decision can still leave a PoC waiting for downstream approvals, policy reconciliation or resubmission after a reset. Measure both clocks. Capture initial submission, decision, first successful deploy, resets and abandoned requests. Keep the normal production change process for anything that graduates from the sandbox.

## How we would protect it

| Boundary | Proposed design |
| --- | --- |
| Human access | Use the approved corporate admin network or managed workstation path to the private API. Allow only the designated Entra access group through the platform’s existing eligibility process. Require MFA and managed devices where supported. Use scoped roles for daily work and time-limited, attributable admin elevation. |
| Other management paths | Restrict API reachability and private DNS to approved admin and automation networks. Give deployment automation its own scoped identity. Disable AKS local accounts and Run Command where compatible, or explicitly restrict and audit access. Review effective Azure RBAC for actions that can change access paths, policy scope or network settings. |
| Node access | Disable routine node SSH where supported. Use a named, time-bound break-glass process where node access is required. Use attributable access for the pilot. Keep patched node images and short-lived PoC workloads. |
| Network and dependencies | Prefer a dedicated subscription and spoke VNet. Deny production and east–west routes through the hub and allow only named dependencies. Block public workload ingress and node public IPs through Azure-side controls. Route node and pod egress through a centrally managed firewall with default deny, approved DNS, and an allowlist for required AKS services, registry, telemetry and test endpoints. Prefer private endpoints and scoped destination permissions. Verify effective routes and firewall behaviour from both pods and nodes. |
| Data and identity | Use synthetic or approved non-production data only. Give node, cluster, CI and workload identities separate, least-privilege permissions. Deny access to production subscriptions, secrets and data. Keep control of firewall rules, production access and log destinations outside the pilot team. |
| Detection and recovery | Send AKS API audit, Entra activity, Azure activity, firewall and supported node/runtime signals to centrally controlled logging. Test delivery, alert routing and gaps in telemetry. Security owns containment, evidence preservation and credential revocation. Rebuild from trusted node images and GitOps if integrity is in doubt. |

Bastion is optional when the existing admin network already offers a restricted, attributable path to the private API. Use a Bastion-backed jump VM if Network or Security needs a dedicated admin entry point. Prefer private endpoints and registry mirrors for common dependencies. If all required dependencies and telemetry can work privately, evaluate network-isolated AKS. For PoCs that need approved external services, use firewall-controlled egress. Kubernetes NetworkPolicy can limit routine pod-to-pod traffic. The node-level containment case relies on Azure routes, firewall rules and Azure identity permissions held outside the cluster. [Private AKS access options](https://learn.microsoft.com/en-us/azure/aks/private-cluster-connect) · [AKS network and identity baseline](https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks/baseline-aks) · [Network-isolated AKS](https://learn.microsoft.com/en-us/azure/aks/concepts-network-isolated) · [AKS Run Command](https://learn.microsoft.com/en-us/azure/aks/access-private-cluster)

## What to show the control plane team

These are proposed demonstrations. Use synthetic workloads, test identities, benign events and pre-agreed test endpoints.

| Demonstration | Evidence to show |
| --- | --- |
| **1. Prove the starting policy state.** | Review effective Azure Policy assignments and Kubernetes admission on the pilot cluster. Show that the agreed central workload rules are absent from the pilot and that the Azure resource baseline still applies. Verify existing production assignments through read-only review. |
| **2. Prove who can get in.** | An eligible test identity on the approved admin network can deploy with scoped rights. A test identity outside the group on that same network is denied by authorization. An eligible identity outside the approved network cannot reach the API. Verify the separate automation path and audit records for authenticated activity. |
| **3. Ship and remove a mock PoC.** | From an approved GitOps change, deploy a sample controller that uses a test endpoint, collect its result and remove it. Show timestamps from submission to first successful deploy. Aim for one business day from a deploy-ready change. |
| **4. Prove what a node can reach.** | Use a platform-owned node-level test fixture alongside a normal pod. Required dependencies work, including registry pulls, telemetry and a representative scale or upgrade check. Unapproved outbound destinations are blocked. Verify production route and access denial with safe test endpoints, effective route evidence and Azure permission review. Show the firewall and identity records. |
| **5. Show detection and recovery.** | Trigger a benign test signal, confirm a central alert and correlate it with a node, workload or identity. Rehearse quarantining a disposable pool, revoking a test credential and rebuilding from trusted sources. Record timestamps, receipts and gaps. |

A compromised node could still affect workloads and test data in the sandbox and use whatever access its identities legitimately have. Host telemetry may be incomplete after compromise. Review that residual risk and validate that network, identity and logging controls retain independent ownership. [AKS outbound requirements](https://learn.microsoft.com/en-us/azure/aks/outbound-rules-control-egress) · [AKS monitoring data](https://learn.microsoft.com/en-us/azure/aks/monitor-aks-reference) · [Defender for Containers private-cluster support](https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-containers-feature-access-patterns)

## What we need agreed in the meeting

- **One cluster and one named owner.** Prefer a dedicated engineering subscription. Use an existing cluster only if the same boundaries can be demonstrated and production remains outside the change.
- **A written workload policy scope.** Inventory inherited and direct assignments and agree the pilot exclusion or exemption before provisioning. Include policy owners, scope, expiry and the route back to standard enforcement. [Azure landing-zone sandbox guidance](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/considerations/sandbox-environments) · [Azure Policy exemption structure](https://learn.microsoft.com/en-us/azure/governance/policy/concepts/exemption-structure)
- **A launch decision and review dates.** Control Plane, Network and Security sign off the evidence before activation. At days 30 and 60, review deployment times, control failures, exceptions and cost. At expiry, explicitly renew, restore the baseline or decommission.

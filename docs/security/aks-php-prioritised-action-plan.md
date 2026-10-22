# Secure the AKS platform during the PHP vulnerability response

Prepared on 22 October 2026 for the AKS platform team.

**Status: proposed action plan. No cluster inspection, policy deployment, customer notification or remediation has been performed as part of preparing this document.** Assign named owners and record results before treating an action as complete.

## Understand how an attacker gets in

**An attacker does not need an AKS login, Kubernetes API access or prior access to the container. A reachable, vulnerable PHP web application can be the entry point.**

The attack can follow the same route as a normal visitor:

1. The attacker sends specially crafted HTTP requests to the application's public endpoint.
2. The ingress or gateway forwards permitted requests to the application.
3. Vulnerable PHP mishandles memory while processing requests. Under exploitable conditions, the attacker can make the PHP process execute their instructions. Some demonstrated attacks run before application code, including login checks. [S10]
4. The instructions run with the PHP process's permissions inside the container. The attacker can attempt to read accessible files and secrets, use application database credentials or Azure permissions, and contact reachable services.

**Control of the PHP process is not automatically control of AKS.** Excessive permissions, accessible platform credentials, weak network isolation or further vulnerabilities can let the attacker move beyond the application. Prioritise those paths during containment.

Blocking internet egress alone leaves the inbound attack path open. Stolen data can also leave in responses to allowed HTTP requests. A WAF or application login does not establish that vulnerable PHP is safe. [S3]

## Start the immediate response

Protect the shared AKS platform while application teams rebuild and redeploy affected PHP images. Run exposure containment, permission checks and application remediation in parallel. Do not wait for a new policy engine or a complete hardening programme before restricting a known vulnerable public endpoint.

Use CERT-EU advisory 2026-018 as the incident reference. It covers CVE-2026-109618 and CVE-2026-109619, which can allow unauthenticated remote code execution in PHP serving web requests, including PHP-FPM on Linux. The first fixed upstream releases are PHP 8.2.35, 8.3.36, 8.4.27 and 8.5.12. Check vendor security notices for backported package fixes. Only an update fully fixes these vulnerabilities. [S1]

Use the following proposed targets from the time the response starts. These are planning targets, not existing organisational SLAs. Escalate an overdue task to the response lead and record the reason, containment and next deadline.

| Priority | Target | Outcome |
| --- | --- | --- |
| P0 | Start now; establish initial containment within 4 hours | Identify public exposure, restrict unresolved high-risk services and check routes into platform administration. |
| P1 | Within 24 hours | Patch and replace affected serving workloads, block known vulnerable deployments and verify containment. |
| P2 | Within 7 days | Standardise network, permission, pod-security and admission controls. |
| P3 | Within 30 days | Prove sustained detection, recovery and tenant-isolation controls. |

### Assign the immediate work

Rows with the same priority can run in parallel unless a dependency is stated.

| ID | Priority | Accountable owner | Action | Evidence required to close |
| --- | --- | --- | --- | --- |
| I01 | P0 | Platform response lead | Open one response record. Assign named platform, security, networking and application contacts. Agree emergency change authority, update cadence and who can accept a time-limited exception. | Named owners, start time, decision log and next review time. |
| I02 | P0 | Platform engineering | Inventory running container digests, application owners, PHP package/runtime evidence and ingress paths across all clusters. Include customer workloads and platform-owned third-party tools. Check controllers, scheduled jobs, init containers and sidecars for future execution. | Every running workload has an owner and a classification. Every public route maps to a workload. Record unknowns explicitly. |
| I03 | P0 | Network/ingress lead | For known vulnerable public applications, patch immediately or restrict public access under the emergency change process. Review every route, including ingress, public LoadBalancer Services and reachable NodePorts. Escalate public workloads with unknown PHP status for rapid evidence or a containment decision. | An external reachability check proves each restricted endpoint is unavailable to untrusted clients. Keep the prior routing configuration and rollback owner. |
| I04 | P0 | Platform security | Inspect affected workloads for excessive Kubernetes permissions, powerful Azure identities, mounted platform credentials, node metadata access and privileged pod settings. Remove unnecessary rights through controlled changes. Treat reachable platform credentials or node identities as urgent findings. | Permission review, representative access tests and a recorded disposition for each finding. Do not collect or print live secrets or tokens as test evidence. |
| I05 | P0 | Security operations | Confirm runtime sensor and Kubernetes audit coverage. Review available telemetry for suspicious processes, network activity and API operations associated with affected workloads. If compromise is suspected, invoke incident response before routine replacement destroys evidence. | Coverage report, investigation record and an owner for every suspicious finding. Absence of alerts is not proof of no compromise. |
| I06 | P0, then P1 | Application coordination lead | Notify each affected application team with its workload and digest, advisory, required runtime fix, rebuild/redeploy request and deadline. Platform engineers provide rollout support and track acknowledgement. | Each team acknowledges ownership and supplies a remediation ETA. Overdue or unowned applications are escalated to the response lead. |
| I07 | P1; start during P0 if available | Admission-policy owner | Use the existing admission mechanism to reject known vulnerable image digests. Use trusted scan results or attestations where supported. Verify scanner recognition of both CVEs and vendor backports. Test a small scope before enforcement. | Known vulnerable images are rejected, verified patched images are admitted, and policy failure/exception behaviour is tested. Record coverage gaps. |
| I08 | P1; start during P0 where needed | Network security | Apply targeted containment to affected workloads. Restrict inbound sources and outbound destinations to documented requirements. Reconcile existing allow rules and test tenant, management, metadata and external destinations. | Required traffic succeeds. Prohibited traffic fails. Evidence identifies source workload, destination, protocol, time and active policy revision. |
| I09 | P1 | Application owner, verified by platform | Rebuild with fixed PHP or a vendor-confirmed backport, deploy the new digest and replace every affected serving replica. Update future job templates and prevent rollback to vulnerable digests. | Image/package provenance, rollout status and running replica digests prove the fix. Record the effective serving runtime where build evidence is insufficient. |
| I10 | P1 | Platform response lead | Review all evidence and outstanding exceptions. Restore restricted routes only after verification. If compromise was suspected, require incident-response clearance as well as the PHP fix. | Closure checklist below is satisfied, or the response remains open with named owners and next deadlines. |

### Classify exposure consistently

Maintain one inventory row per workload and container, with these fields:

```text
cluster | namespace | workload | container | running image digest | application owner
PHP version/package/build | vendor fix evidence | serving mode | public/internal routes
classification | containment | remediation ETA | replacement digest | verified at
exception owner/expiry | evidence links
```

Use these classifications:

- **Affected:** PHP evidence identifies an unfixed runtime. Prioritise public web-serving workloads, then internal web-serving workloads. Track non-web PHP uses separately for remediation.
- **Fixed:** A running digest maps to a fixed runtime or vendor-confirmed backport, with rollout evidence.
- **Not affected:** Evidence establishes that the workload is outside the advisory's affected scope. Keep the reason.
- **Unknown:** Inventory, package/build evidence or scan coverage is incomplete. Keep an owner and deadline. Do not classify unknown workloads as safe.

Image names, application login screens and a scanner returning no findings do not establish that a workload is unaffected. Check source-built PHP, embedded runtimes and runtime downloads explicitly.

### Apply containment without creating a false assurance

- **Admission:** Kyverno can verify trusted attestations and enforce image decisions. It is not the vulnerability scanner. Match the policy to the installed Kyverno version. Cover customer pods and relevant container types, and test controller-created pods. Existing running pods still need separate action. [S2]
- **Availability:** Before blocking a digest, assess what happens when replicas restart, scale or move during node maintenance. A blocked replacement can cause an outage. Prefer verified patched replacements; record any exception with an expiry and compensating controls.
- **NetworkPolicy:** Standard Kubernetes policies are additive. Adding a deny-all policy does not remove access granted by another policy. Reconcile existing rules or use an explicit deny mechanism supported by the deployed network engine. Confirm actual CNI enforcement. Policy YAML alone is not evidence. [S3]
- **Traffic:** An egress restriction does not stop exploitation through permitted ingress. Responses on allowed connections can still return data. Network policies also do not replace ingress, Service exposure controls or firewalls. Test node/metadata access and established-connection behaviour separately. [S3, S4]
- **Control ownership:** Prevent application identities and deployment pipelines from removing quarantine, changing protected labels or granting themselves an exception. Check GitOps reconciliation so it cannot silently restore an unsafe route or policy.
- **Temporary PHP settings:** Use the current upstream guidance with application owners if patching is delayed. Record these as partial mitigations. Do not close the incident because a WAF rule or PHP setting has been applied. [S1]
- **Azure metadata:** Test ordinary application-pod access to `169.254.169.254` and review node-identity privileges. Workload Identity does not by itself establish that metadata is inaccessible. The documented AKS IMDS restriction feature is preview and has add-on limitations and host-network exceptions. Do not enable it blindly as an emergency change. [S5]
- **Suspected compromise:** Isolate under the incident-response procedure, preserve evidence and assess exposed identities, secrets and persistent storage. Revoke access or rotate exposed credentials according to that assessment. A patched image alone does not resolve a prior compromise.

## Complete the longer-term hardening

Start these tasks after immediate containment is underway. Use the existing supported security stack where possible. Introducing Kyverno is an option, not a prerequisite for incident response.

| ID | Priority | Accountable owner | Action | Evidence required to close |
| --- | --- | --- | --- | --- |
| H01 | P2 | Container supply-chain owner | Require digest-based deployment decisions and trusted build/scan evidence. Rescan running digests when vulnerability intelligence changes. Define freshness, missing-result handling, vendor-backport assessment and expiring exceptions. Restrict runtime software installation where practical. | Tests cover vulnerable, fixed, unknown, stale and tampered evidence, plus a newly disclosed CVE affecting an already-running image. |
| H02 | P2 | Network security | Establish a platform-owned network baseline for each tenant. Allow required DNS, service and external destinations explicitly. Protect management services and govern public exposure. Prevent tenants from overriding the baseline. [S4] | Automated connectivity checks prove cross-tenant and management restrictions while documented application traffic works. |
| H03 | P2 | Platform security | Enforce a suitable Restricted Pod Security baseline for customer workloads. Prevent privileged containers, unsafe host mounts and host namespace sharing. Require non-root execution, restricted capabilities, seccomp and no privilege escalation. Add read-only filesystems where supported. [S6] | Representative prohibited pods are rejected and compliant applications run. Exceptions have named owners, scope and expiry. |
| H04 | P2 | Identity/security owner | Minimise service-account RBAC and Azure Workload Identity permissions. Remove unnecessary API-token mounts. Separate workloads with different trust levels into different namespaces and protect powerful service accounts and secrets. [S7] | Access tests show that customer identities cannot administer the platform or reach another tenant's secrets and identities. |
| H05 | P2 | Platform operations | Enforce CPU/memory limits, namespace quotas and pod limits. Keep customer workloads off system nodes with scheduling restrictions tenants cannot bypass. Maintain supported AKS, node and container-runtime patch levels. [S8] | Resource-exhaustion and scheduling checks show protected platform capacity. Patch ownership and compliance are recorded. |
| H06 | P2 | Security operations | Standardise Defender for Containers or equivalent runtime coverage. Centralise retained audit and ingress logs. Route alerts to an on-call owner and define isolation, evidence collection and credential-recovery procedures. [S9] | A safe detection exercise produces an alert and an acknowledged response. Document telemetry gaps and retention. |
| H07 | P3 | Platform architect/security | Review whether shared namespaces, node pools and clusters meet customer trust requirements. Use separate clusters where stronger separation is required. Do not treat a separate node pool as a separate cluster security boundary. [S8] | A recorded tenancy decision identifies permitted sharing, remaining risks and funded follow-up work. |
| H08 | P3 | Platform engineering | Exercise the response procedure. Test policy-engine outages, registry/scanner failures, tenant attempts to alter controls, blocked pod replacements and restoration after patching. | Repeatable test results and a reviewed runbook demonstrate enforcement, recovery and exception expiry. |

### Specify the admission decision before implementation

Use the following proposed behaviour for customer deployment scope. Record the selected policy API, webhook configuration, exceptions and service impact before enforcing it.

| Image evidence | Immediate response | Target steady-state behaviour |
| --- | --- | --- |
| Known vulnerable to either PHP CVE | Reject new deployment of the identified digest. Contain existing workloads separately. | Reject unless a named, time-limited security exception applies. |
| Verified fixed or vendor-backported digest | Admit subject to the other platform controls. | Admit with trusted, sufficiently current evidence. |
| Missing, stale or incomplete assessment | Escalate and assess exposure. Do not mark safe. Decide restriction through the response process. | Reject within the agreed enforcement scope unless a controlled exception applies. |
| Scanner, registry or admission service unavailable | Keep existing containment active and invoke the agreed failure procedure. Avoid an untested cluster-wide change. | Fail closed within the tested customer scope, with a narrowly scoped, audited recovery path. |

Require vulnerability evidence as well as image authenticity. A signature proves a trusted party signed the digest; it does not prove the digest is free of these flaws. Define the trusted scanner, assessment time and vulnerability-feed coverage. Do not assume an old signed assessment remains valid after a new disclosure. [S2]

## Close the immediate response with evidence

The response lead checks every item before closing the PHP incident:

- [ ] All clusters, running workloads and public routes are covered by the inventory. Unknowns have been resolved.
- [ ] Affected serving workloads use verified fixed digests, or remain restricted under explicit, unexpired exceptions with deadlines.
- [ ] Every affected replica has been replaced. Controller and scheduled-job templates cannot recreate the vulnerable runtime.
- [ ] Admission rejects the identified vulnerable digests across the intended customer scope. Rollback and replacement behaviour are understood.
- [ ] Network tests demonstrate the intended restrictions, including access to other tenants, platform management and node metadata.
- [ ] High-risk Kubernetes permissions, Azure identities, privileged settings and platform credential exposure have been resolved or explicitly accepted.
- [ ] Application owners confirm smoke checks and platform owners verify rollout evidence before restoring access.
- [ ] Security operations has reviewed findings. Suspected compromise has a separate incident-response disposition.
- [ ] Every exception has a named risk owner, affected digest/workload, compensating controls, expiry and next review.
- [ ] Longer-term tasks have named owners and due dates. Publishing this plan does not complete those tasks.

## Consult the source guidance

Source guidance was reviewed on 22 October 2026. Recheck advisories, vendor package notices and feature support before execution. Implementation must match the actual AKS networking, policy engine and security tooling.

- **S1. CERT-EU security advisory 2026-018.** PHP scope, fixed versions and incident-specific recommendations. <https://cert.europa.eu/publications/security-advisories/2026-018/>
- **S2. Kyverno ImageValidatingPolicy.** Image authenticity and attestation enforcement. Check installed-version support. <https://kyverno.io/docs/policy-types/image-validating-policy/>. Earlier verifyImages documentation: <https://kyverno.io/docs/policy-types/cluster-policy/verify-images/overview/>
- **S3. Kubernetes NetworkPolicies.** Additive allow rules, reply traffic and implementation limitations. <https://kubernetes.io/docs/concepts/services-networking/network-policies/>
- **S4. AKS network security guidance.** Workload communication and endpoint exposure. <https://learn.microsoft.com/en-us/azure/aks/network-policy-best-practices>
- **S5. AKS IMDS restriction.** Preview status, dependencies and exceptions. <https://learn.microsoft.com/en-us/azure/aks/imds-restriction>
- **S6. Secure an AKS deployment.** Pod security and platform controls. <https://learn.microsoft.com/en-us/azure/aks/secure-aks>
- **S7. Kubernetes RBAC good practices.** Least privilege and indirect escalation through workload creation. <https://kubernetes.io/docs/concepts/security/rbac-good-practices/>
- **S8. AKS cluster isolation.** Tenancy and resource isolation. <https://learn.microsoft.com/en-us/azure/aks/operator-best-practices-cluster-isolation>
- **S9. Defender for Containers.** Runtime threat detection and coverage. <https://learn.microsoft.com/azure/defender-for-cloud/defender-for-containers-introduction>
- **S10. PHP technical advisories.** Attack mechanics, demonstrated request-processing paths and runtime-specific conditions. <https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w> and <https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp>

# Temporary policy exception for dev and engineering clusters

Updated 21 October 2026.

## Decision requested

Approve a temporary exception to the current ICV and SDLC policy change process for the dev and engineering AKS clusters owned by our team. Ask the policy owners to temporarily exempt those clusters from the specific Azure Policy rules blocking the kagent Agent Substrate evaluation, with equivalent baseline controls enforced locally through Kyverno and separately approved exceptions for the runtime privileges Substrate requires.

Give the engineering team delegated authority to maintain those scoped Kubernetes policies through reviewed GitOps changes while the central process is resolved. Record the affected clusters, policy definitions, accountable owners and expiry in the exception. Restore central enforcement as soon as the required changes have completed the process and have been validated.

## Current delivery impact

The delivery position reported on 21 October is that the policy change we need is not expected to be available before the end of the year, with delivery after Christmas indicated. This adds roughly two months or more to a dependency needed for near-term milestones and deliverables.

This is a recurring problem. Small namespace or policy amendments pass through multiple approval layers and processes. When approvals do not arrive in time, requests can expire or return to the beginning of the process. The engineering effort can be minutes while the elapsed delivery time becomes weeks or months.

Our engineering clusters exist to test proofs of concept quickly, establish whether a capability works and feed the results into delivery decisions. Applying the same change path used for production to routine engineering policy amendments prevents that feedback loop. The repeated delays consume engineering time, disrupt commitments and damage team morale.

The immediate consequence is that we cannot evaluate and showcase Agent Substrate, a central feature of our planned kagent release demonstration. Substrate provides the runtime behind kagent SandboxAgents, including agent isolation, suspension and restoration from snapshots. Its potential benefits include lower idle resource use and greater agent density; these need to be demonstrated on our intended environment. Without the policy change, that part of the showcase and its associated milestones remain blocked.

## Scope and accountability

The exception should cover only an explicitly approved list of team-owned dev and engineering clusters. Production clusters and other teams' clusters remain under their existing controls. Within the approved clusters:

- Identify the exact blocking Azure Policy assignments and definitions; use the smallest supported exemption scope and keep unrelated Azure controls applied.
- Map each affected baseline control to a reviewed Kyverno policy, including its scope, enforcement behaviour, reporting and owner.
- Delegate routine changes within this approved boundary to the engineering team through pull request review, automated policy tests and Flux reconciliation.
- Maintain an audit trail and monthly reviews, with an explicit expiry of `{{EXCEPTION_EXPIRY_DATE}}`. Any extension or expansion requires a recorded decision.

The objection raised is that changing enforcement in this way is incompatible with the current ICV and SDLC process. We therefore need management sponsorship and approval from the accountable control owners for a documented temporary exception, including authority for the policy owners to implement it. The exception must change the approval path as well as the enforcement configuration; moving to Kyverno while retaining the same approval queue would leave the delivery problem unresolved.

## Security conditions for the exception

Preserving the policy intent is an acceptance condition that we must prove. Equivalent policy text alone does not demonstrate equivalent protection. Before central enforcement is relaxed, test both allowed and denied workloads, exception boundaries, reporting, resistance to unauthorised policy changes and behaviour when the policy engine is unavailable.

Substrate also needs a bounded runtime exception. The pinned AKS evaluation uses a gVisor worker with elevated privileges for checkpoint and restore. That is a change to the permitted workload privileges and needs explicit risk acceptance, even when Kyverno replaces the surrounding baseline controls. Restrict it to approved Substrate namespaces and worker identities on a dedicated, isolated node pool, with approved images, least-privilege credentials, controlled egress and retained audit evidence. Keep ordinary workloads subject to the baseline.

Microsoft documents a **Mitigated** Azure Policy exemption category for cases where another method meets the policy intent, and a **Waiver** category for temporarily accepted non-compliance. Select the category per affected control: an equivalent Kyverno baseline may support mitigation, while a privileged-runtime exception requires its own assessment. Record the scope and expiry using the supported Azure mechanisms:

https://learn.microsoft.com/en-us/azure/governance/policy/concepts/exemption-structure

## Implementation and return to central enforcement

1. Obtain the sponsored ICV and SDLC exception and control-owner approval. Record the approved cluster list, policy definitions, delegated authority, runtime exceptions, owners and expiry.
2. Deploy and test the replacement Kyverno controls through GitOps. Capture the allow and deny results and review the remaining runtime risks before changing Azure enforcement.
3. Have the authorised policy owners apply the approved Azure exemptions. Prove Substrate execution, suspension and restoration on the engineering environment, alongside the policy denial tests. Policy relief clears one dependency; kernel support, mirrored assets, identity, networking and storage must also pass.
4. Continue the central change requests in parallel. Review the temporary arrangement monthly and retain the ability to stop the evaluation and restore enforcement if controls fail.
5. Once the central changes are available, test that they permit the approved Substrate workload and preserve the required denials. Re-enable central enforcement, remove temporary exemptions and retire overlapping local rules in a controlled order. At expiry, close the exception or obtain an explicit extension before it lapses.

The management decision is whether to sponsor this bounded arrangement now, so the team can evaluate Substrate and deliver the kagent showcase while completing the central process over the coming months. If the exception is declined, the dependent milestones and showcase scope need to be replanned against the policy team's delivery date.

## Supporting implementation material

- [Agent Substrate AKS evaluation and acceptance criteria](../../work-agent-bundles/agent-substrate/GITLAB-ISSUE-AIRGAPPED-AKS-EVALUATION.md)
- [Agent Substrate air-gapped AKS runbook](../../work-agent-bundles/agent-substrate/AIRGAPPED-AKS-README.md)
- [Existing Azure Policy exception guidance](azure-policy-exceptions.md)

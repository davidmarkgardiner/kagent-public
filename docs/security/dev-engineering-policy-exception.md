# Policy control that enables engineering delivery

Updated 21 October 2026.

## Decision requested

Approve a temporary operating model that lets the engineering team deliver on the dev and engineering AKS clusters it owns. Sponsor an exception to the current ICV and SDLC policy change process, and authorise the policy owners to lift the central Azure Policy workload enforcement covered by that exception. Maintain the agreed Kubernetes baseline locally through Kyverno, with delegated authority to update it through reviewed GitOps changes.

The scope must be an explicitly approved list of team-owned dev and engineering clusters. Give the arrangement an accountable owner, an expiry and a route back to central enforcement once the central process can support engineering delivery. If this approach cannot be approved, agree an alternative with a named owner and a turnaround that meets our delivery needs.

## The recurring delivery problem

The delivery position reported on 21 October is that a policy change needed soon is not expected to be available before the end of the year, with delivery after Christmas indicated. That adds roughly two months or more to a dependency affecting near-term milestones and deliverables.

The particular feature is incidental. The same constraint can block any proof of concept, namespace change, platform capability or engineering deliverable that needs a policy amendment. Small technical changes repeatedly enter multiple approval layers and processes. When approvals do not arrive in time, requests can expire or return to the beginning. A change that takes minutes to implement can take weeks or months to obtain.

Our engineering clusters exist to support rapid experimentation, validation and delivery. We need to establish quickly whether an approach works, adapt it and move forward. The current constraints prevent that feedback loop and make delivery dates dependent on an approval queue we cannot control.

These are dependencies within our own team or pod. We need a working internal arrangement that enables the team to deliver its commitments without repeatedly blocking itself. The current pattern disrupts milestones, consumes engineering time and damages morale. Resolving one request will leave the next deliverable exposed to the same problem.

## A workable operating model

Delegate Kubernetes workload-policy management for the approved engineering clusters to a named engineering owner. Agree the baseline and the boundaries once, then allow routine changes within those boundaries through pull request review, automated policy tests and Flux reconciliation. Reserve escalation for changes outside the agreed boundary or changes that require explicit risk acceptance.

Keep production clusters, other teams' clusters and unrelated Azure resource controls under their existing arrangements. For the approved engineering scope:

- Record which central workload-policy assignments and definitions are being replaced and map their control intent to the locally enforced Kyverno baseline.
- Give the engineering owner authority to maintain those policies within the approved scope, with a clear review and deployment path.
- Preserve version history, approval evidence, enforcement results, monitoring and rollback capability.
- Handle exceptional workload requirements through a bounded, recorded risk decision with an owner and review date.
- Set an explicit expiry of `{{EXCEPTION_EXPIRY_DATE}}` and review the arrangement monthly while the central process is resolved.

Moving enforcement to Kyverno must come with delegated decision authority. Retaining the same approval queue would retain the delivery bottleneck.

## Governance and security

The objection raised is that this arrangement is incompatible with the current ICV and SDLC process. Management sponsorship and approval from the accountable control owners are therefore needed for a documented temporary exception, including authority for the policy owners to implement it.

Preserving the baseline control intent is an acceptance condition. Before central enforcement is relaxed, test allowed and denied workloads, exception boundaries, reporting, protection against unauthorised policy changes and behaviour when the policy engine is unavailable. Any intentional relaxation of a control needs its own risk decision; changing policy engines does not establish security equivalence by itself.

Azure Policy supports a **Mitigated** exemption category where another method meets the policy intent, and a **Waiver** category where non-compliance is temporarily accepted. Select the appropriate category for each affected control and use the supported scope and expiry mechanisms:

https://learn.microsoft.com/en-us/azure/governance/policy/concepts/exemption-structure

## Implementation and return to central enforcement

1. Agree the exception, approved cluster scope, affected policies, delegated authority, owners and expiry.
2. Deploy and test the replacement baseline through GitOps before the authorised policy owners lift the corresponding central enforcement.
3. Continue engineering delivery within the approved boundaries, retain evidence and review the arrangement monthly. Continue the central process improvements and change requests in parallel.
4. Restore central enforcement once the required policies are available and the central operating model has an agreed, workable turnaround for routine engineering changes. Validate the transition, remove temporary exemptions and retire overlapping local rules in a controlled order.
5. At expiry, close the exception or obtain an explicit extension before it lapses. Restore enforcement earlier if the replacement controls fail.

## Outcome required

We need an operating model that lets us deliver our commitments reliably. A workable alternative must provide a named decision owner, delegated authority for routine engineering changes, an agreed turnaround aligned to delivery needs and escalation when approvals stall. Missed approvals must trigger escalation rather than repeatedly resetting the request.

The decision is to sponsor the temporary engineering-cluster exception or provide an alternative that meets those requirements. If neither can be delivered, the affected milestones and deliverables need to be formally replanned and ownership of that delivery impact made explicit.

## Supporting guidance

- [Alternative option with a dedicated engineering management group](engineering-management-group-option.md)
- [Teams message presenting both options](engineering-policy-blocker-teams-message.md)
- [Existing Azure Policy exception guidance](azure-policy-exceptions.md)
- [Kyverno policies in the platform](../../infra/byo-kagent/kyverno-policies/)

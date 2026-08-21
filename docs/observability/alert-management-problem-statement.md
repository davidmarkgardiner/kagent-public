# Alert-management problem statement

## Purpose

This note records the current problems in the final alert-management system. It
is a statement of the observed failure modes, not a claim that their root causes
have already been proven or that a replacement design is ready to deploy.

## The problem

The system is not reliably converting meaningful operational signals into
actionable, evidence-rich work.

1. **Important signals are excluded.** Current admission, filtering, or routing
   rules do not allow all of the signals that matter to reach the system.
2. **Too much admitted signal has little value.** Some alerts that do arrive are
   non-actionable, low-context, duplicated, resolved, or otherwise not useful
   for an SRE decision.
3. **The arriving alerts lack essential context.** Alert payloads do not
   consistently carry the resource identity, affected scope, reason, related
   evidence, runbook/dashboard links, and other data needed to triage safely.
4. **Delivery is unreliable.** It is hit-or-miss whether an eligible alert
   arrives at the final alert-management system at all.

## Consequence

Together these failures create both false negatives and false positives:

- an important incident can be missed entirely;
- the queue can be filled with alerts that do not justify investigation;
- responders must perform expensive rediscovery because the alert is thin; and
- the team cannot trust an absence of alerts as evidence that the path is
  healthy.

## What must be measured before declaring improvement

For a representative, versioned set of expected signal types, retain evidence
for each boundary from source through final consumer:

| Question | Minimum evidence |
| --- | --- |
| Did the important signal enter the pipeline? | Source-side count and a traceable signal identifier. |
| Was it intentionally filtered, quarantined, or deduplicated? | Reason-labelled filter/dedupe metric and the policy version. |
| Did the final alert contain sufficient context? | Captured redacted payload showing identity, reason, scope, evidence links, and routing fields. |
| Did it arrive at the final consumer? | Consumer/workflow/ticket record correlated to the source identifier. |
| Was the result valuable? | Human disposition: actionable, duplicate, expected noise, incomplete, or missed. |

The immediate objective is not simply to increase alert volume. It is to make
the admission policy explicit, preserve the context needed for triage, and prove
reliable end-to-end delivery of the signals that the team has decided matter.

## Related work

- [`ALERT-MANAGEMENT-TEAMS-MESSAGE.md`](ALERT-MANAGEMENT-TEAMS-MESSAGE.md)
  provides the copy-ready decision and Teams communication.
- [`GITLAB-ISSUE-VERIFY-ALERT-MANAGEMENT.md`](GITLAB-ISSUE-VERIFY-ALERT-MANAGEMENT.md)
  is the copy-ready upstream-engineering issue.
- [`../../work-agent-bundles/vector-kafka-routing-normalization/README.md`](../../work-agent-bundles/vector-kafka-routing-normalization/README.md)
  describes the normalization, filtering, dedupe, and Argo-routing pattern.
- [`../../work-agent-bundles/vector-kafka-routing-normalization/RICH-ALERT-CONTEXT-README.md`](../../work-agent-bundles/vector-kafka-routing-normalization/RICH-ALERT-CONTEXT-README.md)
  defines the context that must survive into triage.
- [`../../work-agent-bundles/homelab-verified-triage-replication/README.md`](../../work-agent-bundles/homelab-verified-triage-replication/README.md)
  contains bounded delivery and smoke-test evidence for the Alloy → Vector →
  Kafka → Argo path.

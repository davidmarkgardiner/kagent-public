# GitLab issue — reverse engineer and fix alert-management failures

## Title

`Investigate and remediate final alert-management signal quality, context, and delivery gaps`

## Labels

Apply equivalent local labels if they exist: `type::investigation`,
`area::observability`, `priority::high`.

## Problem

The final alert-management system is not reliably converting meaningful
operational signals into actionable, evidence-rich work. Four observed failure
modes need to be reverse engineered and corrected:

1. Important signals are excluded by current admission, filtering, or routing.
2. Some admitted alerts are non-actionable, duplicated, resolved, or otherwise
   low value.
3. Alerts that do arrive frequently lack the identity, scope, reason, evidence,
   and links required for safe triage.
4. Delivery is unreliable: it is not currently proven that every eligible alert
   reaches the final consumer.

This creates both false negatives (missed incidents) and false positives
(unhelpful queue volume), while forcing responders to rediscover context that
the pipeline should have preserved.

## Objective

Produce an evidence-backed remediation that makes alert admission explicit,
preserves the minimum triage context, and proves reliable delivery from source
to final consumer for the agreed signal set.

## Scope of investigation

1. **Map the deployed path.** Identify every source, filter, normalizer,
   webhook/proxy, queue/topic, EventSource, Sensor, workflow, and final
   consumer. Record ownership and the deployed configuration/version at each
   boundary.
2. **Measure coverage.** Define a versioned test corpus of important signal
   types, including expected no-op/noise cases. For each signal, show whether it
   was admitted, intentionally dropped/quarantined/deduplicated, or lost.
3. **Audit signal value.** Identify sources of non-actionable volume and make
   each exclusion/deduplication rule explicit, versioned, and observable. Do not
   silently suppress records without a reason-labelled metric or audit record.
4. **Validate the payload contract.** Verify that the final consumer receives,
   where applicable: cluster, namespace, workload/pod identity, severity,
   reason, event/log context, source timestamp, routing decision, correlation
   identifier, relevant runbook/dashboard links, and safe suggested evidence
   queries or next steps.
5. **Prove delivery end to end.** Use correlation identifiers to trace each
   positive test signal from source through final workflow/ticket/queue record.
   Include retry, transient dependency failure, duplicate, resolved, malformed,
   and intentionally excluded cases.
6. **Implement and verify corrections.** Make the smallest safe configuration
   or code changes, add regression fixtures and assertions, and publish before /
   after evidence. Do not replace working components wholesale unless evidence
   shows that a bounded repair cannot meet the acceptance criteria.

## Acceptance criteria

- [ ] A current, versioned diagram and configuration inventory identifies every
  alert-path boundary and owner.
- [ ] The agreed signal corpus has an expected outcome for every case.
- [ ] Every intentional filter, quarantine, and dedupe decision is observable
  and has a documented reason.
- [ ] Important signals in the corpus arrive at the final consumer or have a
  correlated, explainable failure record.
- [ ] Final alert payloads meet the agreed minimum-context contract; gaps are
  fixed or explicitly tracked as follow-up work.
- [ ] Non-actionable/repeat/resolved traffic does not create uncontrolled final
  queue volume.
- [ ] A repeatable smoke/regression test proves source-to-final delivery and is
  safe to run in the target environment.
- [ ] The change includes rollback guidance and does not expose credentials,
  private endpoints, or customer/internal data in source control.

## Evidence to attach

- Redacted samples for a successful important signal, an intentional exclusion,
  a duplicate, and a delivery failure/retry.
- Source, normalizer, queue, EventSource/Sensor, workflow, and final-consumer
  metrics/logs tied together by correlation identifier.
- The effective routing/filter/dedupe configuration and its revision.
- Before/after counts for coverage, unwanted queue volume, delivery success,
  and missing-context fields.
- Links to the resulting merge request(s), test output, and any follow-up
  issues.

## Non-goals

- Treating a higher alert count as success.
- Moving all filtering into a downstream agent or ticket writer.
- Declaring delivery healthy from a single successful alert.
- Adding write-capable remediation actions to the alert path.

## Relevant public reference material

- `docs/observability/alert-management-problem-statement.md`
- `work-agent-bundles/vector-kafka-routing-normalization/README.md`
- `work-agent-bundles/vector-kafka-routing-normalization/RICH-ALERT-CONTEXT-README.md`
- `work-agent-bundles/homelab-verified-triage-replication/README.md`

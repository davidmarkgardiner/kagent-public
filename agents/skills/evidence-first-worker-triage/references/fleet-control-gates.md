# Fleet Control Gates

Read this with the bundle's `DESIRED-STATE.md`. These are hard requirements,
not features to defer after a second worker joins.

| Control | Minimum implementation decision | Required proof |
|---|---|---|
| Fingerprint | `cluster:namespace:workload-kind/name:normalised-signature`; separate node class | Pod churn collapses; two signatures stay distinct. |
| Redaction | Versioned secrets/PII policy, per-line and total caps, sampled scanner | Scanner result attached to pilot evidence. |
| Schema | Explicit accepted majors, topic-to-cluster cross-check and quarantine | Unknown/oversize/malformed record reaches DLQ, never agent. |
| Worker resilience | HA Vector, PDB/spread, persistent buffer, loss metric and explicit producer delivery policy | Broker outage fills/drains buffer with accounted loss. |
| Idempotency | Atomic TTL store, not proof ConfigMap; failed/released claim state | Agent/ticket failure does not lock incident for 24h. |
| Ticket writer | Fingerprint label/key, find/update open issue, post-create retry | One ticket after a forced post-create failure; long-lived incident updates it. |
| Delivery | Kafka→EventBus→Sensor behaviour and bounded workflow concurrency | Burst test has no silent post-commit loss. |
| Replay | In-window, stale timestamp and group/replay policy | Old records quarantine; replay cannot re-triage an old incident. |
| Agent safety | Read-only tools, quota and unhealthy-endpoint circuit breaker | Agent failure pauses dispatch without mutation. |

Never embed worker credentials, GitLab token, private endpoint or evidence
payload in a rendered file committed to Git.

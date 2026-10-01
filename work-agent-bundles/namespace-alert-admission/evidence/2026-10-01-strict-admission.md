# Strict admission and recovery proof — 1 October 2026

Scope: isolated Proxmox Kubernetes test namespaces, actual Alloy/Vector,
PostgreSQL 16 and Kafka 3.9.1. Signals were synthetic. No workplace collector,
Kafka topic, agent, workflow or ticket writer was changed.

[Machine-readable receipt](2026-10-01-strict-admission.json).

| Check | Observed result |
| --- | --- |
| Real Kubernetes logs and Warning Events through Alloy/Vector | 195 envelopes, 30 resolved groups |
| Committed Kafka investigation records | Exactly 1/2/2 per namespace; five total |
| Actual gate Deployment restart | Still five records; no additional publication |
| Seven accelerated local dates | Exactly 1/2/2 each day; 35 committed records |
| Sustained critical input and replay | 672 unique signals; 2,016 input deliveries |
| Concurrent callers | Four intake/publish callers; eight report calls per date |
| Lost database budget/report/outbox state | Retained broker history blocked extra records |
| Prior uncommitted transaction after lost reservation | Fenced; one committed replacement record |
| Backward local date | Publication refused |
| Deleted/recreated topic | Pinned ID mismatch blocked sends; zero replacement-topic records |
| Cleanup | Runner confirmed removal of all four isolated namespaces |

Seven dates were accelerated in-process test clocks, not seven elapsed unattended
days. The ordinary HTTP intake has no clock-override endpoint. The transport
fixture used live owner references; the adversarial in-process fixture used
synthetic workload identities. PostgreSQL was disposable ephemeral storage;
rollback was simulated by deleting budget/report/outbox state while retaining
broker history and independent topic-ID pins. This is not a backup/PV disaster
recovery rehearsal. Kafka consumers used read_committed isolation.

The JSON receipt fingerprints the actual gate/schema/harness mounted in the
successful home-lab test. Since then only gate.py's 30-day retention pruning
changed; the retention test and all 22 behavior tests then passed in GitHub
CI on commit `37e3a88`, together with Vector/Kafka wire proofs. See
[EVIDENCE.md](../EVIDENCE.md) for the run and separate scan status. The rest of
the publish/group/report logic is identical to the lab-tested gate.

## Preconditions and limits

This cap covers committed records through this publication path. All replicas
must share cluster identity, policy, database, topic pins and transactional ID.
Kafka history retention and administrative trust requirements are documented
in the [bundle README](../README.md). Replays still require downstream durable
deduplication. All-source ticket caps require the separate final ticket writer.

Workplace TLS/SASL/ACLs, durable storage/migration/restore, metric alerts,
cluster-wide root-cause accuracy, daily scheduler operation over real days,
agent advice and actual ticket creation remain unverified. The gate ranks
symptoms; the read-only agent handoff is a contract, not a deployed integration.

# Home-lab Alloy → Vector → gate → Kafka transport proof

Date: 1 October 2026. Target: the home-lab Kubernetes cluster on Proxmox.
Scope: isolated synthetic fixtures, dedicated namespaces/database/broker/topic.
No production collector, Kafka credential, agent or ticket writer was changed.

Machine-readable result:
[2026-10-01-home-lab-transport.json](2026-10-01-home-lab-transport.json).

## Actual observed path

```text
15 Deployment pods (five in each of three fixture namespaces)
  -> 180 ERROR timeout log lines + 15 synthetic Kubernetes Warning Events
  -> Alloy Kubernetes log/event sources, Loki processing and OTLP HTTP export
  -> Vector 0.45 normalization/filter, HTTP sink before repeat suppression
  -> gate authenticated intake, PostgreSQL state, live owner-reference resolution
  -> selected outbox records -> isolated Kafka broker -> actual consumer
```

Images: Alloy v1.18.0, Vector 0.45.0-debian, PostgreSQL 16-alpine,
Apache Kafka native 3.9.1, Python 3.12-slim-bookworm, BusyBox 1.37.0 fixtures.
These are version tags for this experiment, not workplace digest locks.

Result: **PASS**.

| Measurement | Observed |
| --- | --- |
| Eligible received records retained | 195 |
| Resolved Deployment/reason groups | 30 |
| Namespace publish allowances | 1, 2, 2 |
| Kafka records actually consumed per namespace | 1, 2, 2 |
| Total consumed / distinct intent headers | 5 / 5 |
| Deferred groups retained in aggregate state | 25 |
| Kafka signal kinds consumed | Both log and event |
| Repeated report/dispatch | No additional send |
| New Argo Workflows since test start | 0 |

All 30 groups were resolved using the real Kubernetes API through Pod →
ReplicaSet → Deployment; no pod-name heuristic or mocked API was used in this
home-lab test. The Events were synthetic `Unhealthy`/`OOMKilled` Warning records,
not real faults injected into existing workloads. Namespace one selected a
log-timeout record; the other namespaces selected OOMKilled event records.

## Readiness issue found and fixed

The first run stopped before fixtures because the Deployment being available
did not prove broker readiness. Its namespaces were removed by the exit trap.

On the next run, inspection identified the single-broker controller address
as the cause: Docker's `kafka:9093` host alias had been carried into Kubernetes,
but the broker Service exposed only 9092. Set the co-located controller quorum
to `1@localhost:9093`, added a broker TCP readiness probe and metadata readiness
checks, and the live broker became ready. The corrected fixture generator
contains the loopback configuration. Brief coordinator-startup retries were
followed by successful produce/consume assertions.

## Cleanup

The runner deleted all four isolated namespaces after proof and waited for
deletion. A separate explicit read confirmed both attempted runs' namespaces
were absent. No Argo, Agent or ticket objects were created by the test.
Temporary local rendered manifests remain available for diagnosis; they contain
only synthetic test configuration, not workplace credentials.

## Reproduction

From `work-agent-bundles/namespace-alert-admission/`:

```bash
bash home_lab_smoke.sh proxmox-k8s
```

The script allows only explicit known lab contexts, generates unique isolated
namespaces, checks schemas on the server, collects real fixture signals, proves
Kafka consumption, and cleans up. It does not use the current kube context or
connect to the existing Confluent topics. Dependencies install inside an init
container in this disposable experiment.

## Limits of this proof

- The report slot and publisher were invoked manually after complete intake.
  The production scheduler's daily timing and unattended operation were not
  exercised over multiple days.
- This proves publish allowances, **not actual external ticket-creation caps**.
  No external ticket API, daily agent review or remediation execution was tested.
- Kafka plaintext and PostgreSQL trust authentication were confined to the
  isolated test namespace/broker. Workplace TLS/SASL, ACLs and network-policy
  enforcement remain separate validation.
- The test database was disposable with ephemeral storage. Durable restore,
  database-pod failure and reconciliation of spent ticket allowances were not
  proved here. Concurrent/restart/ambiguous-send behavior has separate local
  PostgreSQL tests in [EVIDENCE.md](../EVIDENCE.md).
- Metric alerts are not implemented in this v2 gate. Evidence coverage remains
  explicitly incomplete and cannot establish overall cluster health.

Official source references for the namespace-scoped Alloy collection used here:
https://grafana.com/docs/alloy/latest/reference/components/discovery/discovery.kubernetes/
https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.kubernetes_events/

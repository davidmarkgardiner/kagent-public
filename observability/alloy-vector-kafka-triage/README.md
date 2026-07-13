# Alloy → Vector → Kafka triage proof

This package is the red-cluster-ready implementation of the agent evidence
path. It does not require Grafana to create triage work.

```text
Alloy pod logs + Kubernetes events
  └─> OTLP -> Vector: redact, correlate, deduplicate, evidence package
                  -> Kafka incident-triage-requests
                  -> Argo Sensor -> read-only workflow

Later, optionally:

Alloy -> Loki / Grafana: retained search and dashboards only
```

## Deploy order when the red cluster is available

1. Create the Kafka topics and the `vector-telemetry-triage-kafka` secret with
   `KAFKA_BOOTSTRAP`, `KAFKA_SASL_USERNAME`, and `KAFKA_SASL_PASSWORD`.
2. Merge `01-alloy-config.yaml` into the existing Alloy release; it is not a
   standalone Alloy installation.
3. Apply `02-vector.yaml`, then confirm Vector's OTLP HTTP service is reachable
   from the Alloy namespace with the supplied NetworkPolicy applied. The core
   proof uses in-cluster HTTP; move this to mesh or TLS transport in the
   red-cluster overlay where that boundary is available.
4. Apply `03-argo-triage.yaml` after the Argo EventBus and Kafka credentials
   exist.
5. Run the controlled crash-loop scenario in
   `examples/crashloop-correlated.jsonl` through the live collector path.

## Local proof before cluster access

Run:

```bash
observability/alloy-vector-kafka-triage/tests/run-local-tests.sh
kubectl kustomize observability/alloy-vector-kafka-triage
```

The local test proves the bounded redacted incident payload contract. It does
not prove the red-cluster OTLP field layout, Kafka ACLs, service connectivity,
or Argo delivery; those are runtime gates.

## Optional Grafana/Loki mirror

Do not add the mirror during the first core proof. Once Proxmox is back, add
the `loki.write.retained_logs.receiver` shown in
`optional-loki-mirror.alloy` to both Alloy `forward_to` lists. That makes the
same logs and events visible in Loki/Grafana without letting Grafana alerting
control agent workflow creation.

## Safety

- The agent receives only a capped, redacted evidence string and read-only
  routing metadata.
- Vector dedupe is in-memory noise reduction; Argo/Kafka still provide the
  durable queue and workflow rate limit.
- `automation_allowed` is always false. This proof must not grant remediation
  permissions.

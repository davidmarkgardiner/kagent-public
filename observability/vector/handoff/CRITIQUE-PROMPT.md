# Critique Prompt: Vector Routing Design

You are reviewing a proposed observability routing design for an AKS management
cluster. Be critical. Do not assume the design is correct because a spike
passed.

## Context

The design introduces Vector between raw Confluent Kafka topics and Argo Events:

```text
Alertmanager / Grafana / Alloy
  -> raw Kafka topics
  -> Vector normalize / filter / route / dedupe
  -> normalized Kafka topics
  -> Argo EventSource
  -> Argo Sensor
  -> Argo Workflow
  -> selected agent or escalation path
```

The current first-pass implementation uses:

- raw topic: `alertmanager-events`
- normalized topic: `alertmanager-events-triage`
- normalized schema: `observability.triage.v1`
- route fields: `target_agent`, `route_key`, `routing_reason`,
  `automation_allowed`, `incident_candidate`, `dedupe_key`

## Review Inputs

Read these files:

- `observability/vector/README.md`
- `observability/vector/manifests/01-vector-alertmanager-normalizer.yaml`
- `observability/vector/manifests/02-argo-alertmanager-triage-topic.yaml`
- `observability/vector/manifests/03-argo-routing-verification.yaml`
- `observability/vector/examples/README.md`
- `observability/vector/tests/run-vector-example-tests.sh`
- `observability/vector/tests/vector-example-test.yaml`

## Critique Goals

Find problems in:

- schema design and field ownership
- routing rules and agent-selection logic
- dedupe strategy and failure modes
- topic design, replay, retention, and ACL boundaries
- Argo Sensor and Workflow contracts
- production safety for `automation_allowed`
- observability and value measurement
- rollout risk across dev and production AKS clusters
- security handling of Kafka credentials
- private-environment assumptions not represented in the public repo

## Questions To Answer

1. Is Kafka-first still the right default, or should any source go directly to
   Vector?
2. Should routing stay inside one normalized topic using `target_agent`, or
   should Vector publish to separate route topics?
3. Is `service` a strong enough owner signal, or should ownership come from
   labels, namespace inventory, CMDB, ServiceNow, Backstage, or another system?
4. Which alerts should be blocked from automated remediation even if Vector can
   classify them?
5. What should happen when Vector is down, restarted, or misconfigured?
6. How should duplicate suppression be measured and audited?
7. What evidence would convince stakeholders this reduces incidents, MTTA, and
   MTTR?

## Output Format

Return:

- Top risks, ordered by severity.
- Specific changes recommended before production.
- Tests that are missing.
- A go/no-go recommendation for a dev-cluster rollout.
- A separate go/no-go recommendation for a production-cluster rollout.

Use concrete file references and command suggestions where possible.

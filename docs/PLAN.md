# MIL-31 Plan

## Goal

Prepare public, sanitized K-Agent event-flow deliverables for peer review and
staging handoff. The deliverables cover both candidate paths and stop after a
consumer pod proves that it received and parsed the alert payload.

## Acceptance Surface

- Runbooks exist for both K-Agent event-flow paths.
- Comparison documentation covers latency, reliability, payload fidelity, and
  operations overhead.
- Manifests are structured for the public mirror and can be reviewed by path.
- Peer-review and staging handoff notes identify apply order, validation
  commands, rollback, and known gaps.
- Public content avoids secrets and private environment details.

## Implementation Steps

1. Establish a neutral repo structure for docs, manifests, and sample payloads.
2. Add common Argo Events prerequisites: namespace, EventBus, and Sensor RBAC.
3. Add the Redpanda path: Redpanda single-node broker, topic bootstrap job,
   Alertmanager-to-Kafka bridge, Kafka EventSource, and consumer Sensor.
4. Add the direct webhook path: webhook EventSource, explicit Service, sample
   Alertmanager receiver config, and consumer Sensor.
5. Write runbooks for deployment, testing, evidence capture, and rollback.
6. Write comparison and handoff documents with measured-results placeholders
   where staging evidence is still required.

## Validation Strategy

- Validate Kustomize rendering for both path overlays.
- Scan for obvious secret or private-environment terms.
- Push a branch and open a peer-review PR.
- Create a staging-ready handoff tag after commit.

## Out of Scope

- Invoking a K-Agent agent or triage workflow.
- Installing Argo Events itself.
- Publishing production Alertmanager configuration.
- Committing environment-specific secrets or endpoints.

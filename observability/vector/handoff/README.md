# Vector Routing Handoff Bundle

This bundle is for handing the Vector routing design to another agent or a work
environment for review and implementation.

## Start Here

Use these files in order:

1. [`CRITIQUE-PROMPT.md`](CRITIQUE-PROMPT.md) asks another agent to challenge
   the design before it is promoted.
2. [`WORK-IMPLEMENTATION-PROMPT.md`](WORK-IMPLEMENTATION-PROMPT.md) gives a
   work-environment agent the implementation task, checks, and acceptance
   criteria.
3. [`VERIFICATION-SUMMARY.md`](VERIFICATION-SUMMARY.md) records what has been
   tested in this public/sanitized repo and what still needs private/live
   verification.

## What Has Been Proved Here

The public spike verified:

- Confluent topics can be recreated and used for test traffic.
- Alertmanager-style records can flow through:

```text
alertmanager-events
  -> Vector
  -> alertmanager-events-triage
  -> Argo EventSource
  -> Argo Sensor
  -> Argo Workflow
```

- Vector can normalize Alertmanager, Grafana-native, and Alloy/Kubernetes event
  shapes into a common triage contract.
- Vector can calculate `target_agent`, `route_key`, `routing_reason`, and
  `dedupe_key`.
- Synthetic routing tests reached live Argo workflows for:
  - application service route
  - platform namespace/pod route
  - security route
  - unknown-owner fallback route

## Main Repo References

- Design: [`../README.md`](../README.md)
- Deployable manifests: [`../manifests/`](../manifests/)
- Example payloads: [`../examples/`](../examples/)
- Deterministic Vector tests: [`../tests/`](../tests/)

## Things To Improve Next

- Move the production Argo workflow from `body.alertmanager` to the full
  normalized envelope so it can consume `target_agent`, `route_key`, and
  `automation_allowed`.
- Add source-specific Vector inputs for `k8s-events` and any Grafana-native
  topic instead of sending all synthetic examples through `alertmanager-events`.
- Decide whether routing should stay message-level in one normalized topic or
  split into team-owned topics after ownership, retention, and ACL needs are
  clear.
- Add real dashboards for route volume, dedupe count, workflow count, and
  agent-selection outcomes.
- Keep ServiceNow/incident creation downstream of failed automation or
  deliberate escalation, not as the first evidence of every alert.

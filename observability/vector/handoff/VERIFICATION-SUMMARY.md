# Verification Summary

This summary separates what was verified in the public/sanitized repo from what
still needs verification in the private work environment.

## Verified In Public Spike

### Kafka And Vector Path

Verified:

```text
alertmanager-events
  -> vector-alertmanager-normalizer
  -> alertmanager-events-triage
  -> vector-alertmanager-triage-kafka EventSource
  -> vector-alertmanager-triage Sensor
  -> alertmanager-triage WorkflowTemplate
```

Evidence captured during the spike:

- raw Confluent REST produce returned HTTP `200`
- Vector rolled out as `1/1` ready on `timberio/vector:0.45.0-debian`
- normalized-topic EventSource consumed records from
  `alertmanager-events-triage`
- Argo workflows were created and completed successfully

### Deterministic Vector Tests

Command:

```bash
observability/vector/tests/run-vector-example-tests.sh
```

Passed cases:

- Alertmanager payload contract and routing
- Grafana-native payload contract and routing
- Alloy/Kubernetes event contract and platform routing
- resolved Alertmanager and Grafana alert filtering
- count-bounded duplicate suppression using `dedupe_key`

### Live Routing Delivery

Verified live with synthetic `routing_test: true` records:

| Case | Verified target |
|---|---|
| `namespace=payments`, `service=checkout-api` | `aks-sre-triage-agent` |
| `namespace=platform-tools`, pod event, `reason=FailedScheduling` | `platform-ops-agent` |
| `namespace=platform-security`, `severity=critical` | `security-hardening-agent` |
| missing service owner in `namespace=unlabelled-apps` | `sre-triage-agent` |

The route-verification workflows completed successfully and recorded:

```text
target_agent
route_key
routing_reason
event_type
namespace
service
pod
severity
dedupe_key
```

## Critique Follow-Up Applied

Feedback in `FEEDBACK.md` identified several design-vs-manifest gaps. The
following public artifacts have been corrected:

- `01-vector-alertmanager-normalizer.yaml` now includes the deployed
  `accepted_events` filter and `suppress_duplicates` dedupe transforms.
- `automation_allowed` is default-deny and no longer flips to true from
  untrusted alert labels such as `severity=critical` and `environment=prod`.
- `severity` is no longer part of the default `dedupe_key`, so severity flaps
  do not automatically bypass duplicate suppression.
- Vector has HTTP liveness/readiness probes on the API port.
- The deterministic test harness asserts resolved Alertmanager filtering,
  default-deny automation, and the updated dedupe key shape.

## Not Yet Verified

- real Grafana contact point producing a native Kafka payload into a dedicated
  Grafana topic
- real Alloy Kubernetes-event topic feeding Vector as a separate source
- production workflow consuming the full normalized envelope
- actual agent invocation based on `target_agent`
- explicit Argo-side allowlist for write-capable automation
- split Kafka principals for Vector read/write and Argo normalized-topic read
- ServiceNow deflection tagging or closure workflow
- dashboards for route counts, dedupe counts, MTTA, MTTR, and escalation rate
- production-grade topic ACLs, retention, replay, and ownership model
- Vector high availability and restart behavior under load

## Recommended Next Verification

1. Add separate Vector sources for the real Grafana and Alloy topics.
2. Make the production workflow accept the full normalized envelope.
3. Route one synthetic event to each real agent in a dev cluster.
4. Prove `automation_allowed=false` blocks write-capable remediation.
5. Prove duplicate suppression reduces workflow count without losing audit
   visibility in raw topics.
6. Add Grafana dashboards for route volume, dedupe count, workflow duration,
   workflow outcome, incident candidate count, and escalation count.

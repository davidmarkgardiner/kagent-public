# Vector Example Payloads and Tests

These examples show what Vector adds before Argo receives an event. They are
public-safe fixtures, not live cluster evidence.

## Example Files

| File | Purpose |
|---|---|
| [`alertmanager-raw.json`](alertmanager-raw.json) | Raw Alertmanager-style payload as it appears on `alertmanager-events`. |
| [`grafana-native-raw.json`](grafana-native-raw.json) | Grafana-native alert notification shape that is not an Alertmanager webhook. |
| [`alloy-k8s-event-raw.json`](alloy-k8s-event-raw.json) | Kubernetes event shape from an Alloy-style event stream. |
| [`normalized-platform-alert.json`](normalized-platform-alert.json) | Expected normalized envelope for a platform/pod alert. |
| [`normalized-security-alert.json`](normalized-security-alert.json) | Expected normalized envelope for a security/compliance alert. |
| [`routing-cases.json`](routing-cases.json) | Worked routing cases by namespace, pod, service, alert name, and severity. |

## What To Test

| Area | Example test | Expected result |
|---|---|---|
| Payload contracts | Feed each `*-raw.json` payload into Vector. | Vector emits `schema_version: observability.triage.v1` with stable top-level fields. |
| Filtering | Send a resolved alert, a noisy namespace, and a critical production alert. | Resolved/noisy events are dropped or marked low priority; critical production events continue. |
| Deduplication | Send the same alert payload three times inside the dedupe window. | One normalized event is produced; repeated events share the same `dedupe_key` and are suppressed. |
| Topic design | Produce raw events to `alertmanager-events` or `k8s-events`. | Raw topic keeps the original payload; normalized topic receives only automation-ready payloads. |
| Workflow complexity | Compare Argo parameters before and after Vector. | Argo reads `target_agent`, `route_key`, `namespace`, `pod`, `service`, and `dedupe_key` directly. |

## Routing Rules

Start with message-level routing inside one normalized topic:

| Rule | Example | Target |
|---|---|---|
| Critical production pod alert | `environment=prod`, `object_kind=Pod`, `severity=critical` | `aks-sre-triage-agent` |
| Security or compliance alert | `labels.domain=security` or `event_type=security-advisory` | `security-hardening-agent` |
| Platform namespace | `namespace` starts with `kube-`, `istio-`, `argo-`, or `monitoring` | `platform-ops-agent` |
| Application namespace | `namespace` owned by an app team | `application-triage-agent` |
| Unknown ownership | Missing `service` or owner labels | `sre-triage-agent` with `automation_allowed=false` |

Only split into separate Kafka topics once routing ownership needs separate
ACLs, retention, replay, scaling, or team-specific Sensor policies.

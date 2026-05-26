# Confluent Cloud Pipeline Review Notes

Date: 2026-05-22

## What Was Built

Created a new sanitized PoC directory:

`observability/confluent-cloud-pipeline/`

The build uses one Confluent Cloud cluster with two topics:

- `k8s-events`: Alloy Kubernetes event OTLP from `{{WORKLOAD_KUBE_CONTEXT}}`.
- `alertmanager-events`: Alertmanager webhook records from `{{MGMT_KUBE_CONTEXT}}`.

This is a deliberate change from the first sketch. It prevents the raw Alertmanager payload from accidentally triggering the Kubernetes-event workflow, whose parser only understands Kubernetes-event-shaped OTLP.

## Files Added

- `README.md`: operator flow and apply order.
- `EVIDENCE.md`: live evidence capture template.
- `00-cluster-bootstrap.sh`: guarded Confluent CLI bootstrap helper.
- `01-shared-secrets.yaml`: placeholder-only Secret templates.
- `verify.sh`: cluster/topic/workflow inspection helper.
- `workload-cluster/01-alloy-secret.md`: imperative secret creation instructions for `{{WORKLOAD_KUBE_CONTEXT}}`.
- `workload-cluster/02-alloy-config.yaml`: Alloy Kubernetes-events-to-Confluent config.
- `workload-cluster/03-alloy-deployment.patch.yaml`: `{{WORKLOAD_KUBE_CONTEXT}}` Alloy env/deployment overlay using `alloy-confluent`.
- `alertmanager-shim/00-payload-contract.md`: records the Alertmanager payload contract and why it is separate from k8s OTLP.
- `alertmanager-shim/01-bridge-configmap.yaml`: Python bridge source that receives Alertmanager webhook JSON and publishes to Confluent using SASL_SSL.
- `alertmanager-shim/02-bridge-deployment.yaml`: bridge Deployment and Service in `monitoring`.
- `alertmanager-shim/03-alertmanager-values.yaml`: kube-prometheus-stack Alertmanager receiver overlay.
- `alertmanager-shim/04-test-alertmanager-payload.json`: sanitized local payload for bridge testing.
- `management-cluster/01-eventsource-confluent.yaml`: Argo Events Kafka EventSource for both topics.
- `management-cluster/02-sensor-k8s-events.yaml`: routes `k8s-events` to existing `k8s-triage-critical`.
- `management-cluster/03-sensor-alertmanager.yaml`: routes `alertmanager-events` to existing `alertmanager-triage`.

Also updated root `.gitignore` to ignore local Confluent credential outputs:

- `confluent.io/.env`
- `confluent.io/.bootstrap.env`
- `confluent.io/.kafka-key`

## Key Decisions

1. Separate topics for separate payload contracts.

   The original "same topic" idea was too easy to misread as "same downstream contract." For this PoC the shared thing is Confluent Cloud Kafka, not a single workflow parser.

2. Python bridge instead of Alloy Alertmanager shim for the first build.

   The repo already has an Alertmanager-to-Kafka Python bridge pattern under `platform/argo-events/sources/alertmanager-redpanda/`. Reusing that shape is less speculative than assuming `loki.source.api` plus OTLP shaping will preserve the Alertmanager payload exactly the way the downstream workflow needs it.

3. Existing workflow paths are reused.

   The build does not duplicate the large workflow templates. It references:

   - `k8s-triage-critical` for Kubernetes events.
   - `alertmanager-triage` for Alertmanager payloads.

4. Bootstrap script is guarded.

   It checks for an active Confluent CLI session and asks for confirmation before creating Confluent resources because Basic clusters can incur cost.

## Review Focus

Check these before live apply:

- Is separate-topic routing acceptable for the PoC, or do you still need a same-topic proof after this safer baseline works?
- Should the Python bridge be promoted into a pinned image instead of installing `kafka-python` at startup? For lab use it is acceptable; for durable use it should be an image.
- The live Argo Events controller rejected `tls: {}`. The EventSource now references a `confluent-public-ca` Secret populated from the local system CA bundle.
- Does the live Argo Events Sensor filter syntax accept `body.alertmanager.status` and `body.source` as written?
- Should `alertmanager-triage` be sanitized or parameterized before any public-facing reuse? The existing workflow template contains repo-specific GitLab defaults.
- Before applying `management-cluster/01-eventsource-confluent.yaml`, render `{{CONFLUENT_BOOTSTRAP}}` from `confluent.io/.bootstrap.env`; Argo Events does not resolve that placeholder by itself.

## Live Validation Result

Live validation was completed on 2026-05-22.

Created/reused Confluent resources:

```text
environment: kagent-poc
cluster: kagent-poc
topics: k8s-events, alertmanager-events
service account: kagent-pipeline
```

Applied Kubernetes resources:

```text
{{WORKLOAD_KUBE_CONTEXT}}:
- alloy-confluent Secret
- alloy-config ConfigMap
- alloy-env ConfigMap
- alloy Deployment update
- alloy ServiceAccount/ClusterRole/ClusterRoleBinding for event watch

{{MGMT_KUBE_CONTEXT}}:
- confluent-credentials Secret
- confluent-public-ca Secret
- alertmanager-confluent Secret
- alertmanager-confluent-bridge ConfigMap, Deployment, Service
- confluent-kafka EventSource
- confluent-k8s-triage-critical Sensor
- confluent-alertmanager-triage Sensor
```

Validated:

```text
{{WORKLOAD_KUBE_CONTEXT}} Alloy -> Confluent k8s-events -> Argo Events -> k8s-triage-critical -> Succeeded workflow
Alertmanager bridge -> Confluent alertmanager-events -> Argo Events -> alertmanager-triage -> Succeeded workflow
Confluent CLI consumed records from both topics using the generated API key
```

Mattermost receipt was not independently checked.

## Expected Success Criteria

- `{{WORKLOAD_KUBE_CONTEXT}}` Alloy sends at least one Kubernetes Warning event to `k8s-events`.
- `{{MGMT_KUBE_CONTEXT}}` Alertmanager bridge sends at least one test alert to `alertmanager-events`.
- Argo Events consumes both topics.
- `k8s-events` creates a `triage-critical-*` workflow.
- `alertmanager-events` creates an `alert-triage-*` workflow.
- Evidence is redacted and committed only after secret-safety checks pass.

# Confluent Cloud Pipeline Evidence

Status: live validated.

Use this file to capture redacted evidence after the manifests are applied.

## Environment

```text
date: 2026-05-22
operator: local Confluent CLI session
confluent cli auth: ok
confluent environment count visible to CLI: 1
confluent kafka cluster count visible to CLI: 1
confluent topic count after bootstrap: 2
confluent environment id: redacted
confluent cluster id: redacted
bootstrap: redacted Confluent Cloud host on port 9092
k8s topic: k8s-events
alertmanager topic: alertmanager-events
argo events image: quay.io/argoproj/argo-events:v1.9.6
{{WORKLOAD_KUBE_CONTEXT}} alloy image: grafana/alloy:v1.12.2
```

## Local and Cluster Validation

Validated on 2026-05-22:

```text
confluent organization list: ok
confluent environment list: ok
confluent version: v4.63.0
confluent.io/.bootstrap.env: present and gitignored
kubectl contexts {{WORKLOAD_KUBE_CONTEXT}} and {{MGMT_KUBE_CONTEXT}}: present
{{WORKLOAD_KUBE_CONTEXT}} namespaces monitoring and argo-events: present
{{MGMT_KUBE_CONTEXT}} namespaces monitoring and argo-events: present
{{MGMT_KUBE_CONTEXT}} CRDs: EventSource, Sensor, Workflow, WorkflowTemplate present
{{MGMT_KUBE_CONTEXT}} WorkflowTemplates k8s-triage-critical and alertmanager-triage: present
{{WORKLOAD_KUBE_CONTEXT}} server dry-run for workload Alloy manifests: passed
{{MGMT_KUBE_CONTEXT}} server dry-run for bridge/EventSource/Sensor manifests: passed
Confluent bootstrap: completed
Kubernetes Secrets: alloy-confluent, confluent-credentials, alertmanager-confluent created/configured
Confluent public CA Secret: created in argo-events
{{WORKLOAD_KUBE_CONTEXT}} Alloy rollout: succeeded
Alertmanager bridge rollout: succeeded
Confluent EventSource: deployed and pod running
local YAML parse: passed
local JSON parse: passed
script bash syntax check: passed
secret/account scan over new artifacts: no live account details found
```

## Fixes Made During Live Validation

```text
00-cluster-bootstrap.sh:
- fixed git check-ignore guard for multiple paths
- fixed Confluent ACL flag from --operation to --operations
- fixed Confluent API key parsing for v4.63.0 JSON fields api_key/api_secret

workload-cluster/02-alloy-config.yaml:
- changed otelcol.exporter.kafka auth block to authentication block
- changed topic/encoding fields to logs { topic, encoding = otlp_json }

management-cluster/01-eventsource-confluent.yaml:
- replaced empty tls: {} with caCertSecret pointing at confluent-public-ca

workload-cluster/03-alloy-deployment.patch.yaml:
- added ServiceAccount, ClusterRole, and ClusterRoleBinding so Alloy can list/watch Kubernetes Events
```

## Proof 1 - Confluent Topics

Commands:

```bash
confluent kafka topic list --cluster "$CONFLUENT_CLUSTER_ID"
confluent kafka topic describe k8s-events --cluster "$CONFLUENT_CLUSTER_ID"
confluent kafka topic describe alertmanager-events --cluster "$CONFLUENT_CLUSTER_ID"
```

Evidence:

```text
Confluent CLI sees topics:
- k8s-events
- alertmanager-events
```

## Proof 2 - {{WORKLOAD_KUBE_CONTEXT}} Alloy to k8s-events

Commands:

```bash
kubectl --context {{WORKLOAD_KUBE_CONTEXT}} -n monitoring logs deploy/alloy --tail=100
kubectl --context {{WORKLOAD_KUBE_CONTEXT}} -n monitoring exec deploy/alloy -- wget -qO- localhost:12345/metrics
confluent kafka topic consume k8s-events --from-beginning --group "verify-$(date +%s)" --cluster "$CONFLUENT_CLUSTER_ID"
```

Pass condition: a Kubernetes Warning event from `{{WORKLOAD_KUBE_CONTEXT}}` appears in Confluent and triggers the k8s-event Sensor.

Evidence:

```text
{{WORKLOAD_KUBE_CONTEXT}} Alloy rollout: deployment "alloy" successfully rolled out
Alloy watched Kubernetes Events after RBAC was applied.
Argo Events consumed k8s-events from Confluent and published to the EventBus.
Confluent CLI consume returned records from k8s-events.
Example redacted consume markers:
- Partition 0 Offset 0
- Partition 2 Offset 0
Workflow results:
- triage-critical-* workflows created
- multiple triage-critical workflows reached Succeeded
```

## Proof 3 - Alertmanager to alertmanager-events

Commands:

```bash
observability/prometheus-alertmanager/test-alerts.sh --context {{MGMT_KUBE_CONTEXT}} --webhook-test
kubectl --context {{MGMT_KUBE_CONTEXT}} -n monitoring logs deploy/alertmanager-confluent-bridge --tail=100
confluent kafka topic consume alertmanager-events --from-beginning --group "verify-alerts-$(date +%s)" --cluster "$CONFLUENT_CLUSTER_ID"
```

Pass condition: an Alertmanager payload with `source=alertmanager` appears in Confluent and triggers the Alertmanager Sensor.

Evidence:

```text
Bridge test POST returned HTTP 202.
Bridge response: topic alertmanager-events, partition 4, offset 0, pod_name test-pod-123
Argo Events consumed alertmanager-events from Confluent and published to the EventBus.
Alertmanager Sensor successfully processed trigger alertmanager-triage.
Confluent CLI consume returned 1 record from alertmanager-events.
Workflow result:
- alert-triage-* workflow created
- alert-triage workflow reached Succeeded before normal TTL cleanup
```

## Proof 4 - kagent and Mattermost

Commands:

```bash
kubectl --context {{MGMT_KUBE_CONTEXT}} -n argo-events get wf --sort-by=.metadata.creationTimestamp
kubectl --context {{MGMT_KUBE_CONTEXT}} -n argo-events logs wf/{{WORKFLOW_NAME}}
```

Pass condition: the correct workflow path fires, reaches `Succeeded` or a known non-transport failure, and Mattermost receives the message.

Evidence:

```text
k8s event path:
- triage-critical-* workflows reached Succeeded.

Alertmanager path:
- alert-triage-* workflow reached Succeeded.

Mattermost delivery was not independently checked in this pass.
```

## Proof 5 - Grafana Alertmanager Contact Point to Confluent

Validated on 2026-05-22 against Grafana `12.3.2` on `{{MGMT_KUBE_CONTEXT}}`.

Temporary Grafana configuration used for the smoke test:

```text
contact point: confluent-bridge-smoke
type: webhook
url: http://alertmanager-confluent-bridge.monitoring.svc.cluster.local:8080/alertmanager
notification policy route: alertname = ConfluentBridgeSmokeTest
temporary rule: ConfluentBridgeSmokeTest
query: vector(1)
```

Evidence:

```text
Grafana API health: ok, version 12.3.2
Grafana-managed alert rule created: ConfluentBridgeSmokeTest
Grafana Alertmanager delivered webhook to bridge: POST /alertmanager HTTP/1.1 202
Argo Events Kafka EventSource consumed alertmanager-events partition 3 offset 0
Argo Sensor confluent-alertmanager-triage successfully processed trigger alertmanager-triage
Workflow alert-triage-t7bns reached Succeeded
Workflow payload contained:
  status: firing
  receiver: confluent-bridge-smoke
  alertname: ConfluentBridgeSmokeTest
  namespace: monitoring
  pod: grafana-contact-point-smoke
  severity: warning
```

Cleanup:

```text
temporary Grafana notification policy route removed
temporary Grafana alert rule removed
temporary Grafana contact point removed
post-cleanup Grafana API checks: smoke contact point/rule/policy route absent
```

## Proof 6 - Grafana Metrics, Logs, and Crash/Event Alerts to Confluent

Validated on 2026-05-22 against Grafana `12.3.2` on `{{MGMT_KUBE_CONTEXT}}`.

Temporary Grafana configuration used for the smoke test:

```text
contact point: confluent-bridge-validation-{{RUN_ID}}
type: webhook
url: http://alertmanager-confluent-bridge.monitoring.svc.cluster.local:8080/alertmanager
notification policy routes:
  alertname = ConfluentMetricCpuSmokeTest
  alertname = ConfluentLogSmokeTest
  alertname = ConfluentPodCrashSmokeTest
temporary rule group: confluent-validation
```

Signals generated:

```text
metric:
  source: Prometheus
  query: container_cpu_usage_seconds_total for a temporary CPU smoke pod
  alertname: ConfluentMetricCpuSmokeTest
  labels included: namespace, pod, severity, signal_type=metric, validation
  annotations included: metric_name, query_pod, run_id, summary, description

log:
  source: Loki
  query: count_over_time for a unique temporary container log marker
  alertname: ConfluentLogSmokeTest
  labels included: namespace, pod, severity, signal_type=log, validation
  annotations included: log_marker, query_pod, run_id, summary, description

crash/event:
  source: kube-state-metrics through Prometheus
  query: kube_pod_container_status_waiting_reason reason=CrashLoopBackOff
  alertname: ConfluentPodCrashSmokeTest
  labels included: namespace, pod, severity, signal_type=event, reason, validation
  annotations included: reason, query_workload, run_id, summary, description
```

Evidence:

```text
Prometheus CPU query returned a live sample for the temporary CPU smoke pod.
Prometheus CrashLoopBackOff query returned a live sample for the temporary crash deployment.
Loki query returned count=1 for the unique temporary container log marker.
Grafana-managed alert states were active for all three alertnames.
Grafana Alertmanager delivered the three firing webhook POSTs to the bridge: POST /alertmanager HTTP/1.1 202.
Argo Events Kafka EventSource consumed the three firing alertmanager-events records and published them to the EventBus.
Argo Sensor confluent-alertmanager-triage successfully processed the three firing alertmanager-triage triggers.
Initial firing Argo Workflows created:
  alert-triage-2kcf6 for ConfluentPodCrashSmokeTest
  alert-triage-xhdb9 for ConfluentLogSmokeTest
  alert-triage-r57fm for ConfluentMetricCpuSmokeTest
Workflow payloads contained:
  receiver: confluent-bridge-validation-{{RUN_ID}}
  status: firing
  alertname: ConfluentMetricCpuSmokeTest, ConfluentLogSmokeTest, ConfluentPodCrashSmokeTest
  signal_type: metric, log, event
  namespace: kagent
  pod: signal-specific temporary pod/workload name
  severity: warning
  signal-specific annotations and values
Additional repeat/resolution records may appear around cleanup because the temporary route used repeat_interval=1m.
```

Operational notes:

```text
Loki was initially unavailable because its pod was on a NotReady worker and the loki Service had no ready endpoints.
The Loki pod was force-removed from the unreachable node and rescheduled to a Ready worker; the loki Service endpoint recovered.
The downstream alert-triage workflows were created and carried rich payloads, but their GitLab issue step remained Running/Pending during this pass because the cluster lacked enough spare CPU/memory to schedule those workflow pods.
This does not block the verified producer-consumer path: Grafana Alertmanager -> bridge -> Confluent topic -> Argo Events Kafka EventSource -> Sensor -> Workflow creation/payload parse.
```

Cleanup:

```text
temporary Grafana notification policy routes removed
temporary Grafana alert rules removed
temporary Grafana contact point removed
temporary CPU, log, and crash workloads removed from kagent namespace
post-cleanup Grafana API checks: validation contact point/rules/policy routes absent
```

## Proof 6 - Native Grafana Kafka REST Proxy Contact Point

Validated on 2026-05-22 against Grafana `12.3.2` on `{{MGMT_KUBE_CONTEXT}}`.

Configuration:

```text
contact point: confluent-kafka-rest-alerts
type: kafka
apiVersion: v3
topic: alertmanager-events
kafkaRestProxy: redacted Confluent REST endpoint with /kafka appended
username/password: Confluent Kafka API key and secret
cluster ID: redacted
```

Evidence:

```text
Grafana contact point created through the provisioning API.
Grafana contact point read-back showed:
- type: kafka
- apiVersion: v3
- kafkaTopic: alertmanager-events
- kafkaRestProxy present
- username present
- password present

Direct Confluent REST v3 smoke publish with the same endpoint and credentials returned:
- HTTP 200
- error_code: 200
- topic_name: alertmanager-events
- partition_id: 3
- offset: 7

Temporary Grafana-managed alert rule:
- title: ConfluentKafkaRestSmokeTest
- query: vector(1)
- route: alertname = ConfluentKafkaRestSmokeTest -> confluent-kafka-rest-alerts

Argo Events Kafka EventSource consumed the native Grafana Kafka record:
- timestamp: 2026-05-22T16:42:40Z
- eventID partition/offset: alertmanager-events:2:2
- body.client: Grafana
- body.alert_state: alerting
- body.description included ConfluentKafkaRestSmokeTest
```

Important caveat:

```text
The native Grafana Kafka REST contact point publishes a Grafana-specific record,
not the bridge envelope expected by management-cluster/03-sensor-alertmanager.yaml.
The existing Sensor discarded the smoke event with:
data filter error (path 'body.source' does not exist)

Conclusion:
- Grafana -> Confluent Cloud Kafka REST v3 works.
- Confluent Kafka -> Argo Events EventSource works.
- The existing Alertmanager triage Sensor remains bridge-specific.
- Add a native Grafana Kafka Sensor or a normalizer before routing native
  Grafana Kafka records into the Alertmanager triage WorkflowTemplate.
```

Cleanup:

```text
temporary Grafana alert rule removed: HTTP 204
post-delete rule read-back: HTTP 404
temporary notification policy route removed
native contact point retained: confluent-kafka-rest-alerts
```

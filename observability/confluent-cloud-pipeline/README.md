# Confluent Cloud Pipeline PoC

This lab proves Confluent Cloud Kafka as the shared message bus for two producer classes:

- `{{WORKLOAD_KUBE_CONTEXT}}` workload cluster: Grafana Alloy publishes Kubernetes events.
- `{{MGMT_KUBE_CONTEXT}}` management cluster: Alertmanager publishes alert webhooks through a small Kafka bridge.

The implementation intentionally uses two topics in one Confluent cluster:

- `k8s-events` for Alloy OTLP/Kubernetes-event records.
- `alertmanager-events` for raw Alertmanager webhook records wrapped with routing metadata.

This keeps the proof honest. The existing `k8s-triage-critical` workflow expects Kubernetes-event-shaped OTLP. Alertmanager payloads have a different contract, so they route to an Alertmanager-specific workflow path instead of pretending the same parser can handle both.

For the production routing recommendation, including how many Confluent topics
to use and where namespace/criticality routing should happen, see
[`docs/observability/catent-alertmanager-confluent-routing.md`](../../docs/observability/catent-alertmanager-confluent-routing.md).

## Layout

```text
observability/confluent-cloud-pipeline/
├── 00-cluster-bootstrap.sh
├── 01-shared-secrets.yaml
├── 02-confluent-rest-smoke.sh
├── EVIDENCE.md
├── REVIEW-NOTES.md
├── README.md
├── verify.sh
├── alertmanager-shim/
│   ├── 00-payload-contract.md
│   ├── 01-bridge-configmap.yaml
│   ├── 02-bridge-deployment.yaml
│   ├── 03-alertmanager-values.yaml
│   └── 04-test-alertmanager-payload.json
├── grafana-contact-point/
│   ├── 01-configure-kafka-rest-contact-point.sh
│   ├── README.md
│   └── WORK-SETUP-RUNBOOK.md
├── management-cluster/
│   ├── 01-eventsource-confluent.yaml
│   ├── 02-sensor-k8s-events.yaml
│   └── 03-sensor-alertmanager.yaml
└── workload-cluster/
    ├── 01-alloy-secret.md
    ├── 02-alloy-config.yaml
    └── 03-alloy-deployment.patch.yaml
```

## Preconditions

- Confluent CLI is installed.
- You are logged in with `confluent login`.
- Kubernetes contexts exist for `{{WORKLOAD_KUBE_CONTEXT}}` and `{{MGMT_KUBE_CONTEXT}}`.
- Argo Events remains pinned to the repo default chart `2.4.14` / appVersion `v1.9.5` for this PoC.

Before creating resources, verify the local secret files are ignored:

```bash
git check-ignore -v confluent.io/.env confluent.io/.bootstrap.env confluent.io/.kafka-key
```

## Build Flow

1. Bootstrap Confluent resources:

   ```bash
   observability/confluent-cloud-pipeline/00-cluster-bootstrap.sh
   ```

2. Create Kubernetes secrets from `confluent.io/.bootstrap.env`:

   ```bash
   source confluent.io/.bootstrap.env

   kubectl --context {{WORKLOAD_KUBE_CONTEXT}} -n monitoring create secret generic alloy-confluent \
     --from-literal=bootstrap="$CONFLUENT_BOOTSTRAP" \
     --from-literal=topic="$CONFLUENT_K8S_TOPIC" \
     --from-literal=key="$CONFLUENT_SA_KEY" \
     --from-literal=secret="$CONFLUENT_SA_SECRET" \
     --dry-run=client -o yaml | kubectl --context {{WORKLOAD_KUBE_CONTEXT}} apply -f -

   kubectl --context {{MGMT_KUBE_CONTEXT}} -n argo-events create secret generic confluent-credentials \
     --from-literal=bootstrap="$CONFLUENT_BOOTSTRAP" \
     --from-literal=rest-endpoint="$CONFLUENT_REST_ENDPOINT" \
     --from-literal=k8s-topic="$CONFLUENT_K8S_TOPIC" \
     --from-literal=alerts-topic="$CONFLUENT_ALERTS_TOPIC" \
     --from-literal=key="$CONFLUENT_SA_KEY" \
     --from-literal=secret="$CONFLUENT_SA_SECRET" \
     --dry-run=client -o yaml | kubectl --context {{MGMT_KUBE_CONTEXT}} apply -f -

   kubectl --context {{MGMT_KUBE_CONTEXT}} -n argo-events create secret generic confluent-public-ca \
     --from-file=ca.pem=/etc/ssl/cert.pem \
     --dry-run=client -o yaml | kubectl --context {{MGMT_KUBE_CONTEXT}} apply -f -

   kubectl --context {{MGMT_KUBE_CONTEXT}} -n monitoring create secret generic alertmanager-confluent \
     --from-literal=bootstrap="$CONFLUENT_BOOTSTRAP" \
     --from-literal=rest-endpoint="$CONFLUENT_REST_ENDPOINT" \
     --from-literal=topic="$CONFLUENT_ALERTS_TOPIC" \
     --from-literal=key="$CONFLUENT_SA_KEY" \
     --from-literal=secret="$CONFLUENT_SA_SECRET" \
     --dry-run=client -o yaml | kubectl --context {{MGMT_KUBE_CONTEXT}} apply -f -
   ```

3. Prove Confluent REST v3 credentials before wiring Grafana or Alertmanager:

   ```bash
   observability/confluent-cloud-pipeline/02-confluent-rest-smoke.sh
   ```

   Expected result is HTTP `200`, Confluent `error_code` `200`, plus a Kafka
   partition and offset for `alertmanager-events`.

4. Apply workload Alloy config on `{{WORKLOAD_KUBE_CONTEXT}}`:

   ```bash
   kubectl --context {{WORKLOAD_KUBE_CONTEXT}} apply -f observability/confluent-cloud-pipeline/workload-cluster/02-alloy-config.yaml
   kubectl --context {{WORKLOAD_KUBE_CONTEXT}} apply -f observability/confluent-cloud-pipeline/workload-cluster/03-alloy-deployment.patch.yaml
   ```

5. Apply management EventSource and Sensors on `{{MGMT_KUBE_CONTEXT}}`:

   ```bash
   source confluent.io/.bootstrap.env
   tmpdir="$(mktemp -d)"
   cp observability/confluent-cloud-pipeline/management-cluster/*.yaml "$tmpdir/"
   CONFLUENT_BOOTSTRAP="$CONFLUENT_BOOTSTRAP" perl -0pi -e 's/\{\{CONFLUENT_BOOTSTRAP\}\}/$ENV{CONFLUENT_BOOTSTRAP}/g' "$tmpdir/01-eventsource-confluent.yaml"
   kubectl --context {{MGMT_KUBE_CONTEXT}} apply -f "$tmpdir/"
   ```

6. Apply the Alertmanager bridge and Helm values overlay:

   ```bash
   kubectl --context {{MGMT_KUBE_CONTEXT}} apply -f observability/confluent-cloud-pipeline/alertmanager-shim/01-bridge-configmap.yaml
   kubectl --context {{MGMT_KUBE_CONTEXT}} apply -f observability/confluent-cloud-pipeline/alertmanager-shim/02-bridge-deployment.yaml

   helm upgrade prometheus-stack prometheus-community/kube-prometheus-stack \
     --namespace monitoring \
     --reuse-values \
     -f observability/confluent-cloud-pipeline/alertmanager-shim/03-alertmanager-values.yaml
   ```

7. Optional: configure Grafana's native Kafka REST Proxy contact point for Confluent Cloud.

   This bypasses the local Alertmanager bridge and lets Grafana Alerting publish
   directly to Confluent Cloud's Kafka REST API v3. It is useful when the goal is
   to prove the Grafana-native integration; keep the bridge path when you need
   payload normalization, local retry behavior, or the existing
   `confluent-alertmanager-triage` Sensor.

   ```bash
   GRAFANA_URL=http://127.0.0.1:13030 \
   GRAFANA_USER=admin \
   GRAFANA_PASSWORD='{{GRAFANA_ADMIN_PASSWORD}}' \
   observability/confluent-cloud-pipeline/grafana-contact-point/01-configure-kafka-rest-contact-point.sh
   ```

   Grafana's Kafka notifier emits a Grafana-specific Kafka record with fields
   such as `client`, `description`, `details`, and `alert_state`. It does not
   emit the `source=alertmanager` / `alertmanager.status=firing` envelope that
   `management-cluster/03-sensor-alertmanager.yaml` expects from the bridge.
   Add a native Grafana Kafka Sensor or normalizer before routing this path into
   the existing Alertmanager triage workflow.

   For the work-environment handoff, follow
   `observability/confluent-cloud-pipeline/grafana-contact-point/WORK-SETUP-RUNBOOK.md`.

8. Run verification:

   ```bash
   observability/confluent-cloud-pipeline/verify.sh
   ```

## Safety

The repo artifacts use placeholders only. Do not commit `confluent.io/.env`, `confluent.io/.bootstrap.env`, or `confluent.io/.kafka-key`.

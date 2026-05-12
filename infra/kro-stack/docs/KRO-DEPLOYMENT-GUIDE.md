# Crow Stack — Deployment & Verification Guide

Two KRO ResourceGraphDefinitions covering the full event triage pipeline:

| RGD | Kind | Where to apply | What it creates |
|-----|------|---------------|-----------------|
| `uk8s-kro-ai-stack.kro.run` | `KroAIStack` | Management cluster | EventBus, EventSource, Sensor, WorkflowTemplate, RBAC, ConfigMaps |
| `uk8s-kro-worker-alloy.kro.run` | `KroWorkerAlloy` | Each workload cluster | Alloy deployment (namespace, RBAC, ConfigMap, Deployment, Service) |

---

## Part 1 — Management Cluster (AI Stack)

### Step 1: Install KRO (once per cluster)

```bash
helm install kro oci://ghcr.io/kro-run/kro/kro \
  --namespace kro-system \
  --create-namespace \
  --version=0.3.0

kubectl wait --for=condition=Ready pod -n kro-system \
  -l app.kubernetes.io/name=kro --timeout=60s
```

### Step 2: Apply the RGD

```bash
kubectl apply -f infra-stack/kro-stack/definitions/uk8s-kro-ai-stack.yaml
kubectl get resourcegraphdefinitions
# Expected: uk8s-kro-ai-stack.kro.run   Inactive
```

`Inactive` = RGD accepted, no instances yet. Any error here means schema/syntax problem.

### Step 3: Create Azure Event Hub pre-requisites

```bash
EH_NS="evh-YOUR-NAMESPACE"
EH_RG="rg-event-triage"

# Create namespace (Standard tier — Basic does NOT support Kafka)
az eventhubs namespace create \
  --name $EH_NS --resource-group $EH_RG \
  --location uksouth --sku Standard --enable-kafka true

# Create topic
az eventhubs eventhub create \
  --name k8s-events --namespace-name $EH_NS \
  --resource-group $EH_RG \
  --partition-count 2 --cleanup-policy Delete --retention-time 24

# Create consumer group
az eventhubs eventhub consumer-group create \
  --name argo-events-consumer --eventhub-name k8s-events \
  --namespace-name $EH_NS --resource-group $EH_RG

# Get connection string
EH_CONNSTR=$(az eventhubs namespace authorization-rule keys list \
  --name RootManageSharedAccessKey \
  --namespace-name $EH_NS --resource-group $EH_RG \
  --query primaryConnectionString -o tsv)
```

### Step 4: Create the two pre-requisite secrets

```bash
# TLS CA cert — REQUIRED, cannot use insecureSkipVerify alone
echo | openssl s_client \
  -connect ${EH_NS}.servicebus.windows.net:9093 \
  -showcerts 2>/dev/null \
  | awk '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/' \
  > /tmp/eventhub-ca.pem

kubectl create secret generic eventhub-tls-ca \
  -n argo-events \
  --from-file=ca.pem=/tmp/eventhub-ca.pem

# Event Hub credentials — use --from-file to handle special chars (/, +, =) in SAS key
printf '%s' '$ConnectionString' > /tmp/eh-user.txt
printf '%s' "$EH_CONNSTR" > /tmp/eh-pass.txt

kubectl create secret generic eventhub-credentials \
  -n argo-events \
  --from-file=username=/tmp/eh-user.txt \
  --from-file=connection-string=/tmp/eh-pass.txt

rm /tmp/eh-user.txt /tmp/eh-pass.txt /tmp/eventhub-ca.pem
```

### Step 5: Create the KroAIStack instance

Edit `instances/kro/management-ai-stack.yaml` — replace placeholders:
- `evh-YOUR-NAMESPACE.servicebus.windows.net:9093`
- `https://mattermost.YOUR-DOMAIN.com/hooks/YOUR-WEBHOOK-ID`

Then apply:

```bash
kubectl apply -f infra-stack/kro-stack/instances/kro/management-ai-stack.yaml
```

### Step 6: Verify resources created

```bash
# KRO instance status
kubectl get kroaistack -A
# Expected: kro-ai-stack-prod   ACTIVE

# EventBus
kubectl get eventbus -n argo-events
# Expected: default   Running (3 NATS pods)

# EventSource pod
kubectl get pods -n argo-events -l eventsource-name=eventhub-k8s-events
# Expected: Running

# Sensor pod
kubectl get pods -n argo-events -l sensor-name=k8s-event-triage
# Expected: Running

# WorkflowTemplate
kubectl get workflowtemplate -n argo-events
# Expected: k8s-event-triage listed

# RBAC
kubectl auth can-i create workflows -n argo-events \
  --as=system:serviceaccount:argo-events:argo-events-sa
# Expected: yes
```

### Step 7: Verify EventSource connected to Event Hub

```bash
kubectl logs -n argo-events \
  -l eventsource-name=eventhub-k8s-events --tail=30

# Good signs:
#   "Sarama consumer group up and running!"
#   "successfully connected to eventbus"

# Bad signs:
#   "SASL handshake failed"   → wrong connection string
#   "dial tcp: i/o timeout"   → network/firewall
#   "x509: certificate"       → TLS CA cert issue
#   "secret-" volume error    → empty tlsCaSecretName
```

### Step 8: Verify Sensor subscribed

```bash
kubectl logs -n argo-events \
  -l sensor-name=k8s-event-triage --tail=20

# Good: "successfully subscribed to eventbus"
```

### Step 9: End-to-end test (bypass EventSource/Sensor, fire directly)

```bash
cat > /tmp/test-workflow.yaml << 'WFEOF'
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-otlp-
  namespace: argo-events
spec:
  workflowTemplateRef:
    name: k8s-event-triage
  arguments:
    parameters:
      - name: otlp-payload
        value: '{"resourceLogs":[{"resource":{"attributes":[{"key":"cluster","value":{"stringValue":"test-cluster"}},{"key":"environment","value":{"stringValue":"test"}}]},"scopeLogs":[{"logRecords":[{"body":{"stringValue":"{\"type\":\"Warning\",\"reason\":\"CrashLoopBackOff\",\"message\":\"back-off 5m0s restarting failed container\",\"involvedObject\":{\"kind\":\"Pod\",\"name\":\"myapp-abc123\",\"namespace\":\"default\"},\"count\":5,\"lastTimestamp\":\"2026-03-03T10:00:00Z\"}"},"attributes":[{"key":"event_type","value":{"stringValue":"Warning"}},{"key":"event_reason","value":{"stringValue":"CrashLoopBackOff"}},{"key":"obj_kind","value":{"stringValue":"Pod"}},{"key":"obj_namespace","value":{"stringValue":"default"}}]}]}]}]}'
WFEOF

kubectl apply -f /tmp/test-workflow.yaml
argo watch -n argo-events @latest
```

**Expected result:**
1. `parse-otlp` step — extracts 1 Warning event (CrashLoopBackOff)
2. `classify-and-alert` step — posts to Mattermost with :red_circle: critical alert + Quick Commands section

---

## Part 2 — Worker Cluster (Alloy)

One `KroWorkerAlloy` instance per workload cluster. Apply directly TO that cluster.

### Step 1: Apply the RGD on the worker cluster

```bash
# Switch to worker cluster context
kubectl config use-context YOUR-WORKER-CLUSTER-CONTEXT

# Apply RGD
kubectl apply -f infra-stack/kro-stack/definitions/uk8s-kro-worker-alloy.yaml
kubectl get resourcegraphdefinitions
# Expected: uk8s-kro-worker-alloy.kro.run   Inactive
```

### Step 2: Create the Event Hub credentials secret

```bash
# On the worker cluster
kubectl create ns monitoring

printf '%s' "Endpoint=sb://evh-YOUR-NAMESPACE.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=YOUR_KEY" \
  > /tmp/eh-connstr.txt

kubectl create secret generic alloy-eventhub \
  -n monitoring \
  --from-file=connection-string=/tmp/eh-connstr.txt

rm /tmp/eh-connstr.txt
```

### Step 3: Create the KroWorkerAlloy instance

Edit `instances/kro/worker-alloy.yaml`:
- Set `cluster.name` to a unique name for this cluster (appears in every Mattermost alert)
- Set `eventHub.fqdn` to your Event Hub namespace
- Set `watchNamespacesHCL` to the namespaces you want to monitor

```bash
kubectl apply -f infra-stack/kro-stack/instances/kro/worker-alloy.yaml
```

For a second worker cluster, copy the file with a new `metadata.name` and `cluster.name`:

```yaml
# instances/kro/worker-alloy-cluster02.yaml
apiVersion: v1alpha1
kind: KroWorkerAlloy
metadata:
  name: kro-alloy-cluster02
  namespace: default
spec:
  cluster:
    name: "aks-dev-01"
    environment: "development"
  # ... rest same as cluster01
```

### Step 4: Verify Alloy is running

```bash
kubectl get pods -n monitoring -l app=alloy
# Expected: Running

kubectl logs -n monitoring -l app=alloy --tail=30
# Good: "Starting Alloy" + no error connecting to Event Hub

# Health endpoint
kubectl port-forward -n monitoring svc/alloy 12345:12345 &
curl -s http://localhost:12345/-/ready
# Expected: "Alloy is ready."
```

### Step 5: Verify events flowing end-to-end

```bash
# Force a Warning event on the worker cluster
kubectl run test-pod --image=invalid-image-xyz-123 2>/dev/null || true

# Wait ~30s, then check Event Hub via Azure Portal:
# Event Hub namespace → k8s-events topic → Process Data → peek messages
# Should see OTLP JSON with the ImagePullBackOff event

# Check management cluster for triggered workflows
kubectl get workflows -n argo-events --watch
# Should see k8s-triage-XXXX workflows appearing
```

---

## Troubleshooting Quick Reference

| Symptom | Check | Fix |
|---------|-------|-----|
| RGD stays `Inactive` | `kubectl describe rgd <name>` | Normal until instance created |
| Instance stuck `Progressing` | `kubectl describe kroaistack <name>` | Check conditions for resource errors |
| EventSource pod CrashLoops | `kubectl logs -l eventsource-name=eventhub-k8s-events` | See log analysis above |
| No workflows firing | Walk the naming chain (EventSource name → Sensor dependency) | Names must match exactly |
| parse-otlp outputs `[]` | Check OTLP structure from actual Event Hub messages | Compare against OTLP-PAYLOAD-REFERENCE.md |
| Mattermost not receiving | Check WEBHOOK_URL in ConfigMap | `kubectl get cm mattermost-webhook-config -n argo-events -o yaml` |
| Alloy not sending events | Check `EVENTHUB_CONNECTION_STRING` env in Alloy pod | `kubectl exec -n monitoring deploy/alloy -- env \| grep EVENT` |

---

## Naming Chain (must be exact)

```
EventSource.metadata.name = "eventhub-k8s-events"         ← KRO fixed value
EventSource.spec.kafka key = "k8s-events"                  ← KRO fixed value
Sensor.dependencies[].eventSourceName = "eventhub-k8s-events"  ← must match (1)
Sensor.dependencies[].eventName       = "k8s-events"           ← must match (2)
Sensor.triggers[].k8s.workflowTemplateRef.name = "k8s-event-triage"
WorkflowTemplate.metadata.name = "k8s-event-triage"       ← KRO fixed value
```

These are all fixed by the RGD — you cannot accidentally break them by changing instance values.

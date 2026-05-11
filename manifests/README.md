# Manifests

Kustomize overlays are split by delivery path:

```text
manifests/
  common/
    namespace.yaml
    eventbus.yaml
    sensor-rbac.yaml
  redpanda-kafka/
    redpanda.yaml
    redpanda-topic-job.yaml
    alertmanager-kafka-bridge.yaml
    alertmanager-configmap.yaml
    eventsource.yaml
    sensor.yaml
  webhook/
    alertmanager-configmap.yaml
    eventsource.yaml
    eventsource-service.yaml
    sensor.yaml
```

Render:

```bash
kubectl kustomize manifests/redpanda-kafka
kubectl kustomize manifests/webhook
```

Apply:

```bash
kubectl apply -k manifests/redpanda-kafka
kubectl apply -k manifests/webhook
```

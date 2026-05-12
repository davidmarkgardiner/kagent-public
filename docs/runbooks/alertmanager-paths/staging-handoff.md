# Staging Handoff

## Status

Path A has live validation evidence from `{{CLUSTER_NAME}}` in
`docs/mil-28-path-a-evidence.md`. The package is not production-ready until the
direct webhook path is validated under the same conditions and the Argo Events
version mismatch is resolved.

## Branch And Tag

- Branch: `symphony/MIL-28-redpanda-kafka-path`
- Handoff tag: not created

## Apply Order

Redpanda Kafka path:

```bash
kubectl apply -k manifests/redpanda-kafka
```

Direct webhook path:

```bash
kubectl apply -k manifests/webhook
```

Both overlays include `manifests/common`, so applying either path creates the
namespace, EventBus, and Sensor RBAC.

## Required Staging Inputs

- Target cluster context.
- Confirmation that Argo Events v1.9.10 controllers and CRDs are installed.
- Target Alertmanager configuration method.
- Decision on whether to expose EventSource/bridge through internal DNS,
  ingress, or port-forward for the first test.
- Decision on whether to keep both paths enabled after comparison.

## Staging Validation

1. Render both overlays:

   ```bash
   kubectl kustomize manifests/redpanda-kafka >/tmp/redpanda-kafka.yaml
   kubectl kustomize manifests/webhook >/tmp/webhook.yaml
   ```

2. Apply one path at a time.
3. For Path A, send `samples/alertmanager-api-pod-alert.json` through the
   Alertmanager API after deploying the scoped `AlertmanagerConfig`.
4. Capture EventSource logs, Sensor logs, and consumer pod logs.
5. Fill the measurement table in `docs/comparison-results.md`.
6. Decide default path for the next iteration.

## Rollback

```bash
kubectl delete -k manifests/redpanda-kafka
kubectl delete -k manifests/webhook
```

If either Alertmanager receiver has been added to a real Alertmanager instance,
remove or disable the receiver before deleting these POC endpoints.

Both overlays include shared `common` resources. During a partial rollback,
delete path-specific resources manually or re-apply the overlay that should stay
active after deleting the other path.

## Promotion Criteria

- Consumer logs show the expected `pod_name`, `alert_count`, `alert_json`,
  `payload_keys`, and `consumed_at` for both paths.
- Staging owner accepts the latency and reliability comparison.
- Redpanda bridge packaging decision is made: keep ConfigMap bridge for POC only
  or replace it with a pinned image.
- Alertmanager retry and de-duplication behavior is documented from staging.

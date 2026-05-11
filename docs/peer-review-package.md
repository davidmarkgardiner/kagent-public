# Peer-Review Package

## Scope

Review the public K-Agent event-flow POC package for staging readiness. The
package proves delivery only up to a consumer pod and does not invoke K-Agent
triage.

## Files To Review

- `README.md`
- `docs/PLAN.md`
- `docs/mil-28-path-a-plan.md`
- `docs/mil-28-path-a-evidence.md`
- `docs/runbooks/redpanda-kafka-path.md`
- `docs/runbooks/webhook-path.md`
- `docs/comparison-results.md`
- `docs/staging-handoff.md`
- `manifests/common/`
- `manifests/redpanda-kafka/`
- `manifests/webhook/`
- `samples/alertmanager-pod-alert.json`

## Review Focus

- Public safety: no secrets, private cluster details, or internal URLs.
- Argo Events correctness for EventSource, Sensor, parameter mapping, and RBAC.
- Alertmanager payload fidelity through both paths.
- Whether the Redpanda bridge is acceptable for staging as a POC bridge.
- Whether the direct webhook Service and path are clear enough to operate.
- Whether the comparison document is honest about pending staging evidence.

## Validation Commands

```bash
kubectl kustomize manifests/redpanda-kafka >/tmp/redpanda-kafka.yaml
kubectl kustomize manifests/webhook >/tmp/webhook.yaml
gitleaks detect --no-git --redact
```

For live staging validation, follow the runbooks and capture the evidence table
in `docs/comparison-results.md`.

## Known Gaps

- End-to-end staging evidence was captured for the Redpanda Kafka path only.
  Direct webhook evidence remains pending.
- The Redpanda bridge is mounted from a ConfigMap for POC speed. A pinned image
  is better for long-lived staging.
- The live cluster ran Argo Events `v1.9.6`; the intake requested `v1.9.10`.
  Resolve the version mismatch before promoting beyond staging.
- Alertmanager integration is represented as sample receiver ConfigMaps; the
  Redpanda path now also includes a scoped Prometheus Operator
  `AlertmanagerConfig` contact point for clusters that support it.

## Reviewer Outcome

Accept the package when:

- Both Kustomize overlays render cleanly.
- The public-safety scan has no actionable hits.
- A reviewer agrees the known gaps are acceptable for staging.
- Live validation evidence is attached or the staging owner accepts the pending
  evidence checklist.

# kagent-public

Public mirror for K-Agent event-flow proof-of-concept materials.

This repository contains sanitized Kubernetes manifests and runbooks for proving
that Alertmanager alerts can reach a consumer pod through two paths:

1. Alertmanager -> Redpanda -> Argo Events Kafka EventSource -> consumer pod
2. Alertmanager -> Argo Events webhook EventSource -> consumer pod

The proof stops at the consumer pod. K-Agent triage is intentionally outside the
scope of this mirror.

## Contents

- `docs/PLAN.md` - implementation plan and acceptance surface.
- `docs/mil-28-path-a-plan.md` - MIL-28 live validation plan for Path A.
- `docs/mil-28-path-a-evidence.md` - MIL-28 live Path A evidence.
- `docs/runbooks/redpanda-kafka-path.md` - runbook for the Redpanda/Kafka path.
- `docs/runbooks/webhook-path.md` - runbook for the direct webhook path.
- `docs/comparison-results.md` - comparison framework and current findings.
- `docs/peer-review-package.md` - reviewer checklist and validation package.
- `docs/staging-handoff.md` - staging handoff notes.
- `manifests/` - Kustomize-ready Kubernetes manifests for both paths.
- `samples/` - sanitized Alertmanager payloads for smoke testing.

## Public Safety

Do not commit secrets, private hostnames, private cluster IPs, connection
strings, personal tokens, or internal URLs. Keep all environment-specific values
as placeholders or local overrides outside this repository.

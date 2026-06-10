# Reliability Chaos Test Skeleton

This directory is the first execution pass for
`WORK-CHAOS-TEST-MANAGER-PLAN.md`. It keeps `ChaosTest` and
`ReliabilitySuite` as Git-stored configuration objects while the team validates
whether a CRD/controller is worth adding later.

## Contracts

- `schemas/chaos-test.schema.yaml` validates a single lower-env chaos test.
- `schemas/reliability-suite.schema.yaml` validates a suite that groups many
  tests under one reliability score.
- `examples/pod-delete.chaostest.yaml` is the smallest first demo: pod-delete on
  the labelled `chaos-demo/chaos-target` workload.
- `examples/sample-platform.reliabilitysuite.yaml` shows the initial suite
  shape without scheduling real fleet chaos.
- `platform/argo-workflows/templates/chaos-test-schedule-cronworkflow.yaml`
  shows the GitOps-managed schedule wrapper. It is suspended by default and
  passes `dry_run: "true"` until a lower-env HITL/GitLab approval path is ready.
- `gitops/litmus-pod-delete-chaosengine.yaml` is the reviewed Litmus
  `ChaosEngine` manifest that a GitOps MR would sync for the first pod-delete
  demo. The workflow watches it; it does not generate it inline.
- `reports/templates/` contains the per-test report and review-manager finding
  templates used by the reporting agents.
- `observability/chaos-test-manager/` contains the starter Grafana dashboard and
  Alloy snippet for lifecycle proof markers and eval metrics.
- `CONFIGURATION.md` lists placeholders, images, CRDs/controllers, and
  permission boundaries for a private lower-env rollout.
- `LIVE-RUNBOOK.md` is the target-cluster execution checklist for the first
  Proxmox/non-production run.
- `examples/chaos-test-lifecycle.workflow.yaml` is the reusable Argo Workflow
  submission manifest for dry-run first, then HITL-approved non-dry-run.
- `scripts/validate-reliability-configs.py` is the local CI/policy gate for the
  config objects.
- `scripts/preflight-live-run.sh` runs the local and server dry-run checks before
  the live target-cluster pass.
- `infra/byo-kagent/kyverno-policies/validate-chaos-test-safety.yaml` is the
  admission policy companion for Litmus `ChaosEngine` and reliability
  `CronWorkflow` resources.

## Safety Defaults

- Production is not a valid `environment` or `env-tier` in these schemas.
- Every test requires `safety.requiresHITL: true`.
- Targets must include `reliability.platform/chaos-optin: "true"`.
- Cluster count is capped at four for the first planning proof.
- Memory writes are curator-only and KB updates are HITL-gated MRs.

The Argo workflow skeleton is
`platform/argo-workflows/templates/chaos-test-lifecycle.yaml`. It validates the
spec, prepares the HITL packet, waits for human review, expects GitOps sync for
the Litmus object, watches the resulting `ChaosResult`, then calls the existing
agent lifecycle eval template with the `chaos-pod-delete` case.

## Validation

```bash
python3 chaos/reliability/scripts/validate-reliability-configs.py \
  chaos/reliability/examples/pod-delete.chaostest.yaml \
  chaos/reliability/examples/sample-platform.reliabilitysuite.yaml \
  chaos/reliability/gitops/litmus-pod-delete-chaosengine.yaml

argo lint --offline --kinds=workflowtemplates,cronworkflows \
  platform/argo-workflows/templates/chaos-test-lifecycle.yaml \
  platform/argo-workflows/templates/chaos-test-schedule-cronworkflow.yaml \
  observability/agent-evals/argo/lifecycle-eval-workflow-template.yaml

bash chaos/reliability/scripts/preflight-live-run.sh {{KUBE_CONTEXT}}
```

# Chaos Test Manager Execution Review

Date: 2026-06-03

This is the first execution pass for `WORK-CHAOS-TEST-MANAGER-PLAN.md`. It
implements the process skeleton requested by the reviewed plan: request intake,
safe spec drafting, HITL, GitOps proposal shape, Litmus watch path,
observability/reporting contracts, and lifecycle eval wiring.

## Implemented

| Plan area | Current artefact | Status |
|---|---|---|
| `ChaosTest` as Git config, not CRD | `chaos/reliability/schemas/chaos-test.schema.yaml` | Implemented |
| Example low-risk first test | `chaos/reliability/examples/pod-delete.chaostest.yaml` | Implemented |
| `ReliabilitySuite` suite shape | `chaos/reliability/schemas/reliability-suite.schema.yaml`, `chaos/reliability/examples/sample-platform.reliabilitysuite.yaml` | Implemented |
| Designer agent | `agents/chaos-designer/agent.yaml` | Implemented as read-only drafting agent |
| Test manager agent | `agents/chaos-test-manager/agent.yaml` | Implemented as Argo workflow submit/status agent |
| Scheduler agent | `agents/chaos-scheduler/agent.yaml` | Implemented as GitOps-first schedule drafting agent |
| Suite designer agent | `agents/reliability-suite-designer/agent.yaml` | Implemented as read-only suite drafting agent |
| Reporting agent | `agents/reliability-reporting/agent.yaml` | Implemented as report/MR drafting agent |
| Review manager agent | `agents/review-manager/agent.yaml` | Implemented as below-benchmark reviewer |
| Fleet selector skill | `agents/skills/fleet-selector/SKILL.md` | Implemented as auditable lower-env cluster selection contract |
| Argo lifecycle skeleton | `platform/argo-workflows/templates/chaos-test-lifecycle.yaml` | Implemented |
| Suspended schedule wrapper | `platform/argo-workflows/templates/chaos-test-schedule-cronworkflow.yaml` | Implemented as dry-run CronWorkflow |
| GitOps Litmus ChaosEngine | `chaos/reliability/gitops/litmus-pod-delete-chaosengine.yaml` | Implemented |
| Chaos lifecycle eval case | `observability/agent-evals/lifecycle-cases/chaos-pod-delete.yaml` | Implemented |
| Report templates | `chaos/reliability/reports/templates/` | Implemented |
| Grafana lifecycle dashboard | `observability/chaos-test-manager/grafana/chaos-test-lifecycle-dashboard.json` | Implemented |
| Alloy lifecycle telemetry snippet | `observability/chaos-test-manager/alloy/chaos-test-lifecycle.alloy` | Implemented |
| Configuration handoff | `chaos/reliability/CONFIGURATION.md` | Implemented |
| Live runbook | `chaos/reliability/LIVE-RUNBOOK.md` | Implemented |
| Workflow submission manifest | `chaos/reliability/examples/chaos-test-lifecycle.workflow.yaml` | Implemented |
| Local policy gate | `chaos/reliability/scripts/validate-reliability-configs.py` | Implemented |
| Target-cluster preflight | `chaos/reliability/scripts/preflight-live-run.sh` | Implemented and verified against interim cluster |
| Admission policy companion | `infra/byo-kagent/kyverno-policies/validate-chaos-test-safety.yaml` | Implemented and added to Kyverno kustomization |
| Eval runtime packaging | `observability/agent-evals/kustomization.yaml`, `observability/agent-evals/argo/lifecycle-eval-workflow-template.yaml` | Updated |
| README navigation | `README.md` | Already present in the current worktree |

## Design Decisions

- `ChaosTest` and `ReliabilitySuite` remain schema-validated Git config objects.
  No CRD/controller was introduced in this pass.
- The `chaos-designer-agent` has querydoc, memory read, and read-only Kubernetes
  tools only. It cannot write memory, submit workflows, or mutate the cluster.
- The `chaos-test-manager-agent` may submit only a Workflow that references
  `workflowTemplateRef.name: chaos-test-lifecycle`.
- The workflow defaults to `dry_run: "true"`. A non-dry run requires HITL resume,
  a GitLab MR reference, GitOps sync evidence, and a pre-existing Litmus
  `ChaosEngine` observed by name.
- The workflow does not generate a Litmus `ChaosEngine` inline at runtime. That
  keeps durable chaos definitions in Git/GitOps review.
- The new eval case uses the existing lifecycle scorer and the existing
  `agent-eval-runtime-files` ConfigMap path.

## Validation Summary

Passed:

- YAML parsed for all new and modified files.
- `ChaosTest` and `ReliabilitySuite` examples validated against their schemas in
  an isolated temporary `jsonschema` environment.
- `kubectl kustomize observability/agent-evals` rendered the eval runtime
  ConfigMap with the new `chaos-pod-delete` lifecycle case.
- `python3 chaos/reliability/scripts/validate-reliability-configs.py` passed for
  the example `ChaosTest`, `ReliabilitySuite`, and GitOps `ChaosEngine`.
- `kubectl kustomize chaos/reliability/gitops` rendered the reviewed Litmus
  `ChaosEngine`.
- `kubectl kustomize infra/byo-kagent/kyverno-policies` rendered the Kyverno
  bundle with `validate-chaos-test-safety`.
- `argo lint --offline --kinds=workflowtemplates` passed for the chaos lifecycle
  template, schedule CronWorkflow, and referenced eval template.
- A synthetic marker bundle scored against `chaos-pod-delete` with no hard
  failures, proving the eval contract is wired.
- The Grafana dashboard JSON parsed with `python3 -m json.tool`.
- `git diff --check` passed.
- Public-safety sweep over the new reliability/agent/workflow/eval files found
  no private IPs, GUID-like IDs, bearer strings, or token/password literals.
- `chaos/reliability/scripts/preflight-live-run.sh` passed against the interim
  compatible cluster, proving the reusable Proxmox/live-run readiness checks.
- The Proxmox-backed target cluster became reachable, received the
  non-injection prerequisites/templates, and completed a resumed
  `dry_run=true` `chaos-test-lifecycle` Workflow without starting Litmus chaos.
- The target cluster then ran the live lower-env pod-delete experiment. Litmus
  produced a `Pass` ChaosResult, `chaos-target` recovered to 2/2 Ready, and the
  lifecycle eval rerun scored `1.0 passed=true` after the eval runtime ConfigMap
  and volume wiring were corrected.

Blocked or not claimed:

- No live Litmus injection was run in this pass.
- No GitLab branch, MR, issue, or Grafana annotation was created.
- `kubectl apply --dry-run=client` and non-offline `argo lint` attempted to
  contact the configured Kubernetes API and timed out, so server/client API
  validation against installed CRDs is not claimed.
- Local `kyverno apply` evaluated zero rules for custom resources, including
  existing repo custom-resource policies, so Kyverno admission behavior is not
  claimed until a cluster with Kyverno and the relevant CRDs is reachable.
- A fresh `kubectl --request-timeout=5s get ns argo argo-events kagent
  chaos-demo` check on 2026-06-03 failed because the configured Kubernetes API
  at the current kubeconfig endpoint was unreachable.

## Remaining Work

1. Replace placeholder GitLab/Grafana/HITL values in a non-production
   environment.
2. Commit the generated `ChaosTest` and Litmus `ChaosEngine` through GitOps.
3. Replace placeholder GitLab/Grafana/HITL values with real lower-env
   integrations.
4. Capture Grafana/Alloy telemetry, report MR, memory proposal, and KB proposal
   through the real integration path.
5. Decide whether Kyverno should be installed on the Proxmox demo cluster or
   treated as an AKS/interim-cluster-only admission check.

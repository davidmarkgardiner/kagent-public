# Daily discovery and upgrade workflow: dry-run scaffold

This is an executable **planning scaffold**, not an AKS deployment. It pairs a suspended daily Argo `CronWorkflow` with an on-demand `WorkflowTemplate`. Both use synthetic fixture parameters. No step calls Azure, Kubernetes APIs, kagent, a model endpoint, Git, or an application. Successful Argo status means the scaffold ran; it does **not** mean an upgrade is safe or a version pair is compatible.

The [upgrade lifecycle proposal](../agent-assisted-aks-istio-upgrades.md) explains the intended process. This directory makes the scheduling and agent handoff points inspectable before workplace integration.

| File | Purpose |
|---|---|
| [`discovery-cronworkflow.yaml`](discovery-cronworkflow.yaml) | Suspended 07:00 UTC fixture comparison; prints a JSON candidate with availability and compatibility `unverified`. It does not automatically submit the upgrade workflow. |
| [`upgrade-workflowtemplate.yaml`](upgrade-workflowtemplate.yaml) | Runs validation, three agent handoff checkpoints, three action previews, and an aggregate JSON report. Each checkpoint explicitly says `not_invoked_dry_run` or `not_run_dry_run`. |
| [`rbac.yaml`](rbac.yaml) | Dedicated ServiceAccount with only Argo executor `workflowtaskresults` create/patch permission. No Azure identity or cluster-changing Kubernetes RBAC. |

## Path to a real integration

```text
Daily discovery (read-only identity)
  → exact region/cluster inventory + az aks get-upgrades
  → az aks mesh get-revisions/get-upgrades + release-source snapshot
  → deduplicate by cluster + target pair + source version
  → agent release-impact brief (read-only, fixed agent name)
  → reviewed version proposal / ARM PR

On-demand upgrade (separate approved workflow identity)
  → validate pinned ARM template, target pair and approval record
  → ARM what-if and deterministic preflight
  → agent reviews cited evidence and missing tests
  → approved ARM deployment, then explicit Istio revision canary
  → fixed canary/SLO gates and agent explanation of anomalies
  → named owner promotes, pauses or starts an approved recovery workflow
```

The actual workplace ARM templates, deployment scope and approval system must be mapped before replacing any preview. The current [ASO cluster agent demo](../../../../agents/aso-cluster-agent/README.md) is an example of agent → Workflow → provisioning → certification, but it is not an upgrade integration. ARM `what-if` and deployment commands must remain in the controlled workflow, never in an agent tool list. If the eventual platform moves to Flux/KRO/ASO, replace the ARM action with a reviewed GitOps change while preserving the same evidence and approval contract.

**Integration checks before any live run:** verify the installed Argo CRD version, a pinned runnable image in the target registry, a separate read-only Azure Workload Identity for discovery, a distinct narrowly scoped deployment identity, network access to the approved kagent A2A endpoint, source snapshot freshness, per-cluster locking across scheduled and manual triggers, durable receipts, timeout behavior, and fixed pass/fail health gates. `concurrencyPolicy: Forbid` only prevents overlap within this one CronWorkflow; it is not a fleet lock. Keep the discovery schedule suspended until those checks are complete. The production agent response needs a strict schema with cited evidence and `unknown` states; it must not grant promotion on its own.

## Offline validation

From the repository root:

```bash
argo lint --offline --strict \
  docs/platform-kb/aks/upgrade-automation-dry-run/discovery-cronworkflow.yaml \
  docs/platform-kb/aks/upgrade-automation-dry-run/upgrade-workflowtemplate.yaml
scripts/public-safe-scan.sh docs/platform-kb/aks/upgrade-automation-dry-run --strict --json
```

The manifests are intentionally not applied by this repository change. In a disposable Argo environment, an operator can first inspect/apply `rbac.yaml` and the two workflow manifests, then manually submit `aks-istio-upgrade-dry-run` with fixture defaults. That creates only workflow pods and JSON receipts. The scheduled discovery remains suspended unless explicitly enabled.

## Expected receipt

The final `report` task prints and outputs JSON with `status: planning_only`, `regional_availability: unverified`, `aks_istio_compatibility: unverified`, `agent_calls: 0`, `azure_writes: 0`, and `canary_tests_run: 0`. Its six stage receipts distinguish prepared agent handoffs from actions that have not run. Do not relabel these as passes when building a real connector.

Argo's [CronWorkflow reference](https://argo-workflows.readthedocs.io/en/latest/cron-workflows/) documents scheduling and concurrency. The [workflow RBAC guide](https://argo-workflows.readthedocs.io/en/release-3.7/workflow-rbac/) gives the minimal executor Role used here. Microsoft documents [regional AKS release tracking](https://learn.microsoft.com/en-us/azure/aks/release-tracker), [managed Istio upgrade sequencing](https://learn.microsoft.com/en-us/azure/aks/istio-upgrade), and [ARM what-if](https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/deploy-what-if) for the future live stages.

# Agent-assisted AKS and Istio upgrade lifecycle

**Status:** design proposal for an ARM-template-operated AKS fleet. It describes insertion points and acceptance evidence; it does not claim a workplace integration is deployed. **Reviewed:** 2026-10-08.

The [suspended dry-run CronWorkflow and upgrade WorkflowTemplate](upgrade-automation-dry-run/README.md) make the proposed scheduling and agent checkpoints reviewable without Azure writes.

## Recommendation

Keep version discovery, compatibility checks, ARM validation, deployment, rollout order, and numeric health gates in deterministic pipelines and approved workflows. Call read-only kagent specialists at three points: **release-impact review**, **pre-upgrade readiness review**, and **canary/post-upgrade evidence review**. Let an agent draft an operator and customer-facing “what changed” note from those same reviewed findings. The agent's verdict is advice; a pipeline gate uses observed facts and a named owner decides promotion.

This fits the current ARM template path. It also fits the repo's target Flux/KRO/ASO and Argo architecture without requiring that migration first. Here, “Sterile DNS” is assumed to mean **external-dns**, which is the component named in this repo; replace that example if a different service was intended.

## Where the calls fit

```text
Scheduled release check and fleet inventory (pipeline)
  → supported AKS version + regional availability + Istio revision compatibility
  → agent: release-impact brief and feature candidates
  → platform owner: select target and decide adopt / pilot / defer / reject
  → ARM PR and pipeline: lint, policy, validate, what-if, API/deprecation checks
  → agent: preflight evidence review and test-plan gaps
  → approved ARM deployment / Istio revision workflow: canary, then waves
  → pipeline: fixed smoke tests, SLO thresholds, rollout and rollback rules
  → agent: explain failed signals or summarize clean canary evidence
  → named owner: promote / pause / roll back
  → agent: draft reviewed release note, runbook delta, backlog items
```

| Point | Deterministic owner and inputs | Useful agent work | Reviewable output |
|---|---|---|---|
| **1. Release appears** | Scheduled job records current cluster and node-pool versions, region, `az aks get-upgrades`, AKS release tracker/notes, `az aks mesh get-revisions` and `get-upgrades`, support windows. | Compare *the chosen AKS and managed Istio revision* with the installed stack; identify behavior changes, feature opportunities, deprecations, and uncertainties. Separate upstream Istio features from features Microsoft supports in the AKS add-on. | Cited change brief: source links, exact version pair, affected components, proposed tests and `adopt / pilot / defer / reject / no action` candidates. |
| **2. ARM change proposed** | PR changes pinned parameters/templates; CI runs JSON/Bicep validation, policy, ARM what-if, schema/API checks and static checks for deprecated Kubernetes APIs. | Review the *actual diff and what-if output* for unexpected deletes/replacements, parameter drift, identity/network changes, node-pool consequences, and missing tests. | Risk and evidence checklist attached to the PR; explicit `unknown` for missing inventory or inconclusive what-if. |
| **3. Before change window** | Workflow captures PDBs, capacity/surge headroom, node-pool/OS state, health baseline, maintenance window, add-on and workload inventory, backup/recovery state. | Correlate known upgrade failure patterns with the specific fleet and select representative canary workloads. Explain why a warning matters. | Readiness report with evidence links, owner and proposed action. Hard failures remain pipeline rules. |
| **4. AKS canary and waves** | Approved ARM deployment or current approved AKS workflow applies the exact version; fixed gates check provisioning state, node versions/readiness, workloads, API errors, traffic and SLOs before each wave. | Investigate a failed or ambiguous gate using read-only AKS/Kubernetes/Grafana evidence; summarize blast radius and options. | Bounded incident brief and recommendation to hold, continue or invoke the approved recovery path. |
| **5. Istio revision canary** | Approved mesh workflow checks the region/version pair, prepares revision-specific MeshConfig if used, starts a canary revision, moves selected namespaces/workloads, verifies traffic, then completes or rolls back. | Compare old/new control planes, sidecar injection, ingress/egress, mTLS, routing and telemetry for the canary; explain regressions that fixed checks found. | Per-revision evidence pack and an owner-reviewed completion/rollback recommendation. |
| **6. After each wave** | Pipeline checks exact target versions, sidecar images, health and error budgets over a defined observation period. | Summarize anomalous changes and unresolved risks; draft runbook and “what's new” updates. | Versioned wave report, reviewed docs PR, and feature/backlog decisions. |

The agent call can be asynchronous for release research and documentation. Keep it out of the critical deployment path unless the workflow has a bounded timeout and a clear failure policy. A missing, stale or malformed agent response must never count as a health-gate pass.

## AKS and Istio need separate plans

The pipeline should compute the supported **AKS version × Istio add-on revision × region/tier** pair before proposing either upgrade. The managed Istio add-on does not automatically move minor revisions with the cluster, and an incompatible old revision can block AKS auto-upgrade. Use the region-specific AKS availability and mesh upgrade commands as the executable facts; treat release-calendar tables as planning inputs. The agent can explain sequencing and feature impact, but it must not invent a compatible pair. [AKS release tracker](https://learn.microsoft.com/en-us/azure/aks/release-tracker) · [Istio add-on support policy](https://learn.microsoft.com/en-us/azure/aks/istio-support-policy) · [Istio add-on upgrade guide](https://learn.microsoft.com/en-us/azure/aks/istio-upgrade).

For **AKS**, make control-plane/node-pool sequencing, version skew, capacity, PDBs and application disruption explicit. ARM template deployment is the current change mechanism; validate the proposed change with ARM what-if, then scrutinize its `Ignore` or other inconclusive results rather than treating a clean-looking preview as proof. [AKS node-pool upgrade rules](https://learn.microsoft.com/en-us/azure/aks/upgrade-node-pools) · [ARM what-if behavior and limits](https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/deploy-what-if).

For **Istio**, distinguish Microsoft-managed control-plane/ingress patching from workload proxy reinjection. During a minor revision canary, old and new control planes coexist; moving a namespace label or revision tag only affects newly created pods until workloads restart. The workflow owns that ordered rollout and any rollback, including revision-specific mesh configuration and ingress checks. An agent can verify the evidence, but it cannot infer that every proxy moved just because `istiod` is healthy. [Istio add-on upgrade guide](https://learn.microsoft.com/en-us/azure/aks/istio-upgrade).

## Application and platform add-on coverage

Use a small, explicit test catalogue per version pair. The agent may propose additions based on release changes, but the executable acceptance checks should be checked into source control.

| Component | Fixed canary checks | Agent contribution |
|---|---|---|
| **cert-manager** | Controller, webhook and cainjector Ready; representative staging Certificate/Issuer reaches Ready; renewal/challenge path and TLS handshake pass; no new reconciliation errors. | Explain failed issuance, webhook or identity evidence; assess whether a new AKS feature changes the certificate operating model. Do not replace cert-manager because a feature appeared upstream without an AKS support and migration decision. |
| **external-dns** | Controller Ready; sync errors remain within baseline; a disposable test record is created/updated and resolves through the intended DNS path; ownership and cleanup are verified. | Correlate DNS, workload identity, Azure API and ingress changes; draft a narrowly scoped fix or test gap. |
| **Istio ingress and meshed applications** | Representative HTTP/gRPC/TLS and mTLS routes pass; old/new proxy versions are counted; gateway health, 5xx, latency and authorization behavior remain in threshold; application readiness/PDBs pass. | Compare telemetry across revisions, identify a likely config or proxy issue and identify which workloads still need reinjection. |
| **Shared platform services** (for example External Secrets, CSI, Kyverno, Alloy, Flux) | Selected controller readiness, API compatibility, reconciliation and one end-to-end functional probe per critical service. | Map release-note changes to the installed versions and nominate targeted tests rather than claiming all add-ons are affected. |

The repo already has an [Istio system diagnostic agent](../../../agents/kagent-triage/aks/istio-system-agent.yaml), a [cert-manager diagnostic agent](../../../agents/kagent-triage/cert-manager-agent.yaml), [worker-cluster namespace coverage](../../../agents/kagent-triage/aks/README-WORKER-CLUSTER.md), and an [evidence-first triage pattern](../../../work-agent-bundles/evidence-first-worker-triage/README.md). These are useful starting points for **read-only analysis**, not proof of an upgrade integration. Reuse or narrow their tools and output contracts; do not turn a namespace triage agent into a general deployment principal.

## A release brief the agent can actually produce

The brief should be generated for an exact proposed version pair and source snapshot, then reviewed before publication. Suggested sections:

1. **Current → target:** AKS control plane, each node pool/OS image, Istio add-on revision and proxy patch; region/tier and support status.
2. **What changed:** separate AKS release changes, upstream Kubernetes changes, Microsoft-managed Istio add-on changes and upstream Istio changes; label each as supported, unsupported, preview, or not yet verified for this estate.
3. **What it means here:** affected ARM fields, policies, network/identity, Istio resources, cert-manager, external-dns and a few representative application paths.
4. **Action and evidence:** mandatory upgrade work, candidate features to pilot, tests, rollback constraints, owners and links to source documents and canary results.
5. **Customer-facing summary:** concise benefits and required customer action, only after the platform owner verifies applicability and wording. Publish through the existing documentation review path.

This makes feature review part of each AKS minor upgrade instead of a separate optional activity, matching the [existing team proposal](azure-container-linux-acl/TEAM-MESSAGE.md). A release note is a draft until the exact feature is verified in the supported AKS/add-on version and, where relevant, exercised in a representative environment.

## Minimal integration contract

Start with one canary cluster and one chosen AKS/Istio pair. The release job should create a bounded, redacted input artifact containing: target versions and region, source URLs plus retrieval time, template commit and what-if summary, installed add-on inventory, relevant baseline metrics, fixed test results, and links to raw evidence. The agent returns structured findings with `claim`, `source/evidence`, `confidence`, `affected_component`, `recommended_action`, and `unknowns`. Record the agent/model/tool versions, invocation ID, source snapshot and human disposition with the upgrade change record.

For a pilot, measure whether the agent finds actionable gaps the existing checklist misses, the time it saves in release research and incident analysis, citation accuracy, false alarms, and operator acceptance of the drafted notes. Score against a few past upgrade records plus one live non-production canary. Do not claim upgrade safety or productivity from a generated narrative alone.

**Permission boundary:** source-reading and telemetry tools only for analysis; redact logs and template inputs; no secrets in prompts or this public repo. The agent can propose a PR or workflow request after review. ARM deployments, Istio revision changes, namespace relabels, restarts and rollbacks run under the existing approved pipeline/workflow identity. Promotion uses fixed gates and named human approval where required. The same boundary is documented in the repo's [evidence-first triage pattern](../../../work-agent-bundles/evidence-first-worker-triage/README.md) and [target delivery architecture](../../../STATEMENT-OF-WORK.md).

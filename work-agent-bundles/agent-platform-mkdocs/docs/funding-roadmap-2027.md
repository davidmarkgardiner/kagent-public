# Proposed AKS agent platform funding roadmap

This appendix sets out potential work for a funding discussion from January to September 2027. It builds on the existing agent platform and recent Sentinel and Lookout work. It is a proposal, not an approved delivery plan or a claim that a workplace deployment is live. The [delivery roadmap](roadmap.md) remains the maintained record of milestone states and evidence.

**Effort** is an initial, high-level estimate in person-weeks for engineering and testing. The 18 ranges sum to 49–68 person-weeks, including continuation of existing roadmap work; this is not an additional headcount requirement. The ranges are not bottom-up estimates and exclude contingency, leave, coordination, security and data reviews, environment setup, ongoing support, model usage and infrastructure costs. Validate the scope, staffing, costs and dependencies with the team before using them as a funding commitment. Two activities per month make 18 items across nine months.

This is a funding discussion view of potential continuation and extension, not a replacement for the existing January–March delivery calendar. Several activities overlap with existing evaluation, registry, triage and other milestones; reconcile their scope and estimates with the [delivery roadmap](roadmap.md) before adding budgets. The ASO work includes platform engineering with agent assistance.

## January

- **Sentinel workplace pilot — 3–4 person-weeks.** Validate scheduled application and cluster health checks in an agreed environment, including investigation of failed checks and missing reports. Agree evaluation cases and a baseline for useful findings and false positives alongside the existing evaluation work.
- **SRE maturity assessment — 2–3 person-weeks.** Map DICE Run maturity criteria and SRE processes to current incident, alerting and operational practices; identify workflows where agents can reduce manual effort.

## February

- **Lookout security review pilot — 3–4 person-weeks.** Trial advisory merge-request reviews for agreed platform repositories, measuring useful findings and review overhead. Engineers retain approval and merge decisions.
- **Agent evaluation and registry — 3–4 person-weeks.** Continue the owner-confirmed work already underway: agree thresholds, record representative test results, complete registration metadata and prove authorised discovery and use.

## March

- **Policy deviation scanner — 3–4 person-weeks.** Compare selected AKS and Azure configurations against agreed baselines, identify approved exceptions and produce evidence-backed findings for platform owners.
- **ITIL change assistance — 2–3 person-weeks.** Prepare change records with affected services, risk, dependencies, test results and recovery steps for review through the existing change process.

## April

- **CVE investigation agent — 3–4 person-weeks.** Correlate existing vulnerability findings with deployed images and workloads; prioritise affected services and propose fixes for security and application owners.
- **Capacity and upgrade readiness — 2–3 person-weeks.** Report utilisation, quota constraints, node-pool headroom and potential upgrade blockers, with recommendations for SRE review.

## May

- **Azure Service Operator migration assessment — 3–4 person-weeks.** Inventory the ARM-managed AKS platform, map resources and dependencies to a selected ASO version, and identify ownership, capability and migration gaps.
- **ASO non-production proof of concept — 3–5 person-weeks.** Prepare and test a narrowly scoped resource migration, including reconciliation, access, drift, deletion behaviour and recovery. Agree a single management owner for each resource before handover. The estimate depends on an accessible target and needs detailed sizing; owners decide whether to proceed after reviewing the results.

## June

- **Agent-assisted cluster upgrades — 3–4 person-weeks.** Prepare readiness reports and proposed changes; test compatibility, disruption budgets and capacity in non-production, then collect rollout evidence where authorised.
- **Sentinel fleet expansion — 3–4 person-weeks.** Subject to pilot evaluation and owner approval, extend agreed checks to additional applications or clusters, with inventory, reporting freshness and investigation of missing reports.

## July

- **Audit evidence collection — 3–4 person-weeks.** Assemble dated evidence for a small, agreed set of compliance controls, linking findings, exceptions and ownership; confirm with internal audit which evidence is acceptable.
- **ServiceNow incident workflow — 3–4 person-weeks.** Subject to the earlier incident queue contract and triage work, evaluate a later expansion to additional agreed cases, producing evidence-backed investigation summaries and suggested next steps for SRE review.

## August

- **Red-team and security assurance support — 2–3 person-weeks.** Help authorised teams collect in-scope evidence, track findings and verify remediation; agree scope and handling of sensitive results first.
- **ASO ongoing maintenance — 3–4 person-weeks.** If the ASO proof and subsequent adoption are approved, pilot agent-assisted review of configuration changes, reconciliation failures and drift; prepare changes for the established GitOps and change process. Otherwise, use the review to decide the next non-production experiment.

## September

- **New AKS feature evaluation — 3–4 person-weeks.** Assess selected new features, prepare repeatable non-production tests and produce an adoption recommendation with compatibility, operational and security evidence.
- **Scale and funding review — 2–3 person-weeks.** Review pilot outcomes, adoption, time saved, finding quality and operating costs; recommend which workflows to expand, improve or stop.

## Boundaries and dependencies

Sentinel and Lookout have lab and prototype work to build on; proposed pilots still require workplace validation. At the last roadmap review, the execution policy boundary and runtime validation were blocked. Dependent work and dates require those gates, target access, identity, security review, service ownership and change approvals to be resolved. Confirm accountable roles and measurable success or stop criteria before starting each item. Agent recommendations do not grant permission to deploy, merge, upgrade or remediate. Use receiving-system evidence when claiming outcomes; keep populated workplace details and receipts private.

Before sending source code, vulnerability information or audit and red-team material to a model, agree classification, provider approval, access, retention and the evidence-handling approach with the relevant owners.

ASO manages Azure resources through Kubernetes tooling, but its supported resource versions, permissions and reconciliation behaviour must be verified for the selected implementation. Test adoption and deletion behaviour before transferring ownership. AKS upgrades should be tested against workloads and disruption settings before production. See [Azure Service Operator](https://azure.github.io/azure-service-operator/), [ASO reconciliation failures](https://azure.github.io/azure-service-operator/guide/diagnosing-problems/reconciliation-failures/) and [AKS upgrade guidance](https://learn.microsoft.com/en-us/azure/aks/upgrade-options).

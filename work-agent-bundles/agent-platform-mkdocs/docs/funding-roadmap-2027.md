# Proposed AKS agent platform funding roadmap

This appendix sets out potential work for a funding discussion from January to September 2027. It builds on the existing agent platform and recent Sentinel and Lookout work. It is a proposal, not an approved delivery plan or a claim that a workplace deployment is live. The [delivery roadmap](roadmap.md) remains the maintained record of milestone states and evidence.

**Effort** is an initial, high-level estimate in person-weeks for engineering and testing. The 18 ranges sum to 49–68 person-weeks, including continuation of existing roadmap work; this is not an additional headcount requirement. The ranges are not bottom-up estimates and exclude contingency, leave, coordination, security and data reviews, environment setup, ongoing support, model usage and infrastructure costs. Validate the scope, staffing, costs and dependencies with the team before using them as a funding commitment. Two activities per month make 18 items across nine months.

This is a funding discussion view of potential continuation and extension, not a replacement for the existing January–March delivery calendar. Several activities overlap with existing evaluation, registry, triage and other milestones; reconcile their scope and estimates with the [delivery roadmap](roadmap.md) before adding budgets. The ASO work includes platform engineering with agent assistance.

## What the team will build and why it matters

The proposal funds platform, SRE, security and integration specialists to build and improve agent-assisted services around the processes the department already owns. People define the problem, trusted sources, permissions, evaluation cases and escalation rules. They review the output, make operational decisions and improve the service using feedback. Agents perform bounded investigation and preparation so staff can spend more time resolving issues and improving the platform.

The intended pattern uses kagent for specialist agents and approved tools; agentgateway for controlled access to agents and tools; and the platform's chosen runtime, including Substrate where approved and validated, for execution. MCP tools connect agents to explicitly authorised information and services. These are design intentions: each integration, identity and runtime capability needs verification in the receiving environment.

A typical workflow is: **an existing event or request → an approved trigger → a bounded agent investigation → evidence and a recommendation → the existing human review or change process → a recorded outcome**. Deterministic checks should detect conditions where appropriate; the agent adds context and investigation. The workflow must handle missing data, tool failures and uncertainty, and should identify the source and time of evidence. Draft updates only reach ServiceNow, GitLab or another system through an approved integration with scoped permissions.

For a funding discussion, the following detail describes what staff could build and how it would fit into each process. All examples are proposals, and their effort is included in the corresponding monthly bullet rather than an additional estimate.

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

## How the proposed work fits existing processes

### January

- **Sentinel workplace pilot:** SREs choose health signals, thresholds, test scenarios and escalation routes. Engineers configure scheduled checks and a read-only kagent investigator to gather relevant Kubernetes and observability evidence when a check fails or a report is missing. The result goes to the existing alert or incident workflow for an SRE to validate; compare detection time, useful findings and false positives with the current process.
- **SRE maturity assessment:** SRE and DICE Run owners supply their agreed maturity criteria and process evidence. The team builds an assessment workflow that gathers approved evidence and drafts a gap analysis with references; owners validate the gaps, priorities and improvements in their existing service review. Missing evidence is reported as unknown, not scored as a failure.

### February

- **Lookout security review pilot:** Security and platform engineers define review rules and known-good and known-bad examples. A merge-request pipeline can pass a change reference to a kagent reviewer through the approved gateway; scoped tools retrieve the change and present an advisory finding to the existing reviewer. The person validates findings and decides whether to merge. Measure findings caught, false positives and review time.
- **Agent evaluation and registry:** Agent owners and consumers define test cases, expected behaviour and access requirements. Engineers extend the existing evaluation and registration work so each agent, tool or skill has a version, owner, intended scope and supporting test results. The existing publication and onboarding process controls which entries are discoverable and usable; a consuming team confirms it can find and use an approved capability.

### March

- **Policy deviation scanner:** Policy owners select controls, approved exceptions and severity. Engineers build scheduled read-only checks against Azure and Kubernetes state, with an agent explaining the affected resource and available evidence. Findings enter the established compliance review or ticket workflow after deduplication; a human confirms exceptions and approves remediation. Measure coverage and validated deviations.
- **ITIL change assistance:** Change and SRE owners define the fields, sources and acceptance criteria for a useful change record. A kagent workflow assembles a draft from an approved change request, affected services, test evidence and runbooks, flagging missing information and uncertainty. The requester and change authority review and approve it in the existing process; measure completeness and preparation time.

### April

- **CVE investigation agent:** Security owners choose trusted scanner inputs, risk criteria and handling rules. Engineers connect a scoped agent to approved vulnerability findings and workload inventory so it can identify affected deployments, summarise exposure and suggest supported fixes. Findings feed the existing vulnerability or incident workflow for an owner to assess; a receiving scan or other independent evidence verifies an approved fix.
- **Capacity and upgrade readiness:** Platform engineers define the clusters, metrics, quotas and time windows to examine. A scheduled agent-assisted report combines approved utilisation and quota evidence with upgrade readiness checks and highlights gaps or capacity risks. SREs use it in capacity planning and upgrade review; measure lead time and whether reported risks were actionable.

### May

- **Azure Service Operator migration assessment:** Platform engineers own the ARM inventory and migration decisions. They build an agent-assisted mapping from current resources to the selected ASO schemas, supported properties and dependencies, producing a reviewable gap and ownership report. The existing architecture and change reviews decide which resources, if any, move forward; unsupported or uncertain mappings require manual investigation.
- **ASO non-production proof of concept:** Engineers implement a small, representative ASO configuration and tests in an approved non-production environment. An agent can inspect status and reconcile failures, compare desired and actual state and summarise evidence for reviewers. Platform and security owners judge adoption, ownership, access, drift, deletion and recovery before a go/no-go decision; the agent does not transfer ownership by itself.

### June

- **Agent-assisted cluster upgrades:** Platform and application owners specify versions, workloads, maintenance windows and acceptance criteria. An agent gathers compatibility, deprecated API, disruption budget and capacity evidence and prepares a change proposal; an approved pipeline runs non-production tests. The existing change process authorises any rollout, with people and monitoring reviewing health and recording the outcome. Measure preparation time and test coverage.
- **Sentinel fleet expansion:** Following the pilot, SREs choose additional teams and set ownership and alert thresholds. Engineers extend the check and investigation templates, expected inventory and reporting-freshness monitoring. Findings and missing reports enter each team's existing support workflow; owners compare signal quality and adoption before further expansion.

### July

- **Audit evidence collection:** Control owners and internal audit agree the control scope, provenance, retention and acceptable evidence. Engineers build a read-only collection workflow that assembles dated configuration, approval and execution records with source references and gaps. People validate the evidence and submit it through the existing audit process; assess completeness and preparation effort without claiming automated audit sign-off.
- **ServiceNow incident workflow:** SRE and ServiceNow owners agree eligible incidents, data handling and ticket permissions. Engineers extend the existing integration so a qualifying incident can trigger a bounded investigation and return a cited summary and recommended checks to the agreed review point. An SRE decides the next action; any ticket update requires the approved identity and receiving-system read-back. Measure triage quality and time to useful context.

### August

- **Red-team and security assurance support:** Security and red-team owners set the authorised scope and handling rules. Engineers provide agents with limited access to approved evidence and a workflow to organise findings and track remediation verification. The authorised team conducts and judges the assessment; findings flow into its existing remediation process, and sensitive material remains within approved boundaries.
- **ASO ongoing maintenance:** If adoption is approved, platform engineers define the managed resource scope and operating runbooks. An agent reviews ASO conditions, drift and reconciliation errors, gathers related evidence and drafts a proposed GitOps change or escalation. Engineers review changes in the existing repository and change process; monitor resolution time and recurring failure patterns. If adoption does not proceed, use the time for an agreed non-production experiment.

### September

- **New AKS feature evaluation:** Platform and service owners select a feature and agree success criteria. Engineers prepare a repeatable non-production test; an agent gathers release and configuration evidence, assists investigation of results and drafts a compatibility and operations assessment. Architecture, security and service owners decide whether to adopt through the existing process; the test evidence remains available for that decision.
- **Scale and funding review:** The team brings pilot metrics, support costs, user feedback and known limitations to platform and service owners. An agent can assemble a referenced summary, but people validate the figures, decide which services to continue and set the next funding and ownership plan. Compare against baselines agreed before the pilots and include unsuccessful or inconclusive results.

## Boundaries and dependencies

Sentinel and Lookout have lab and prototype work to build on; proposed pilots still require workplace validation. At the last roadmap review, the execution policy boundary and runtime validation were blocked. Dependent work and dates require those gates, target access, identity, security review, service ownership and change approvals to be resolved. Confirm accountable roles and measurable success or stop criteria before starting each item. Agent recommendations do not grant permission to deploy, merge, upgrade or remediate. Use receiving-system evidence when claiming outcomes; keep populated workplace details and receipts private.

Before sending source code, vulnerability information or audit and red-team material to a model, agree classification, provider approval, access, retention and the evidence-handling approach with the relevant owners.

ASO manages Azure resources through Kubernetes tooling, but its supported resource versions, permissions and reconciliation behaviour must be verified for the selected implementation. Test adoption and deletion behaviour before transferring ownership. AKS upgrades should be tested against workloads and disruption settings before production. See [Azure Service Operator](https://azure.github.io/azure-service-operator/), [ASO reconciliation failures](https://azure.github.io/azure-service-operator/guide/diagnosing-problems/reconciliation-failures/) and [AKS upgrade guidance](https://learn.microsoft.com/en-us/azure/aks/upgrade-options).

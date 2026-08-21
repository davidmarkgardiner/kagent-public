# kagent-public

Platform engineering monorepo — GitOps-first delivery, fleet automation, and AI-driven SRE on Azure Kubernetes Service.

This is the primary working repo for a six-month platform modernisation programme targeting declarative AKS fleet management, Argo-based orchestration, and AI-driven SRE via kagent.

---

## What is this?

A complete platform stack for production Kubernetes on Azure:

- **KRO + ASO** — declarative AKS cluster lifecycle; replace ARM templates with GitOps PRs
- **Flux CD** — single reconciliation plane across management + worker clusters
- **Argo Workflows + Argo Events** — namespace onboarding, cluster provisioning, fleet updates, AI-driven triage
- **kagent** — CNCF Sandbox AI agent framework ([upstream](https://github.com/kagent-dev/kagent))
- **agentgateway** — unified LLM + MCP + A2A routing ([upstream](https://github.com/agentgateway/agentgateway))
- **AKS-MCP** — kubectl/az access via Model Context Protocol ([upstream](https://github.com/Azure/aks-mcp))

---

## Kagent v2 TL;DR

The first iteration was a basic specialist agent focused on namespace-level triage. This iteration evolves it into a connected AI SRE system with triage, evidence gathering, remediation planning, governance, and evaluation.

- **Moved beyond a single namespace triage agent** — v1 could inspect and reason about one area; v2 coordinates multiple connected specialists.
- **Smart triage fan-out** — incidents can be routed across Kubernetes, networking, Grafana/observability, and GitOps/remediation specialists.
- **Grafana integration** — read-only Grafana MCP patterns and evidence-agent contracts are defined; work-side proof must use approved live Grafana datasources.
- **GitLab MCP integration** — sandbox branch/MR/comment patterns are documented; work use requires a dedicated sandbox project and scoped token before any write-capable tool is exposed.
- **Human-in-the-loop control** — approval and GitOps governance are part of the target path; public demos may synthesize approval markers unless the evidence file shows a real suspend/resume identity.
- **Agent-to-agent workflows** — A2A patterns let agents collaborate, hand off context, and combine specialist findings into one incident summary.
- **Chaos-driven validation** — lower-env pod-delete injection and lifecycle eval are proven; chaos-triggered specialist fan-out is currently a skeleton/marker contract until wired to live backends.
- **Evaluation layer** — agent output can be scored for evidence quality, correctness, safety, and remediation usefulness.
- **Workplace lift-and-shift package** — work-specific endpoints, secrets, namespaces, GitLab/Grafana config, and cluster details are parameterized with placeholders.
- **Stakeholder demo assets** — HTML visualizations and runbooks explain the architecture and provide copyable proof commands for demos.

Bottom line: v2 turns the original single-purpose triage agent into the foundation for a connected, observability-aware, GitOps-aware, human-governed, testable AI SRE system.

---

## AI capabilities and productivity measures

The triage system uses AI to convert operational signals into an evidence-backed,
human-governed response. It does not autonomously change production: any
non-read-only action must use an approved workflow or GitOps path and pass a
human approval gate.

| Capability | What it contributes | Measure of value |
|---|---|---|
| Signal triage and classification | Interprets alerts, logs, events, impact, and likely cause. | Time to first useful analysis; routing correctness; low-value ticket rate. |
| Specialist orchestration | Calls Kubernetes, network, Grafana, knowledge, or evaluation specialists when relevant. | Human handoffs avoided; specialist-call success rate; time to the right resolver group. |
| Evidence gathering and correlation | Collects Kubernetes/AKS facts and correlates metrics, logs, traces, dashboards, and events. | Evidence-pack completeness; manual commands/searches avoided; mean time to diagnose. |
| Knowledge-base lookup | Retrieves cited runbooks and platform guidance; records stale or missing documentation gaps. | Runbook-search time; cited-answer rate; documentation-gap closure time. |
| Remediation planning | Produces a bounded recommendation with risk, rollback, and verification steps. | Time to reviewable plan; plan acceptance/rejection rate; unsafe-plan rate. |
| HITL and GitOps handoff | Pauses for approval, then submits work through controlled workflows, tickets, or pull requests. | Approval turnaround; valid approval evidence; time from approval to review-ready change. |
| Evaluation and feedback | Scores evidence, safety, completeness, and correctness; captures human corrections. | Evaluation pass/score trend; override rate; post-PASS correction rate. |
| Continuous improvement | Feeds incident and documentation gaps back into reviewed knowledge updates. | Repeat-incident reduction; manual steps saved; avoided escalations. |

Track the value loop using equivalent incidents: compare baseline versus
agent-assisted **time to analyse**, **time to remediate**, **human touches**,
**evidence quality**, **routing/tool accuracy**, and **repeat-incident rate**.
Do not claim productivity from a single demonstration; report the measured trend
and the associated human review outcome.

---

## Repository Layout

```
infra/              KRO + ASO cluster provisioning, workload identity, BYO-kagent platform
platform/           Argo Workflows templates, Argo Events sources/sensors, agentgateway, HITL
observability/      Alloy → EventHub pipeline, LGTM stack, AlertManager → Argo Events
agents/             kagent Agent CRs, sensors, skills — organised by agent purpose
a2a/                A2A protocol memory reference + call examples
docs/               Architecture diagrams, runbooks, handover notes
examples/           Quickstart and sample payloads
```

---

## Quick Navigation

| I want to… | Go to |
|---|---|
| See every showcase demo in one place | [`DEMOS.md`](DEMOS.md) |
| Use the Kagent v2 work-agent bundle catalogue | [`work-agent-bundles/`](work-agent-bundles/README.md) |
| Explain the Kagent platform value story to stakeholders | [`WORK-KAGENT-VALUE-STORY-ONE-PAGER.md`](WORK-KAGENT-VALUE-STORY-ONE-PAGER.md) |
| Present the Kagent v2 stakeholder demo | [`WORK-STAKEHOLDER-DEMO-RUNBOOK.html`](WORK-STAKEHOLDER-DEMO-RUNBOOK.html) |
| Compare worker-local vs management-cluster triage (blast-radius briefing) | [`WORK-KAGENT-TRIAGE-DEPLOYMENT-MODELS.html`](WORK-KAGENT-TRIAGE-DEPLOYMENT-MODELS.html) |
| Review the evidence-first worker-to-management triage decision | [`WORK-WORKER-TO-MANAGEMENT-EVIDENCE-TRIAGE.html`](WORK-WORKER-TO-MANAGEMENT-EVIDENCE-TRIAGE.html) |
| Ask Fable to critique the future office replication design | [`docs/observability/FABLE-WORKER-TO-MANAGEMENT-TRIAGE-CRITIQUE-PROMPT.md`](docs/observability/FABLE-WORKER-TO-MANAGEMENT-TRIAGE-CRITIQUE-PROMPT.md) |
| Start the Kagent triage v2 handoff | [`WORK-KAGENT-TRIAGE-V2-FRONT-SHEET.md`](WORK-KAGENT-TRIAGE-V2-FRONT-SHEET.md) |
| Hand a start prompt to the work agent | [`WORK-KAGENT-TRIAGE-V2-WORK-AGENT-START-PROMPT.md`](WORK-KAGENT-TRIAGE-V2-WORK-AGENT-START-PROMPT.md) |
| Run the local handoff verifier | [`scripts/verify-kagent-triage-v2-handoff.sh`](scripts/verify-kagent-triage-v2-handoff.sh) |
| Review current Kagent triage system v2 status | [`WORK-KAGENT-TRIAGE-V2-REVIEW-PROMPT.md`](WORK-KAGENT-TRIAGE-V2-REVIEW-PROMPT.md) |
| Tick off the work implementation checklist | [`WORK-KAGENT-TRIAGE-V2-WORK-IMPLEMENTATION-CHECKLIST.html`](WORK-KAGENT-TRIAGE-V2-WORK-IMPLEMENTATION-CHECKLIST.html) |
| Measure Copilot Agent usage on small tasks | [`docs/copilot-usage-smoke-test/`](docs/copilot-usage-smoke-test/README.md) |
| Check Kagent triage v2 completion gates | [`WORK-KAGENT-TRIAGE-V2-COMPLETION-CHECKLIST.md`](WORK-KAGENT-TRIAGE-V2-COMPLETION-CHECKLIST.md) |
| See the latest Kagent triage v2 verification pass | [`WORK-KAGENT-TRIAGE-V2-VERIFICATION-PASS.md`](WORK-KAGENT-TRIAGE-V2-VERIFICATION-PASS.md) |
| Review the current kagent/agentgateway release baseline | [`docs/platform-kb/agents/kagent-agentgateway-release-review-2026-06-30.md`](docs/platform-kb/agents/kagent-agentgateway-release-review-2026-06-30.md) |
| Pick up the Hermes AgentHarness proof tomorrow | [`docs/platform-kb/agents/agentharness-hermes-next-steps.md`](docs/platform-kb/agents/agentharness-hermes-next-steps.md) |
| Follow the SRE operating guide for chaos and BYO-agent workflows | [`WORK-KAGENT-TRIAGE-V2-SRE-OPERATING-GUIDE.md`](WORK-KAGENT-TRIAGE-V2-SRE-OPERATING-GUIDE.md) |
| Walk through first-time ASTHERI/SRE onboarding | [`WORK-KAGENT-TRIAGE-V2-ASTHERI-SRE-WALKTHROUGH.md`](WORK-KAGENT-TRIAGE-V2-ASTHERI-SRE-WALKTHROUGH.md) |
| Review the ASTHERI/SRE rehearsal findings | [`WORK-KAGENT-TRIAGE-V2-ASTHERI-SRE-REHEARSAL.md`](WORK-KAGENT-TRIAGE-V2-ASTHERI-SRE-REHEARSAL.md) |
| View the SRE workflow visualization | [`WORK-KAGENT-TRIAGE-V2-SRE-WORKFLOW.html`](WORK-KAGENT-TRIAGE-V2-SRE-WORKFLOW.html) |
| Run the first-time SRE onboarding demo | [`demos/sre-first-contact/`](demos/sre-first-contact/README.md) |
| View the first-contact SRE storyboard | [`WORK-KAGENT-TRIAGE-V2-SRE-FIRST-CONTACT.html`](WORK-KAGENT-TRIAGE-V2-SRE-FIRST-CONTACT.html) |
| Check the HITL proof status | [`WORK-KAGENT-TRIAGE-V2-HITL-PROOF.md`](WORK-KAGENT-TRIAGE-V2-HITL-PROOF.md) |
| Check the KB/querydoc proof status | [`WORK-KAGENT-TRIAGE-V2-KB-QUERYDOC-PROOF.md`](WORK-KAGENT-TRIAGE-V2-KB-QUERYDOC-PROOF.md) |
| Prove KB docs can be updated through GitLab MCP and retrieved through querydoc | [`demos/kb-gitlab-mcp-update/`](demos/kb-gitlab-mcp-update/README.md) |
| Demonstrate private code submissions evaluated in air-gapped GitLab | [`demos/gitlab-private-evaluation/`](demos/gitlab-private-evaluation/README.md) |
| View the Kagent triage v2 proof board | [`WORK-KAGENT-TRIAGE-V2-PROOF-BOARD.html`](WORK-KAGENT-TRIAGE-V2-PROOF-BOARD.html) |
| Follow the work-agent replication checklist | [`WORK-KAGENT-TRIAGE-V2-WORK-AGENT-CHECKLIST.md`](WORK-KAGENT-TRIAGE-V2-WORK-AGENT-CHECKLIST.md) |
| Hand this zip to a work agent for lift-and-shift | [`WORK-ZIP-AGENT-HANDOFF.md`](WORK-ZIP-AGENT-HANDOFF.md) |
| Replicate memory and knowledge-base features at work | [`WORK-MEMORY-KB-NEXT-HANDOFF-README.md`](WORK-MEMORY-KB-NEXT-HANDOFF-README.md) |
| Verify memory, doc2vec, and GitLab MCP evidence | [`WORK-MEMORY-KB-VERIFY-PROMPT.md`](WORK-MEMORY-KB-VERIFY-PROMPT.md) |
| Plan natural-language chaos test generation | [`WORK-CHAOS-TEST-MANAGER-PLANNING-PROMPT.md`](WORK-CHAOS-TEST-MANAGER-PLANNING-PROMPT.md) |
| Review the chaos test manager implementation plan | [`WORK-CHAOS-TEST-MANAGER-PLAN.md`](WORK-CHAOS-TEST-MANAGER-PLAN.md) |
| Build the chaos test manager skeleton | [`chaos/reliability/`](chaos/reliability/README.md) |
| View the Proxmox chaos live-run dashboard | [`observability/chaos-test-manager/chaos-test-lifecycle-live.html`](observability/chaos-test-manager/chaos-test-lifecycle-live.html) |
| Import the kagent fleet Grafana dashboard | [`observability/agent-evals/grafana/kagent-fleet-overview-dashboard.json`](observability/agent-evals/grafana/kagent-fleet-overview-dashboard.json) |
| Verify the work-side triage/remediation integration | [`WORK-TRIAGE-REMEDIATION-VERIFICATION-README.md`](WORK-TRIAGE-REMEDIATION-VERIFICATION-README.md) |
| See what changed recently | [`CHANGELOG.md`](CHANGELOG.md) |
| Provision a new AKS cluster declaratively | [`infra/kro-stack/`](infra/kro-stack/README.md) |
| Onboard a namespace via PR | [`platform/argo-workflows/templates/namespace-onboarding/`](platform/argo-workflows/templates/namespace-onboarding/) |
| Set up AI triage for a namespace | [`agents/kagent-triage/`](agents/kagent-triage/README.md) |
| Build and validate Kubernetes delivery YAML with read-only kagent specialists | [`work-agent-bundles/kubernetes-delivery-harness/`](work-agent-bundles/kubernetes-delivery-harness/README.md) |
| Try the K-Agent knowledge-base UI POC | [`agents/kagent-knowledge-ui/`](agents/kagent-knowledge-ui/README.md) |
| Wire K8s events → EventHub → AI diagnosis | [`observability/alloy-eventhub-pipeline/`](observability/alloy-eventhub-pipeline/) |
| Decide Alertmanager metric vs Alloy/Vector event-log routing into kagent | [`docs/observability/dual-source-kafka-triage-routing.md`](docs/observability/dual-source-kafka-triage-routing.md) |
| Translate Kafka portal producer/topic/consumer onboarding into the triage setup | [`docs/observability/work-confluent-onboarding-guide.md`](docs/observability/work-confluent-onboarding-guide.md) |
| Monitor kagent + agentgateway with Alloy/Grafana | [`docs/observability/k-agent-alloy-grafana.md`](docs/observability/k-agent-alloy-grafana.md) |
| Score whether agents are doing the right job | [`observability/agent-evals/`](observability/agent-evals/README.md) |
| Lift the agent eval pattern into another environment | [`KAGENT-EVAL-LIFT-AND-SHIFT-HANDOFF.md`](KAGENT-EVAL-LIFT-AND-SHIFT-HANDOFF.md) |
| Deploy the kagent + agentgateway observability bundle | [`docs/observability/k-agent-agentgateway-observability.md`](docs/observability/k-agent-agentgateway-observability.md) |
| Decide whether Alloy should use VPA auto mode | [`docs/observability/alloy-vpa/`](docs/observability/alloy-vpa/) |
| Test Grafana MCP with kagent observability | [`docs/observability/grafana-mcp-home-lab.md`](docs/observability/grafana-mcp-home-lab.md) |
| Adapt AI + Grafana triage ideas to this stack | [`docs/ai-grafana/README.md`](docs/ai-grafana/README.md) |
| Hand over the CAF-style Grafana/alerts/Argo flow | [`docs/observability/caf-style-observability-handoff.md`](docs/observability/caf-style-observability-handoff.md) |
| Sync managed Mimir/Loki rules from Kubernetes | [`observability/managed-lgtm-integration/rule-sync/`](observability/managed-lgtm-integration/rule-sync/README.md) |
| Deploy the AI gateway (LLM + MCP + A2A) | [`platform/agentgateway/`](platform/agentgateway/README.md) |
| Deploy LitmusChaos and watch kagent triage chaos events | [`chaos/litmus/WORK-INSTALL.md`](chaos/litmus/WORK-INSTALL.md) |
| Create a custom kagent tool | [`docs/kagent-custom-tools/`](docs/kagent-custom-tools/README.md) |
| Prepare Azure Policy exceptions for kagent/agentgateway | [`docs/security/azure-policy-exceptions.md`](docs/security/azure-policy-exceptions.md) |
| Run the Agentgateway MVP demo set | [`DEMOS.md#2-agentgateway-mvp-control-plane-demo-set`](DEMOS.md#2-agentgateway-mvp-control-plane-demo-set) |
| Add a HITL approval gate for remediation | [`platform/teams-hitl/`](platform/teams-hitl/README.md) |
| Bring Your Own Agent to the platform | [`infra/byo-kagent/`](infra/byo-kagent/README.md) |
| Run the BYO-agent showcase demo | [`demos/byo-agent-showcase/`](demos/byo-agent-showcase/README.md) |
| Understand A2A + kagent memory | [`a2a/`](a2a/README.md) |
| See the full programme scope | [`STATEMENT-OF-WORK.md`](STATEMENT-OF-WORK.md) |

---

## Prerequisites

- Kubernetes cluster (AKS or kind for local dev)
- [KRO](https://github.com/kubernetes-sigs/kro) on management cluster
- [Azure Service Operator v2](https://github.com/Azure/azure-service-operator) on management cluster
- [Argo Workflows v3.x](https://argoproj.github.io/argo-workflows/) in `argo` namespace
- [Argo Events](https://argoproj.github.io/argo-events/) in `argo-events` namespace — **pin chart 2.4.14 / app v1.9.5** (see [EventHub regression note](platform/argo-events/README.md#eventhub-version-pin))
- [kagent v0.9.10+](https://github.com/kagent-dev/kagent) in `kagent` namespace for the current stable baseline

---

## Validating manifests

Check that every Kubernetes manifest under `k8s/` is syntactically valid YAML (offline, no cluster or network access required):

```bash
scripts/lint-yaml.sh
```

Prints `OK <path>` or `FAIL <path>` per file and exits non-zero if any file fails to parse. Use the `--quiet` flag to print only failures and a final summary line.

For machine-readable output, use `--json`. The script then emits exactly one JSON object on stdout and nothing else, exiting non-zero if any file fails to parse:

```json
{"checked":7,"failed":0,"failures":[]}
```

`failures` is a JSON array of repo-relative paths (e.g. `k8s/observability/k-agent-alloy.yaml`) for files that failed to parse; it is empty on success. The `checked` and `failed` counts always agree with `failures.length`. Stderr is reserved for diagnostics (unknown options, missing directories) and stays empty on a successful run, so `--json` output is safe to pipe into `jq` or any other parser. `--json` and `--quiet` can be combined; per-file lines are suppressed either way and the JSON object is still emitted.

---

## Public Safety

Do not commit secrets, private hostnames, cluster IPs, connection strings, tokens, or internal URLs.
Use `{{PLACEHOLDER}}` tokens for all environment-specific values. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## Related

- [kagent upstream](https://github.com/kagent-dev/kagent)
- [agentgateway upstream](https://github.com/agentgateway/agentgateway)
- [Official upstream reference map](docs/upstreams.md)
- [A2A specification](https://a2aproject.org)
- [Argo Workflows docs](https://argoproj.github.io/argo-workflows/)
- [Argo Events docs](https://argoproj.github.io/argo-events/)
- [KRO docs](https://kro.run)
- [Azure Service Operator docs](https://azure.github.io/azure-service-operator/)

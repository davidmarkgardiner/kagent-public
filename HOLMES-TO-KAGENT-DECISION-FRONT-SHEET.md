# HolmesGPT to kagent Decision Front Sheet

Purpose: give management a concise explanation of why HolmesGPT was retired as
the default Kubernetes triage engine and why the platform standardised on
kagent.

## Executive answer

HolmesGPT was good at open-ended Kubernetes investigation, but that strength was
a poor fit for our most common requirement: take a known alert, collect the
minimum relevant evidence, produce a reliable diagnosis, and hand off a safe
next action.

In practice, Holmes could continue investigating beyond what a simple triage
task justified. This increased latency and token/context consumption and made
completion less predictable. The repository's original comparison recorded
kagent winning all five tests, completing triage in roughly 55 seconds versus
roughly 120 seconds for Holmes, and diagnosing consistently where Holmes was
confused by its shell/subshell context.

We therefore chose kagent as the default. It gave us bounded specialist agents,
structured Kubernetes tools, A2A orchestration, separate read and write paths,
and a foundation we could extend with Argo, agentgateway, GitOps, human approval,
evaluation, memory, knowledge retrieval, observability, and BYO agents.

The decision was not that Holmes was incapable. It was that kagent was the more
controllable and extensible platform for repeatable operational workflows.

## Decision comparison

| Decision factor | HolmesGPT | kagent | Why it mattered |
|---|---|---|---|
| Investigation style | Broad, autonomous investigation is useful for an unfamiliar incident, but can do more work than a routine alert needs. | Specialist prompts and explicit workflow stages bound the evidence-gathering task. | Routine triage needs a predictable answer, not an unlimited investigation. |
| Token and context use | Our operational experience was that long investigations could consume the token budget or context window before producing a dependable result. | Scope can be constrained by agent, tool grant, workflow step, timeout, model route, and output contract. | Lower and more predictable consumption improves completion rate and cost control. |
| Test result | Lost the recorded comparison 0–5. | Won the recorded comparison 5–0. | We selected the option that worked more consistently in our own tests. |
| Triage speed | Approximately 120 seconds in the recorded comparison. | Approximately 55 seconds in the recorded comparison. | Faster triage fits an alert-driven pipeline and reduces workflow timeout risk. |
| Kubernetes tool path | `call_kubectl` through a shell/subshell was recorded as fragile. | Native or structured MCP tools avoid much of the shell quoting and context ambiguity. | Tool reliability matters more than an impressive narrative when the diagnosis must be repeatable. |
| Diagnosis quality | Recorded as becoming confused by subshell context. | Recorded as diagnosing the comparison cases consistently. | A shorter, grounded diagnosis is more useful than a longer uncertain investigation. |
| Multi-agent orchestration | No A2A support in the original comparison. | A2A supports routing and specialist-to-specialist delegation. | We can use focused observability, network, policy, deployment, and incident agents instead of one universal investigator. |
| Safety model | A broad investigator is harder to fit into a narrowly permissioned automated path. | Read-only triage is separated from write-capable remediation; risky action can require HITL and GitOps review. | Alerts can trigger diagnosis automatically without also granting automatic repair authority. |
| Workflow integration | Primarily an investigation tool. | Fits Argo Events and Workflows, GitLab, Teams, Flux/GitOps, evaluation, and reporting. | Triage is one stage of an operational lifecycle, not the whole lifecycle. |
| Model and cost control | Investigation behaviour and model use were less aligned with our platform control plane. | agentgateway provides model routing, fallback, usage telemetry, and per-task model choice. | We can match model capability and cost to the task instead of treating every alert as deep research. |
| Platform reuse | Strongest as a Kubernetes troubleshooting specialist. | Supports SRE triage plus remediation planning, BYO agents, knowledge workflows, security, compliance, and other business use cases. | The investment produces a reusable agent platform rather than a single-purpose bot. |

## HolmesGPT: pros and cons

### Pros

- Purpose-built for Kubernetes troubleshooting and useful for unfamiliar,
  ambiguous incidents.
- Its broad investigative behaviour can uncover evidence that a narrowly scoped
  workflow was not explicitly told to collect.
- Stable enough to remain a possible on-demand second-opinion or deep-RCA tool.
- Helped prove the original alert-to-investigation concept before the wider
  platform architecture existed.

### Cons for our use case

- Frequently too investigative for a simple, high-volume triage task.
- Operationally token-hungry; long tool loops could exhaust token or context
  limits and fail to return a useful answer.
- Slower in the recorded comparison: about 120 seconds versus about 55 seconds.
- Fragile shell/subshell Kubernetes tool path reduced diagnostic reliability.
- No A2A support for the specialist fan-out model we wanted.
- Harder to turn into a bounded detect → diagnose → approve → remediate → verify
  lifecycle.

## kagent: pros and cons

### Pros

- Bounded domain and namespace specialists instead of one generic investigator.
- Structured native/MCP tool calls with explicit tool grants.
- Read-only triage agents separated from remediation agents and workflow service
  accounts.
- A2A routing and smart fan-out to the right specialists.
- Argo orchestration for deterministic steps, retries, timeouts, approval, and
  evidence capture.
- HITL and GitOps paths for changes rather than unrestricted direct mutation.
- agentgateway model routing, fallback, token telemetry, and cost attribution.
- Repeatable evaluation, chaos/regression cases, recovery verification, and
  dashboard/report outputs.
- Extensible to Grafana evidence, knowledge retrieval, memory, GitLab workflows,
  ServiceNow escalation, and team-owned BYO agents.

### Trade-offs

- kagent is a platform, so we own more integration, policy, testing, and
  operational engineering than with a single packaged investigator.
- Governance, HITL, evaluation, and GitOps controls must be deliberately wired
  and proven; they are not automatic merely because an Agent resource exists.
- Results remain model-dependent. Smaller models may be suitable for bounded
  single-step triage but unreliable for multi-step orchestration.
- kagent does not eliminate token runaway by itself; prompts, tool grants,
  workflow deadlines, output limits, gateway budgets, and telemetry still need
  to enforce the boundary.
- Some capabilities have stronger home-lab evidence than work-environment
  evidence and must not be presented as production-proven until replicated.

## Recommended management wording

> We moved away from HolmesGPT as the default because it behaved like a deep
> investigator when most alerts needed bounded, repeatable triage. It was
> slower, its Kubernetes shell-tool path was less reliable in our tests, and its
> longer investigations could consume the token or context budget before
> completing. kagent won our comparison tests and gave us a composable platform:
> focused read-only specialists, structured tools, A2A routing, workflow and
> human-approval gates, model/cost controls, evaluation, and GitOps-safe
> remediation. Holmes may still have value for a deliberately invoked deep RCA,
> but kagent is the better default control plane.

## Evidence and qualification

- [`observability/PRODUCTION-READINESS.md`](observability/PRODUCTION-READINESS.md)
  records the original 5–0 comparison, approximate timings, tool-path findings,
  diagnosis result, A2A difference, and planned Holmes decommission decision.
- [`WORK-KAGENT-TRIAGE-V2-FRONT-SHEET.md`](WORK-KAGENT-TRIAGE-V2-FRONT-SHEET.md)
  records the later specialist fan-out, HITL, evaluation, knowledge, memory,
  chaos, and BYO-agent direction, including what remains to be proven at work.
- [`WORK-KAGENT-VALUE-STORY-ONE-PAGER.md`](WORK-KAGENT-VALUE-STORY-ONE-PAGER.md)
  records the broader operational value and measurable outcomes expected from
  the agentic harness.
- [`observability/prometheus-alertmanager/KAGENT-ALERT-TRIAGE-ARCHITECTURE.md`](observability/prometheus-alertmanager/KAGENT-ALERT-TRIAGE-ARCHITECTURE.md)
  records the read-only triage/write remediation separation, A2A route,
  agentgateway, and structured AKS-MCP tool path.

The token/context-exhaustion point is an operational recollection from the
original Holmes trials. The current public repository preserves the comparative
latency and reliability result, but not a per-run Holmes token benchmark. It
should therefore be described as observed behaviour rather than a measured cost
claim unless the original telemetry is recovered.

# Offline and Online Agent Evaluation Design

## TLDR

Offline and online evaluation are not the same as non-prod and prod.

```text
offline eval = evaluate captured, synthetic, or replayed runs outside the live path
online eval  = evaluate a real workflow run during or immediately after execution
```

Non-prod and prod are environments. Offline and online are evaluation modes.

The intended platform model is:

| Mode | Where it usually starts | What it proves |
| --- | --- | --- |
| Offline eval | CI, dev, staging, sanitized replay | The agent/prompt/tooling still meets known golden cases before promotion. |
| Online eval | dev/staging first, then prod audit/gate | A real incident workflow did the right thing end to end. |

## Definitions

### Offline Evaluation

Offline evaluation scores agent behavior without sitting in the live workflow
path. Inputs are captured or synthetic:

- golden cases
- sample run JSON
- sanitized Argo Workflow exports
- replayed traces
- previously captured incident evidence

Offline eval is useful for:

- prompt regression testing
- tool-permission regression testing
- model/provider comparison
- CI checks before an agent is promoted
- replaying sanitized production incidents safely
- proving known failure modes still score correctly

Offline eval should fail a promotion, not a live incident.

### Online Evaluation

Online evaluation scores a real workflow run as part of the runtime operating
loop. Inputs are created by the actual incident workflow:

- alert payload
- A2A specialist outputs
- incident commander synthesis
- HITL decision
- remediation workflow result
- verification evidence
- GitLab ticket update result
- workflow duration and trace metadata

Online eval is useful for:

- runtime audit
- ticket close gates
- production score dashboards
- low-score alerts
- detecting agents that claim success without proof
- measuring drift, latency, and operational reliability

Online eval can be audit-only or gating. Start audit-only for lower-confidence
paths; gate high-risk write/remediation paths once the evidence contract is
stable.

## Relationship To Environments

| Environment | Offline eval | Online eval |
| --- | --- | --- |
| Local/dev | Run golden cases and samples while developing prompts/tools. | Optional workflow smoke test. |
| CI | Required for changed prompts, tools, cases, or scorers. | Usually not applicable unless CI runs Argo integration tests. |
| Non-prod/staging | Required before promotion. | Run on every incident simulation and chaos test. |
| Prod | Replay sanitized incidents offline for regression and learning. | Start audit-only; gate remediation/ticket closure after confidence. |

The important distinction:

```text
non-prod/prod = where the agent runs
offline/online = when the evaluation runs relative to that agent run
```

## Reference Architecture

```text
                 Offline Evaluation
                 ------------------
golden case + captured run
        |
        v
score-agent-run.py / score-lifecycle-run.py
        |
        +--> JSON report
        +--> Markdown report
        +--> Prometheus text metrics
        +--> CI/promotion verdict


                  Online Evaluation
                  -----------------
alert -> triage -> A2A fan-out -> HITL -> remediation -> verification -> ticket update
                                                                           |
                                                                           v
                                                            agent-lifecycle-eval Argo step
                                                                           |
                                                                           +--> score
                                                                           +--> hard gates
                                                                           +--> metrics/dashboard
                                                                           +--> allow/block ticket close
```

## Current Repo Implementation

### Offline Pieces

| File | Purpose |
| --- | --- |
| `cases/` | Golden single-agent scenarios. |
| `lifecycle-cases/` | Golden end-to-end incident lifecycle scenarios. |
| `results/sample/` | Public-safe sample runs and generated reports. |
| `scripts/score-agent-run.py` | Scores one captured agent run. |
| `scripts/run-agent-evals.py` | Batch-runs offline cases. |
| `scripts/score-lifecycle-run.py` | Scores one normalized lifecycle run. |
| `scripts/summarize-agent-scores.py` | Produces Markdown and Prometheus metrics. |

### Online Pieces

| File | Purpose |
| --- | --- |
| `argo/lifecycle-eval-workflow-template.yaml` | Reusable Argo post-run evaluator. |
| `kustomization.yaml` | Generates the ConfigMap-mounted runtime files. |
| `a2a/smart-triage-fanout-demo/workflow.yaml` | Demo workflow calls the lifecycle evaluator after proof markers. |
| `alerting/agent-eval-rules.yaml` | Alerts on low scores and hard failures. |
| `grafana/agent-eval-scorecard-dashboard.json` | Scorecard dashboard. |
| `grafana/kagent-fleet-overview-dashboard.json` | Fleet-level dashboard. |

## Evaluation Layers

### Layer 1: Deterministic Checks

These are the foundation and should run everywhere:

- required diagnosis terms
- required evidence terms
- required lifecycle steps
- required/forbidden tool calls
- expected namespace
- HITL before remediation
- verification before success
- ticket update before close
- public-safety leak checks

### Layer 2: Telemetry Checks

These run when telemetry is present:

- latency
- token count
- model/provider errors
- tool errors
- workflow duration
- retry rate

Missing telemetry should be marked `not_scored`, not guessed.

### Layer 3: Judge-Based Quality Checks

LLM-as-judge or frameworks such as DeepEval can be added later for subjective
quality:

- clarity
- completeness
- reasoning quality
- operator usefulness
- escalation quality

Judge-based checks should supplement deterministic gates, not replace them.

## Score and Gates

The normalized lifecycle score is stored from `0.0` to `1.0`.

Dashboard views may display it as `0` to `10`.

Hard gates fail regardless of score:

- remediation before HITL
- remediation without verification
- missing ticket update
- wrong namespace
- missing required agents
- forbidden write tool use
- public-safety leak

## Online Gating Policy

Recommended rollout:

| Workflow type | Initial online mode | Mature online mode |
| --- | --- | --- |
| read-only triage | audit-only | sampled audit |
| HITL recommendation | audit-only | 100 percent audit |
| remediation planning | audit-only | gate plan promotion |
| write-capable remediation | gate before ticket close | gate before ticket close |
| ticket-closing workflow | gate before close | gate before close |

## Open Design Decisions

- Whether production read-only triage should be sampled or scored every time.
- Whether low-score but non-hard-failure runs should block ticket close or only
  add a warning comment.
- How long raw run evidence should be retained before only the sanitized score
  report remains.
- Whether LLM-as-judge is required for promotion or only for periodic audit.
- Which system owns final metrics ingestion: Prometheus textfile collector,
  OTEL collector, workflow artifact import, or a dedicated eval exporter.

## Suggested Stakeholder Discussion Summary

Use this wording:

> We separate offline and online evaluation from environment. Offline eval is
> our replay and promotion path: golden cases, captured runs, synthetic
> incidents, and sanitized trace replay. Online eval is our runtime audit path:
> after an actual Argo/kagent incident workflow runs, we score whether A2A,
> HITL, remediation, verification, and GitLab update happened correctly. We
> start both in non-prod, then move production online eval from audit-only to
> gating for write-capable remediation and ticket closure.

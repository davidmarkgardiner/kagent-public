# DeepEval Fit Analysis for Kagent Evaluation

Date: 2026-06-05

## Decision

DeepEval can be used for Kagent evaluation, but it should be an optional
semantic judge layer, not the primary promotion gate.

Keep the existing deterministic scorecard as the authoritative pass/fail path
for Kagent incidents. It already checks the operational controls that must not
depend on another LLM: forbidden tools, wrong namespace, remediation before
human approval, missing verification, missing ticket updates, and public-safety
leakage.

Use DeepEval where exact matching is too weak:

- diagnosis quality
- evidence relevance and faithfulness
- tool choice quality
- argument quality
- plan or step quality
- task-completion judgement from traces

## Current Repo Fit

The current local evaluation stack is already well aligned with production
promotion gates:

- `observability/agent-evals/cases/` stores golden single-agent cases.
- `observability/agent-evals/lifecycle-cases/` stores end-to-end incident cases.
- `scripts/score-agent-run.py` scores captured agent output and tool calls.
- `scripts/score-lifecycle-run.py` scores alert-to-remediation lifecycle runs.
- `scripts/collect-lifecycle-evidence.py` conservatively normalizes sanitized
  Argo/evidence markers into `AgentLifecycleRun` JSON.
- `scripts/summarize-agent-scores.py` emits Markdown and Prometheus metrics.
- Grafana dashboards consume normalized `0.0` to `1.0` scores and display them
  as out-of-10 operational views.

Sample checks run during this analysis:

```bash
python3 observability/agent-evals/scripts/score-agent-run.py \
  --case observability/agent-evals/cases/crashloop-wrong-env-var.yaml \
  --run observability/agent-evals/results/sample/crashloop-wrong-env-var.run.json \
  --output-dir /tmp/kagent-deepeval-analysis-agent

python3 observability/agent-evals/scripts/score-lifecycle-run.py \
  --case observability/agent-evals/lifecycle-cases/pod-crashloop-hitl-remediation.yaml \
  --run observability/agent-evals/results/sample/lifecycle/pod-crashloop-hitl-remediation.lifecycle-run.json \
  --output-dir /tmp/kagent-deepeval-analysis-lifecycle
```

Both returned `score=1.0 passed=true`.

## DeepEval Capability Match

| Kagent evaluation need | DeepEval fit | Notes |
| --- | --- | --- |
| Diagnosis correctness beyond required terms | Good | Use `GEval` or `DAGMetric` against an incident-specific rubric. |
| Tool selection quality | Good | `ToolCorrectnessMetric` maps well to `requiredTools` and `forbiddenTools`. |
| Tool argument quality | Good | Use stricter tool correctness or argument correctness where captured calls include arguments. |
| Agent task completion | Good after tracing | `TaskCompletionMetric` needs an LLM trace; it is not a plain JSON-only check. |
| RAG/runbook answer grounding | Good | Use faithfulness/context metrics when retrieved runbook context is available. |
| HITL ordering | Poor as authority | Keep deterministic lifecycle hard gates. |
| Namespace safety | Poor as authority | Keep deterministic checks against tool arguments and incident namespace. |
| Remediation verification | Poor as authority | Verify from workflow/Kubernetes/Grafana evidence, then score deterministically. |
| A2A concurrency capacity | Not a fit | Keep `bench-kagent-a2a.sh` and `capacity-sweep-kagent-a2a.sh`; success is completed A2A state, not judge score. |
| Public-safety leakage | Supplemental only | DeepEval has safety metrics, but repo leak scans and deterministic regex gates remain the control. |

## Recommended Architecture

Add DeepEval as a supplemental runner that consumes the same case/run artifacts:

```text
AgentEvalCase YAML + captured run JSON
  -> deterministic scorer
  -> authoritative AgentEvalResult
  -> DeepEval adapter
  -> supplemental semantic result
  -> optional metric: agent_eval_llm_judge_score
```

For lifecycle runs:

```text
AgentLifecycleRun JSON
  -> deterministic lifecycle scorer
  -> authoritative AgentLifecycleEvalResult
  -> DeepEval semantic review of triage/evidence summaries only
  -> optional metric: agent_lifecycle_llm_judge_score
```

Do not let DeepEval decide whether a ticket can close, remediation can proceed,
or an agent can be promoted. Let it explain quality gaps and catch semantic
drift that deterministic checks miss.

## Deployment Model

DeepEval itself is not a long-running Kubernetes service and does not need a
Helm chart for the open-source path. Treat it like `pytest` for LLM systems:

```text
repo eval fixtures + captured Kagent run JSON
  -> Python runner with deepeval installed
  -> deepeval test run ...
  -> JSON/Markdown/Prometheus result artifacts
```

It can run in any of these places:

- a developer laptop;
- a GitHub Actions, GitLab CI, Jenkins, or Azure DevOps runner;
- an Argo Workflow or Kubernetes Job with a purpose-built runner image;
- a scheduled CronWorkflow for nightly regression checks.

DeepEval's docs describe CI usage as `deepeval test run` with a Pytest
integration. They also document local/provider model configuration through the
CLI, including OpenAI, Azure OpenAI, Anthropic, Bedrock, Ollama, local HTTP
models, and LiteLLM.

## Work Environment Setup

Recommended work-side rollout:

1. Keep the existing deterministic scorer in the current Argo lifecycle eval
   template.
2. Add a separate DeepEval runner for semantic checks in CI first.
3. Use sanitized sample runs and sanitized golden cases only.
4. Configure an approved judge model endpoint.
5. Publish DeepEval output as supplemental artifacts or metrics.
6. Move to an Argo/Kubernetes Job only after CI behavior is stable.

Minimal runner contents:

```text
python 3.10 or 3.11
deepeval pinned to an approved version
pytest
pyyaml
jsonschema, if schema validation is added to the adapter
repo adapter code under observability/agent-evals/deepeval/
```

Recommended environment variables:

```bash
export DEEPEVAL_TELEMETRY_OPT_OUT=1
export DEEPEVAL_DISABLE_DOTENV=1
export {{JUDGE_MODEL_API_KEY_ENV}}={{SECRET_REF}}
export {{JUDGE_MODEL_ENDPOINT_ENV}}={{PLACEHOLDER_ENDPOINT}}
```

Use `CONFIDENT_API_KEY` only if the Confident AI hosted or self-hosted platform
has been approved for the environment. Without that platform, DeepEval can still
run locally and in CI; results stay as local command output and generated
artifacts.

## Images Needed

For the open-source DeepEval runner, build and own a small internal image. Do
not depend on mutable public `latest` tags.

Example target shape:

```text
{{REGISTRY}}/platform/kagent-deepeval-runner:{{VERSION}}
```

Example Dockerfile shape:

```dockerfile
FROM python:3.11-slim

ENV DEEPEVAL_TELEMETRY_OPT_OUT=1
ENV DEEPEVAL_DISABLE_DOTENV=1

RUN pip install --no-cache-dir \
    deepeval=={{DEEPEVAL_VERSION}} \
    pytest=={{PYTEST_VERSION}} \
    pyyaml=={{PYYAML_VERSION}} \
    jsonschema=={{JSONSCHEMA_VERSION}}

WORKDIR /workspace
ENTRYPOINT ["deepeval"]
```

For internal Kubernetes use, mirror this image into the approved registry and
run it as an Argo Workflow step or Kubernetes Job. Mount or checkout the repo,
inject only approved judge-model credentials, and write results to the same
artifact/metrics path used by the current eval stack.

## Kubernetes Operation

If Kagent semantic evals need to run inside the cluster, the recommended shape is
an Argo Workflow or CronWorkflow:

```text
Workflow/CronWorkflow
  -> checkout or mount sanitized eval fixtures
  -> run deterministic scorer
  -> run DeepEval supplemental scorer
  -> write JSON/Markdown result
  -> emit optional Prometheus text metric
```

Required Kubernetes pieces:

- `ServiceAccount` with no Kubernetes mutation permissions.
- `Secret` or External Secret for judge-model credentials.
- `ConfigMap` or checked-out repo content for test files and adapters.
- `NetworkPolicy` allowing egress only to the approved judge endpoint and any
  approved artifact destination.
- `ResourceQuota`/requests/limits because LLM-judge evals can be slow and
  concurrent.

Do not put the DeepEval runner in the current `agent-lifecycle-eval` Argo
template until dependency, image, egress, and credential handling are approved.

## Confident AI Platform Option

Confident AI is the optional platform behind DeepEval for shared dashboards,
datasets, traces, regression history, and production monitoring. This is
separate from the open-source Python package.

Based on the current Confident AI self-hosting docs, the self-hosted platform
can run in Kubernetes. Their Azure Kubernetes deployment guide describes
vendor-provided Kubernetes manifests, not a public Helm chart, with services
such as:

- `confident-backend`
- `confident-frontend`
- `confident-evals`
- `confident-otel`
- `redis`

The docs describe container images stored in Confident AI's AWS ECR, with exact
version tags and ECR access provided by a Confident AI representative. The
deployment also expects ingress, TLS, External Secrets, and credential sync from
Azure Key Vault in the Azure path.

Treat this as a separate product deployment decision:

```text
DeepEval open-source runner
  -> no platform required
  -> simplest for Kagent pilot

Confident AI managed or self-hosted platform
  -> optional dashboard/history/tracing layer
  -> requires vendor images, secrets, ingress, storage/database setup, and
     security review
```

For this repo, the recommended first step is the open-source runner only. Do not
plan a Confident AI platform deployment until the organization has approved the
data-handling model and vendor/self-hosting path.

## Pilot Plan

Start with a local-only pilot under this directory:

```text
observability/agent-evals/deepeval/
|-- README.md
|-- requirements.txt              # later, if the pilot is implemented
|-- test_agent_semantics.py        # later
|-- adapters/
|   |-- kagent_case_loader.py      # later
|   `-- result_writer.py           # later
`-- results/                       # later, ignored or generated outside repo
```

Initial cases:

- `crashloop-wrong-env-var`
- `imagepullback-bad-secret`
- `flux-reconciliation-failure`

Initial metrics:

- `ToolCorrectnessMetric` for expected tool usage.
- `GEval` or `DAGMetric` for diagnosis correctness and evidence quality.
- RAG faithfulness/context metrics only when a retrieved runbook/context bundle
  is included in the captured run.

Run policy:

```bash
export DEEPEVAL_TELEMETRY_OPT_OUT=1
deepeval test run observability/agent-evals/deepeval
```

## Runtime Guidance

Do not install DeepEval into the current Argo lifecycle eval template yet. The
current runtime intentionally uses a small public image plus `python3` and
`py3-yaml`. DeepEval adds Python dependencies, judge-model credentials, and
network/model-provider requirements.

Use this rollout order:

1. Run DeepEval locally or in CI with sanitized sample data.
2. Compare DeepEval scores with deterministic scores for several cases.
3. Add supplemental Prometheus metrics only after score stability is understood.
4. Build an approved internal eval image if this needs to run in-cluster.
5. Keep deterministic hard gates as the only blocking gate.

## Public-Safety Notes

- Do not send private hostnames, cluster IPs, tenant IDs, subscription IDs, or
  real ticket URLs to an external judge model.
- Keep case fixtures public-safe and placeholder-based.
- Set `DEEPEVAL_TELEMETRY_OPT_OUT=1` for work-style runs unless telemetry is
  explicitly approved.
- Do not use the Confident AI hosted platform for work data unless data
  handling is approved separately.
- Prefer an approved internal or tenant-approved judge model when evaluating
  real incident text.

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| LLM judge nondeterminism | Flaky promotion decisions | Keep DeepEval supplemental; pin model and threshold during pilot. |
| Extra cost/latency | Slower CI or incident workflows | Run on sample/regression suites first, not every live workflow. |
| Data exposure | Work incident data leaves approved boundary | Sanitize inputs and use approved judge endpoints. |
| False confidence | Semantic score hides operational safety failure | Deterministic hard gates stay authoritative. |
| Trace gap | Task-completion metric cannot evaluate full agent behavior | Add OpenTelemetry/kagent/agentgateway trace capture before relying on task completion. |

## Recommendation

Adopt DeepEval for a narrow Phase 3 pilot after the current deterministic
scorecard remains the baseline:

- yes for semantic diagnosis and evidence-quality review;
- yes for supplemental tool correctness and argument quality;
- maybe for task completion once Kagent traces are captured;
- no for HITL, remediation, namespace safety, ticket closure, or A2A capacity
  gates.

## Sources

- [DeepEval GitHub repository](https://github.com/confident-ai/deepeval)
- [DeepEval introduction](https://deepeval.com/docs/introduction)
- [DeepEval metrics introduction](https://deepeval.com/docs/metrics-introduction)
- [DeepEval unit testing in CI/CD](https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd)
- [DeepEval CLI settings](https://deepeval.com/docs/command-line-interface)
- [Tool Correctness metric](https://deepeval.com/docs/metrics-tool-correctness)
- [Task Completion metric](https://deepeval.com/docs/metrics-task-completion)
- [DeepEval data privacy](https://deepeval.com/docs/data-privacy)
- [Confident AI Kubernetes deployment](https://www.confident-ai.com/docs/self-hosting/azure/kubernetes-deployment)

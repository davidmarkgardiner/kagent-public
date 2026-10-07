# Promptfoo versus DeepEval for AKS skills and kagent

Research date: 7 October 2026. Decision scope: our GitLab-mounted AKS skills, kagent/A2A agents, internal model gateway and air-gapped Kubernetes evaluation service.

**Recommendation: keep Promptfoo as the primary runner and interactive workbench for this bundle. Pilot DeepEval as an additional Python evaluator of recorded agent traces if its diagnostic metrics improve decisions.** Replacing the upstream Promptfoo suites now creates migration work without resolving our main gap: collecting complete, trustworthy kagent tool trajectories. Neither framework supplies that proof automatically.

This is a source-led architectural comparison with small synthetic checks, not a model-quality, speed or cost benchmark. It does not select or deploy a new product. The current bundle remains Promptfoo-based.

## Versions and evidence boundaries

| Item | Inspected version / source | Evidence |
|---|---|---|
| Promptfoo | `0.122.2`, tag source `89052308bce06f53645b1f189ada5ac9d1897347` | Official source inspection; existing derived ARM64 image rerun with networking disabled |
| DeepEval | Python `4.2.8`, source `ec9b9837a3bf4a41b7fc01f2de0bfeba4997c159` | Official source inspection; source installed into a fresh Python 3.11.13 virtual environment; deterministic metric and local JSON checks |
| DeepTeam | Current official documentation only | Dedicated red teaming framework considered for scope; no package installation, pinned release or attack run |
| Our agent bundle | [Evaluation contract](../aks-skills-specialists/EVALUATION.md) and [Kubernetes runner](README.md) | Existing assets inspected; no live workplace invocation or deployment |

DeepEval's source snapshot declares Python `>=3.9,<4.0`; that metadata is not proof that every optional integration works on every Python version. It also has a TypeScript SDK, whose README explicitly identifies remaining gaps relative to Python. This comparison uses Python, including its tool-permission metric. Do not interpret “Python-oriented” as “Python-only.” [DeepEval package metadata](https://github.com/confident-ai/deepeval/blob/ec9b9837a3bf4a41b7fc01f2de0bfeba4997c159/pyproject.toml), [TypeScript SDK and parity](https://github.com/confident-ai/deepeval/blob/ec9b9837a3bf4a41b7fc01f2de0bfeba4997c159/typescript/README.md).

Documentation can move ahead of these snapshots. Prefer the pinned source for implementation details. Exact dependency locks, image digests and selected plugins still need workplace qualification.

## Capability comparison

The fit judgments below are our assessment for this repository, rather than vendor benchmark results.

| Dimension | Promptfoo | DeepEval | Implication for our process |
|---|---|---|---|
| Primary authoring workflow | YAML test matrices, CLI, custom JavaScript/Python providers and assertions | Python test cases, metrics, pytest-style assertions; TypeScript also available | Promptfoo preserves the Azure skill suites; DeepEval fits Python application tests |
| Deterministic checks | Exact text/JSON checks, executable assertions and trace/trajectory assertions | Custom metrics/assertions; built-in tool correctness and tool permission checks | Use hard checks for scope, forbidden actions and evidence completeness |
| Judged quality | Rubrics and LLM grading alongside deterministic assertions | Named quality/RAG/agent metrics, GEval and configurable judges | Both need calibrated judges and realistic expected outcomes |
| Agent internals | OTLP tracing, trace correlation, trajectory assertions | Instrumented spans/components and full-trajectory metrics | Both require an adapter or instrumentation for our actual runtime |
| Retrieval quality | Assertions and configurable grading over supplied evidence | Dedicated retrieval/faithfulness metrics | DeepEval is attractive if runbook retrieval becomes a major subsystem |
| Red teaming | Built into the broader tool; generation, strategies, evaluation and reports | Dedicated attack framework is the separate DeepTeam package | Compare Promptfoo with DeepEval **plus DeepTeam** for attack generation |
| Local review experience | Browser UI and persistent local results | Local JSON/SQLite and optional terminal inspector | Promptfoo is the closer fit to the requested in-cluster browser workbench |
| Shared managed platform | Separate enterprise/cloud capabilities | Confident AI, separate from the OSS framework | OSS runner availability does not establish enterprise deployment entitlement |
| Existing investment | Azure upstream suites and our container/manifests already use it | Requires a new adapter, suite mapping and packaged runtime | Keep a measured adoption threshold for introducing a second evaluator |

Mechanisms are documented in [Promptfoo Python integration](https://www.promptfoo.dev/docs/integrations/python/), [Promptfoo assertions](https://www.promptfoo.dev/docs/configuration/expected-outputs/), [DeepEval introduction](https://deepeval.com/docs/introduction) and [DeepEval agent quickstart](https://deepeval.com/docs/getting-started-agents). Deployment, tracing and attack limitations are detailed below.

## How the evaluations differ

### Promptfoo: compare configurations against a common test matrix

A provider executes the target, tests supply inputs and assertions, and the runner records verdicts across prompts/models/configurations. Custom providers can invoke an application rather than a raw model. Python support does not remove the Node.js runtime; a Python provider adds the Python interpreter and its dependencies to that runner. [Provider lifecycle](https://www.promptfoo.dev/docs/providers/python/).

For this bundle, the skill provider inserts skill text into a model prompt. Our quality, routing and baseline suites preserve the upstream approach. This is useful for skill-content regressions, but it bypasses real kagent startup, GitLab authentication, skill-tool invocation, MCP authorization and workflow handoff. Keeping Promptfoo does not excuse those missing acceptance checks.

**Pros:** accessible versioned configuration; straightforward model/prompt comparisons; existing Azure test compatibility; local browser review; deterministic and judged checks in one run.

**Cons:** complex workflows move into provider/assertion code; a broad assertion catalog does not define our safety policy; the OSS UI has operational limits; some attack generators depend on hosted services.

### DeepEval: express application behavior as tests and metrics

The application or adapter produces test inputs, actual outputs and relevant runtime evidence. DeepEval measures that evidence using selected metrics. Its Python path supports direct `evaluate()` calls and pytest-based `assert_test()` workflows. Tracing can attach metrics at component or trajectory level, which helps explain which step failed. [End-to-end evaluation](https://deepeval.com/docs/evaluation-end-to-end-llm-evals), [Agent tracing workflow](https://deepeval.com/docs/getting-started-agents).

Its agent metrics distinguish task completion, tool selection and argument correctness. For example, ToolCorrectness can compare expected calls deterministically and optionally use a model to assess selection when `available_tools` is supplied. Exactness, ordering and parameter checks are configurable. This is more specific than a generic answer rubric, but only as reliable as the recorded calls. [Tool correctness semantics](https://deepeval.com/docs/metrics-tool-correctness), [Task completion](https://deepeval.com/docs/metrics-task-completion).

**Pros:** natural fit for Python test ownership; explicit agent/RAG metrics; component-level failure diagnosis; custom metrics and judge implementations; local execution without a required SaaS account.

**Cons:** porting YAML cases and custom Azure assertions requires semantic review; metrics introduce their own assumptions and judge prompts; instrumentation increases integration work; local inspection is not an equivalent turnkey shared web service; adding DeepTeam creates another package/version surface.

### Scores and defaults are not interchangeable

A Promptfoo rubric score of `0.9` and a DeepEval metric score of `0.9` do not establish equal quality. The evaluation prompts, decomposition, aggregation, evidence and failure semantics can differ. Preserve the business expectation, then calibrate each evaluator against human-reviewed passing and failing cases. Never migrate a threshold merely because its number matches.

DeepEval GEval supports custom criteria; structured decision workflows are also available. A structured scoring graph does not make every underlying model judgment deterministic. Conversely, a deterministic name match does not establish a correct diagnosis. [GEval](https://deepeval.com/docs/metrics-llm-evals).

## Tool actions, permissions and missing evidence

Promptfoo supports OpenTelemetry and assertions for tool presence, sequence, argument matching and step count. Its pinned trajectory implementation rejects absent trace data. A traced provider request alone still does not expose the tools called behind a remote A2A endpoint. Correlation and runtime instrumentation must supply those child actions. [Tracing](https://www.promptfoo.dev/docs/tracing/), [Pinned trajectory assertions](https://github.com/promptfoo/promptfoo/blob/89052308bce06f53645b1f189ada5ac9d1897347/src/assertions/trajectory.ts).

DeepEval can evaluate supplied calls without instrumenting the target in-process, while component-level analysis benefits from instrumentation. Its Python ToolPermission metric compares called **names** to allowed/denied names. It is deterministic and uses no judge. That does not check namespaces, resource selectors, SQL arguments, credentials or actual execution outcomes. [Pinned permission metric](https://github.com/confident-ai/deepeval/blob/ec9b9837a3bf4a41b7fc01f2de0bfeba4997c159/deepeval/metrics/tool_permission/tool_permission.py).

Our synthetic checks exposed two useful boundaries:

- An empty `tools_called` list scores `1.0` for permission compliance. That is sensible for a genuine no-tool response, but dangerous if a broken collector silently converts a missing trace to an empty list.
- An allowed `get_pod` call with `namespace=other-team` also scores `1.0`. A separate argument/scope policy must reject it when that namespace is unauthorized.

For either framework, require an explicit trace-completeness marker; distinguish attempted, denied and completed calls; validate arguments and authorization; retain backend receipts. Use a per-case hard failure for any forbidden action. A high average score must not dilute one secret retrieval or production mutation. No evaluator replaces RBAC, MCP authorization or workflow approval.

## Air-gapped operation and additional tooling

Neither evaluator must host a model or require a GPU when it calls an approved internal inference endpoint. The target, judge and optional generator are separate roles; they may use the same deployment, but must be configured explicitly. Neither reads our kagent ModelConfig automatically. Reusing the agent's model also risks correlated mistakes, so calibrate a fixed judge against human labels.

| Dependency | Promptfoo path | DeepEval path |
|---|---|---|
| Core runtime | Node.js in official or derived OCI image | Python package and fully resolved wheels in an approved OCI image |
| Custom integration | Python only if the selected provider/assertion needs it | Our Python A2A/trace adapter and tests |
| Evaluation judge | Explicit internal provider for each grading path | Explicit internal model passed/configured for the selected metrics |
| Generation/embedding | Package only the chosen features and internal endpoints | Add generator/embedding dependencies only for the chosen metrics/features |
| Browser service | Included OSS server, subject to single-replica limitations | Separate service or supported platform deployment needed for comparable shared web access |
| Attack generation | Selected local-capable plugins, or approved enterprise arrangement | DeepTeam plus reviewed model/attack configuration; qualify separately |

DeepEval commonly defaults model-backed metrics to OpenAI. For internal judges, use a supported provider or `DeepEvalBaseLLM`; custom judges must satisfy the schema-aware synchronous/asynchronous output contract for the metrics selected. An endpoint that can answer chat prompts is not automatically a compatible structured-output judge. [Judge configuration FAQ](https://deepeval.com/docs/faq), [Custom judge contract](https://deepeval.com/guides/guides-using-custom-llms).

For DeepEval 4.2.8, a proposed container baseline is telemetry opt-out, dotenv autoload disabled, no Confident credentials/login state, explicit internal judges, local results and public egress denied. The inspected settings include `DEEPEVAL_TELEMETRY_OPT_OUT=1`, `DEEPEVAL_DISABLE_DOTENV=1`, `DEEPEVAL_UPDATE_WARNING_OPT_IN=0`, `DEEPEVAL_EVAL_MODE=llm` and `DEEPEVAL_RESULTS_FOLDER=/data/runs/RUN_ID`. Explicit `llm` mode avoids accidentally selecting a separately configured Jev/system-one evaluator. These are starting settings, not a tested offline image recipe. [Pinned settings](https://github.com/confident-ai/deepeval/blob/ec9b9837a3bf4a41b7fc01f2de0bfeba4997c159/deepeval/config/settings.py).

Pin direct and transitive dependencies, build for the cluster architecture, retain licenses/SBOM, and transfer the OCI image into the internal registry. Avoid package installation at startup. Python wheels with native dependencies need matching OS/architecture support. Keep credentials and trusted CA roots outside the image. Public egress controls must cover every process, beyond configuration flags.

### Promptfoo offline red teaming is a subset

In 0.122.2, `PROMPTFOO_DISABLE_REMOTE_GENERATION` disables remote generation generally; `PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION` provides a narrower red-team switch. Disabling telemetry/update checks and passing `--no-share`, as our existing runner does, is not sufficient qualification for newly enabled red-team features. Add the general remote-generation control, disable sharing globally, and test the actual selected feature set under denied public egress. [Pinned generation controls](https://github.com/promptfoo/promptfoo/blob/89052308bce06f53645b1f189ada5ac9d1897347/src/redteam/remoteGeneration.ts), [Offline guidance](https://www.promptfoo.dev/docs/faq/).

The pinned remote-only plugin list includes `indirect-prompt-injection`, `mcp`, `bola`, `bfla`, `data-exfil` and `reasoning-dos`. These are relevant to our agents. Mirroring the image and configuring a local judge does **not** make those generators available offline. Curated equivalent scenarios can still be evaluated through ordinary local suites; that is our recommended first step. It is distinct from claiming identical generated attack coverage. [Remote-only plugin registry](https://github.com/promptfoo/promptfoo/blob/89052308bce06f53645b1f189ada5ac9d1897347/src/redteam/constants/plugins.ts).

Current vendor pages describe both local generation and remote-only exclusions; descriptions of the `redteam.provider` role are not fully consistent across pages. Verify the exact command/plugin paths in the pinned version rather than relying on that one setting to contain all inference. Enterprise fully air-gapped support is a separate offering whose supported features and deployment terms must be confirmed. [Generation configuration](https://www.promptfoo.dev/docs/red-team/configuration/), [Inference restrictions](https://www.promptfoo.dev/docs/red-team/troubleshooting/inference-limit/).

### DeepEval and DeepTeam have separate responsibilities

DeepEval's source directs red teaming users to DeepTeam from v3 onward. DeepTeam generates attacks against a target callback and grades vulnerability outcomes, with local risk-assessment persistence and optional Confident AI integration. Its documented custom-model path is promising for internal inference; no complete air-gap feature qualification was performed here. Do not assume every attack or optional model backend is offline merely because the core package is open source. [Migration notice](https://github.com/confident-ai/deepeval/blob/ec9b9837a3bf4a41b7fc01f2de0bfeba4997c159/deepeval/red_teaming/README.md), [DeepTeam workflow](https://www.trydeepteam.com/docs/getting-started).

## Kubernetes: persistent service and manual run alternatives

### Persistent workbench, without a pipeline

**Promptfoo:** retain our Deployment, Service and PVC pattern. Use one replica and serialized manual suite execution; inspect results in the browser. The OSS server uses local SQLite and in-memory jobs and has no built-in authentication/SSO. It should sit behind our existing authenticated access layer. Its limitations matter for a team service, not merely installation convenience. [Self-hosting constraints](https://www.promptfoo.dev/docs/usage/self-hosting/).

**DeepEval:** a persistent development/workbench Pod can run Python tests on demand and retain results on a PVC. Optional `deepeval inspect` is a terminal interface for local JSON/SQLite, not a browser dashboard. For an always-on shared web service, build and operate an authenticated submission API, bounded queue, workers and result viewer, or procure an appropriately supported Confident AI deployment. The reviewed OSS package does not supply the same turnkey server pattern as our Promptfoo bundle. The build-your-own option adds cancellation, access control, retention and queue-recovery responsibilities. [Local storage](https://deepeval.com/docs/evaluation-local-backend-storage), [Pinned inspector](https://github.com/confident-ai/deepeval/blob/ec9b9837a3bf4a41b7fc01f2de0bfeba4997c159/deepeval/cli/inspect.py).

Our preference is Promptfoo for this interactive requirement. This does not imply its OSS service is suitable for unrestricted multi-team production use.

### Manually launched Kubernetes Job, without a pipeline

Both can run a pinned test suite as a manually created Job. Promptfoo already has manifests and a runner here. DeepEval would need a Python image, test entrypoint and equivalent fail-closed result validation. Use per-run output locations, explicit deadlines, bounded concurrency and no automatic quality retries. Keep passing, failing and errored results distinguishable.

Our proposed DeepEval Job should use the test CLI for pytest assertions or an explicit `evaluate()` result-to-exit-code wrapper. Calling a library and printing failed metrics is not itself a Kubernetes failure signal. Preserve reports before cleanup. Neither option requires GitLab CI; either can later be invoked by CI or Argo when desired. These DeepEval deployment shapes are design proposals, not included manifests or deployed resources.

## Licensing, data handling and operating cost

Promptfoo's inspected core is MIT; DeepEval's inspected core is Apache-2.0. Their commercial platforms have separate terms. Review redistributed dependencies and enterprise capabilities separately; core licensing is not an entitlement to self-host vendor SaaS. [Promptfoo license](https://github.com/promptfoo/promptfoo/blob/89052308bce06f53645b1f189ada5ac9d1897347/LICENSE), [DeepEval license](https://github.com/confident-ai/deepeval/blob/ec9b9837a3bf4a41b7fc01f2de0bfeba4997c159/LICENSE.md).

Both can retain sensitive prompts, logs, tool arguments and outputs in reports/traces. Sanitize before persistence, restrict result access, set retention and prevent public sharing. DeepEval saves locally and uploads test runs when Confident integration is enabled; absence of an environment key alone is insufficient if cached login/configuration can supply one. Use clean runtime state and denied egress. [Pinned upload condition](https://github.com/confident-ai/deepeval/blob/ec9b9837a3bf4a41b7fc01f2de0bfeba4997c159/deepeval/test_run/test_run.py).

No defensible speed/cost winner was measured. Budget target calls, grading calls, generated attacks, repeated turns, retries and optional embeddings separately. A named metric can make several judge calls; a red-team strategy can expand one seed into many attempts. Cache policy and concurrency change observed cost and latency. Record actual tokens and call counts rather than estimating from case count. Prefer deterministic hard gates first and judged scoring only where it adds information.

## Adoption and a fair comparison experiment

1. Preserve the existing Azure quality/routing/baseline suites. Add startup/hash and real A2A scenario receipts to the release evidence independently of evaluator choice.
2. Define one framework-neutral, redacted run record: case/revision, skill hash, model/runtime identifiers, input/final output, ordered attempted/completed/denied tool calls and arguments, trace-completeness status, relevant retrieved evidence, latency, tokens and bytes. Retain observed facts separately from evaluator verdicts.
3. Build one kagent capture adapter, then export the same records to Promptfoo and a small DeepEval pilot. Replay avoids comparing different stochastic target runs. For task/trajectory metrics that require native traces, map the required fields explicitly rather than pretending an answer string is sufficient.
4. Use a small human-labelled set covering correct diagnosis, wrong diagnosis, injected logs, namespace violations, forbidden mutation, bounded evidence, missing traces and no-tool legitimate replies. Measure each evaluator's missed unsafe cases, false failures, agreement with reviewers, judge-call cost and diagnostic usefulness.
5. Fix candidate/judge revisions and sampling; disable cache for the comparison; cap concurrency; record all first-run failures and infrastructure errors. Repeat a declared subset to estimate judge variability. Do not retry selectively until green or compare raw scores across frameworks.
6. Adopt DeepEval only if the pilot reveals useful failures or materially improves diagnosis enough to justify maintenance. Keep one authoritative release verdict: packaging and trace completeness, zero critical safety violations, then calibrated quality criteria. A blended quality score cannot override a safety failure.

For now, the next useful investment is a real kagent A2A/trace adapter and curated adversarial cases. Introducing a second dashboard or rewriting all upstream tests would postpone that proof. If our future workload becomes a Python-owned RAG/agent application with direct instrumentation access, DeepEval becomes a stronger primary-runner candidate.

## Validation performed for this comparison

See [the comparison receipt](evidence/COMPARISON-VALIDATION-2026-10-07.md). Source/version checks, limited synthetic runtime checks, relative links, source URLs, whitespace and public-safety checks are included. No paid model inference, generated red-team scan, live AKS/kagent test, DeepEval OCI build or Kubernetes deployment was performed.

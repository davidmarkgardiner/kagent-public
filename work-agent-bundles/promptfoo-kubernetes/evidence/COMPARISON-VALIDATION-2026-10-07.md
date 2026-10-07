# Promptfoo / DeepEval comparison validation

Date: 7 October 2026. Scope: source-led documentation and limited synthetic plumbing checks. No model-performance winner is established by these checks.

## Source inspection

- Promptfoo tag `0.122.2`: `89052308bce06f53645b1f189ada5ac9d1897347`. Inspected package/license metadata, trajectory assertions, tracing docs, remote-generation switches, remote-only plugin registry and self-hosting limitations.
- DeepEval source: `ec9b9837a3bf4a41b7fc01f2de0bfeba4997c159`, package version `4.2.8`. Inspected Python constraints/dependencies, TypeScript parity, ToolPermission and ToolCorrectness metrics, local storage/inspector, settings and upload conditions.
- DeepTeam: official documentation only. Not installed or executed.
- The comparison contains source citations at each relevant claim. Moving documentation is distinguished from pinned implementation evidence.

## Promptfoo runtime checks

Used the existing local `promptfoo-aks-evals:0.122.2-arm64` image. Each container had `--network none`, a temporary config directory and no model credentials. Set telemetry/update/remote-generation/sharing disabled and self-hosted mode. Passed `--no-cache --no-share`.

| Synthetic check | Actual result |
|---|---|
| Existing `tests/smoke.yaml` with deterministic fixture provider | 1 passed, 0 failed, 0 errors; CLI exit `0` |
| Existing `tests/fail.yaml` with deliberately incorrect expected output | 0 passed, 1 failed, 0 errors; CLI exit `100` |
| `trajectory:tool-used` requiring `get_pod`, with a provider that supplies no trace | 0 passed, 0 failed, 1 error; CLI exit `100`; explicit missing-trace error |

The missing-trace fixture used the same provider as the other checks and this assertion:

```yaml
assert:
  - type: trajectory:tool-used
    value: get_pod
```

The error was `No trace data available for trajectory:tool-used assertion`. This demonstrates the missing-trace path, not complete real-agent trace ingestion. JSON output paths were written inside disposable containers; this rerun did not retain those exports. Existing persistence/restart evidence is separately documented in [LOCAL-VALIDATION.md](LOCAL-VALIDATION.md).

## DeepEval runtime checks

Installed the inspected source into a fresh virtual environment using `uv`; it reported DeepEval `4.2.8` on Python `3.11.13`. Installation used connected package access. This is not a locked air-gap wheelhouse or OCI image.

Before importing DeepEval, the test cleared inherited environment variables, used fresh temporary HOME/state directories, disabled dotenv autoload, opted out of telemetry and update warnings, selected `llm` evaluation mode and disabled trace flushing. No API key or saved login was provided. A Python audit hook rejected DNS resolution and IP socket connection attempts; zero such attempts were observed. This is a process-level diagnostic, **not** kernel/container network isolation or proof about other metric paths.

Metric: `ToolPermissionMetric(allowed_tools=['get_pod'], denied_tools=['drain_node'], strict_mode=True)`.

| Supplied synthetic calls | Observed score | Interpretation |
|---|---|---|
| `get_pod(namespace='approved')` | `1.0` | Allowed name |
| `drain_node` | `0` | Explicitly denied name |
| `get_pod`, then `drain_node` | `0` | Strict mode rejects a mixed trajectory |
| Empty calls list | `1.0` | Permission compliance is vacuously true; collector completeness must be checked separately |
| `get_pod(namespace='other-team')` | `1.0` | Name-level policy does not inspect namespace arguments |

All five results matched the metric's source semantics. The final row is deliberately outside the hypothetical namespace policy; its metric PASS is the important limitation, not successful scope enforcement.

Also ran `evaluate()` on the allowed fixture with synchronous execution, cache read/write disabled, errors/missing parameters not ignored and local result persistence. It returned a successful test result and wrote one timestamped `test_run_*.json`. No judged metric, DeepTeam attack, pytest failure-exit path or Confident platform integration was tested.

## Documentation checks

- Reviewed comparison against the inspected source and current official documentation.
- Checked 7 relative Markdown targets/heading anchors and all 30 comparison source URLs (HTTP success), `git diff --check` and strict public-safety scans before publication.
- Changed only the comparison, this receipt and the two bundle documentation entrypoints.

## Remaining qualification

No paid inference, candidate/judge calibration, accuracy/latency/cost benchmark, live kagent/A2A capture, backend permission exercise, generated red-team scan, DeepEval image build, AMD64 runtime check or Kubernetes deployment was performed. The comparison's proposed adapter, pilot and DeepEval deployment shapes remain future work.

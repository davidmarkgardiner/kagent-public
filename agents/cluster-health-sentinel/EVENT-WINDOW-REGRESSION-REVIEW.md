# Sentinel event-window regression review — 2026-10-10

Scope: the regression files were prepared by an isolated worker from checked-in commit `620108e990fafb0a3256430eb808c6dc24d7764f` and copied to the clean `codex/sentinel-event-window-regression` review branch based on remote `main` at `164d72924998439065088a06cdb72f4dbd611edf`. The collector payload is identical at both bases. The certification workflow differs at its two `when` expressions (lines 123 and 134); this event-window test does not certify those expressions. The checked-in six-defect list is `work-agent-bundles/cluster-health-baseline-sentinel/README.md` under “Six defects, and how each was found”; `LESSONS.md` gives details. A separately dated “accepted six-defect matrix (2026-10-10)” was not found in the branch base. The classifications below use the checked-in list and should be reconciled if that separate matrix differs. This review checks source and runs offline tests. It makes no claim about current cluster state.

## Six recorded defects

| Recorded defect | Classification | Checked-in evidence and limit |
|---|---|---|
| Trigger payload interpolated into Python source, allowing code execution | **Fixed in source** for the merged certification path | `03-certification-workflow.yaml:443-462,506-518,579-613` carries check results, report, and verdict through environment variables; its script bodies read them with `os.environ`. The historical standalone EventSource/WorkflowTemplate path described in `LESSONS.md` is not checked in under this sentinel directory, so this classification does not verify any separately deployed copy. No hostile-payload regression receipt is checked in. |
| Fractional `eventTime` rejected, making event windows ineffective | **Fixed in source** | `02-collector-configmap.yaml:161-199` parses fractional RFC3339 timestamps and falls back across Event fields; `319-355,400-454` excludes stale and undated Events from FailedScheduling and Warning counts. New offline tests execute the embedded `collect.py` and check these cases. |
| `PolicyViolation` exclusion claimed but not applied | **Fixed in source** | `02-collector-configmap.yaml:82-94,422-454` applies reason/namespace exclusions after the time filter and reports `excluded_total`. `03-certification-workflow.yaml:64-67` passes the exclusion parameter. The new warning test checks one in-window PolicyViolation is excluded; an environment-specific exclusion policy remains to be derived. |
| Node CPU commit collected but never thresholded | **Fixed in source** | `02-collector-configmap.yaml:278-316,620-627,674-694` computes per-node commit and emits `node_cpu_commit` / `node_memory_commit` breaches at configured defaults. `06-baselines-configmap.yaml` does not set those keys, so the collector defaults currently supply the values. Threshold calibration is missing. |
| Node list truncated to 20 before detection | **Fixed in source** | `02-collector-configmap.yaml:294-316,674-694` retains all nodes in `commit` for breach detection and truncates only the display list `nodes`. A >20-node offline regression and multi-node live receipt are still missing. |
| `bitnami/kubectl` image cannot be pulled | **Open** at repository scope; sentinel source migrated | `03-certification-workflow.yaml:158,394,441,504,577` uses `python:3.11-slim` for sentinel checks. Other checked-in workflows still specify `bitnami/kubectl:latest`, including `platform/argo-workflows/templates/namespace-onboarding/namespace-onboarding-template.yaml:175` and `infra/kro-stack/certification/workflows/uk8s-cluster-certification.yaml:139`. Current image-pull status was not checked. |

“Fixed in source” means the checked-in path addresses the recorded defect. It does not mean the deployed version or end-to-end behaviour is verified.

## Changed paths and offline check

- `agents/cluster-health-sentinel/test_event_window.py` — four deterministic `unittest` cases execute the Python embedded in `02-collector-configmap.yaml` with a fixed UTC clock and stubbed API. They cover fractional `eventTime`, null `lastTimestamp`, field fallback and precedence, exact window boundary, stale and undated Warning Events, and FailedScheduling message counts. The expected Warning total is 2 and FailedScheduling count is 3; stale, malformed, and undated Events do not inflate either count. No cluster API is called.
- `agents/cluster-health-sentinel/EVENT-WINDOW-REGRESSION-REVIEW.md` — this review.

Exact command from repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s agents/cluster-health-sentinel -p 'test_event_window.py' -v
```

Result: **4 tests passed**, exit 0, on local Python 3.12.8. The workflow image uses Python 3.11, which is not installed locally; these tests do not prove execution in that image.

## Proof still missing before re-enablement

### Offline regression

- A hostile triple-quote payload test for the merged workflow's data path and any separately deployed trigger path.
- Focused source tests for PolicyViolation and namespace exclusion variants, CPU and memory commit thresholds, and >20-node detection. The new event test covers one PolicyViolation only.
- A Python 3.11 run or equivalent offline image test, plus an offline workflow render/parse check against the target Argo version. Neither was run here.

### Fault injection

- No execution receipt for any case in `07-fault-injection.yaml`: scheduling pressure, workload stress, storage pressure, or collector permission loss. The scheduling case also needs duplicate-workflow and recovery-transition receipts. These require a controlled cluster run and are outside this task.

### Threshold evidence

- `06-baselines-configmap.yaml:1-5` says the values are educated guesses. There is no current-cluster 1–2 week log-only sample, event-rate distribution, node commit distribution, false-positive review, or approved threshold change. The CPU/memory commit defaults in `02-collector-configmap.yaml:620-627` need the same calibration.

### Current-cluster and live receipts

- No current-cluster readback of the deployed collector/workflow version, CronWorkflow suspension, `report-mode`, EventSource/Sensor absence, or recent workflow/ticket history. The historic RED stand-down in `work-agent-bundles/cluster-health-baseline-sentinel/README.md` is not a current receipt.
- No current-cluster manual certification run showing snapshot counts against actual Kubernetes Events, a correct agent verdict, safe log-only reporting, and no duplicate dispatch.
- No multi-node, restart/recovery, schedule, or image-pull receipt. A current-cluster proof must precede any decision to re-enable the sentinel.

## Stand-down and next human decision

The checked-in CronWorkflow remains `suspend: true` (`04-cronworkflow.yaml:30`), and the certification ConfigMap remains `report-mode: "log-only"` (`03-certification-workflow.yaml:36`). Neither file was changed. The original worker made no commit; this review branch contains only the test and this note. No cluster access, credentials, deployment, push, or merge occurred.

**Decision:** keep the sentinel stood down. A human owner should decide whether to authorize a separate controlled proof window after the remaining offline regressions and threshold plan are reviewed. Re-enablement needs current-cluster receipts and a separate decision; this source review is insufficient.

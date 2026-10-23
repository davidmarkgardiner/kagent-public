# Fault-injection preflight — offline audit

Audit date: 2026-10-11. Baseline: `620108e990fafb0a3256430eb808c6dc24d7764f`.
At the start of round 2, `git status --short` was empty. Decision: **keep the sentinel stood down**.
No injection was run. No cluster credentials, cluster calls, deployment, live
changes, commit, merge or push were used. This review establishes source facts,
not current cluster health or readiness to restart.

Source citations below use repository-relative paths and line numbers. Local
links point to the cited files; line numbers refer to this audited checkout.

## Six recorded defects

The six-defect scope is [plan §11](../../WORK-CLUSTER-HEALTH-SENTINEL-PLAN.md),
lines 388–401. “Fixed in source” means the relevant correction is present in the
checked-in sentinel path; regression and live proof remain separate gates.

| # | Recorded defect | Classification | File evidence and limits |
|---|---|---|---|
| 1 | PolicyViolation noise not excluded | **Fixed in source** | [collector](02-collector-configmap.yaml):80–95 defines reason/namespace exclusions; 400–454 filters and counts exclusions. [workflow](03-certification-workflow.yaml):64–67,407–410 passes defaults. Environment-specific filters still need validation; [README](README.md):120–125 explicitly requires re-derivation. |
| 2 | CPU commit collected but never thresholded | **Fixed in source** | Collector:626 default CPU threshold 90; 676–695 checks CPU and memory commit with warning severity. [baselines](06-baselines-configmap.yaml) omits these keys, so `load_baselines` at 630–640 merges defaults. These are requests/allocatable, not measured utilisation. |
| 3 | TOP_N cap hides node 21+ from detection | **Fixed in source** | Collector:293–316 builds full `commit` list before truncating report `nodes`; 677 reads `commit`. Detection at 1041 precedes size trimming at 1046. The plan's 25-node test claim has no executable test receipt here. |
| 4 | Dead bitnami/kubectl workflow image | **Fixed in source** | Workflow:157–160,394,441,504,577 uses `python:3.11-slim` and API code. Structural parse confirms eight embedded scripts; no image pull was attempted. README:167–170 reports repo-wide legacy images; that historical count was not independently revalidated in this scoped audit. |
| 5 | Trigger payload interpolated into Python enables RCE | **Fixed in source** | Current workflow:443–462 transports aggregate results via env vars; 466–472 JSON-decodes them; 506–518 transports the report via env vars. No Argo parameter interpolation occurs in its inline Python source. The original webhook chain is not present in this directory; its deployed state and authentication/NetworkPolicy are **unknown**, not proven secured. Plan:400 records the open-webhook gap. |
| 6 | MicroTime parsing and null timestamps bypass windows | **Fixed in source** | Collector:161–199 uses `fromisoformat` and populated-field fallback; 340–346 excludes undated/old scheduling events; 412–420 strictly excludes undated/old warning events and 455 records `undated`. Boundary, series-event and pagination semantics still need regression proof. |

Historical [bundle evidence](../../work-agent-bundles/cluster-health-baseline-sentinel/evidence/)
contains a snapshot, agent verdict and issue #444 from the older standalone
chain. It does not prove these four injections or this checkout's certification
path. README:165 explicitly says the injections have never run. Plan:390–392
mentions 44 passing tests; no executable sentinel regression suite was located
in `agents/cluster-health-sentinel`, the matching bundle, or the targeted scripts
search. Do not turn those historical claims into a new test receipt.

## Four-case signal and acceptance map

| Case / source | Expected collection and detection | Offline finding | Missing live receipt |
|---|---|---|---|
| 1 — scheduling, [injection](07-fault-injection.yaml):18–61 | 12 Pending pods; `scheduling.pending_count >= 10`, `oldest_pending_seconds >= 600`; `pending_pods` and `stuck_scheduling` warning breaches. Collector:319–355,698–712; baseline JSON specifies 10/600. | Deployment/replica structure parsed. Two scheduled cycles now correctly describe 30m, but schedule remains suspended. CPU 200/memory 400Gi is not a guarantee on every possible cluster. `FailedScheduling` is supporting evidence, not the detector's threshold input. Exactly one `cluster-health-triage` and a resolved event are unsupported by this directory's current integration; see blockers below. | Prove requests exceed every target node, then timestamped Pending count/age, failed scheduling messages, breaches, baseline result, aggregate and agent output. Observe duplicate counts across repeated runs and namespace sensors. After isolated cleanup, retain pointer/history and prove actual recovery semantics; background breaches must be absent for a healthy verdict. |
| 2 — workload stress, injection:63–103 | Four exit-1 containers can enter CrashLoopBackOff; `crashloop_containers >= 3` gives `crashloop`, warning. Collector:457–491,767–780; baseline threshold 3. Agent should report app-local, warning (injection:68–71; [agent](05-orchestrator-agent.yaml):211–212,245–246). | Command crashes; it does **not** exhaust memory or inject OOMKilled. Header corrected. OOM threshold is 5 and only four replicas exist, so this case cannot establish the OOM check. CrashLoopBackOff is sampled state, not guaranteed at every snapshot. App-local is an agent judgment, not a deterministic detector field. | Snapshot with at least three waiting containers, breach and agent verdict; evidence that concurrent node/addon/IP faults do not confound severity or root layer; repeated false-positive and recovery observations. Separate OOM injection remains missing. |
| 3 — storage, injection:105–128 | Non-Bound PVC contributes `storage.not_bound_count >= 1`, producing warning `pvc_not_bound`. Collector:493–507,749–758; threshold 1. Workflow:370–383 independently fails storage on an unbound claim. Agent root layer expected storage. | PVC structure parsed. Nonexistent class name must actually be absent on the target. Unbound count is cluster-wide and includes any non-Bound phase; it does not identify this claim alone. | Verify class absence, claim phase and identity, collection and both certification checks, aggregate, agent root layer, then cleanup/recovery without unrelated unbound claims. |
| 4 — collector resilience, injection:130–146 | `section()` catches read errors as unavailable/error (collector:145–156); node detector skips unavailable sections (642–660); collector health lists nodes (1030–1037). Without other breaches, core blindness gives unknown (816–838), holds prior pointer verdict (1050–1064), and suppresses transition dispatch (1073–1095). | Procedure is notes, not a fault manifest. Removing `/rules/0` removes reads for **all** core resources in that rule, not just nodes ([RBAC](01-rbac.yaml):30–41); scheduling/storage/IP data may also become unavailable. Other breaches take precedence over unknown. Step exit 0 is conditional on snapshot writes working; permission failures in persistence are not covered by `section()`. | Approved shared-RBAC blast radius, exact pre-change rules and guaranteed restoration; actual forbidden-read error strings, unavailable-section list, no synthetic node breach, pointer retention across degraded → blind → restored runs, successful persistence and restoration. Full certification may still escalate errors; no new healthy result merely from blindness. |

All four cases were compared with collector/detector, README and plan, including
plan §10 finding 16's duplicate, false-positive, resolution and resilience
criteria. These criteria are obligations, not existing proof.

## Remaining source/runbook blockers

1. **Snapshot writer identity mismatch.** Workflow:49 and CronWorkflow:34 run
   `argo-events-sa`; RBAC:132–149 binds the `kagent` snapshot-writer Role only to
   `cluster-health-collector`. Cluster read binding at 99–114 does not grant
   snapshot writes. Collector:912,923–929 persists without a failure wrapper;
   missing writes can crash check-baseline. Additional deployed permissions are
   unknown. Resolve the checked-in grant deliberately before live rehearsal.
2. **Duplicate and resolution criteria do not match integration.** Workflow:
   120–142 escalates whenever aggregate has failures, regardless of baseline
   `transitioned`; aggregate:480–492 counts failed/error on every run. Collector:
   983 fails whenever non-healthy, and `MODE=check` at 1093–1095 returns before
   webhook dispatch. No `cluster-health-triage` template/sensor/webhook deployment
   exists in this directory. Healthy recovery is not escalated and emits no
   resolved event through this path. Forbid/mutex serialises runs; it does not
   deduplicate sequential incidents. Plan §10:371–386's durable incident and
   recovery design is not proof of implementation here. Human must choose the
   current certification contract or restore the standalone contract, with
   regression proof; this audit does not silently relax the criteria.
3. **One-case isolation and cleanup remain unsafe as written for live use.**
   Applying the entire multi-document file activates all three workload faults;
   the ConfigMap notes instruct whole-file deletion, including the Namespace.
   This is not case selection. Clearing history/pointer before observing
   recovery destroys transition evidence and relative warning baselines (which
   require three usable historical samples; collector:793–809). Future runbook
   needs per-case selection, recovery capture before reset, and bounded cleanup.
4. **Case 4 changes a shared ClusterRole.** It affects both bound service
   accounts, including other certification runs. Scratch namespace containment
   does not contain this RBAC procedure. Keep scheduling suspended and design a
   controlled restoration receipt before authorizing it.
5. Baseline-only cases omit CPU/memory commit, >20-node coverage, actual node
   NotReady/pressure, addon failure, IP/max-pods, warning-spike/history and storm
   thresholds. Passing these four cases would not certify all detector branches.

Only clear defects in `07-fault-injection.yaml` were corrected: absent cleanup
filename, wrong 20m cadence, misleading OOM label, stale CronJob step wording and
manual creation command. The manual-run note now points to README's on-demand
Workflow. Runtime/RBAC/acceptance redesigns are documented, not changed.

## Missing receipts, separated by purpose

- **Regression (offline, not run):** reproducible adversarial tests for exclusions
  plus excluded counters; CPU/memory threshold boundaries; 25+ nodes with the
  breached node outside report TOP_N; hostile quotes/newlines treated as data in
  every workflow script; MicroTime/null/malformed/old/exact-cutoff timestamps;
  zero/insufficient/three-sample history; unavailable core sections with existing
  warning/critical breaches; degraded → blind → restored pointer sequence;
  snapshot-write failures; repeated certification failures and resolution;
  clean certification with skipped triage/ticket tasks. AST parsing is not these
  tests and does not validate Argo substitution or DAG execution.
- **Fault-injection:** timestamped setup, isolated fault identity, precondition,
  raw snapshot, baseline/aggregate output, verdict, duplicate counts, recovery
  and cleanup/restore receipts for every case above. OOM and the omitted detector
  branches need additional scenarios. None were produced in this audit.
- **Threshold:** 1–2 weeks of log-only observations, reviewed baseline values,
  expected benign/chronic noise, false-positive rate with denominator, detection
  latency and acceptable misses. README:86–89,155 and baselines:1–5 call the
  thresholds guesses. No numerical false-positive acceptance bound is specified.
- **Live cluster:** separately authorized target/version inventory; server-side
  schema checks, image pulls, collector mount in `argo-events`, effective reads
  and snapshot writes for the actual workflow SA, immutable snapshot/pointer/GC
  persistence, serialization of manual and scheduled runs, Agent Accepted/Ready
  and real specialist resolution, A2A output and error handling, log-only no-ticket
  receipt, namespace-sensor routing partition, any retained webhook access
  controls, multi-node behavior and applicable Azure subnet identity evidence.
  Existing historical RED evidence is neither a fresh health check nor permission
  to re-enable. No live receipt or current cluster state was obtained.

## Exact offline checks executed

Round 3 corrected the round-2 hardcoded eight-file count: there are **seven**
YAML files, 17 documents, eight inline Python scripts and ten valid review links.
The YAML-file count below is now computed from the parsed files. Source citations
and the four-case/six-defect findings were rechecked; the stand-down decision and
missing proof remain unchanged. Only this review was edited in round 3; the
round-2 injection-file edits are retained.

From repository root, the following command was rerun and exited **0**. It reads local YAML,
parses Python syntax without executing it, parses baseline JSON and asserts
selected structural/default properties. No token/CA files or network are read.

```bash
python3 - <<'PY'
import ast, json
from pathlib import Path
import yaml
root = Path('agents/cluster-health-sentinel')
parsed = {p.name: list(yaml.safe_load_all(p.read_text())) for p in sorted(root.glob('*.yaml'))}
print('PASS: {} YAML files, {} documents'.format(len(parsed), sum(map(len, parsed.values()))))
collector = parsed['02-collector-configmap.yaml'][0]['data']['collect.py']
ast.parse(collector)
workflow = parsed['03-certification-workflow.yaml'][1]
count = 0
for template in workflow['spec']['templates']:
    source = template.get('script', {}).get('source')
    if source:
        ast.parse(source)
        count += 1
print('PASS: collector and {} inline Python scripts parse (not executed)'.format(count))
json.loads(parsed['06-baselines-configmap.yaml'][0]['data']['baselines.json'])
assert parsed['04-cronworkflow.yaml'][0]['spec']['suspend'] is True
assert parsed['03-certification-workflow.yaml'][0]['data']['report-mode'] == 'log-only'
cases = parsed['07-fault-injection.yaml']
assert [d['kind'] for d in cases] == ['Namespace', 'Deployment', 'Deployment', 'PersistentVolumeClaim', 'ConfigMap']
assert all(d['metadata'].get('namespace') == 'cluster-health-test' for d in cases[1:])
assert cases[1]['spec']['replicas'] == 12 and cases[2]['spec']['replicas'] == 4
notes = cases[-1]['data']['README']
assert '09-fault-injection.yaml' not in notes
assert '07-fault-injection.yaml' in notes and '--from=cronjob/' not in notes
print('PASS: baseline JSON, stood-down defaults, injection structure and corrected references')
PY
```

Output:

```text
PASS: 7 YAML files, 17 documents
PASS: collector and 8 inline Python scripts parse (not executed)
PASS: baseline JSON, stood-down defaults, injection structure and corrected references
```

`git diff --check` exited **0**, no whitespace errors. Review-link existence
check below exited **0**. These are narrow parse/structural checks, not Kubernetes
schema validation, fault injection or functional detector tests.

```bash
python3 - <<'PY'
from pathlib import Path
import re
p = Path('agents/cluster-health-sentinel/FAULT-INJECTION-PREFLIGHT.md')
links = re.findall(r'\]\(([^)]+)\)', p.read_text())
for link in links:
    assert (p.parent / link).exists(), link
print('PASS: {} local review links exist'.format(len(links)))
PY
```

Review-link output:

```text
PASS: 10 local review links exist
```

Additional scope/default checks were rerun from repository root:

```bash
git diff --check
git diff --exit-code -- agents/cluster-health-sentinel/03-certification-workflow.yaml agents/cluster-health-sentinel/04-cronworkflow.yaml
git status --short
```

The first two commands exited **0** with no output: no whitespace errors and
no diff to either stand-down control file. `git status --short` exited **0**:

```text
 M agents/cluster-health-sentinel/07-fault-injection.yaml
?? agents/cluster-health-sentinel/FAULT-INJECTION-PREFLIGHT.md
```

Changed paths relative to the checked-in baseline (two-file scope):

- `agents/cluster-health-sentinel/07-fault-injection.yaml`
- `agents/cluster-health-sentinel/FAULT-INJECTION-PREFLIGHT.md`

Unchanged safety controls verified: [CronWorkflow](04-cronworkflow.yaml):30
keeps `suspend: true`; workflow ConfigMap:36 keeps `report-mode: "log-only"`.
Human next decision: commission scoped source/regression work to close the
identity, duplicate/recovery and isolation blockers, then separately authorize
an isolated live rehearsal. Re-enablement remains blocked pending those fixes,
threshold review and live health/fault/recovery receipts.

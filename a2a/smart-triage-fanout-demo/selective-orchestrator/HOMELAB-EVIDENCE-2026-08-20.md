# Selective SRE orchestrator: homelab evidence

Date: 2026-08-20

Kubernetes context: `red`

Issue: `#86`

## Scope and claims

The live run exercised Alertmanager, Argo Events, the selective Argo
WorkflowTemplate, issue #85 lifecycle state and deterministic fixture
specialists. It did not deploy the existing smart-triage Agent CRs, call a
model, execute Azure/kubectl, retrieve credentials or mutate a monitored
workload. This preserves the issue #48 always-on cost boundary while proving
selection, contracts, budgets and failure routing.

`fixture` findings passed the same runtime Finding v1 validator used by issue
#85. The existing specialist prompts now support the same JSON contract for a
later authorised `live` run.

## Offline gates

```text
15 tests ran: OK
SMART_TRIAGE_SELECTIVE_ORCHESTRATOR_VERIFY_OK
PUBLIC_SAFE_SCAN_OK: yes
git diff --check: clean
server-side dry runs: accepted
```

The tests cover focused routing, FailedScheduling, workload identity, bounded
full audit, target ambiguity, request-specific credential planning, contract
failure, timeout/partial synthesis, truncation, prompt-injection and
credential-like input handling, read-only manifests, call-count comparison,
the SRE-corrected false-positive fixture and one generated report.

The rendered kustomization contains only:

```text
ConfigMap/smart-triage-selective-orchestrator-code
WorkflowTemplate/smart-triage-selective-orchestrator
```

It contains no Deployment and adds no always-on specialist.

## Sensor integration defect found and fixed

The first replay created Workflow `smart-triage-alert-k6pgr` against the old
unconditional template. The changed Sensor YAML had accidentally moved the
embedded Workflow `spec` outside `source.resource`; the API accepted the CR but
Argo Events silently dropped the embedded template reference.

The indentation was fixed, the Sensor pod rolled, and live status then showed:

```text
source.resource.spec.workflowTemplateRef.name = smart-triage-selective-orchestrator
```

The verifier now renders the Sensor and asserts that exact nested path. The
erroneous disposable Workflow was deleted so it could not continue producing
noise.

## Focused CrashLoop run

Final-code Alertmanager replay `upstream-selective-86-final` created Workflow
`smart-triage-alert-pthln`:

```text
phase: Succeeded
workflowTemplateRef: smart-triage-selective-orchestrator
status: VALIDATED_REPORT
lifecycle: NEW
ticketAction: CREATE
selected: [kubernetes, grafana]
specialistCalls: 2
synthesisCalls: 1 (deterministic fixture synthesis)
selectedPathCalls: 3
unconditionalBaselinePathCalls: 9
modelCalls: 0
parallelismLimit: 3
lowerThanUnconditionalFanout: true
```

Both fixture specialist outputs validated as Finding v1 and entered the report
as `PROVEN`. Job, security, network, GitOps, knowledge, deployment and trace
specialists were not called.

The checked-in `run-smart-triage-demo.sh` helper was also executed against
`red`. Workflow `smart-triage-fanout-886wm` succeeded with the final metric
contract: `selectedPathCalls=3`, `unconditionalBaselinePathCalls=9`,
`modelCalls=0`, lifecycle `NEW` and ticket action `CREATE`.

## Unchanged replay

The same stable signal with upstream fingerprint `upstream-selective-86-c`
created Workflow `smart-triage-alert-57mtd`:

```text
phase: Succeeded
status: UNCHANGED_SUPPRESSED
lifecycle: ONGOING
ticketAction: NONE
selected: []
specialistCalls: 0
synthesisCalls: 0
toolCalls: 0
```

This is the issue #85 deterministic routine path: a changed upstream alert ID
did not cause specialist fan-out or a repeated ticket action.

## Routing matrix proof

```text
smart-triage-selective-scheduling-2sprm
  phase: Succeeded
  selected: [kubernetes, deployment, grafana]
  selected path: 4 calls versus baseline 9

smart-triage-selective-identity-b5m78
  phase: Succeeded
  selected: [policy, kubernetes]
  selected path: 3 calls versus baseline 9
  secretValuesRequested: false

smart-triage-selective-full-ctztx
  phase: Succeeded
  selected: all eight existing capabilities
  parallelismLimit: 3
  selected path: 9 calls
```

The full audit ran only because the Workflow argument explicitly set
`full_health_audit=true`.

## Target blocking proof

Workflow `smart-triage-selective-blocked-hxccg` supplied an unknown target:

```text
phase: Succeeded
status: BLOCKED_TARGET_CONTEXT
lifecycle: NOT_EVALUATED
ticketAction: NONE
selected: []
credentialPreparation.count: 0
specialistCalls: 0
toolCalls: 0
```

For approved fixtures, the report records one request-specific credential
preparation plan, a unique `/tmp/aks-triage/<run-id>.kubeconfig`, explicit
subscription/resource-group/cluster fields, the exact context and namespace,
`--admin` as forbidden, and `sharedCurrentContextChanged=false`. The public
fixture does not falsely mark that plan as executed.

## Contract and evidence boundaries

- Invalid/free-text live A2A output becomes `SPECIALIST_CONTRACT_FAILED`.
- Timeout or access denial produces `PARTIAL_EVIDENCE` and `UNKNOWN`, never an
  all-clear.
- Per-specialist evidence is capped at 4096 bytes and total synthesis input at
  16384 bytes.
- `TOOL_OUTPUT_TRUNCATED` records source, original bytes, retained bytes and a
  required narrowing action.
- Prompt-like and credential-like incident text is detected but is not copied
  into finding evidence or the generated report.
- Existing Agent manifests expose no `toolNames`; the selective code never
  installs or invokes apply, patch, delete, restart, scale or exec tooling.

## SRE feedback regression

The sanitized `FALSE_POSITIVE` fixture describes an intentionally healthy
single-replica non-production workload. A naive critical-single-replica rule
would fail it; the corrected path retains the SRE outcome and produces
`severity=info` findings. The test asserts the correction for every selected
specialist result.

## Retained evidence and remaining work-environment gates

Successful Workflows above remain under the 24-hour Workflow TTL. The
selective ConfigMap, WorkflowTemplate and updated Sensor remain installed for
review.

The following are deliberately not claimed by this public homelab run:

- Azure authorization and a real `az aks get-credentials` execution;
- request-specific kubeconfig use by a real AKS-MCP specialist call;
- live model latency/token/cost from the work model provider; and
- a real GitLab writer action.

Those gates require the approved private target registry, managed identity,
AKS-MCP connectivity, ready existing specialist Agents and an authorised
non-production GitLab project. The code fails closed or records explicit
evidence boundaries until those dependencies exist.

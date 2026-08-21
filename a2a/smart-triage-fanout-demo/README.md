# Smart Triage Fan-Out Demo

The current Alertmanager path proves the selective smart-triage orchestration
shape:

1. Normalize one synthetic incident payload, or one Alertmanager webhook payload.
2. Classify the finding against durable management-plane lifecycle state.
3. Select one to three relevant existing specialists for an ordinary incident,
   or all eight only for an explicit bounded full-health audit.
4. Validate every specialist result as Finding v1 and preserve timeouts,
   access denials and contract failures as evidence boundaries.
5. Synthesize one GitLab-ready report linked to the lifecycle decision and the
   existing human alert path.

The demo is public-safe and recommendation-only. It installs only its own demo
Agents and workflow RBAC. The GitOps specialist produces an MR/issue draft, not
a real GitLab change, and the workflow does not mutate incident workloads. The
post-run lifecycle eval uses synthetic public-safe remediation and ticket-update
markers to prove the audit gate wiring; in a work environment those markers
should come from the real remediation, verification, and GitLab steps.

Finding identity and notification state are provided by
[`finding-lifecycle/`](finding-lifecycle/). The service stores only bounded,
typed finding metadata on a management-plane PVC. If that service is
unavailable, the workflow emits `STATE_UNAVAILABLE`, continues the existing
alert/investigation path, and refuses to claim durable deduplication or
automatic ticket eligibility.

[`selective-orchestrator/`](selective-orchestrator/) is the current Argo Events
target. It resolves one approved target, selects only the relevant existing
specialists, validates Finding v1 outputs, applies hard budgets and produces
one GitLab-ready report. It adds no always-on specialist Deployment. The older
`smart-triage-fanout` WorkflowTemplate remains available as the unconditional
comparison baseline.

## Unconditional comparison baseline markers

- `SMART_TRIAGE_FANOUT: started`
- `LIFECYCLE_STATUS: NEW|ESCALATED|ONGOING|ACKNOWLEDGED|RESOLVED|RECURRENT|PROVISIONAL|STALE|STATE_UNAVAILABLE`
- `LIFECYCLE_FINGERPRINT: stf-v1-...`
- `TICKET_ACTION: CREATE|UPDATE|NONE`
- `SPECIALIST_KUBERNETES: completed`
- `SPECIALIST_NETWORK: completed`
- `SPECIALIST_GRAFANA: completed`
- `SPECIALIST_GITOPS: completed`
- `SPECIALIST_KNOWLEDGE: completed`
- `SPECIALIST_DEPLOYMENT: completed`
- `SPECIALIST_POLICY: completed`
- `SPECIALIST_TRACE: completed`
- `CITATIONS: docs/platform-kb/runbooks/checkout-api-crashloop.md#chunk-1`
- `DEPLOYMENT_VERDICT: bad_deploy`
- `POLICY_REMEDIATION_SAFETY: blocked`
- `TRACE_FALLBACK: NO_TRACE`
- `INCIDENT_SYNTHESIS: completed`
- `HITL_STATUS: resumed`
- `KB_UPDATE_MR: dry_run_after_hitl`
- `REMEDIATION_MODE: gitops_or_workflow_only`
- `REMEDIATION_EXECUTED: yes`
- `VERIFICATION_PASSED: yes`
- `TICKET_UPDATED: yes`
- `OUTPUT_SANITIZED: yes`
- `SMART_TRIAGE_PATTERN: proven`

## Prerequisites

- kagent in the `kagent` namespace.
- Argo Workflows in the `argo` namespace.
- A working chat `ModelConfig` only for `execution_mode=live`.
- Local `kubectl`, `argo`, and `jq`.
- The agent lifecycle eval template installed:

  ```bash
  kubectl apply -k observability/agent-evals
  ```

Install the finding lifecycle service before the WorkflowTemplate:

```bash
kubectl apply -k a2a/smart-triage-fanout-demo/finding-lifecycle
kubectl rollout status -n argo deployment/smart-triage-finding-lifecycle
```

## Run

The helper below installs and runs the focused deterministic fixture. It does
not deploy the specialist Agents:

```bash
a2a/smart-triage-fanout-demo/scripts/run-smart-triage-demo.sh
```

With an explicit context:

```bash
KUBE_CONTEXT={{KUBE_CONTEXT}} \
  a2a/smart-triage-fanout-demo/scripts/run-smart-triage-demo.sh
```

## Alert Ingestion

The manual workflow is a thin reference to the same WorkflowTemplate, so the
event and manual paths cannot drift. The demo also includes an
Alertmanager -> Argo Events -> smart-triage path:

```text
EventSource: a2a/smart-triage-fanout-demo/sensors/eventsource-alertmanager.yaml
Sensor: a2a/smart-triage-fanout-demo/sensors/alertmanager-to-fanout-sensor.yaml
Cross-namespace submit RBAC: a2a/smart-triage-fanout-demo/sensors/sensor-submit-rbac.yaml
WorkflowTemplate: a2a/smart-triage-fanout-demo/selective-orchestrator/workflow-template.yaml
Replay helper: a2a/smart-triage-fanout-demo/scripts/replay-alert.sh
```

Apply the alert path after the base demo agents/RBAC:

```bash
kubectl apply -f a2a/smart-triage-fanout-demo/workflow-template.yaml
kubectl apply -k a2a/smart-triage-fanout-demo/selective-orchestrator
kubectl apply -f a2a/smart-triage-fanout-demo/sensors/sensor-submit-rbac.yaml
kubectl apply -f a2a/smart-triage-fanout-demo/sensors/eventsource-alertmanager.yaml
kubectl apply -f a2a/smart-triage-fanout-demo/sensors/alertmanager-to-fanout-sensor.yaml
```

Replay one public-safe Alertmanager payload:

```bash
a2a/smart-triage-fanout-demo/scripts/replay-alert.sh
```

Use a unique synthetic reason when you want a fresh lifecycle finding. Changing
only the upstream Alertmanager fingerprint does not change canonical identity:

```bash
ALERT_NAME=KubePodCrashLoopingSelective$(date +%Y%m%d%H%M%S) \
  a2a/smart-triage-fanout-demo/scripts/replay-alert.sh
```

Expected first-run selective summary in the workflow logs:

```text
status: VALIDATED_REPORT
lifecycle: NEW
ticketAction: CREATE
selected: [kubernetes, grafana]
selectedPathCalls: 3
unconditionalBaselinePathCalls: 9
```

Replay the same stable workload/reason a second time to prove ongoing-state
suppression. The upstream Alertmanager fingerprint may change; lifecycle
identity does not depend on it. The second workflow should complete without
specialist fan-out:

```text
status: UNCHANGED_SUPPRESSED
lifecycle: ONGOING
ticketAction: NONE
selected: []
specialistCalls: 0
synthesisCalls: 0
```

The Sensor and EventSource include a lab-only control-plane toleration for
saturated non-production clusters. Replace it with your normal work-cluster
scheduling policy before production use.

## Integration Spike Specialists

The public PoC includes all planned spike specialists. These are public-safe
contract proofs; work implementations should replace synthetic evidence sources
with approved live tools.

| Spike | Specialist | Marker | Public proof source |
|---|---|---|---|
| 8 | Knowledge/runbooks | `SPECIALIST_KNOWLEDGE: completed` | Git-backed demo runbook citation |
| 5 | Deployment state | `SPECIALIST_DEPLOYMENT: completed` | Synthetic Flux/Helm release state |
| 6 | Policy/security | `SPECIALIST_POLICY: completed` | Synthetic Kyverno/image-policy context |
| 4 | Trace context | `SPECIALIST_TRACE: completed` | Synthetic Tempo contract with `NO_TRACE` fallback |

Per-spike proof helpers:

```bash
a2a/smart-triage-fanout-demo/scripts/prove-knowledge-citation.sh <workflow>
a2a/smart-triage-fanout-demo/scripts/prove-deployment-readonly.sh <workflow>
a2a/smart-triage-fanout-demo/scripts/prove-policy-summary.sh <workflow>
a2a/smart-triage-fanout-demo/scripts/prove-trace-link.sh <workflow>
```

The execution review with captured live evidence is
[`../../SMART-TRIAGE-FANOUT-EXECUTION-REVIEW.md`](../../SMART-TRIAGE-FANOUT-EXECUTION-REVIEW.md).
The raw evidence snapshot is
[`../../SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md`](../../SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md).
The work lift-and-shift handoff is
[`../../SMART-TRIAGE-FANOUT-WORK-HANDOFF.md`](../../SMART-TRIAGE-FANOUT-WORK-HANDOFF.md).
The GitLab branch/commit/MR live-write demo is
[`../../SMART-TRIAGE-GITLAB-MCP-MR-DEMO.md`](../../SMART-TRIAGE-GITLAB-MCP-MR-DEMO.md).
That demo includes both a terminal `glab` proof and a kagent-mounted MCP shim
proof. The public fan-out workflow remains synthetic GitOps by default; use the
GitLab MCP proof only against a sandbox project.
Successful workflow objects are retained for 24 hours for reviewer checks.

## Validate

```bash
bash -n a2a/smart-triage-fanout-demo/scripts/run-smart-triage-demo.sh
bash -n a2a/smart-triage-fanout-demo/scripts/replay-alert.sh
python3 -m unittest discover -s a2a/smart-triage-fanout-demo/finding-lifecycle/tests -v
sh a2a/smart-triage-fanout-demo/selective-orchestrator/verify.sh
kubectl kustomize a2a/smart-triage-fanout-demo/finding-lifecycle
kubectl kustomize a2a/smart-triage-fanout-demo/selective-orchestrator
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/agents.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/workflow-rbac.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/workflow-template.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/sensors/sensor-submit-rbac.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/sensors/eventsource-alertmanager.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/sensors/alertmanager-to-fanout-sensor.yaml
kubectl kustomize observability/agent-evals
kubectl create --dry-run=client -f a2a/smart-triage-fanout-demo/workflow.yaml
```

## Cleanup

```bash
kubectl delete -f a2a/smart-triage-fanout-demo/workflow-rbac.yaml --ignore-not-found
kubectl delete -f a2a/smart-triage-fanout-demo/agents.yaml --ignore-not-found
kubectl delete -f a2a/smart-triage-fanout-demo/sensors/alertmanager-to-fanout-sensor.yaml --ignore-not-found
kubectl delete -f a2a/smart-triage-fanout-demo/sensors/eventsource-alertmanager.yaml --ignore-not-found
kubectl delete -f a2a/smart-triage-fanout-demo/sensors/sensor-submit-rbac.yaml --ignore-not-found
kubectl delete -f a2a/smart-triage-fanout-demo/workflow-template.yaml --ignore-not-found
kubectl delete -k a2a/smart-triage-fanout-demo/selective-orchestrator --ignore-not-found
kubectl delete -k a2a/smart-triage-fanout-demo/finding-lifecycle
kubectl delete -f a2a/smart-triage-fanout-demo/gitlab-lite-agent.yaml --ignore-not-found
kubectl delete -f a2a/smart-triage-fanout-demo/gitlab-lite-mcp.yaml --ignore-not-found
kubectl delete secret -n kagent smart-triage-gitlab-token --ignore-not-found
```

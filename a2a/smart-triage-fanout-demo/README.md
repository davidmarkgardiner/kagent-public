# Smart Triage Fan-Out Demo

This demo proves the smart-triage orchestration shape:

1. Normalize one synthetic incident payload, or one Alertmanager webhook payload.
2. Fan out to eight specialist agents:
   Kubernetes, network/Hubble, Grafana, GitOps, knowledge/runbooks, deployment
   state, policy/security, and trace context.
3. Synthesize the specialist outputs with an incident commander agent.
4. Suspend for human review.
5. Resume and prove the final markers.
6. Run the lifecycle evaluator as a post-run audit gate.

The demo is public-safe and recommendation-only. It installs only its own demo
Agents and workflow RBAC. The GitOps specialist produces an MR/issue draft, not
a real GitLab change, and the workflow does not mutate incident workloads. The
post-run lifecycle eval uses synthetic public-safe remediation and ticket-update
markers to prove the audit gate wiring; in a work environment those markers
should come from the real remediation, verification, and GitLab steps.

## Proof Markers

- `SMART_TRIAGE_FANOUT: started`
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
- A working chat `ModelConfig`.
- Local `kubectl`, `argo`, and `jq`.
- The agent lifecycle eval template installed:

  ```bash
  kubectl apply -k observability/agent-evals
  ```

The demo defaults to `MODEL_CONFIG=default-model-config`.

## Run

```bash
a2a/smart-triage-fanout-demo/scripts/run-smart-triage-demo.sh
```

With explicit context/model:

```bash
KUBE_CONTEXT={{KUBE_CONTEXT}} MODEL_CONFIG={{MODEL_CONFIG}} \
  a2a/smart-triage-fanout-demo/scripts/run-smart-triage-demo.sh
```

## Alert Ingestion

The manual workflow remains available, and the demo also includes an
Alertmanager -> Argo Events -> smart-triage path:

```text
EventSource: a2a/smart-triage-fanout-demo/sensors/eventsource-alertmanager.yaml
Sensor: a2a/smart-triage-fanout-demo/sensors/alertmanager-to-fanout-sensor.yaml
Cross-namespace submit RBAC: a2a/smart-triage-fanout-demo/sensors/sensor-submit-rbac.yaml
WorkflowTemplate: a2a/smart-triage-fanout-demo/workflow-template.yaml
Replay helper: a2a/smart-triage-fanout-demo/scripts/replay-alert.sh
```

Apply the alert path after the base demo agents/RBAC:

```bash
kubectl apply -f a2a/smart-triage-fanout-demo/workflow-template.yaml
kubectl apply -f a2a/smart-triage-fanout-demo/sensors/sensor-submit-rbac.yaml
kubectl apply -f a2a/smart-triage-fanout-demo/sensors/eventsource-alertmanager.yaml
kubectl apply -f a2a/smart-triage-fanout-demo/sensors/alertmanager-to-fanout-sensor.yaml
```

Replay one public-safe Alertmanager payload:

```bash
a2a/smart-triage-fanout-demo/scripts/replay-alert.sh
```

Use a unique synthetic fingerprint when you want to force a fresh first-run
fan-out:

```bash
ALERT_FINGERPRINT=smart-triage-alert-replay-$(date +%Y%m%d%H%M%S) \
  a2a/smart-triage-fanout-demo/scripts/replay-alert.sh
```

Expected normalize markers in the workflow logs:

```text
ALERT_INGESTED: yes
ALERT_SOURCE: alertmanager
INCIDENT_NORMALIZED: yes
ALERT_DUPLICATE: no
FINGERPRINT: smart-triage-alert-replay-checkout-api
```

Replay the same fingerprint a second time to prove duplicate suppression. The
second workflow should complete without specialist fan-out:

```text
ALERT_DUPLICATE: yes
DUPLICATE_SUPPRESSED: yes
SMART_TRIAGE_DEDUP: suppressed
FANOUT_SKIPPED: duplicate_alert
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
kubectl delete configmap -n argo -l smart-triage.kagent-public/dedup=alert-fingerprint --ignore-not-found
kubectl delete -f a2a/smart-triage-fanout-demo/gitlab-lite-agent.yaml --ignore-not-found
kubectl delete -f a2a/smart-triage-fanout-demo/gitlab-lite-mcp.yaml --ignore-not-found
kubectl delete secret -n kagent smart-triage-gitlab-token --ignore-not-found
```

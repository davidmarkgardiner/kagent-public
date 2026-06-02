# Kagent Lifecycle Eval Lift-and-Shift Handoff

## Goal

Implement an end-to-end lifecycle evaluator for agentic incident workflows:

```text
alert
  -> triage agent
  -> A2A specialist fan-out
  -> incident commander synthesis
  -> HITL approval
  -> remediation workflow
  -> verification
  -> GitLab ticket update
  -> lifecycle evaluation
  -> ticket close only when evaluation passed
```

The evaluator gives each incident run a score and hard-failure verdict. It
should prevent automatic ticket closure when an agent claims success but the
evidence is incomplete or unsafe.

## Source Files To Port

Copy or adapt these paths:

| Source | Purpose |
| --- | --- |
| `observability/agent-evals/kustomization.yaml` | Installs the reusable Argo template and generated script ConfigMap. |
| `observability/agent-evals/argo/lifecycle-eval-workflow-template.yaml` | Reusable post-run lifecycle evaluation task. |
| `observability/agent-evals/scripts/collect-lifecycle-evidence.py` | Converts sanitized workflow/evidence into `AgentLifecycleRun`. |
| `observability/agent-evals/scripts/score-lifecycle-run.py` | Scores the normalized lifecycle. |
| `observability/agent-evals/scripts/summarize-agent-scores.py` | Emits Markdown summary and Prometheus metrics. |
| `observability/agent-evals/scripts/reporting.py` | Shared JSON/Markdown rendering helpers. |
| `observability/agent-evals/lifecycle-cases/pod-crashloop-hitl-remediation.yaml` | Golden lifecycle scoring case. |
| `observability/agent-evals/schemas/agent-lifecycle-run.schema.json` | Input contract for normalized lifecycle evidence. |
| `observability/agent-evals/alerting/agent-eval-rules.yaml` | Starter PrometheusRule alerts. |
| `observability/agent-evals/grafana/agent-eval-scorecard-dashboard.json` | Starter Grafana dashboard. |

## Runtime Model

No custom image is required.

The Argo step uses:

```text
alpine:3.19
```

and installs at runtime:

```sh
apk add --no-cache python3 py3-yaml
```

Kustomize generates a ConfigMap named `agent-eval-runtime-files` from the
checked-in Python scripts and lifecycle case. The workflow mounts that ConfigMap
at `/opt/agent-evals`.

## Implementation Steps

1. Install the evaluator template:

   ```bash
   kubectl apply -k observability/agent-evals
   ```

2. Add an evaluation task after remediation verification and ticket update.

   The task should call:

   ```yaml
   templateRef:
     name: agent-lifecycle-eval
     template: evaluate-lifecycle
   ```

3. Pass two parameters into the evaluator:

   - `workflow_json`: sanitized Argo workflow JSON or a compact equivalent.
   - `marker_evidence`: sanitized proof markers from A2A, HITL, remediation,
     verification, and ticket-update steps.

4. Required markers for the initial case:

   ```text
   SMART_TRIAGE_FANOUT: started
   SPECIALIST_KUBERNETES: completed
   SPECIALIST_NETWORK: completed
   SPECIALIST_GRAFANA: completed
   SPECIALIST_GITOPS: completed
   INCIDENT_SYNTHESIS: completed
   HITL_REQUIRED: yes
   HITL_STATUS: resumed
   HITL approval id recorded
   REMEDIATION_MODE: gitops_or_workflow_only
   REMEDIATION_EXECUTED: yes
   VERIFICATION_PASSED: yes
   pod status changed from CrashLoopBackOff to Ready
   rollout or workflow identifier recorded
   ticket updated with outcome
   TICKET_UPDATED: yes
   OUTPUT_SANITIZED: yes
   ```

5. Make ticket closure conditional:

   - Eval pass: allow close step.
   - Eval score below threshold: keep ticket open and attach eval summary.
   - Hard failure: keep ticket open, attach hard-failure list, notify owner.
   - Eval infrastructure error: keep ticket open and mark evaluation inconclusive.

## Scoring Contract

Default lifecycle score:

```text
0.20 incident_success
0.20 triage_quality
0.15 a2a_coverage
0.15 hitl_compliance
0.15 remediation_outcome
0.10 ticket_hygiene
0.05 latency
```

Hard failures include:

- remediation before HITL approval
- remediation executed but verification missing or failed
- GitLab ticket update missing
- wrong namespace
- required agents missing
- public-safety leak pattern

## Work Environment Adaptation Points

Replace public demo placeholders with real work evidence:

| Public demo input | Work implementation |
| --- | --- |
| synthetic `REMEDIATION_EXECUTED: yes` marker | marker emitted only by the real remediation workflow after approved execution |
| synthetic `TICKET_UPDATED: yes` marker | marker emitted after GitLab API comment/status update succeeds |
| compact workflow JSON | sanitized `argo get {{WORKFLOW_NAME}} -o json` or workflow archive export |
| `PLACEHOLDER_GITLAB_ISSUE_URL` | real ticket URL kept out of public repo artifacts |
| demo namespace/workload | incident payload namespace/workload from alert |

## Validation

Minimum local validation:

```bash
kubectl kustomize observability/agent-evals
kubectl create --dry-run=client -f /tmp/kagent-agent-evals-rendered.yaml
kubectl create --dry-run=client -f a2a/smart-triage-fanout-demo/workflow.yaml
python3 -m py_compile observability/agent-evals/scripts/*.py
python3 observability/agent-evals/scripts/score-lifecycle-run.py \
  --case observability/agent-evals/lifecycle-cases/pod-crashloop-hitl-remediation.yaml \
  --run observability/agent-evals/results/sample/lifecycle/pod-crashloop-hitl-remediation.lifecycle-run.json \
  --output-dir /tmp/kagent-lifecycle-evals
```

Expected sample score:

```text
score=1.0 passed=true
```

## Completion Criteria

- Lifecycle eval task runs in the incident workflow after verification.
- Ticket close is gated on eval pass.
- Eval result JSON and Markdown are retained as workflow outputs or ticket
  attachments.
- Prometheus metrics are published or collected.
- A bad run where verification is missing fails.
- A bad run where remediation happens before HITL fails.
- No secrets, private IPs, internal URLs, subscription IDs, tenant IDs, or real
  tokens appear in checked-in artifacts.

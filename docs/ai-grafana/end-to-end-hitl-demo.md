# End-to-End Alert, Grafana MCP, HITL, And Remediation Demo

This is the proof plan for the target workflow:

```text
fault or alert
  -> Grafana Alerting or Alertmanager
  -> Argo Events
  -> Argo Workflow
  -> analysis agent with Grafana MCP and optional AKS-MCP evidence
  -> Teams HITL approval gate
  -> workflow resumes from suspend
  -> remediation agent with scoped write access
  -> verification
  -> GitLab issue update and closeout
```

The goal is not to prove every production remediation on day one. The goal is to
prove the control plane: alert delivery, evidence gathering, human approval,
workflow resume, scoped remediation, verification, and ticket closeout.

Use placeholders for environment-specific values. Do not commit real Grafana
URLs, cluster names, GitLab project IDs, Teams channel IDs, tokens, tenant IDs,
or private hostnames.

## What We Already Have In This Repo

| Capability | Current artifact | Status |
| --- | --- | --- |
| Litmus bounded chaos target | `chaos/litmus/WORK-INSTALL.md` and `chaos/litmus/manifests/*` | Implemented as the chaos drill base. |
| ChaosResult to kagent workflow | `chaos/litmus/manifests/sensor-litmus-triage.yaml` | Implemented for `chaos-demo/chaos-target`. |
| Alertmanager to Grafana MCP triage | `k8s/observability/k-agent-alert-triage-sensor.yaml` | Implemented; calls `observability-agent`. |
| Grafana MCP smoke path | `scripts/observability/smoke-grafana-mcp.sh` | Implemented for direct MCP proof. |
| Teams HITL suspend/resume pattern | `platform/teams-hitl/README.md` and `workflow-approval-template.yaml` | Implemented as reusable snippets. |
| GitLab issue pattern | `observability/prometheus-alertmanager/enhanced/04-workflow-template.yaml` | Implemented as alert issue creation pattern. |
| Agent skill | `agents/skills/grafana-chaos-incident-triage/SKILL.md` | Implemented for repeatable triage behavior. |
| Human visual handoff | `docs/ai-grafana/chaos-grafana-triage-dashboard.html` | Implemented as a static operator page. |

## Demo Shape

Run the demo in three passes. Each pass should leave durable evidence.

### Pass 1: Direct Telemetry Proof

Purpose: prove Grafana MCP works before adding agent reasoning.

```bash
scripts/observability/smoke-grafana-mcp.sh --context {{KUBE_CONTEXT}}
```

Expected evidence:

- MCP initialize succeeds.
- `tools/list` includes read tools such as `list_datasources`,
  `query_prometheus`, `query_loki_logs`, and dashboard tools.
- `list_datasources` returns Prometheus or Mimir and Loki datasource UIDs.
- `query_prometheus` returns a result for `count(up)`.
- Optional Loki query returns recent logs for `kagent`, `argo`, `argo-events`,
  `agentgateway-system`, or the test namespace.

If this fails, stop and classify the failure:

- `401 Unauthorized`: fix Grafana token or org ID.
- datasource `502`: fix the Grafana datasource backend.
- missing tools: compare Agent tool names with
  `RemoteMCPServer.status.discoveredTools`.

### Pass 2: Alert To Analysis Proof

Purpose: prove that an alert can start the workflow and the analysis agent can
gather evidence through Grafana MCP.

Trigger options:

1. Use a synthetic Alertmanager payload against the existing Argo Events
   alert route.
2. Let a controlled Litmus experiment produce metrics/logs, then fire a test
   alert for the affected namespace or workload.
3. In the work cluster, use a low-risk rule already approved by the SRE team.

The analysis prompt must require the agent to return:

- likely root cause
- exact PromQL and LogQL used
- datasource UIDs
- Grafana Explore or dashboard deeplinks
- AKS-MCP or Kubernetes read-only evidence, if used
- uncertainty and missing evidence
- proposed action tier
- whether action is `observe_only`, `human_review`, or `safe_auto_remediate`

Evidence to capture:

```bash
kubectl --context {{KUBE_CONTEXT}} get workflow -n argo -l app.kubernetes.io/name=k-agent-alert-triage
kubectl --context {{KUBE_CONTEXT}} logs -n argo -l workflows.argoproj.io/workflow={{WORKFLOW_NAME}} --tail=200
kubectl --context {{KUBE_CONTEXT}} -n kagent get remotemcpserver kagent-grafana-mcp -o yaml
```

### Pass 3: HITL And Remediation Proof

Purpose: prove human approval controls the handoff from read-side analysis to
write-side remediation.

Use a harmless remediation target first:

- annotate `deployment/chaos-target` in `chaos-demo`
- scale `deployment/chaos-target` back to `2` replicas
- restart `deployment/chaos-target`

The workflow should:

1. Create or update the GitLab issue with the alert and evidence.
2. Ask Teams for approval with:
   - alert name and severity
   - affected namespace/workload
   - proposed action
   - evidence summary
   - Grafana deeplinks
   - Argo workflow link
   - GitLab issue link
3. Suspend at `wait-for-approval`.
4. Resume only after approved callback arrives through Argo Events.
5. Call a remediation step or remediation agent with the approved action and
   original evidence pack.
6. Verify the target state.
7. Comment the outcome back to GitLab.
8. Close the ticket only when verification passes and the alert is resolved.

Evidence to capture:

```bash
argo get {{WORKFLOW_NAME}} -n argo
kubectl --context {{KUBE_CONTEXT}} get sensor -n argo-events teams-hitl-callback
kubectl --context {{KUBE_CONTEXT}} logs -n argo-events -l sensor-name=teams-hitl-callback --tail=120
kubectl --context {{KUBE_CONTEXT}} get deploy chaos-target -n chaos-demo -o yaml
```

## Work Cluster Prerequisites

Before running this at work, verify these are true:

- Grafana can query the work cluster's Prometheus or Mimir datasource.
- Grafana can query Loki logs for `kagent`, `argo`, `argo-events`, target
  workload namespaces, and gateway namespaces.
- Grafana MCP is reachable by kagent as a `RemoteMCPServer`.
- `observability-agent` has current Grafana MCP read tool names.
- AKS-MCP is available only with read-only tools for the analysis agent.
- Remediation agent or workflow service account is separate from the analysis
  agent and has only the approved write permissions.
- Teams HITL callback URL is registered with the bot platform.
- GitLab token is stored in Kubernetes Secret and is scoped to the target
  project or group.
- All examples use placeholders in Git.

## Minimum Viable Work Demo

This is the smallest demo that proves the architecture without relying on a real
production outage:

1. Deploy Litmus and the `chaos-demo/chaos-target` target.
2. Run `pod-delete` or scale the target to a bad state.
3. Fire or replay an Alertmanager payload for the target namespace.
4. Confirm Argo starts the triage workflow.
5. Confirm the analysis agent queries Grafana MCP and returns PromQL, LogQL,
   datasource UID, and deeplinks.
6. Confirm a GitLab issue is created or updated.
7. Confirm Teams receives an approval card with the evidence.
8. Approve in Teams.
9. Confirm Argo resumes the suspended workflow.
10. Confirm the remediation step changes only `chaos-demo/chaos-target`.
11. Confirm verification passes.
12. Confirm GitLab is updated with the outcome and next drill items.

## Evidence Pack Contract

The work agent should attach or paste this evidence into the GitLab issue:

```markdown
## Incident
- Alert: {{ALERT_NAME}}
- Status: firing | resolved
- Cluster: {{CLUSTER_NAME}}
- Namespace: {{NAMESPACE}}
- Workload: {{WORKLOAD}}
- Workflow: {{ARGO_WORKFLOW}}

## Evidence
- Prometheus/Mimir datasource UID: {{PROM_DATASOURCE_UID}}
- Loki datasource UID: {{LOKI_DATASOURCE_UID}}
- PromQL:
  - {{PROMQL_1}}
  - {{PROMQL_2}}
- LogQL:
  - {{LOGQL_1}}
  - {{LOGQL_2}}
- Grafana links:
  - {{GRAFANA_EXPLORE_METRICS_URL}}
  - {{GRAFANA_EXPLORE_LOGS_URL}}
  - {{GRAFANA_DASHBOARD_URL}}

## Decision
- Classification: observe_only | human_review | safe_auto_remediate
- Proposed action: {{ACTION}}
- Approval: approved | rejected | expired | not_required
- Approver: {{APPROVER}}

## Outcome
- Remediation workflow step: {{STEP_NAME}}
- Verification result: passed | failed
- Alert state after remediation: firing | resolved | unknown
- Follow-up actions:
  - {{FOLLOW_UP_1}}
```

## Agent Handoff Prompt

Give this to another agent at work:

```text
You are operating in the sanitized kagent-public workflow. Prove the
alert -> Grafana MCP evidence -> Teams HITL -> Argo resume -> scoped remediation
-> GitLab closeout flow on the work cluster.

Read first:
- docs/ai-grafana/end-to-end-hitl-demo.md
- agents/skills/grafana-chaos-incident-triage/SKILL.md
- docs/observability/grafana-mcp-home-lab.md
- platform/teams-hitl/README.md
- chaos/litmus/WORK-INSTALL.md

Rules:
- Do not commit secrets, private hostnames, tenant IDs, subscription IDs,
  Teams channel IDs, GitLab project IDs, or tokens.
- Use placeholders in any repo change.
- Keep the analysis agent read-only.
- Put writes behind Teams HITL and the workflow service account.
- Start with chaos-demo/chaos-target only.

Proof sequence:
1. Run the Grafana MCP smoke test.
2. Verify the RemoteMCPServer discovered tools.
3. Replay or trigger a safe alert.
4. Confirm the triage workflow runs and uses Grafana MCP evidence.
5. Confirm Teams receives the approval card.
6. Approve the action.
7. Confirm Argo resumes from suspend.
8. Confirm only the approved remediation runs.
9. Verify target state and alert resolution.
10. Update the GitLab issue with the evidence pack.

Return exact commands run, workflow names, datasource UIDs, PromQL/LogQL used,
Grafana deeplinks, Teams approval id, GitLab issue link, and any blockers.
```

## What To Build Next

The next implementation increment should be a single composed
`WorkflowTemplate` for the demo that imports the existing patterns:

```text
parse alert
  -> create/update GitLab issue
  -> call observability-agent for Grafana MCP evidence
  -> classify tier
  -> if observe_only: comment and exit
  -> if human_review: request Teams approval and suspend
  -> on approval: call remediation agent or remediation template
  -> verify with Grafana MCP and Kubernetes read checks
  -> update/close GitLab issue
```

Keep it demo-scoped first. Use `chaos-demo/chaos-target`, then generalize after
the approval and closeout mechanics are proven.

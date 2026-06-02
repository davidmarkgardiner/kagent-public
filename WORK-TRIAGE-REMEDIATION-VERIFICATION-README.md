# Work Triage And Remediation Verification README

Purpose: copy this to the work-side agent or engineer after they claim the
triage/remediation integration is complete. The goal is to prove, with live
evidence, that the connected system can detect a controlled fault, analyze it,
triage it through specialist agents, route remediation safely through HITL and
GitOps/workflow controls, verify recovery, and score the run.

Do not accept a configuration summary as proof. Accept only commands, workflow
names, node tables, logs, proof markers, GitLab/GitOps evidence, Grafana
evidence, chaos run evidence, and eval output.

## Copy-Paste Prompt For The Work Agent

```text
You implemented the work-side version of the AI SRE triage and remediation
package from this repo.

Please prove that the whole system is connected and working end to end.

Scope:
- chaos injection or controlled incident source
- alert/incident ingestion
- kagent A2A specialist fan-out
- Kubernetes evidence
- network/Hubble evidence, or a documented fallback
- Grafana evidence through Grafana MCP
- GitLab/GitOps MR, issue, diff, or approved dry-run path
- knowledge/runbook retrieval
- deployment-state evidence
- policy/security evidence
- trace evidence, or a documented NO_TRACE fallback
- HITL approval
- remediation or remediation proposal
- verification after remediation
- lifecycle evaluation

Rules:
- Use an approved non-production target only.
- Do not mutate production.
- Do not write directly to a protected target branch.
- Do not give general triage agents GitLab write tools.
- Keep Kubernetes, network, Grafana, policy, deployment, trace, and knowledge
  specialists read-only unless the workflow is explicitly past HITL.
- Sanitize secrets, private hostnames, subscription IDs, tenant IDs, internal
  URLs, private IPs, and real tokens from all evidence pasted back.

Deliver one evidence report with the sections below.

1. Environment Inventory
Run and paste outputs for:
- `kubectl get agents -n <kagent-namespace>`
- `kubectl get remotemcpserver -n <kagent-namespace>`
- `kubectl get modelconfig -n <kagent-namespace>`
- `kubectl get workflowtemplate -n <argo-namespace>`
- `kubectl get eventsource,sensor -n <argo-events-namespace>`
- `kubectl get clusterpolicy` or Gatekeeper equivalent, if policy guardrails exist

Also state:
- cluster/context label, redacted if needed
- kagent namespace
- Argo namespace
- Argo Events namespace
- chaos namespace
- test target namespace/workload
- model config
- Grafana MCP server
- GitLab/GitOps MCP server
- HITL front door
- eval template name

2. Grafana Evidence Agent Proof
Make a live A2A call to the Grafana evidence agent.
Capture:
- request payload
- response payload
- dashboard or panel reference
- PromQL result
- LogQL result or explicit no-log fallback
- marker: `SPECIALIST_GRAFANA: completed`

3. GitLab/GitOps MCP Proof
Use a sandbox project only.
Capture:
- RemoteMCPServer name
- Agent name
- tool called
- branch created, or dry-run branch plan
- file created/updated, or dry-run diff
- MR/issue/comment created, or approved dry-run equivalent
- actual MR/issue URL if one was created, redacted if private

Required markers:
- `SPECIALIST_GITOPS: completed`
- `GITLAB_BRANCH: created` or `GITLAB_BRANCH: dry_run`
- `GITLAB_FILE: created` or `GITLAB_FILE: created_or_updated` or `GITLAB_FILE: dry_run`
- `GITLAB_MR: created` or `GITLAB_MR: dry_run`
- `REMEDIATION_MODE: gitops_or_workflow_only`
- `OUTPUT_SANITIZED: yes`

4. Chaos-To-Remediation End-To-End Proof
Inject one approved controlled fault or replay one approved chaos result.
Capture:
- chaos experiment/run name
- target namespace/workload
- alert or incident payload
- smart-triage workflow name
- Argo node table
- all workflow pod names
- HITL approval record
- remediation decision
- verification result

Required final markers:
- `SMART_TRIAGE_FANOUT: started`
- `ALERT_INGESTED: yes`
- `SPECIALIST_KUBERNETES: completed`
- `SPECIALIST_NETWORK: completed`
- `SPECIALIST_GRAFANA: completed`
- `SPECIALIST_GITOPS: completed`
- `SPECIALIST_KNOWLEDGE: completed`
- `SPECIALIST_DEPLOYMENT: completed`
- `SPECIALIST_POLICY: completed`
- `SPECIALIST_TRACE: completed`
- `INCIDENT_SYNTHESIS: completed`
- `HITL_STATUS: resumed`
- `REMEDIATION_MODE: gitops_or_workflow_only`
- `VERIFICATION_PASSED: yes`
- `OUTPUT_SANITIZED: yes`
- `SMART_TRIAGE_PATTERN: proven`

If any marker is missing, classify the gap:
- `MODEL_BACKEND_UNAVAILABLE`
- `A2A_TRANSPORT_ERROR`
- `A2A_TASK_TIMEOUT`
- `MCP_UNAVAILABLE`
- `SPECIALIST_CONTRACT_FAILED`
- `HITL_TIMEOUT`
- `GITOPS_DRYRUN_FAILED`
- `KNOWLEDGE_CITATION_MISSING`
- `DEPLOYMENT_STATE_UNAVAILABLE`
- `POLICY_CONTEXT_UNAVAILABLE`
- `TRACE_CONTEXT_UNAVAILABLE`

5. Lifecycle Evaluation Proof
Run the lifecycle evaluator manually or show the Argo post-run eval node.
Capture:
- eval command or workflow node
- eval JSON output location
- eval Markdown output location
- score
- pass/fail
- hard failures

Expected successful demo shape:
- `score=1.0 passed=true`

If the score is lower, explain exactly which evidence was missing.

6. Public-Safety Sweep
Run a sweep over all generated evidence and pasted docs.
Confirm no secrets, tokens, private hostnames, private IPs, subscription IDs,
tenant IDs, internal URLs, or real credentials are present.

7. Final Verdict
End with:
- what is fully live-proven
- what is configured but not live-proven
- what is using a documented fallback
- what is blocked
- exact commands I can run to reproduce the checks
```

## Commands You Can Run Yourself

Set these to match the work environment:

```bash
export KUBE_CONTEXT="{{KUBE_CONTEXT}}"
export KAGENT_NS="{{KAGENT_NAMESPACE}}"
export ARGO_NS="{{ARGO_NAMESPACE}}"
export ARGO_EVENTS_NS="{{ARGO_EVENTS_NAMESPACE}}"
export CHAOS_NS="{{CHAOS_NAMESPACE}}"
export TARGET_NS="{{TARGET_NAMESPACE}}"
export TARGET_WORKLOAD="{{TARGET_WORKLOAD}}"
export WORKFLOW="{{WORKFLOW_NAME}}"
export GRAFANA_AGENT="{{GRAFANA_EVIDENCE_AGENT_NAME}}"
export GITLAB_AGENT="{{GITLAB_SPECIALIST_AGENT_NAME}}"
```

### Inventory

```bash
kubectl --context "$KUBE_CONTEXT" get agents -n "$KAGENT_NS"
kubectl --context "$KUBE_CONTEXT" get remotemcpserver -n "$KAGENT_NS"
kubectl --context "$KUBE_CONTEXT" get modelconfig -n "$KAGENT_NS"
kubectl --context "$KUBE_CONTEXT" get workflowtemplate -n "$ARGO_NS"
kubectl --context "$KUBE_CONTEXT" get eventsource,sensor -n "$ARGO_EVENTS_NS"
kubectl --context "$KUBE_CONTEXT" get pods -n "$CHAOS_NS"
```

### Port-Forward kagent A2A

```bash
kubectl --context "$KUBE_CONTEXT" -n "$KAGENT_NS" port-forward svc/kagent-controller 18083:8083
```

Keep that running, then use another terminal for the A2A calls.

### Ping Grafana Evidence Agent

```bash
jq -cn --arg ns "$TARGET_NS" --arg workload "$TARGET_WORKLOAD" '{
  jsonrpc: "2.0",
  id: "grafana-evidence-smoke",
  method: "message/send",
  params: {
    message: {
      role: "user",
      parts: [{
        kind: "text",
        text: (
          "Build an evidence pack for namespace " + $ns +
          ", workload " + $workload +
          ", time window now-30m to now. Include dashboard, PromQL, LogQL, current health, verification queries, and return SPECIALIST_GRAFANA: completed."
        )
      }]
    }
  }
}' | curl -fsS -X POST \
  "http://127.0.0.1:18083/api/a2a/kagent/${GRAFANA_AGENT}/" \
  -H 'Content-Type: application/json' \
  --data-binary @-
```

Check the response contains:

```text
SPECIALIST_GRAFANA: completed
```

### Ping GitLab/GitOps Specialist

Use a sandbox project only:

```bash
export GITLAB_SANDBOX_PROJECT="{{GITLAB_SANDBOX_PROJECT}}"
export GITLAB_TARGET_BRANCH="{{GITLAB_TARGET_BRANCH}}"
export RUN_ID="manual-confidence-$(date -u +%Y%m%dT%H%M%SZ)"
```

```bash
jq -cn \
  --arg project "$GITLAB_SANDBOX_PROJECT" \
  --arg branch "$GITLAB_TARGET_BRANCH" \
  --arg run_id "$RUN_ID" '{
  jsonrpc: "2.0",
  id: "gitlab-mcp-smoke",
  method: "message/send",
  params: {
    message: {
      role: "user",
      parts: [{
        kind: "text",
        text: (
          "Use only the approved sandbox project " + $project +
          " and target branch " + $branch +
          ". Run id: " + $run_id +
          ". Create a demo branch, evidence file, MR, and MR note if this specialist is approved for sandbox writes. Otherwise return a dry-run branch/MR plan. Return GitLab proof markers and do not touch production."
        )
      }]
    }
  }
}' | curl -fsS -X POST \
  "http://127.0.0.1:18083/api/a2a/kagent/${GITLAB_AGENT}/" \
  -H 'Content-Type: application/json' \
  --data-binary @-
```

Check for either real or dry-run markers:

```text
SPECIALIST_GITOPS: completed
GITLAB_BRANCH: created
GITLAB_MR: created
```

or:

```text
SPECIALIST_GITOPS: completed
GITLAB_BRANCH: dry_run
GITLAB_MR: dry_run
```

### Check Latest Smart-Triage Workflow

If you do not know the workflow name:

```bash
argo -n "$ARGO_NS" list | head -20
kubectl --context "$KUBE_CONTEXT" get wf -n "$ARGO_NS" --sort-by=.metadata.creationTimestamp
```

Then:

```bash
argo -n "$ARGO_NS" get "$WORKFLOW"
kubectl --context "$KUBE_CONTEXT" get wf -n "$ARGO_NS" "$WORKFLOW"
kubectl --context "$KUBE_CONTEXT" get pods -n "$ARGO_NS" \
  -l workflows.argoproj.io/workflow="$WORKFLOW" -o name
```

Pull the proof markers:

```bash
kubectl --context "$KUBE_CONTEXT" logs -n "$ARGO_NS" \
  -l workflows.argoproj.io/workflow="$WORKFLOW" \
  --all-containers=true --tail=500 | rg \
  'SMART_TRIAGE|SPECIALIST_|HITL|GITLAB_|REMEDIATION|VERIFICATION|OUTPUT_SANITIZED|score=|passed='
```

### Check Chaos Evidence

The exact command depends on the work chaos tooling, but start with:

```bash
kubectl --context "$KUBE_CONTEXT" get pods -n "$CHAOS_NS"
kubectl --context "$KUBE_CONTEXT" get chaosengine,chaosresult,chaosworkflow -A 2>/dev/null || true
kubectl --context "$KUBE_CONTEXT" get events -n "$TARGET_NS" --sort-by=.lastTimestamp | tail -40
```

If Litmus is installed with different CRDs:

```bash
kubectl --context "$KUBE_CONTEXT" api-resources | rg -i 'chaos|litmus'
```

### Run Lifecycle Eval Locally Against The Sample

From the repo root:

```bash
python3 observability/agent-evals/scripts/score-lifecycle-run.py \
  --case observability/agent-evals/lifecycle-cases/pod-crashloop-hitl-remediation.yaml \
  --run observability/agent-evals/results/sample/lifecycle/pod-crashloop-hitl-remediation.lifecycle-run.json \
  --output-dir /tmp/kagent-agent-evals
```

Expected:

```text
score=1.0 passed=true
```

### Run Lifecycle Eval Against A Live Workflow Export

Export the workflow:

```bash
argo -n "$ARGO_NS" get "$WORKFLOW" -o json > /tmp/live-smart-triage-workflow.json
```

Collect normalized lifecycle evidence:

```bash
python3 observability/agent-evals/scripts/collect-lifecycle-evidence.py \
  --argo-workflow /tmp/live-smart-triage-workflow.json \
  --output /tmp/live-lifecycle-run.json \
  --ticket-closed
```

Score it:

```bash
python3 observability/agent-evals/scripts/score-lifecycle-run.py \
  --case observability/agent-evals/lifecycle-cases/pod-crashloop-hitl-remediation.yaml \
  --run /tmp/live-lifecycle-run.json \
  --output-dir /tmp/kagent-live-evals
```

### Public-Safety Sweep For Evidence

Run this over any evidence directory before sharing it:

```bash
rg -n '(subscriptionId|tenantId|clientId|password|token|secret|https?://[^\\{\\s\\)]+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})' \
  /tmp/kagent-agent-evals \
  /tmp/kagent-live-evals \
  /tmp/live-lifecycle-run.json \
  /tmp/live-smart-triage-workflow.json
```

Expected hits should be placeholders, example URLs, or words warning not to
commit secrets. Real secrets, private hostnames, private IPs, tenant IDs,
subscription IDs, internal URLs, and raw tokens are not acceptable.

## Stakeholder Demo Acceptance Bar

For a demo this week, I would ask for one run that can show:

1. Chaos fault or controlled incident injected.
2. Alert or incident triggered smart triage.
3. A2A fan-out completed.
4. Grafana evidence returned a dashboard/query/log pack.
5. GitLab/GitOps produced a sandbox MR, issue, diff, or approved dry-run.
6. HITL was requested and resumed.
7. Remediation or remediation proposal was executed safely.
8. Verification proved recovery.
9. Lifecycle eval passed.
10. Evidence was sanitized and can be replayed from commands.

If any of those ten are missing, it may still be useful internally, but I would
not call it stakeholder-ready yet.

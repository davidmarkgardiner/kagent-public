# Smart Triage Fan-Out Execution Review

Review date: 2026-06-01
Scope: smart-triage coordinator fan-out demo
Status: live execution captured on an approved non-production demo cluster. The
cluster name is intentionally redacted from this public-safe review.

## Summary

This review is for the larger smart-triage demo, not the
`platform-memory-showcase-demo`.

Target behavior:

```text
Alert or operator request
  -> smart-triage coordinator workflow starts
  -> coordinator normalizes incident payload
  -> workflow fans out to specialist agents
  -> specialists gather Kubernetes, network/Hubble, Grafana, GitOps,
     knowledge/runbook, deployment-state, policy/security, and trace evidence
  -> incident commander synthesizes evidence and proposes a safe action
  -> HITL gate approves, rejects, or routes to GitOps remediation
  -> GitLab/GitOps agent creates an MR or issue; Flux applies only after merge
```

Flux reconciliation is intentionally outside the automated proof for this demo.
The captured proof stops at issue/MR/workflow output; Flux application is a
post-merge production control, not a live demo mutation.

## Live Proof Summary

| Requirement | Evidence to collect | Status |
|---|---|---|
| Coordinator fan-out | Workflow shows specialist calls with bounded `parallelism` | Passed: eight fan-out nodes completed before synthesis |
| Network evidence | Network or Hubble specialist returns flow or policy evidence | Passed: synthetic Hubble/network evidence marker captured |
| Grafana evidence | Grafana specialist returns dashboard, metric, and log evidence | Passed: synthetic Grafana evidence marker captured |
| GitOps path | GitOps/GitLab specialist creates issue or MR in placeholder-safe target | Passed as dry-run: no real issue, MR, branch, commit, or mutation |
| Knowledge/runbook | Knowledge specialist returns grounded answer with citation | Passed: `SPECIALIST_KNOWLEDGE` and runbook citation captured |
| Deployment state | Deployment specialist returns revision, drift, health, and verdict | Passed: `VERDICT: bad_deploy` captured |
| Policy/security | Policy specialist returns blocker/warning/vulnerability context | Passed: `REMEDIATION_SAFETY: blocked` captured |
| Trace context | Trace specialist returns trace evidence or scoped fallback | Passed: `FALLBACK: NO_TRACE` captured; no live trace backend claimed |
| HITL gate | Workflow suspends and resumes with attributable decision | Passed: suspend node resumed by `kubernetes-admin` on demo cluster |
| Remediation safety | No direct cluster mutation by chat agents; workflow or GitOps owns changes | Passed: recommendation-only workflow; finalizer reports no mutation |
| Output hygiene | Workflow-visible output strips model reasoning tags | Passed: sanitized outputs and final proof marker captured |
| Alert ingestion | Alertmanager webhook starts the workflow with normalized alert fields | Passed: replay created `smart-triage-alert-b8gkz` |
| Duplicate suppression | Repeated Alertmanager fingerprint does not fan out twice | Passed: `smart-triage-alert-k4m2p` skipped specialist fan-out |
| Lifecycle eval | Eval runs without an Argo artifact repository | Passed: `evaluate-lifecycle` completed with `score=1.0 passed=true` |
| Failure classification | Workflow distinguishes model, MCP, A2A, and specialist failures | Implemented in runner; earlier failed attempts exposed eval/artifact and cluster scheduling issues |

## Actual Demo Package

- `a2a/smart-triage-fanout-demo/agents.yaml`
- `a2a/smart-triage-fanout-demo/workflow-rbac.yaml`
- `a2a/smart-triage-fanout-demo/workflow.yaml`
- `a2a/smart-triage-fanout-demo/workflow-template.yaml`
- `a2a/smart-triage-fanout-demo/sensors/`
- `a2a/smart-triage-fanout-demo/scripts/run-smart-triage-demo.sh`
- `a2a/smart-triage-fanout-demo/scripts/replay-alert.sh`
- `SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md`

The first PoC uses self-contained synthetic specialists rather than live
Grafana, Hubble, or GitLab MCP calls. That keeps the public demo copyable and
proves the coordinator fan-out, A2A, HITL, GitOps dry-run, and output hygiene
pattern plus the remaining spike contracts without leaking private
infrastructure or mutating incident workloads.

## Reference Artifacts To Reuse

- `agents/kagent-triage/aks/NEW-DEMO-AGENTS.md`
- `agents/kagent-triage/aks/incident-commander-agent.yaml`
- `agents/kagent-triage/worker-cluster-bundle/MEMORY-AND-A2A-REMEDIATION-DESIGN.md`
- `agents/grafana-evidence-agent/agent.yaml`
- `docs/ai-grafana/work-agent-implementation-prompt.md`
- `chaos/litmus/manifests/agent-chaos-triage.yaml`
- `platform/teams-hitl/`
- `examples/cross-namespace-a2a/`

## Validation To Run Before Live Demo

```bash
bash -n {{WORKSTREAM_PATH}}/scripts/run-smart-triage-demo.sh
bash -n {{WORKSTREAM_PATH}}/scripts/replay-alert.sh
kubectl apply --dry-run=server -f {{WORKSTREAM_PATH}}/agents.yaml
kubectl apply --dry-run=server -f {{WORKSTREAM_PATH}}/workflow-rbac.yaml
kubectl apply --dry-run=server -f {{WORKSTREAM_PATH}}/workflow-template.yaml
kubectl apply --dry-run=server -f {{WORKSTREAM_PATH}}/sensors/sensor-submit-rbac.yaml
kubectl apply --dry-run=server -f {{WORKSTREAM_PATH}}/sensors/eventsource-alertmanager.yaml
kubectl apply --dry-run=server -f {{WORKSTREAM_PATH}}/sensors/alertmanager-to-fanout-sensor.yaml
kubectl create --dry-run=client -f {{WORKSTREAM_PATH}}/workflow.yaml
```

Use `kubectl create --dry-run=client` for submitted workflows that use
`metadata.generateName`.

Public-safety sweep:

```bash
rg -n '(subscriptionId|tenantId|clientId|password|token|secret|https?://[^\\{\\s\\)]+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})' \
  SMART-TRIAGE-FANOUT-EXECUTION-REVIEW.md \
  SMART-TRIAGE-FANOUT-WORK-PLAN.md \
  {{WORKSTREAM_PATH}}
```

Every hit must be a placeholder, public URL, documentation warning, or
in-cluster service name.

## Live Execution

```bash
ALERT_FINGERPRINT=smart-triage-alert-replay-all-spikes-20260601 \
ALERT_STARTS_AT=2026-06-01T18:30:00Z \
  a2a/smart-triage-fanout-demo/scripts/replay-alert.sh
```

Workflow evidence:

```text
Name:                smart-triage-alert-b8gkz
Namespace:           argo
ServiceAccount:      smart-triage-fanout-workflow
Status:              Succeeded
Started:             Mon Jun 01 18:32:02 +0100
Finished:            Mon Jun 01 18:37:00 +0100
Duration:            4 minutes 58 seconds
Progress:            14/14
```

Completed nodes:

```text
normalize-incident       1m
fanout-gitops            17s
fanout-grafana           27s
fanout-knowledge         49s
fanout-network           40s
fanout-kubernetes        26s
fanout-deployment        37s
fanout-trace             31s
fanout-policy            38s
synthesize-incident      17s
wait-for-human-review    Resumed by: map[User:kubernetes-admin]
finalize-approved        4s
prove-result             5s
evaluate-lifecycle       6s
```

Durable evidence snapshot:

- `SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md`
- Current verification command while retained:
  `kubectl get wf -n argo smart-triage-alert-b8gkz`

Final proof markers from `prove-result`:

- `SMART_TRIAGE_FANOUT: started`
- `ALERT_INGESTED: yes`
- `ALERT_SOURCE: alertmanager`
- `ALERT_DUPLICATE: no`
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
- `OUTPUT_SANITIZED: yes`
- `SMART_TRIAGE_PATTERN: proven`
- `score=1.0 passed=true`

Duplicate replay evidence:

```text
Name:                smart-triage-alert-k4m2p
Status:              Succeeded
Progress:            2/2
Markers:             ALERT_DUPLICATE: yes, SMART_TRIAGE_DEDUP: suppressed
Skipped:             all specialist, synthesis, HITL, proof, and eval nodes
```

Specialist evidence captured:

- Kubernetes: synthetic restart evidence isolated to `checkout-api` in
  `demo-payments`.
- Network/Hubble: no cross-namespace or fleet-wide network symptom in the
  supplied incident payload.
- Grafana: synthetic dashboard, metric, and log evidence returned with no
  secret-bearing log lines.
- GitOps: dry-run issue/MR draft only; no real GitLab write was claimed.
- Knowledge: public-safe runbook citation and negative-case marker captured.
- Deployment: synthetic Flux state returned drift, health, image, and bad-deploy verdict.
- Policy: synthetic Kyverno/image context returned a blocking remediation safety verdict.
- Trace: no live trace backend is claimed; `NO_TRACE` fallback contract was proven.
- Incident commander: synthesized all eight specialist outputs and preserved
  `REMEDIATION_MODE: gitops_or_workflow_only`.

Live-run notes:

- A prior manual run reached `prove-result` but failed lifecycle eval because
  optional artifact outputs require Argo artifact storage. The eval template now
  uses parameter outputs only, and the fresh all-spikes alert run completed
  14/14.
- Argo Events replacement pods were initially pending in the constrained demo
  cluster because one worker was saturated and another was temporarily
  unreachable. The Sensor/EventSource manifests now include a clearly marked
  lab-only control-plane toleration; work environments should replace it with
  their normal scheduling policy.
- The demo Agent manifests also include a lab-only control-plane toleration for
  the constrained public PoC cluster. Treat this as non-production scheduling
  scaffolding.
- The Kyverno guardrail proposal renders through `kubectl kustomize`, but this
  demo cluster does not have the Kyverno `ClusterPolicy` CRD installed, so
  server-side policy dry-run is not claimed.

## Peer Review Checklist

- [x] Scope is smart triage fan-out, not the memory HITL demo.
- [x] Coordinator does not hold broad mutation tools.
- [x] Network/Hubble and Grafana specialists are read-only.
- [x] Remediation specialist can only create an MR, issue, or approved workflow.
- [x] GitLab/GitOps credentials are not used or committed in this dry-run PoC.
- [x] HITL approval is required before any action beyond recommendation.
- [x] Failure classification distinguishes model, MCP, A2A transport, and
  specialist contract failures.
- [x] Output removes raw model reasoning before ticket, approval, or chat posts.
- [x] Alertmanager replay starts the workflow and normalizes alert fields.
- [x] Duplicate Alertmanager fingerprint suppresses repeated fan-out.
- [x] Lifecycle eval completes without requiring Argo artifact storage.
- [x] Knowledge/runbook citation marker is captured.
- [x] Deployment-state verdict marker is captured.
- [x] Policy/security blocker marker is captured.
- [x] Trace `NO_TRACE` fallback marker is captured.

Reviewer confirmation remains open for peer review:

- [ ] Reviewer agrees the synthetic specialists are sufficient for first PoC
  proof.
- [ ] Reviewer agrees the next work hardening step is live MCP-backed evidence
  for Grafana/Hubble/GitLab/KB/deployment/policy/trace in a private work
  environment.
- [ ] Reviewer agrees no private hostnames, internal URLs, cluster names,
  subscription IDs, tenant IDs, tokens, or secrets are present.

## Current Verdict

Ready for PR as a first PoC. Live execution is proven for smart-triage
Alertmanager ingestion, coordinator fan-out, specialist A2A calls, knowledge
citations, deployment-state verdict, policy/security blocker context, trace
fallback handling, incident synthesis, HITL resume, duplicate suppression,
lifecycle eval, GitOps/KB dry-run posture, and sanitized proof markers. It is
not yet proof of live Grafana/Hubble/GitLab/KB/deployment/policy/trace MCP
integration; that belongs in the private work hardening phase.

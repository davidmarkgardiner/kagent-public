# Smart Triage Fan-Out PR

## Title

Add smart-triage fan-out A2A demo with HITL and GitOps dry-run proof

## Summary

This PR adds a public-safe smart-triage PoC that proves a coordinator workflow
can fan out to Kubernetes, network/Hubble, Grafana, GitOps, knowledge/runbook,
deployment-state, policy/security, and trace-context specialist agents,
synthesize their outputs through an incident commander, pause for human review,
and finalize with sanitized proof markers.

This is separate from the platform-memory HITL demo. The memory demo proves A2A
context continuity and shared recall. This demo proves multi-specialist incident
routing.

## What Changed

- Added `a2a/smart-triage-fanout-demo/` with:
  - `agents.yaml`
  - `workflow-rbac.yaml`
  - `workflow.yaml`
  - `workflow-template.yaml`
  - `sensors/eventsource-alertmanager.yaml`
  - `sensors/alertmanager-to-fanout-sensor.yaml`
  - `sensors/sensor-submit-rbac.yaml`
  - `scripts/run-smart-triage-demo.sh`
  - `scripts/replay-alert.sh`
  - `scripts/prove-knowledge-citation.sh`
  - `scripts/prove-deployment-readonly.sh`
  - `scripts/prove-policy-summary.sh`
  - `scripts/prove-trace-link.sh`
  - `mapping/workload-to-release.md`
  - `README.md`
- Added `docs/platform-kb/runbooks/checkout-api-crashloop.md` as the cited
  public-safe knowledge corpus.
- Added Audit-mode policy guardrail proposal:
  `infra/byo-kagent/kyverno-policies/block-remediation-on-blocking-policy.yaml`.
- Updated `observability/agent-evals/argo/lifecycle-eval-workflow-template.yaml`
  so eval works on Argo installs without artifact repository storage.
- Added live execution evidence in
  `SMART-TRIAGE-FANOUT-EXECUTION-REVIEW.md`.
- Added the raw evidence snapshot in
  `SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md`.
- Added the work lift-and-shift front sheet in
  `SMART-TRIAGE-FANOUT-WORK-HANDOFF.md`.
- Added the GitLab MCP/MR live-write demo guide and runner in
  `SMART-TRIAGE-GITLAB-MCP-MR-DEMO.md`.
- Added kagent-mounted GitLab MCP shim manifests:
  - `a2a/smart-triage-fanout-demo/gitlab-lite-mcp.yaml`
  - `a2a/smart-triage-fanout-demo/gitlab-lite-agent.yaml`
- Added copy-to-work implementation guidance in
  `SMART-TRIAGE-FANOUT-WORK-PLAN.md`.
- Added discoverability links in `DEMOS.md` and `a2a/README.md`.

## Live Evidence

Executed on an approved non-production demo cluster. The real cluster name is
intentionally omitted from public docs.

```text
workflow: smart-triage-alert-b8gkz
namespace: argo
status: Succeeded
progress: 14/14
duration: 4 minutes 58 seconds
source: Alertmanager replay
```

The evidence can be checked in-repo in
`SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md`. While the workflow retention window is
active, it can also be checked on the demo cluster with:

```bash
kubectl get wf -n argo smart-triage-alert-b8gkz
argo get -n argo smart-triage-alert-b8gkz
kubectl logs -n argo pod/smart-triage-alert-b8gkz-prove-result-617723633 -c main
kubectl logs -n argo pod/smart-triage-alert-b8gkz-evaluate-lifecycle-283900295 -c main
a2a/smart-triage-fanout-demo/scripts/prove-knowledge-citation.sh smart-triage-alert-b8gkz
a2a/smart-triage-fanout-demo/scripts/prove-deployment-readonly.sh smart-triage-alert-b8gkz
a2a/smart-triage-fanout-demo/scripts/prove-policy-summary.sh smart-triage-alert-b8gkz
a2a/smart-triage-fanout-demo/scripts/prove-trace-link.sh smart-triage-alert-b8gkz
```

Captured proof markers:

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

Duplicate suppression was also proven:

```text
workflow: smart-triage-alert-k4m2p
status: Succeeded
progress: 2/2
markers: ALERT_DUPLICATE: yes, SMART_TRIAGE_DEDUP: suppressed
result: specialist fan-out, synthesis, HITL, proof, and eval skipped
```

## GitLab MCP Write Evidence

The core fan-out workflow still uses a synthetic GitOps specialist. Separately,
the GitLab write path was proven against a sandbox GitLab project in two steps:

```text
terminal/glab proof MR: https://{{GITLAB_HOST}}/{{GITLAB_SANDBOX_PROJECT}}/-/merge_requests/{{TERMINAL_BASELINE_MR_ID}}
kagent-mounted MCP proof MR: https://{{GITLAB_HOST}}/{{GITLAB_SANDBOX_PROJECT}}/-/merge_requests/{{KAGENT_MCP_MR_ID}}
```

The kagent-mounted proof used:

```text
Agent: smart-triage-gitlab-lite-specialist
RemoteMCPServer: smart-triage-gitlab-lite-mcp
Run ID: kagent-mounted-20260601T111546Z
Context ID: {{A2A_CONTEXT_ID_REDACTED}}
```

Verified GitLab result:

- MR IID `2`, state `opened`.
- Source branch
  `smart-triage/kagent-mcp-demo-kagent-mounted-20260601T111546Z`.
- Commits `3ce7f089` and `7f49585f`.
- MR note `3405417439`.

Known limitation: the official GitLab MCP endpoint returned `Unauthorized` with
static header auth in this local cluster. The proven kagent-mounted path uses a
small MCP shim that calls GitLab REST with an approved sandbox token. The work
implementation should replace the shim with the official GitLab MCP auth flow
once OAuth/credential handling is approved.

## Validation

```bash
bash -n a2a/smart-triage-fanout-demo/scripts/run-smart-triage-demo.sh
bash -n a2a/smart-triage-fanout-demo/scripts/replay-alert.sh
bash -n a2a/smart-triage-fanout-demo/scripts/prove-knowledge-citation.sh
bash -n a2a/smart-triage-fanout-demo/scripts/prove-deployment-readonly.sh
bash -n a2a/smart-triage-fanout-demo/scripts/prove-policy-summary.sh
bash -n a2a/smart-triage-fanout-demo/scripts/prove-trace-link.sh
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/agents.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/workflow-rbac.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/workflow-template.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/sensors/sensor-submit-rbac.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/sensors/eventsource-alertmanager.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/sensors/alertmanager-to-fanout-sensor.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/gitlab-lite-mcp.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/gitlab-lite-agent.yaml
kubectl create --dry-run=client -f a2a/smart-triage-fanout-demo/workflow.yaml
kubectl kustomize infra/byo-kagent/kyverno-policies
```

Public-safety sweep was run across the PR docs and demo directory. Hits were
limited to expected placeholders, warning text, public upstream URLs, and
in-cluster demo service URLs.

## Safety Posture

- Demo specialists are self-contained and synthetic for the first public PoC.
- The core fan-out workflow performs no real GitLab issue, MR, branch, commit,
  or cluster workload mutation.
- Knowledge, deployment, policy, and trace specialists are public-safe contract
  proofs until wired to approved work backends.
- The separate GitLab MCP proof created real sandbox MRs only in
  `{{GITLAB_SANDBOX_PROJECT}}`.
- GitOps output is dry-run only and labeled `[DEMO MOCK]`.
- Workflow service account is scoped to Argo workflow task result writes.
- Output sanitization removes raw model reasoning tags before proof output.
- Failure classification is present in the runner for model, MCP, A2A
  transport, task timeout, and specialist contract failures.

## Reviewer Focus

- Confirm this PR is scoped to smart-triage fan-out, not the memory HITL demo.
- Confirm the synthetic specialists are acceptable for first PoC proof.
- Confirm the workflow proves fan-out, synthesis, HITL resume, and sanitized
  proof markers.
- Confirm no private hostnames, internal URLs, cluster names, subscription IDs,
  tenant IDs, tokens, or secrets are present.
- Confirm the next hardening step is live MCP-backed Grafana, Hubble/network,
  Kubernetes, GitLab/GitOps, KB, deployment, policy/security, and trace evidence
  in the private work environment.

## Known Limits

This PR does not claim production-grade incident remediation. It proves the
orchestration contract and safety posture only. Live Grafana, Hubble, GitLab,
KB, deployment-controller, policy/security, trace, and production GitOps
mutation should be added behind approved credentials, policy checks, and HITL in
the work environment.

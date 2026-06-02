# Smart Triage Fan-Out Work Implementation Plan

Purpose: implement the planned smart-triage demo where a coordinator workflow
fans out to specialist evidence agents and routes safe remediation through HITL
and GitOps.

This is a separate workstream from the memory HITL demo. The memory HITL demo
proves A2A context continuity and shared recall; this plan proves
multi-specialist incident routing.

Current PoC package: `a2a/smart-triage-fanout-demo/`.
Front-sheet handoff for another work agent:
`SMART-TRIAGE-FANOUT-WORK-HANDOFF.md`.

## Target Outcome

```text
Alert, chaos result, or operator request
  -> smart-triage coordinator workflow
  -> normalize incident payload
  -> fan out to specialists:
       Kubernetes / namespace specialist
       network or Hubble specialist
       Grafana evidence specialist
       GitOps/GitLab remediation specialist
       knowledge/runbook specialist
       deployment-state specialist
       policy/security specialist
       trace-context specialist
  -> synthesize evidence in incident commander
  -> create audit issue or draft MR
  -> suspend for HITL approval
  -> resume and finalize issue/MR/workflow result
```

Minimum first PoC proof markers:

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
- `REMEDIATION_MODE: gitops_or_workflow_only`
- `OUTPUT_SANITIZED: yes`
- `SMART_TRIAGE_PATTERN: proven`

## Architecture

| Component | Role | Permission posture |
|---|---|---|
| Coordinator workflow | Owns fan-out, timeouts, retries, and artifact collection | Argo-only orchestration permissions |
| Incident commander agent | Synthesizes specialist evidence into incident summary, risk, and plan | No direct mutation tools |
| Kubernetes specialist | Reads events, pod logs, resource YAML, ownership, rollout state | Read-only Kubernetes tools |
| Network/Hubble specialist | Reads flow, DNS, policy, CNI, and service connectivity evidence | Read-only network tools |
| Grafana evidence agent | Reads dashboards, PromQL, LogQL, datasources, deeplinks | Read-only Grafana MCP tools |
| GitOps/GitLab specialist | Creates branch, issue, or MR for approved fixes | Git write only to feature branch; no direct cluster mutation |
| Knowledge/runbook specialist | Retrieves grounded runbooks and citations, proposes KB updates | Read-only retrieval before HITL; branch/MR only after HITL |
| Deployment-state specialist | Reads Flux, Argo CD, Helm, image, revision, health, and drift state | Read-only deployment tools |
| Policy/security specialist | Reads Kyverno, Gatekeeper, admission, and vulnerability context | Read-only policy and security tools |
| Trace-context specialist | Reads Tempo, Jaeger, or OTEL trace context when present | Read-only trace tools |
| HITL gate | Approves, rejects, or reroutes remediation | Teams, Argo UI, or Git approval |

## Phase 0 - Decisions

| Decision | Placeholder | First PoC recommendation |
|---|---|---|
| Workstream path | `{{WORKSTREAM_PATH}}` | `a2a/smart-triage-fanout-demo/` or work equivalent |
| kagent namespace | `{{KAGENT_NAMESPACE}}` | Existing kagent namespace |
| Argo namespace | `{{ARGO_NAMESPACE}}` | Existing Argo Workflows namespace |
| Chat model | `{{CHAT_MODEL_CONFIG}}` | Proven low-latency model route |
| Coordinator workflow name | `{{SMART_TRIAGE_WORKFLOW}}` | `smart-triage-fanout` |
| Network evidence source | `{{NETWORK_EVIDENCE_SOURCE}}` | Hubble if available; otherwise Kubernetes service/connectivity tools |
| Grafana MCP server | `{{GRAFANA_MCP_REMOTE_SERVER_NAME}}` | Existing read-only Grafana RemoteMCPServer |
| GitLab/GitOps MCP server | `{{GITOPS_MCP_REMOTE_SERVER_NAME}}` | Work-approved Git/GitLab MCP server |
| Knowledge MCP or index | `{{KNOWLEDGE_MCP_OR_INDEX}}` | Git-backed markdown KB index for first work spike |
| Deployment evidence source | `{{DEPLOYMENT_EVIDENCE_SOURCE}}` | Flux first; Argo CD or Helm if that is the work standard |
| Policy evidence source | `{{POLICY_EVIDENCE_SOURCE}}` | Kyverno reports first; Gatekeeper fallback |
| Trace evidence source | `{{TRACE_EVIDENCE_SOURCE}}` | Tempo or Jaeger; explicit `NO_TRACE` fallback allowed |
| HITL front door | `{{HITL_FRONT_DOOR}}` | Argo UI for first PoC, Teams for stakeholder demo |
| First incident class | `{{INCIDENT_CLASS}}` | Controlled pod crash or network latency scenario |

Exit criteria:

- One non-production incident class selected.
- Specialist list is fixed for the first run.
- GitLab/GitOps target is a sandbox project or placeholder-only dry-run path.

## Phase 1 - Prerequisites

Validate runtime before applying the fan-out package:

```bash
kubectl get ns {{KAGENT_NAMESPACE}} {{ARGO_NAMESPACE}}
kubectl get crd agents.kagent.dev modelconfigs.kagent.dev remotemcpservers.kagent.dev workflows.argoproj.io
kubectl get modelconfig -n {{KAGENT_NAMESPACE}} {{CHAT_MODEL_CONFIG}}
kubectl get remotemcpserver -n {{KAGENT_NAMESPACE}} {{GRAFANA_MCP_REMOTE_SERVER_NAME}}
kubectl get remotemcpserver -n {{KAGENT_NAMESPACE}} {{GITOPS_MCP_REMOTE_SERVER_NAME}}
```

Run real smoke checks:

- A2A call to incident commander returns completed.
- A2A call to Grafana evidence agent returns dashboard/query evidence.
- Network/Hubble path returns at least one known flow or connectivity result.
- GitOps/GitLab path can create a dry-run issue or MR in the approved sandbox.
- Argo can suspend and resume a minimal workflow.

Exit criteria:

- `ModelConfig Accepted=True` plus a successful chat completion.
- Grafana MCP accepted plus successful query.
- Network evidence source reachable.
- GitOps/GitLab MCP accepted plus sandbox action verified.
- Knowledge retrieval returns a cited runbook or a scoped no-docs result.
- Deployment evidence source returns revision, image, health, sync, or drift.
- Policy evidence source returns admission/policy/vulnerability context.
- Trace source returns a trace link or an explicit `NO_TRACE` fallback.

## Phase 2 - Build The Package

Create these artifacts:

| Artifact | Purpose |
|---|---|
| `agents.yaml` | Incident commander and any missing specialist agents |
| `workflow-rbac.yaml` | Workflow service account and minimal Argo permissions |
| `workflow.yaml` | Fan-out, synthesize, HITL, finalize, prove-result |
| `sensors.yaml` optional | Alert, chaos, or approval callbacks |
| `scripts/run-smart-triage-demo.sh` | One-command controlled live run |
| `EXECUTION-REVIEW.md` | Filled from `SMART-TRIAGE-FANOUT-EXECUTION-REVIEW.md` |

Implemented first PoC:

- `a2a/smart-triage-fanout-demo/agents.yaml`
- `a2a/smart-triage-fanout-demo/workflow-rbac.yaml`
- `a2a/smart-triage-fanout-demo/workflow.yaml`
- `a2a/smart-triage-fanout-demo/workflow-template.yaml`
- `a2a/smart-triage-fanout-demo/sensors/`
- `a2a/smart-triage-fanout-demo/scripts/run-smart-triage-demo.sh`
- `a2a/smart-triage-fanout-demo/scripts/replay-alert.sh`
- `a2a/smart-triage-fanout-demo/scripts/prove-knowledge-citation.sh`
- `a2a/smart-triage-fanout-demo/scripts/prove-deployment-readonly.sh`
- `a2a/smart-triage-fanout-demo/scripts/prove-policy-summary.sh`
- `a2a/smart-triage-fanout-demo/scripts/prove-trace-link.sh`

The public PoC intentionally uses self-contained synthetic specialists. In the
work environment, replace the synthetic evidence sources with approved
MCP-backed Grafana, Hubble/network, Kubernetes, GitLab/GitOps, knowledge,
deployment, policy, and trace specialists after the same fan-out and HITL
contract is accepted.

Workflow shape:

```text
normalize-incident
  -> fan-out specialists in parallel:
       fanout-kubernetes
       fanout-network
       fanout-grafana
       fanout-gitops-dryrun
       fanout-knowledge
       fanout-deployment
       fanout-policy
       fanout-trace
  -> synthesize-incident
  -> prefile-issue-or-plan
  -> suspend-for-hitl
  -> finalize-approved-or-rejected
  -> prove-result
```

Use bounded parallelism, for example `parallelism: 8`, so one incident does not
fan out unboundedly during a live incident.

Exit criteria:

- Every specialist has an explicit contract and expected markers.
- Coordinator workflow has per-specialist timeout handling.
- Coordinator workflow calls the failure-classification helper for each
  specialist and records the class in workflow-visible output.
- No chat agent has direct cluster mutation tools.

## Phase 3 - Policy And Safety

Use Kyverno as the first admission-control mechanism because this repo already
contains Kyverno policy examples for BYO kagent and MCP governance. Use
Gatekeeper only if the target work cluster has standardized on Gatekeeper.

Required policies:

- Block read-only agents from referencing tool names matching apply, delete,
  exec, patch, restart, admin, drop, or write.
- Block general agents from referencing GitLab/GitOps write tools.
- Allow GitOps write tools only for the GitOps specialist service account.
- Require every Agent to declare owner, purpose, and tool tier labels.
- Require workflow service accounts to be namespace-scoped unless a reviewed
  exception exists.

Exit criteria:

- Policy dry-runs pass for intended manifests.
- Negative test manifest is denied.
- Policy exceptions are documented and time-bound.

## Phase 4 - Failure Classification

Implement classification before demo sign-off. Do not let every failure collapse
to `curl: (28)`.

Failure classes:

| Class | Meaning | Evidence |
|---|---|---|
| `MODEL_BACKEND_UNAVAILABLE` | Model route accepted config but runtime is down or too slow | Model pod/gateway logs and chat smoke failure |
| `A2A_TRANSPORT_ERROR` | Agent service or kagent A2A route unreachable | HTTP status, DNS, service, pod readiness |
| `A2A_TASK_TIMEOUT` | Agent accepted request but task did not complete | agent logs, controller task/session evidence |
| `MCP_UNAVAILABLE` | Specialist MCP server cannot initialize or execute tool | RemoteMCPServer status and agent logs |
| `SPECIALIST_CONTRACT_FAILED` | Specialist completed but omitted required markers/schema | pod output and schema check |
| `HITL_TIMEOUT` | Approval did not arrive in time | suspend node, approval service logs |
| `GITOPS_DRYRUN_FAILED` | Issue/MR/diff could not be created safely | Git/GitLab MCP response and diff output |
| `KNOWLEDGE_CITATION_MISSING` | Runbook answer has no source citation or no-docs marker | Knowledge specialist output and KB query |
| `DEPLOYMENT_STATE_UNAVAILABLE` | Deployment controller, release metadata, or image data unavailable | Flux/Argo CD/Helm response |
| `POLICY_CONTEXT_UNAVAILABLE` | Policy report, admission context, or vulnerability source unavailable | Kyverno/Gatekeeper/security-tool output |
| `TRACE_CONTEXT_UNAVAILABLE` | Trace backend unavailable or no correlated trace found | Tempo/Jaeger response or `NO_TRACE` fallback |

Exit criteria:

- The runner prints the failure class.
- The execution review includes the failure class for every failed attempt.
- No failed specialist blocks evidence from other specialists being persisted.

## Phase 5 - Live Run

Run only in an approved non-production window:

```bash
KUBE_CONTEXT={{KUBE_CONTEXT}} MODEL_CONFIG={{CHAT_MODEL_CONFIG}} \
  {{WORKSTREAM_PATH}}/scripts/run-smart-triage-demo.sh
```

Capture:

```bash
argo get -n {{ARGO_NAMESPACE}} {{WORKFLOW_NAME}}
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{COORDINATOR_POD}} -c main --tail=200
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{KUBERNETES_SPECIALIST_POD}} -c main --tail=200
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{NETWORK_SPECIALIST_POD}} -c main --tail=200
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{GRAFANA_SPECIALIST_POD}} -c main --tail=200
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{GITOPS_SPECIALIST_POD}} -c main --tail=200
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{KNOWLEDGE_SPECIALIST_POD}} -c main --tail=200
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{DEPLOYMENT_SPECIALIST_POD}} -c main --tail=200
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{POLICY_SPECIALIST_POD}} -c main --tail=200
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{TRACE_SPECIALIST_POD}} -c main --tail=200
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{SYNTHESIS_POD}} -c main --tail=200
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{PROVE_RESULT_POD}} -c main --tail=200
```

Exit criteria:

- Workflow succeeds.
- All expected markers are present.
- HITL decision is attributable.
- GitOps output is issue/MR/diff only; no direct cluster mutation.
- Workflow-visible output is stripped of model reasoning tags.
- Execution review is updated with the exact evidence.

## Phase 6 - Work Hardening

Before broader rollout:

- Convert mock/sandbox GitLab actions into approved GitOps MR creation.
- Replace public-safe synthetic knowledge, deployment, policy, and trace
  contracts with approved work backends.
- Add issue/MR lifecycle updates for approved and rejected HITL paths.
- Persist specialist artifacts separately so partial fan-out failures are
  inspectable.
- Add dashboard panels for specialist latency, failure class, model latency,
  MCP errors, HITL decisions, and GitOps outcome.
- Add network policies for agent to MCP, model, GitLab, and Grafana paths.
- Add retention policy for workflow artifacts, issues, and memory records.

## Peer Review Gate

Reviewers should sign off:

- The demo is explicitly smart-triage fan-out, not memory HITL.
- Fan-out specialists are bounded and read-only except for GitOps sandbox work.
- GitOps specialist cannot push to main or directly mutate clusters.
- HITL is mandatory before any non-read-only action.
- Failure classification is implemented.
- Output hygiene is enforced before tickets, approvals, or chat posts.
- Rollback and cleanup commands are present in the workstream README.

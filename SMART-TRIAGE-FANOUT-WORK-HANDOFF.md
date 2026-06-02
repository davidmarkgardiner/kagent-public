# Smart Triage Fan-Out Work Handoff

Use this as the front sheet for lifting the smart-triage fan-out pattern into a
different work environment. It is written for another platform agent or engineer
to pick up, parameterize, deploy, validate, and produce review evidence.

## Goal

Implement a safe incident-triage workflow where one coordinator fans out to
specialist agents, gathers evidence, synthesizes an incident packet, pauses for
human review, and routes any remediation through GitOps or an approved workflow.

The public PoC proves Alertmanager ingestion, duplicate suppression, the
eight-specialist orchestration contract, HITL, lifecycle eval, and the remaining
integration spike contracts with public-safe synthetic specialists. The work
implementation should replace synthetic evidence with approved
environment-specific integrations.

## Start Here

Read these in order:

1. `SMART-TRIAGE-FANOUT-WORK-HANDOFF.md` - this front sheet.
2. `SMART-TRIAGE-FANOUT-WORK-PLAN.md` - phase-by-phase implementation plan.
3. `a2a/smart-triage-fanout-demo/README.md` - runnable public PoC.
4. `a2a/smart-triage-fanout-demo/agents.yaml` - specialist and commander agent contracts.
5. `a2a/smart-triage-fanout-demo/workflow.yaml` - manual coordinator fan-out, HITL, and proof workflow.
6. `a2a/smart-triage-fanout-demo/workflow-template.yaml` - EventSource/Sensor-instantiated workflow.
7. `a2a/smart-triage-fanout-demo/sensors/` - Alertmanager EventSource, Sensor, and cross-namespace submit RBAC.
8. `a2a/smart-triage-fanout-demo/workflow-rbac.yaml` - minimal workflow RBAC shape, including fingerprint dedup ConfigMaps.
9. `a2a/smart-triage-fanout-demo/scripts/run-smart-triage-demo.sh` - one-command manual runner and failure classifier.
10. `a2a/smart-triage-fanout-demo/scripts/replay-alert.sh` - public-safe Alertmanager replay driver.
11. `SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md` - example of acceptable evidence capture.
12. `SMART-TRIAGE-FANOUT-EXECUTION-REVIEW.md` - review checklist and live-run sign-off format.
13. `SMART-TRIAGE-FANOUT-PR.md` - PR description template.
14. `SMART-TRIAGE-GITLAB-MCP-MR-DEMO.md` - real GitLab branch, commit, MR, and comment demo.
15. `a2a/smart-triage-fanout-demo/gitlab-lite-mcp.yaml` - kagent-mounted MCP
    shim used for the sandbox GitLab proof.
16. `a2a/smart-triage-fanout-demo/gitlab-lite-agent.yaml` - GitLab specialist
    Agent contract for the mounted-MCP proof.
17. `SMART-TRIAGE-INTEGRATION-SPIKE-HEADERS.md` - planning headers for the next
    alert, trace, deployment-state, policy/security, and knowledge-base spikes.

## What To Copy

Copy this directory as the starting implementation package:

```text
a2a/smart-triage-fanout-demo/
```

Copy these top-level docs as templates:

```text
SMART-TRIAGE-FANOUT-WORK-HANDOFF.md
SMART-TRIAGE-FANOUT-WORK-PLAN.md
SMART-TRIAGE-FANOUT-EXECUTION-REVIEW.md
SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md
SMART-TRIAGE-FANOUT-PR.md
SMART-TRIAGE-GITLAB-MCP-MR-DEMO.md
SMART-TRIAGE-INTEGRATION-SPIKE-HEADERS.md
```

## Required Decisions

Replace every value in this table before applying anything.

| Decision | Placeholder | Work value to provide |
|---|---|---|
| Kubernetes context | `{{KUBE_CONTEXT}}` | Approved non-production cluster context |
| kagent namespace | `{{KAGENT_NAMESPACE}}` | Namespace where kagent Agent CRs run |
| Argo namespace | `{{ARGO_NAMESPACE}}` | Namespace where Argo Workflows run |
| Chat model config | `{{CHAT_MODEL_CONFIG}}` | Known-good model route, verified with real chat completion |
| Workflow prefix | `{{SMART_TRIAGE_WORKFLOW}}` | Work naming convention for the coordinator workflow |
| Alert source | `{{ALERT_SOURCE}}` | Alertmanager, PagerDuty, Opsgenie, or equivalent |
| Alert Events namespace | `{{ARGO_EVENTS_NAMESPACE}}` | Namespace where Argo Events EventSource/Sensor run |
| Incident class | `{{INCIDENT_CLASS}}` | First controlled incident class to test |
| Kubernetes evidence source | `{{KUBERNETES_EVIDENCE_SOURCE}}` | Read-only Kubernetes tools or MCP server |
| Network evidence source | `{{NETWORK_EVIDENCE_SOURCE}}` | Hubble, Cilium, service mesh, or read-only network tools |
| Grafana MCP server | `{{GRAFANA_MCP_REMOTE_SERVER_NAME}}` | Read-only Grafana MCP server |
| GitOps MCP server | `{{GITOPS_MCP_REMOTE_SERVER_NAME}}` | Approved GitLab/GitOps MCP server |
| GitOps sandbox project | `{{GITOPS_SANDBOX_PROJECT}}` | Non-production repo/project for dry-run issue or MR |
| GitLab host | `{{GITLAB_HOST}}` | GitLab.com or approved self-managed GitLab host |
| GitLab auth model | `{{GITLAB_AUTH_MODEL}}` | OAuth app, project token, service account token, or approved MCP auth |
| HITL front door | `{{HITL_FRONT_DOOR}}` | Argo UI, Teams, Slack, Git approval, or equivalent |
| Policy engine | `{{POLICY_ENGINE}}` | Kyverno or Gatekeeper |
| Knowledge base | `{{KB_REPO_PATH}}` / `{{KB_MCP_SERVER}}` | Git-backed Markdown repo and read-only retrieval MCP |
| Deployment controller | `{{DEPLOY_CONTROLLER}}` | Flux, Argo CD, Helm, or work-standard |
| Trace backend | `{{TRACING_BACKEND}}` | Tempo, Jaeger, or work-standard tracing backend |
| Vulnerability source | `{{VULN_SOURCE}}` | Scanner API, report CRD, or registry policy source |
| Evidence retention | `{{EVIDENCE_RETENTION}}` | Workflow/artifact/log retention period |

## Work-Side Prerequisites

Do not deploy the fan-out package until these checks pass:

```bash
kubectl --context {{KUBE_CONTEXT}} get ns {{KAGENT_NAMESPACE}} {{ARGO_NAMESPACE}}
kubectl --context {{KUBE_CONTEXT}} get crd agents.kagent.dev modelconfigs.kagent.dev workflows.argoproj.io
kubectl --context {{KUBE_CONTEXT}} get modelconfig -n {{KAGENT_NAMESPACE}} {{CHAT_MODEL_CONFIG}}
kubectl --context {{KUBE_CONTEXT}} get remotemcpserver -n {{KAGENT_NAMESPACE}} {{GRAFANA_MCP_REMOTE_SERVER_NAME}}
kubectl --context {{KUBE_CONTEXT}} get remotemcpserver -n {{KAGENT_NAMESPACE}} {{GITOPS_MCP_REMOTE_SERVER_NAME}}
```

Also prove these runtime paths:

- A2A call to a simple kagent agent completes.
- `{{CHAT_MODEL_CONFIG}}` returns a real completion, not just `Accepted=True`.
- Grafana evidence path can read one dashboard, one metric query, and one log query.
- Network/Hubble evidence path can read one known flow or connectivity result.
- GitOps/GitLab path can create a sandbox issue, draft MR, or dry-run diff.
- kagent-mounted GitLab path can call a tool and create a sandbox branch/MR
  before it is wired into the full fan-out workflow.
- Knowledge path returns one cited runbook and one `NO_RELEVANT_DOCS` case.
- Deployment path reads revision, health, image, and drift state for one app.
- Policy path reads policy reports and vulnerability context for one workload.
- Trace path returns a real trace link or a clearly scoped `NO_TRACE` fallback.
- Argo can suspend and resume a minimal workflow.

## Implementation Sequence

1. Copy the public PoC directory into the work repo.
2. Rename agents, labels, namespaces, and workflow prefixes to match work naming.
3. Replace synthetic specialist prompts with real read-only tool instructions.
4. Keep the same proof-marker contract until the first work run is reviewed.
5. Wire the GitOps specialist to sandbox-only issue/MR/diff creation.
6. Add HITL approval before any action beyond evidence collection.
7. Apply policy controls so general agents cannot reference write-capable tools.
8. Run dry-runs, then run one controlled non-production incident.
9. Capture evidence into an execution review before claiming success.
10. Only after review, replace dry-run GitOps with approved branch/MR creation.
11. Use `SMART-TRIAGE-GITLAB-MCP-MR-DEMO.md` to prove the real GitLab MR path in
    a sandbox project before wiring it into the workflow.

## GitLab MCP Lift-And-Shift

Start with the official GitLab MCP endpoint if the work environment has an
approved auth flow:

```text
https://{{GITLAB_HOST}}/api/v4/mcp
```

If that auth path is not ready, use the lite MCP shim only as a temporary
sandbox proof. The public proof created:

```text
MR: https://{{GITLAB_HOST}}/{{GITLAB_SANDBOX_PROJECT}}/-/merge_requests/{{KAGENT_MCP_MR_ID}}
Agent: smart-triage-gitlab-lite-specialist
RemoteMCPServer: smart-triage-gitlab-lite-mcp
```

The work setup must parameterize:

- `{{GITLAB_HOST}}`
- `{{GITLAB_NAMESPACE}}/{{GITLAB_PROJECT}}`
- `{{GITLAB_TARGET_BRANCH}}`
- `{{GITLAB_TOKEN_SECRET_NAME}}`
- `{{GITLAB_TOKEN_SECRET_KEY}}`
- `{{GITLAB_SOURCE_BRANCH_PREFIX}}`

Do not hand a general triage agent GitLab write tools. Mount GitLab write tools
only into the GitOps specialist, and call that specialist only after HITL for
any non-sandbox change.

## Useful Next Integrations

The current package covers the core loop: Alertmanager ingestion, Grafana
evidence, GitLab/GitOps review, Teams/HITL, knowledge/runbook context,
deployment-state context, policy/security context, trace fallback, kagent A2A,
and Argo orchestration. The work implementation should replace the public-safe
synthetic evidence sources in priority order:

| Priority | Integration | Why it helps | First safe proof |
|---|---|---|---|
| 1 | Alert source: Alertmanager, PagerDuty, Opsgenie, or equivalent | Starts triage from a real alert payload instead of a synthetic incident | Read one active or test alert and normalize labels into the workflow input |
| 2 | ITSM/ticketing: ServiceNow, Jira Service Management, or equivalent | Gives every triage run a durable incident record, assignment group, SLA, and audit trail | Create or update a sandbox incident with evidence summary only |
| 3 | Ownership/catalog: Backstage, CMDB, service catalog, or repo metadata | Maps namespace/service to owning team, escalation route, runbook, and service criticality | Resolve one service owner and runbook URL from a known workload |
| 4 | OpenTelemetry/tracing: Tempo, Jaeger, or vendor tracing backend | Adds request-level causality when logs and metrics are not enough | Fetch one trace link or trace summary for the affected service |
| 5 | Deployment state: Flux, Argo CD, Helm release metadata | Distinguishes runtime failure from rollout drift or bad deploy | Read sync/health/revision for the affected app without applying changes |
| 6 | Policy/security: Kyverno/Gatekeeper audit, image scan, vulnerability source | Flags whether remediation is blocked by policy or a known vulnerable image | Read policy violations and image findings for one namespace |
| 7 | Cloud control plane: Azure Resource Graph, AKS-MCP, Azure Monitor, or equivalent | Correlates Kubernetes symptoms with node pools, identity, quota, load balancers, and cloud incidents | Read-only lookup of cluster/nodepool/resource health for one incident |
| 8 | Knowledge/runbooks: Confluence, SharePoint, Markdown repo, or internal KB | Lets synthesis include the known recovery procedure and previous incident context | Retrieve one runbook by service tag and include its link in the HITL packet |

All listed spike contracts are implemented in the public PoC. Keep
`SMART-TRIAGE-INTEGRATION-SPIKE-HEADERS.md` for work-specific variants:
PagerDuty/Opsgenie alert source, real KB retrieval/update, real Flux/Argo CD
reads, real Kyverno/Gatekeeper and vulnerability findings, and real Tempo/Jaeger
trace search.

## Specialist Contracts

Every specialist must return a completed A2A task and its marker.

| Specialist | Required marker | Work replacement |
|---|---|---|
| Kubernetes | `SPECIALIST_KUBERNETES: completed` | Pod events, rollout state, logs, owner references, resource diffs |
| Network/Hubble | `SPECIALIST_NETWORK: completed` | Flow records, DNS/service connectivity, network policy signal |
| Grafana | `SPECIALIST_GRAFANA: completed` | Dashboard link, PromQL result, LogQL result, alert context |
| GitOps | `SPECIALIST_GITOPS: completed` | Sandbox issue/MR/diff only until approved |
| Knowledge | `SPECIALIST_KNOWLEDGE: completed` | Git-backed KB/runbook citation plus KB gap MR after HITL |
| Deployment | `SPECIALIST_DEPLOYMENT: completed` | Flux/Argo CD/Helm sync, health, revision, image, drift |
| Policy | `SPECIALIST_POLICY: completed` | Kyverno/Gatekeeper reports plus vulnerability context |
| Trace | `SPECIALIST_TRACE: completed` | Tempo/Jaeger trace link or scoped `NO_TRACE` fallback |
| Incident commander | `INCIDENT_SYNTHESIS: completed` | Synthesized evidence, risk, recommendation, HITL packet |

The final proof step must emit:

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
- `OUTPUT_SANITIZED: yes`
- `SMART_TRIAGE_PATTERN: proven`

## Safety Rules

- Read-only specialists must not have apply, delete, patch, exec, restart, admin,
  write, or mutation tools.
- The coordinator workflow owns orchestration only; it should not hold broad
  platform mutation permissions.
- The GitOps specialist may write only to a feature branch, sandbox issue, draft
  MR, or approved workflow.
- Production writes require HITL and GitOps review.
- Secrets, tokens, private endpoints, tenant IDs, subscription IDs, internal
  URLs, and real hostnames must not be committed.
- Raw model reasoning must be stripped before writing to tickets, approvals,
  chat, or evidence docs.

## Validation Commands

Run before live execution:

```bash
bash -n {{WORKSTREAM_PATH}}/scripts/run-smart-triage-demo.sh
bash -n {{WORKSTREAM_PATH}}/scripts/replay-alert.sh
bash -n {{WORKSTREAM_PATH}}/scripts/prove-knowledge-citation.sh
bash -n {{WORKSTREAM_PATH}}/scripts/prove-deployment-readonly.sh
bash -n {{WORKSTREAM_PATH}}/scripts/prove-policy-summary.sh
bash -n {{WORKSTREAM_PATH}}/scripts/prove-trace-link.sh
kubectl --context {{KUBE_CONTEXT}} apply --dry-run=server -f {{WORKSTREAM_PATH}}/agents.yaml
kubectl --context {{KUBE_CONTEXT}} apply --dry-run=server -f {{WORKSTREAM_PATH}}/workflow-rbac.yaml
kubectl --context {{KUBE_CONTEXT}} apply --dry-run=server -f {{WORKSTREAM_PATH}}/workflow-template.yaml
kubectl --context {{KUBE_CONTEXT}} apply --dry-run=server -f {{WORKSTREAM_PATH}}/sensors/sensor-submit-rbac.yaml
kubectl --context {{KUBE_CONTEXT}} apply --dry-run=server -f {{WORKSTREAM_PATH}}/sensors/eventsource-alertmanager.yaml
kubectl --context {{KUBE_CONTEXT}} apply --dry-run=server -f {{WORKSTREAM_PATH}}/sensors/alertmanager-to-fanout-sensor.yaml
kubectl --context {{KUBE_CONTEXT}} create --dry-run=client -f {{WORKSTREAM_PATH}}/workflow.yaml
kubectl kustomize infra/byo-kagent/kyverno-policies
```

Use `kubectl create --dry-run=client` for workflows with
`metadata.generateName`.

Run the public-safety sweep before review:

```bash
rg -n '(subscriptionId|tenantId|clientId|password|token|secret|https?://[^\\{\\s\\)]+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})' \
  {{WORKSTREAM_PATH}} \
  SMART-TRIAGE-FANOUT-WORK-HANDOFF.md \
  SMART-TRIAGE-FANOUT-WORK-PLAN.md \
  SMART-TRIAGE-FANOUT-EXECUTION-REVIEW.md \
  SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md \
  SMART-TRIAGE-FANOUT-PR.md \
  SMART-TRIAGE-GITLAB-MCP-MR-DEMO.md \
  {{WORKSTREAM_PATH}}/gitlab-lite-mcp.yaml \
  {{WORKSTREAM_PATH}}/gitlab-lite-agent.yaml
```

Every hit must be a placeholder, public URL, documentation warning, or
in-cluster service name.

## Evidence To Capture

Do not claim the run is proven until these are captured in the execution review:

```bash
argo -n {{ARGO_NAMESPACE}} get {{WORKFLOW_NAME}}
kubectl --context {{KUBE_CONTEXT}} get wf -n {{ARGO_NAMESPACE}} {{WORKFLOW_NAME}}
kubectl --context {{KUBE_CONTEXT}} get pods -n {{ARGO_NAMESPACE}} -l workflows.argoproj.io/workflow={{WORKFLOW_NAME}} -o name
kubectl --context {{KUBE_CONTEXT}} logs -n {{ARGO_NAMESPACE}} pod/{{KUBERNETES_SPECIALIST_POD}} -c main --tail=200
kubectl --context {{KUBE_CONTEXT}} logs -n {{ARGO_NAMESPACE}} pod/{{NETWORK_SPECIALIST_POD}} -c main --tail=200
kubectl --context {{KUBE_CONTEXT}} logs -n {{ARGO_NAMESPACE}} pod/{{GRAFANA_SPECIALIST_POD}} -c main --tail=200
kubectl --context {{KUBE_CONTEXT}} logs -n {{ARGO_NAMESPACE}} pod/{{GITOPS_SPECIALIST_POD}} -c main --tail=200
kubectl --context {{KUBE_CONTEXT}} logs -n {{ARGO_NAMESPACE}} pod/{{KNOWLEDGE_SPECIALIST_POD}} -c main --tail=200
kubectl --context {{KUBE_CONTEXT}} logs -n {{ARGO_NAMESPACE}} pod/{{DEPLOYMENT_SPECIALIST_POD}} -c main --tail=200
kubectl --context {{KUBE_CONTEXT}} logs -n {{ARGO_NAMESPACE}} pod/{{POLICY_SPECIALIST_POD}} -c main --tail=200
kubectl --context {{KUBE_CONTEXT}} logs -n {{ARGO_NAMESPACE}} pod/{{TRACE_SPECIALIST_POD}} -c main --tail=200
kubectl --context {{KUBE_CONTEXT}} logs -n {{ARGO_NAMESPACE}} pod/{{SYNTHESIS_POD}} -c main --tail=200
kubectl --context {{KUBE_CONTEXT}} logs -n {{ARGO_NAMESPACE}} pod/{{PROVE_RESULT_POD}} -c main --tail=200
```

Evidence must include:

- Real workflow name.
- Argo node table.
- Specialist pod names.
- Proof-marker pod log.
- Specialist evidence logs.
- HITL suspend/resume record.
- Any failed attempt and failure class.
- Public-safety sweep result.

## Failure Classes

Classify failures explicitly:

| Class | Use when |
|---|---|
| `MODEL_BACKEND_UNAVAILABLE` | Model config exists but runtime completion fails or times out |
| `A2A_TRANSPORT_ERROR` | Agent service, route, DNS, or HTTP path is unreachable |
| `A2A_TASK_TIMEOUT` | Agent accepted the task but did not complete in time |
| `MCP_UNAVAILABLE` | MCP server is not accepted, initialized, or callable |
| `SPECIALIST_CONTRACT_FAILED` | Specialist returns success but omits markers or schema |
| `HITL_TIMEOUT` | Human approval does not arrive within the workflow window |
| `GITOPS_DRYRUN_FAILED` | Sandbox issue, MR, or diff cannot be created safely |
| `CITATION_MISSING` | Knowledge specialist answers without a source citation |
| `DEPLOY_CONTROLLER_UNAVAILABLE` | Deployment controller read path is unavailable |
| `POLICY_API_UNAVAILABLE` | Policy report or vulnerability read path is unavailable |
| `TRACE_BACKEND_UNAVAILABLE` | Trace backend is unavailable |
| `NO_TRACE_FOUND` | Trace search completed but found no matching trace |

## Done Criteria

The work implementation is not done until:

- The workflow succeeds in an approved non-production environment.
- The final proof step emits every required marker.
- Evidence is written to the execution review with a real workflow name.
- The workflow remains verifiable for the agreed retention window, or raw logs
  are stored in an approved evidence location.
- The PR/front sheet states any limitation plainly, especially synthetic vs live
  evidence.
- A reviewer can reproduce the validation commands without private values in
  the repo.

## Agent Prompt

Use this prompt when handing the work to another agent:

```text
Implement the smart-triage fan-out pattern in this work environment.

Start with SMART-TRIAGE-FANOUT-WORK-HANDOFF.md and follow the referenced
WORK-PLAN, demo manifests, runner, execution review, live evidence example, and
PR template.

Parameterize all environment-specific values. Do not commit secrets, tokens,
private hostnames, internal URLs, subscription IDs, tenant IDs, or real
credentials. Keep Kubernetes, network, and Grafana specialists read-only.
Keep GitOps and KB write capability sandboxed until HITL and review are proven.
Replace synthetic knowledge, deployment, policy, and trace sources with approved
read-only work integrations before claiming live production evidence.

First prove the orchestration contract with a controlled non-production
incident: coordinator fan-out, all specialist markers, synthesis, HITL suspend
and resume, GitOps/KB dry-run, sanitized output, and final proof markers. Capture the
real workflow name, Argo node table, specialist pod logs, proof-marker log, and
any failure classes in the execution review before claiming success.
```

# Work Zip Agent Handoff

Purpose: hand this repository zip to a work-side agent or engineer and ask them
to recreate the proven home-lab patterns in a different work environment.

This is a public-safe package. It intentionally uses placeholders and synthetic
evidence where real work endpoints, secrets, and hostnames would be required.
Do not apply manifests directly to a work cluster until the environment values
below have been replaced and reviewed.

## One-Line Ask For The Work Agent

Take this zip, inspect the referenced files, identify any missing work-specific
variables/images/secrets/endpoints, then implement the same patterns in an
approved non-production work environment with live evidence and a peer-review
execution report.

## TLDR

The current iteration packages an AI SRE operating model:

- Smart triage fan-out: Alertmanager or operator input fans out to Kubernetes,
  Network, Grafana, GitOps, Knowledge, Deployment, Policy, and Trace
  specialists, then pauses for HITL before any non-read-only action.
- Chaos engineering: Litmus chaos events drive kagent/Qwen/Grafana evidence and
  controlled remediation review.
- Agent-to-agent workflows: A2A specialist calls, memory HITL, shared context,
  and platform-memory showcase demos.
- Agent evaluations: deterministic scoring for triage quality, evidence,
  HITL compliance, remediation verification, ticket hygiene, latency, and hard
  failures.
- Grafana evidence: shared Grafana evidence agent, dashboard registry, and
  focused incident evidence dashboards.
- GitLab MCP: sandbox branch/MR/comment proof from terminal and kagent-mounted
  MCP shim.
- KB update loop: GitLab MCP creates or updates KB docs, updates the index,
  opens a merge request, then doc2vec/querydoc proves cited retrieval.
- Work lift-and-shift docs: front sheets, PR templates, execution reviews,
  HTML presenter pages, validation commands, and public-safety guardrails.

## Read Order

Start with the presentation and top-level front sheets:

1. `DEMOS.md` - repo-wide demo map.
2. `WORK-KAGENT-TRIAGE-V2-FRONT-SHEET.md` - one-page starting point,
   current proof tiers, critical path, SRE demo script, and done definition.
3. `WORK-KAGENT-TRIAGE-V2-REVIEW-PROMPT.md` - current-state review brief,
   Opus prompt, and local improvement checklist for Kagent triage system v2.
4. `WORK-KAGENT-TRIAGE-V2-COMPLETION-CHECKLIST.md` - completion gates for
   verification, HTML visuals, Grafana metrics, SRE workflows, and BYO-agent
   integration.
5. `WORK-KAGENT-TRIAGE-V2-VERIFICATION-PASS.md` - current local readiness
   status and remaining priorities.
6. `WORK-KAGENT-TRIAGE-V2-WORK-AGENT-START-PROMPT.md` - direct prompt to hand
   to the work-side agent, including read order, priority order, definition of
   done, and output format.
7. `scripts/verify-kagent-triage-v2-handoff.sh` - one-command local/static
   verifier for the human or work agent before cluster work begins.
8. `WORK-KAGENT-TRIAGE-V2-WORK-IMPLEMENTATION-CHECKLIST.html` - interactive
   checkbox checklist for work-machine implementation, prioritized with
   doc2vec/querydoc KB first, then A2A, GitLab MCP, and Grafana MCP.
9. `WORK-KAGENT-TRIAGE-V2-SRE-OPERATING-GUIDE.md` - SRE-facing operating
   guide for incident replay, controlled chaos, BYO agents, and review routing.
10. `WORK-KAGENT-TRIAGE-V2-ASTHERI-SRE-WALKTHROUGH.md` - first-time ASTHERI/SRE
   walkthrough from app onboarding to chaos, remediation, dashboards, GitLab,
   reports, KB, memory, and eval evidence.
11. `WORK-KAGENT-TRIAGE-V2-ASTHERI-SRE-REHEARSAL.md` - local rehearsal notes,
   discrepancies found, fixes made, and remaining live work-lab proofs.
12. `WORK-KAGENT-TRIAGE-V2-SRE-WORKFLOW.html` - visual SRE workflow for demos
   and team walkthroughs.
13. `WORK-KAGENT-TRIAGE-V2-SRE-FIRST-CONTACT.html` - visual cold-start demo for
   an SRE bringing an app, generating agents, injecting chaos, and evaluating.
14. `demos/sre-first-contact/README.md` - one-folder first-contact demo package
   with prompts, app profile, failure modes, BYO agents, chaos, and eval.
15. `WORK-KAGENT-TRIAGE-V2-HITL-PROOF.md` - real suspend vs mock/full callback
   proof status.
16. `WORK-KAGENT-TRIAGE-V2-KB-QUERYDOC-PROOF.md` - static querydoc validation
   and live-query blocker.
17. `demos/kb-gitlab-mcp-update/README.md` - GitLab MCP KB update loop,
   index update, reindex, querydoc citation, and triage KB lookup acceptance
   test.
18. `WORK-KAGENT-TRIAGE-V2-PROOF-BOARD.html` - presentation-ready proof board.
19. `WORK-KAGENT-TRIAGE-V2-WORK-AGENT-CHECKLIST.md` - prioritized work-side
   replication checklist.
20. `SMART-TRIAGE-FANOUT-PRESENTER.html` - visual explanation for the smart
   triage fan-out package.
21. `SMART-TRIAGE-FANOUT-WORK-HANDOFF.md` - detailed smart-triage lift-and-shift
   front sheet.
22. `SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md` - example of acceptable live evidence.
23. `SMART-TRIAGE-FANOUT-EXECUTION-REVIEW.md` - review checklist format.
24. `KAGENT-EVAL-LIFT-AND-SHIFT-HANDOFF.md` - agent lifecycle evaluation handoff.
25. `A2A-WORK-IMPLEMENTATION-PLAN.md` - memory/A2A work implementation plan.
26. `SMART-TRIAGE-GITLAB-MCP-MR-DEMO.md` - GitLab MCP sandbox proof.
27. `docs/ai-grafana/README.md` - AI and Grafana triage context.
28. `chaos/litmus/WORK-INSTALL.md` - chaos engineering install handoff.

Then inspect the implementation paths:

```text
a2a/smart-triage-fanout-demo/
a2a/platform-memory-showcase-demo/
observability/agent-evals/
agents/grafana-evidence-agent/
agents/skills/grafana-incident-evidence-pack/
observability/grafana/
docs/smart-triage-integration-spikes/
docs/platform-kb/runbooks/
docs/platform-kb/agents/
infra/byo-kagent/kyverno-policies/
demos/byo-agent-showcase/
demos/kb-gitlab-mcp-update/
chaos/litmus/
```

## What Was Proven At Home

### Smart Triage Fan-Out

Home evidence shows the smart-triage workflow completed with all spike
contracts:

```text
workflow: smart-triage-alert-b8gkz
status: Succeeded
progress: 14/14
duration: 4m58s
eval: score=1.0 passed=true
```

Required proof markers:

```text
SMART_TRIAGE_FANOUT: started
ALERT_INGESTED: yes
SPECIALIST_KUBERNETES: completed
SPECIALIST_NETWORK: completed
SPECIALIST_GRAFANA: completed
SPECIALIST_GITOPS: completed
SPECIALIST_KNOWLEDGE: completed
SPECIALIST_DEPLOYMENT: completed
SPECIALIST_POLICY: completed
SPECIALIST_TRACE: completed
CITATIONS: docs/platform-kb/runbooks/checkout-api-crashloop.md#chunk-1
DEPLOYMENT_VERDICT: bad_deploy
POLICY_REMEDIATION_SAFETY: blocked
TRACE_FALLBACK: NO_TRACE
INCIDENT_SYNTHESIS: completed
HITL_STATUS: resumed
REMEDIATION_MODE: gitops_or_workflow_only
OUTPUT_SANITIZED: yes
SMART_TRIAGE_PATTERN: proven
```

At work, keep the same marker contract for the first run, but replace public
synthetic evidence with approved live backends.

Important evidence boundary: the public package includes some synthetic marker
contracts for knowledge retrieval, Grafana evidence, GitLab write paths, and
chaos-triggered specialist fan-out. Treat those as process contracts until the
work environment proves them with approved live backends.

### GitLab MCP

The package includes:

- terminal baseline branch/MR proof
- kagent-mounted MCP shim proof
- sandbox MR creation and MR note
- official GitLab MCP endpoint notes and current auth caveat

Start in a sandbox project. Do not give general triage agents write-capable
GitLab tools. Keep GitLab write tools on the GitOps specialist only, and call
that specialist only after HITL for any non-sandbox action.

Use a dedicated sandbox project and a project-scoped token or approved
least-privilege OAuth identity. Do not reuse a broadly scoped user or group token
for the GitLab MCP path. The public demo's sandbox boundary is partly
prompt-level; work-side isolation must be enforced by token scope and project
permissions.

### Agent Evaluations

The eval package scores both captured agent runs and full incident lifecycles.
The work implementation should wire evals as a post-run Argo task and gate
ticket closure on an eval pass.

Required hard failures include:

- remediation before HITL
- remediation without verification
- missing ticket update
- wrong namespace
- required specialists missing
- public-safety leak pattern

### Chaos Engineering

The chaos package focuses on Litmus-driven incidents and Grafana/kagent triage.
Use it as a separate approved non-production test source for smart-triage
workflows.

## Work Environment Values Required

Ask the work owner to provide these before applying anything.

| Area | Variable or decision | Required work value |
|---|---|---|
| Kubernetes | `{{KUBE_CONTEXT}}` | Approved non-production context |
| Kubernetes | `{{KAGENT_NAMESPACE}}` | Namespace where kagent Agents run |
| Kubernetes | `{{ARGO_NAMESPACE}}` | Namespace where Argo Workflows run |
| Kubernetes | `{{ARGO_EVENTS_NAMESPACE}}` | Namespace where Argo Events runs |
| Kubernetes | `{{CHAOS_NAMESPACE}}` | Namespace for Litmus/chaos demos |
| Kubernetes | `{{DEMO_TARGET_NAMESPACE}}` | Namespace for controlled workload tests |
| Model | `{{CHAT_MODEL_CONFIG}}` | Known-good kagent ModelConfig |
| Model | `{{MODEL_BASE_URL}}` | agentgateway, LiteLLM, Azure OpenAI, KubeAI, or vLLM endpoint |
| Model | `{{MODEL_NAME}}` | Model name served by that endpoint |
| Agentgateway | `{{AGENTGATEWAY_HOST}}` | Internal or ingress hostname |
| Agentgateway | `{{AGENTGATEWAY_NAMESPACE}}` | Namespace where agentgateway runs |
| Grafana | `{{GRAFANA_MCP_REMOTE_SERVER_NAME}}` | Read-only Grafana MCP server |
| Grafana | `{{GRAFANA_URL}}` | Approved Grafana URL |
| Grafana | `{{MIMIR_DATASOURCE_UID}}` | Metrics datasource UID |
| Grafana | `{{LOKI_DATASOURCE_UID}}` | Logs datasource UID |
| Alerts | `{{ALERT_SOURCE}}` | Alertmanager, Grafana Alerting, PagerDuty, Opsgenie, or equivalent |
| Alerts | `{{ALERT_WEBHOOK_URL}}` | Work-approved webhook or EventSource route |
| GitLab | `{{GITLAB_HOST}}` | GitLab.com or self-managed host |
| GitLab | `{{GITLAB_PROJECT}}` | Sandbox project path or ID |
| GitLab | `{{GITLAB_TARGET_BRANCH}}` | Default target branch |
| GitLab | `{{GITLAB_AUTH_MODEL}}` | OAuth, project token, service account, or approved MCP auth |
| GitLab | `{{GITLAB_TOKEN_SCOPE}}` | Project-scoped, least-privilege write scope for the sandbox project |
| GitLab | `{{GITLAB_TOKEN_SECRET_NAME}}` | Kubernetes Secret name, if using token auth |
| GitLab | `{{GITLAB_TOKEN_SECRET_KEY}}` | Secret key containing the token |
| HITL | `{{HITL_FRONT_DOOR}}` | Argo UI, Teams, Slack, Git approval, or ITSM approval |
| Teams | `{{TEAMS_CHANNEL}}` | Channel/team for review notifications |
| Teams | `{{TEAMS_WEBHOOK_SECRET}}` | Secret reference only, never inline value |
| Knowledge | `{{KB_REPO_PATH}}` | Git-backed markdown KB or runbook repo |
| Knowledge | `{{KB_MCP_SERVER}}` | Read-only KB/query MCP server |
| Deployment | `{{DEPLOY_CONTROLLER}}` | Flux, Argo CD, Helm, or equivalent |
| Policy | `{{POLICY_ENGINE}}` | Kyverno or Gatekeeper |
| Policy | `{{VULN_SOURCE}}` | Scanner, registry policy, or report source |
| Trace | `{{TRACING_BACKEND}}` | Tempo, Jaeger, or equivalent |
| Network | `{{NETWORK_EVIDENCE_SOURCE}}` | Hubble, Cilium, mesh telemetry, or K8s-only fallback |
| AKS/Cloud | `{{AKS_MCP_SERVER}}` | AKS-MCP or cloud-control MCP/tool path |
| Evidence | `{{EVIDENCE_RETENTION}}` | Workflow/log/artifact retention period |
| Registry | `{{IMAGE_PULL_SECRET}}` | Pull secret if the cluster requires one |

## Images To Confirm Or Mirror

These image references appear in the package or related paths. Confirm they are
allowed by work registry policy, or mirror them to the approved internal
registry before deployment.

| Image | Where used | Why |
|---|---|---|
| `alpine:3.19` | Smart-triage workflow and eval hook examples | Shell helper steps and lightweight Argo tasks |
| `python:3.11-slim` | Chaos Litmus triage sensor | Python-based Qwen/kagent invocation step |
| `python:3.12-alpine` | GitLab lite MCP shim | Temporary sandbox MCP server |
| `bitnamilegacy/kubectl:1.30.7` | Chaos Litmus triage sensor | Kubernetes status and remediation helper steps |
| `hashicorp/http-echo:1.0.0` | Chaos target workload | Controlled demo target |
| `litmuschaos.docker.scarf.sh/litmuschaos/go-runner:3.28.0` | Litmus experiments | Pod delete, CPU hog, network latency experiments |
| `curlimages/curl` | Agentgateway validation runbooks | Ad-hoc HTTP probes, where used |
| `mcr.microsoft.com/azure-cli:2.58.0` | Agentgateway Azure backend example | Azure token/backend validation, where used |

Also confirm the cluster already has or can install the platform images for:

- kagent controller and agent runtime
- Argo Workflows
- Argo Events
- agentgateway
- Grafana, Mimir/Prometheus, Loki, Alloy
- LitmusChaos control plane, if chaos demos are in scope
- model-serving runtime, for example KubeAI, vLLM, LiteLLM, or Azure OpenAI

## First Work Implementation Sequence

1. Inventory installed CRDs and namespaces: kagent, Argo Workflows, Argo Events,
   RemoteMCPServer, agentgateway, Kyverno/Gatekeeper, Litmus if used.
2. Prove model runtime with a real chat completion. Do not rely on
   `Accepted=True` alone.
3. Prove one read-only A2A call to a simple kagent Agent.
4. Prove Grafana MCP can read one dashboard, one metric query, and one log query.
5. Prove GitLab sandbox branch/MR/comment through the approved auth path.
6. Prove knowledge retrieval returns one cited runbook and one no-docs fallback.
7. Prove deployment-state read-only lookup for one app.
8. Prove policy/security read-only lookup for one workload.
9. Prove trace lookup returns a real trace link or explicit `NO_TRACE`.
10. Apply the smart-triage package in non-production with work values.
11. Run one controlled incident or alert replay.
12. Capture the workflow name, Argo node table, pod logs, proof markers, HITL
    approver, eval output, and any failure classifications.
13. Fill an execution review before claiming success.

## Validation Commands To Adapt

Use these as the minimum validation shape after replacing placeholders:

```bash
bash -n a2a/smart-triage-fanout-demo/scripts/*.sh

kubectl --context {{KUBE_CONTEXT}} apply --dry-run=server \
  -f a2a/smart-triage-fanout-demo/agents.yaml \
  -f a2a/smart-triage-fanout-demo/workflow-rbac.yaml \
  -f a2a/smart-triage-fanout-demo/workflow-template.yaml \
  -f a2a/smart-triage-fanout-demo/sensors/sensor-submit-rbac.yaml \
  -f a2a/smart-triage-fanout-demo/sensors/eventsource-alertmanager.yaml \
  -f a2a/smart-triage-fanout-demo/sensors/alertmanager-to-fanout-sensor.yaml

kubectl --context {{KUBE_CONTEXT}} create --dry-run=client \
  -f a2a/smart-triage-fanout-demo/workflow.yaml

kubectl --context {{KUBE_CONTEXT}} kustomize observability/agent-evals
kubectl --context {{KUBE_CONTEXT}} kustomize infra/byo-kagent/kyverno-policies

python3 -m py_compile observability/agent-evals/scripts/*.py
python3 observability/agent-evals/scripts/score-lifecycle-run.py \
  --case observability/agent-evals/lifecycle-cases/pod-crashloop-hitl-remediation.yaml \
  --run observability/agent-evals/results/sample/lifecycle/pod-crashloop-hitl-remediation.lifecycle-run.json \
  --output-dir /tmp/kagent-lifecycle-evals
```

Public-safety sweep before committing work-side docs:

```bash
rg -n '(subscriptionId|tenantId|clientId|password|token|secret|https?://[^\\{\\s\\)]+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})' \
  SMART-TRIAGE-FANOUT-*.md \
  A2A-*.md \
  KAGENT-EVAL-*.md \
  a2a/smart-triage-fanout-demo \
  a2a/platform-memory-showcase-demo \
  observability/agent-evals \
  docs/smart-triage-integration-spikes \
  docs/platform-kb \
  chaos/litmus
```

Expected hits should be placeholders, public example URLs, in-cluster service
URLs, or text warning not to commit secrets. Raw credentials, private hostnames,
subscription IDs, tenant IDs, and internal URLs are not acceptable.

## Evidence The Work Agent Must Produce

For each implemented pattern, produce a small execution review with:

- exact cluster context label, redacted if needed
- exact workflow name
- exact run time and duration
- Argo node table
- specialist pod names and logs
- proof markers
- HITL approval identity or approval record
- GitLab issue/MR/diff link, redacted if private
- eval score and hard-failure list
- failure classification for every failed attempt
- cleanup/rollback commands
- public-safety sweep result

Do not claim "ready", "proven", or "live evidence" unless the evidence review
contains a workflow name and logs that can be independently checked.

## Questions The Work Agent Should Answer Back

Before implementation, report back:

1. Which required environment values are missing?
2. Which images must be mirrored or replaced?
3. Which MCP servers already exist and which need to be deployed?
4. Which GitLab auth model is approved?
5. Which HITL front door is approved for the first non-production run?
6. Which incident class is approved for the first controlled test?
7. Which docs or manifests cannot be applied because work CRD versions differ?

## Success Criteria

The work implementation is complete when:

- a non-production smart-triage workflow succeeds with the required markers
- all specialists use live work evidence or explicitly documented fallback
- GitLab writes are sandbox-only until HITL and review are proven
- lifecycle eval runs after verification
- ticket or MR closure is gated on eval pass
- chaos input can trigger or rehearse the same triage path, if chaos is in scope
- all checked-in artifacts are scrubbed of secrets and private values
- a peer reviewer can reproduce the evidence from the execution review

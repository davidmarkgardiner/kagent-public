# Smart Triage Integration Spikes — Planning Pack

This folder is the worked-up planning output for the brief in
[`../../SMART-TRIAGE-INTEGRATION-SPIKE-HEADERS.md`](../../SMART-TRIAGE-INTEGRATION-SPIKE-HEADERS.md).

It contains one focused spike plan per integration plus the current completion
status. The public PoC has now implemented every spike contract in
`a2a/smart-triage-fanout-demo/` and captured live evidence in
`SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md`.

This pack has a local Codex review note in
[`CODEX-REVIEW.md`](CODEX-REVIEW.md). Keep adding a review note before each
build-specific implementation pass.

Each spike plan follows the same template so they are interchangeable handoffs:

1. Objective
2. Existing repo reuse (what is already here — do not rebuild it)
3. Proposed architecture
4. First safe proof (read-only unless the spike is explicitly a write spike)
5. Required MCP / tool / server shape
6. kagent Agent contract + required output markers
7. Argo workflow integration point
8. HITL requirement
9. Required manifests / scripts to create
10. Validation commands
11. Public-safe placeholders
12. Evidence to capture
13. Failure classes
14. Rollback / disable path
15. Known risks
16. Exit criteria

## Spike Index

| # | Spike | Plan file | Status | Live evidence |
|---|---|---|---|---|
| 1 | Alert ingestion | [`spike-1-alert-ingestion.md`](spike-1-alert-ingestion.md) | Done | `ALERT_INGESTED: yes`, duplicate suppression |
| 8 | Knowledge & runbook retrieval | [`spike-8-knowledge-runbook-retrieval.md`](spike-8-knowledge-runbook-retrieval.md) | Done as public-safe contract proof | `SPECIALIST_KNOWLEDGE: completed`, cited runbook, KB MR dry-run after HITL |
| 5 | Deployment state | [`spike-5-deployment-state.md`](spike-5-deployment-state.md) | Done as public-safe contract proof | `SPECIALIST_DEPLOYMENT: completed`, `VERDICT: bad_deploy` |
| 6 | Policy & security context | [`spike-6-policy-security-context.md`](spike-6-policy-security-context.md) | Done as public-safe contract proof | `SPECIALIST_POLICY: completed`, `REMEDIATION_SAFETY: blocked`, Audit-mode guardrail proposal |
| 4 | Trace context | [`spike-4-trace-context.md`](spike-4-trace-context.md) | Done as public-safe fallback proof | `SPECIALIST_TRACE: completed`, `FALLBACK: NO_TRACE` |

Spike numbers match the brief. AKS-MCP / cloud-control is intentionally out of
scope (the repo already carries AKS-MCP onboarding patterns).

## Recommended Implementation Order

From the brief, with rationale grounded in what already exists in this repo:

1. **Alert ingestion** — turns the demo from synthetic input into a real
   trigger. The Alertmanager→EventSource→Sensor→WorkflowTemplate chain already
   exists; this is the smallest, highest-leverage spike.
2. **Knowledge / runbook retrieval** — two retrieval patterns and a GitLab MCP
   write path already exist, and a sandbox repo is already named. Citations make
   every downstream specialist more trustworthy.
3. **Deployment state** — highest triage signal-to-effort: most incidents are a
   recent deploy. Greenfield specialist but a clean read-only contract.
4. **Policy / security context** — depends on a target cluster running Kyverno;
   reuses the existing `infra/byo-kagent/kyverno-policies/` posture.
5. **Trace context** — last because the repo has no Tempo/Jaeger backend yet, so
   it carries the most environment dependency and discovery risk.

## Shared Architecture (the thing every spike plugs into)

The current smart-triage fan-out is an Argo Workflow DAG that calls kagent
Declarative Agents over A2A and validates required text markers. Ground truth:

- Workflow: `a2a/smart-triage-fanout-demo/workflow.yaml`
- Agents: `a2a/smart-triage-fanout-demo/agents.yaml`
- RBAC: `a2a/smart-triage-fanout-demo/workflow-rbac.yaml`
- Runner: `a2a/smart-triage-fanout-demo/scripts/run-smart-triage-demo.sh`

```text
normalize-incident
  -> fan out in parallel (parallelism: 4) to specialist Agents via A2A:
       fanout-kubernetes
       fanout-network
       fanout-grafana
       fanout-gitops
       fanout-knowledge
       fanout-deployment
       fanout-policy
       fanout-trace
  -> synthesize-incident (incident commander)
  -> wait-for-human-review   (Argo suspend: {})
  -> finalize-approved
  -> prove-result            (grep all required markers)
  -> evaluate-lifecycle      (templateRef agent-lifecycle-eval)
```

**Every new specialist is added the same way:**

1. Add a `kagent.dev/v1alpha2` Declarative Agent to `agents.yaml` (or a new
   file) with an `a2aConfig.skills` entry and a `systemMessage` that ends in a
   fixed marker block.
2. Add a `fanout-<domain>` task to the workflow DAG, depending on
   `normalize-incident`, using the existing `call-specialist` template (it does
   the A2A `message/send` JSON-RPC, strips `<think>` tags, and greps the marker).
3. Pass the new specialist output into `synthesize-incident` and `prove-result`.
4. Add the new marker to the `prove-result` grep list and to the demo README
   proof-marker list.

### A2A call contract (already implemented, reuse verbatim)

The `call-specialist` template in `workflow.yaml` POSTs JSON-RPC `message/send`
to `http://<agent-name>.<kagent-namespace>:8080/`, then enforces:

- `.result.status.state == "completed"`
- the required marker string is present (`grep -Fq`)
- no `<think>`/`</think>` reasoning tag leaked (`SPECIALIST_CONTRACT_FAILED`)

New specialists need a service URL parameter in `spec.arguments.parameters` and
nothing else new on the transport.

### Normalized incident schema (cross-cutting gap)

Today `normalize-incident` only carries `scenario` + `fingerprint`. Several
spikes need richer correlation. Standardize the normalized payload now so Spikes
1, 4, 5, and 6 share it. Proposed minimum fields (align with the labels already
required by `observability/grafana/dashboard-registry.yaml`):

```text
incident_id, fingerprint, alertname, severity, status,
cluster, environment, namespace, workload, pod, container, service, node,
startsAt, endsAt, runbook_url, source (alertmanager|pagerduty|opsgenie|manual)
```

Unknown fields pass the literal `unknown` (never invented). Spike 1 produces
this payload; Spikes 4/5/6 consume it.

## Shared Planning Rules (from the brief — apply to every spike)

- First proof is **read-only** unless the spike is explicitly a sandbox
  ticket/MR/KB-update spike (only Spike 8 has a write step, gated behind HITL).
- Use `{{PLACEHOLDER}}` for every environment-specific value.
- Never commit secrets, private endpoints, tenant IDs, subscription IDs, tokens,
  or real internal hostnames. Tokens come from `Secret`/`headersFrom` only.
- HITL is mandatory before any non-read-only action.
- Output hygiene: strip model reasoning tags before any ticket, approval, or
  chat post (the workflow already enforces this).

## Cross-Cutting: Permission Posture

Follow `AGENTS.md` and `SMART-TRIAGE-FANOUT-WORK-PLAN.md`:

- Chat/agent front door is separate from execution permissions.
- Read-only specialists must **not** carry apply/delete/exec/patch tool names.
  `infra/byo-kagent/kyverno-policies/mcp-dangerous-verb.yaml` will block them at
  admission — design the tool lists to pass it.
- Only the GitLab/GitOps writer agent gets write tools, and only against the
  sandbox project, on a feature branch, behind HITL.

## Cross-Cutting: Eval Gate

Every spike should leave evidence that plugs into `observability/agent-evals/`.
There are already lifecycle cases worth reusing or extending:

- `observability/agent-evals/cases/flux-reconciliation-failure.yaml` (Spike 5)
- `observability/agent-evals/cases/crashloop-wrong-env-var.yaml` (Spikes 1, 8)
- `observability/agent-evals/lifecycle-cases/pod-crashloop-hitl-remediation.yaml`

The fan-out workflow already ends in an `evaluate-lifecycle` step via
`templateRef: agent-lifecycle-eval`. New spikes add their markers to that run.

## Master Placeholder Catalog

Resolve these once per environment; individual spikes reference them.

| Placeholder | Meaning |
|---|---|
| `{{KAGENT_NAMESPACE}}` | Namespace hosting kagent Agents (`kagent` in the demo) |
| `{{ARGO_NAMESPACE}}` | Argo Workflows namespace (`argo` in the demo) |
| `{{ARGO_EVENTS_NAMESPACE}}` | Argo Events namespace (`argo-events` in repo examples) |
| `{{CHAT_MODEL_CONFIG}}` | Working ModelConfig (`default-model-config` in the demo) |
| `{{KUBE_CONTEXT}}` | Target non-production kube context |
| `{{ALERT_SOURCE}}` | Authoritative alert source |
| `{{TRACING_BACKEND}}` | Tempo / Jaeger / work-standard |
| `{{DEPLOY_CONTROLLER}}` | Flux / Argo CD / Helm |
| `{{POLICY_ENGINE}}` | Kyverno / Gatekeeper |
| `{{GITLAB_SANDBOX_PROJECT}}` | Sandbox GitLab project (repo uses `{{GITLAB_SANDBOX_PROJECT}}`) |
| `{{GRAFANA_MCP_SERVER}}` | Read-only Grafana RemoteMCPServer (`kagent-grafana-mcp` in repo) |

## Codex Review Gate (required before any spike build)

Before implementing any spike, route the selected plan through a separate Codex
review pass. Treat that review as a code-review style gate: findings first,
specific file/line references, and no implementation until blocking findings are
resolved. Do not depend on local-only workflow notes or private assistant
profiles in the portable work handoff.

## Definition Of Done (per spike)

- First safe proof runs read-only against a non-production target and prints its
  required markers.
- Specialist Agent passes `kubectl apply --dry-run=server`.
- Tool list passes the Kyverno dangerous-verb policy (read-only spikes).
- Failure classes are emitted, not collapsed to a generic transport error.
- Rollback/disable path is a single documented command set.
- Evidence captured and linked into `observability/agent-evals/`.

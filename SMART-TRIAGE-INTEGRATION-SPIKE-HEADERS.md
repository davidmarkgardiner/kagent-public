# Smart Triage Integration Spike Headers

Use this as the planning brief for another agent. The goal is not to implement
yet; the goal is to produce focused spike plans for the next smart-triage
integrations.

## Scope

Plan spikes for these integrations:

1. Alert ingestion.
2. Trace context.
3. Deployment state.
4. Policy and security context.
5. Repo-backed knowledge-base retrieval and update.

AKS-MCP/cloud-control is intentionally out of scope for this planning pass
because the repo already carries AKS-MCP deployment and onboarding patterns.

## Shared Planning Rules

- Keep the first proof read-only unless the specific spike is explicitly about
  opening a sandbox ticket, MR, or knowledge-base update.
- Use placeholders for every environment-specific value.
- Do not commit secrets, private endpoints, tenant IDs, subscription IDs,
  tokens, or real internal hostnames.
- Every spike must define:
  - first safe proof;
  - required MCP/tool/server shape;
  - kagent Agent contract;
  - Argo workflow integration point;
  - HITL requirement;
  - evidence to capture;
  - failure classes;
  - rollback/disable path.

## Spike 1: Alert Ingestion

### Objective

Replace synthetic incident input with a real alert payload from Alertmanager,
PagerDuty, Opsgenie, or the work-standard alert source.

### First Safe Proof

Read one test alert or active non-production alert, normalize it into the
smart-triage incident schema, and start the fan-out workflow without performing
remediation.

### Planning Questions

- Which alert source is authoritative for first response?
- What labels identify service, namespace, severity, owner, environment, and
  runbook?
- Should alert ingestion use Argo Events, webhook receiver, polling MCP tool, or
  message bus?
- How are duplicate alerts grouped or suppressed?
- What evidence proves the workflow started from a real alert?

### Expected Output

- Normalized alert schema.
- Trigger path diagram.
- Read-only validation command or webhook replay.
- Failure classes for malformed payload, duplicate alert, source unavailable,
  and workflow submission failure.

## Spike 4: Trace Context

### Objective

Add request-level causality to the incident packet using OpenTelemetry traces
from Tempo, Jaeger, or the work-standard tracing backend.

### First Safe Proof

Given a service, namespace, time window, or trace ID from the alert/Grafana
context, retrieve one trace summary or trace link and include it in the HITL
packet.

### Planning Questions

- Which tracing backend is authoritative?
- How does the workflow derive a trace ID or search window?
- Which fields should the trace specialist return: root span, slow span, error
  span, dependency edge, or trace URL?
- What is the fallback when no trace exists?
- Should trace retrieval be a standalone specialist or part of the Grafana
  specialist?

### Expected Output

- Trace specialist contract.
- Query inputs and output schema.
- Evidence capture commands.
- Failure classes for trace backend unavailable, no trace found, query timeout,
  and ambiguous trace set.

## Spike 5: Deployment State

### Objective

Correlate runtime symptoms with GitOps and release state from Flux, Argo CD,
Helm release metadata, or the work-standard deployment controller.

### First Safe Proof

Read sync status, health, revision, image, and recent rollout events for one
known non-production workload. Do not sync, rollback, restart, or patch.

### Planning Questions

- Is Flux, Argo CD, Helm, or another deployment source authoritative?
- How does the incident payload map to an application/release?
- Which state matters for triage: desired revision, live revision, drift,
  failed sync, health, last deploy time, or image tag?
- Should GitLab MR context be linked back to the deployment state?
- What evidence distinguishes a bad deploy from a runtime/platform issue?

### Expected Output

- Deployment-state specialist contract.
- Read-only tool list.
- Mapping from namespace/workload to release/application.
- Failure classes for controller unavailable, app not found, drift detected,
  failed sync, and stale release metadata.

## Spike 6: Policy And Security Context

### Objective

Add policy and security constraints to the commander packet so remediation does
not propose actions blocked by Kyverno, Gatekeeper, image policy, or known
vulnerability findings.

### First Safe Proof

Read policy reports and image/security findings for one namespace or workload
and return a concise risk/blocker summary.

### Planning Questions

- Is Kyverno or Gatekeeper authoritative in the target cluster?
- Where do image scan or vulnerability findings live?
- Which violations block remediation versus only warn?
- Should policy context be checked before GitLab MR creation, before HITL, or
  both?
- How should the commander present policy-blocked remediation?

### Expected Output

- Policy/security specialist contract.
- Required read-only queries.
- Admission-control guardrail proposal for write-capable MCP tools.
- Failure classes for policy API unavailable, no report found, blocking policy,
  vulnerability source unavailable, and unsafe remediation proposal.

## Spike 8: Knowledge And Runbook Retrieval

### Objective

Let smart-triage agents retrieve approved runbooks, platform docs, previous
incident notes, and service-specific knowledge from Git-backed Markdown
repositories.

### Existing Repo Context

This repo already has three useful patterns:

- `agents/kagent-knowledge-ui/` - Git-backed Markdown retrieval with BM25-style
  chunking and stale-doc PR behavior.
- `ai-platform/kagent-knowledge-base/` - doc2vec/querydoc MCP pattern for
  vector-style Markdown retrieval through `query_documentation`.
- `docs/platform-kb/platform/kagent-docs-rag.md` - architecture note explaining
  why platform docs should stay in Git and be indexed into a queryable database.

### First Safe Proof

Use the existing sandbox GitLab repo as a knowledge repository:

```text
https://{{GITLAB_HOST}}/{{GITLAB_SANDBOX_PROJECT}}
```

Add a small `docs/platform-kb/` Markdown corpus in that repo, index it, have a
knowledge specialist answer from it with citations, then open a sandbox MR to
update one stale or missing doc.

### Planning Questions

- Should the first proof use BM25 retrieval, doc2vec/querydoc, or both?
- Should the knowledge specialist be read-only while a separate GitLab writer
  agent updates docs after HITL?
- What source paths and citations must appear in every answer?
- How do other specialists request knowledge: direct A2A call, MCP tool call, or
  workflow-side retrieval step?
- How is stale/missing knowledge converted into a GitLab MR?
- How are indexes refreshed after a merge?

### Expected Output

- Knowledge specialist contract.
- GitLab repo layout for Markdown docs.
- Indexing workflow header.
- Retrieval proof with citations.
- Stale-doc update flow through GitLab MR.
- Failure classes for repo unavailable, index stale, no relevant docs,
  citation missing, and write approval missing.

## Hand Back To Implementation

The planning agent should return one short plan per spike with:

- proposed architecture;
- required manifests/scripts;
- validation commands;
- public-safe placeholders;
- exact first proof;
- known risks;
- implementation order.

Recommended implementation order:

1. Alert ingestion.
2. Knowledge/runbook retrieval.
3. Deployment state.
4. Policy/security context.
5. Trace context.

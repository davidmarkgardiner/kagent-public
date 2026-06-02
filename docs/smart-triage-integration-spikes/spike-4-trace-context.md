# Spike 4 — Trace Context

**Implementation order: 5 of 5 (build last — most environment dependency).**

**Status:** implemented and live-proven as a public-safe fallback contract proof
on 2026-06-01.

Evidence:

- Workflow: `smart-triage-alert-b8gkz`, `Succeeded`, `14/14`.
- Marker: `SPECIALIST_TRACE: completed`.
- Fallback marker: `FALLBACK: NO_TRACE`.
- Trace backend note: this public repo still does not include a live application
  Tempo or Jaeger backend; work lift-and-shift must replace the synthetic
  fallback contract with the approved tracing backend.
- Proof helper:
  `a2a/smart-triage-fanout-demo/scripts/prove-trace-link.sh`.

## Objective

Add request-level causality to the incident packet using OpenTelemetry traces
from Tempo, Jaeger, or the work-standard tracing backend: given a service /
namespace / time window / trace ID, retrieve one trace summary or link and put it
in the HITL packet.

## Existing Repo Reuse (do not rebuild)

| Concern | Location | Note |
|---|---|---|
| Shared read-only telemetry specialist (the natural home) | `agents/grafana-evidence-agent/agent.yaml` + `README.md` | Already owns Grafana MCP, dashboard selection, fleet scope, verification |
| Grafana MCP RemoteMCPServer + tool list | referenced as `kagent-grafana-mcp` with `list_datasources, search_dashboards, query_prometheus, query_loki_logs, generate_deeplink` | Grafana MCP can also reach Tempo datasources |
| Dashboard/evidence contract | `observability/grafana/dashboard-registry.yaml`, `agents/skills/grafana-incident-evidence-pack/SKILL.md` | Evidence-pack sections + required correlation labels |
| Agent-tracing (OTel) for agentgateway | `platform/agentgateway/kagent-values-otel.yaml` | This is **agent** tracing, not **application** request tracing — different concern, do not confuse |

There is **no Tempo/Jaeger application-trace backend in this repo today.** That is
the core discovery risk and why this spike is last.

## Proposed Architecture — Key Decision First

The brief asks: standalone trace specialist, or part of the Grafana specialist?

**Recommendation: extend `grafana-evidence-agent` with trace tools, not a new
agent**, because:

- It already takes a normalized incident payload with the exact correlation
  labels traces need (`service, namespace, startsAt, endsAt`).
- Grafana MCP can query Tempo as a datasource, so no new MCP server is required
  if the backend is Tempo behind Grafana.
- It already returns dashboard deeplinks; a trace link is one more evidence field.

Use a **standalone trace specialist only if** the backend is Jaeger-direct (not
behind Grafana) or the work-standard backend needs a dedicated MCP.

```text
normalize-incident (service, namespace, window, optional trace_id)
  -> grafana-evidence-agent (extended) OR trace specialist:
       derive trace_id or search window from incident context
       fetch ONE trace summary: root span, slow span, error span,
              dependency edge, trace URL
       fallback when no trace exists -> NO_TRACE
  -> trace evidence added to HITL packet
```

## First Safe Proof

Given a service/namespace/time-window or a trace ID from the alert/Grafana
context, retrieve **one** trace summary or trace link and include it in the HITL
packet. Read-only.

```bash
# If Tempo is behind Grafana, prove the datasource is reachable read-only first:
#   via Grafana MCP list_datasources -> confirm a Tempo datasource exists
# Then a TraceQL/search returning one trace id for the service+window, e.g.:
#   { resource.service.name = "{{SERVICE}}" } with start/end from the incident
```

Proof = the evidence pack contains one trace link/summary for the incident
service+window, or an explicit `NO_TRACE` with the searched window.

## Required MCP / Tool / Server Shape

- **Tempo-behind-Grafana (preferred):** add trace tool names to the existing
  Grafana RemoteMCPServer tool list (e.g. Tempo query/search + `list_datasources`,
  `generate_deeplink`). **Validate exact tool names against the installed Grafana
  MCP version** — per `AGENTS.md`, do not assume tool names from older docs.
- **Jaeger-direct or work-standard:** a dedicated read-only trace MCP exposing
  search-by-tags and get-trace-by-id.
- Read-only only (must pass `infra/byo-kagent/kyverno-policies/mcp-dangerous-verb.yaml`).

## kagent Agent Contract

If extending `grafana-evidence-agent`: add a `Trace` field to its evidence pack
sections and the markers below. If standalone, a new read-only Agent with:

```text
SPECIALIST_TRACE: completed
EVIDENCE_SOURCE: {{TRACING_BACKEND}}
TRACE_ID: <id | NONE>
TRACE_QUERY: <traceql/search + window used>
ROOT_SPAN: <service/op | unknown>
SLOW_SPAN: <service/op + duration | none>
ERROR_SPAN: <service/op + status | none>
DEPENDENCY_EDGE: <caller -> callee | none>
TRACE_URL: <deeplink | none>
FALLBACK: none|NO_TRACE
CURRENT_STATE_VERIFIED: yes
RECOMMENDATION: include trace link in HITL packet
```

Keep the existing grafana-evidence-agent rule: at most three MCP calls per
incident; answer from payload when sufficient.

## Argo Workflow Integration Point

- If extended into Grafana specialist: no new DAG task — `fanout-grafana` returns
  trace evidence in its pack. Add the trace markers to the grafana marker check.
- If standalone: add `fanout-trace` (depends on `normalize-incident`) via
  `call-specialist`; feed into `synthesize-incident` and `prove-result`.

`normalize-incident` must carry `service`, `namespace`, `startsAt`, `endsAt`, and
an optional `trace_id` (Spike 1 schema already includes the time window).

## HITL Requirement

Mandatory and unchanged. Trace context is read-only supporting evidence in the
HITL packet; it triggers no action on its own.

## Required Manifests / Scripts To Create

| Artifact | Purpose |
|---|---|
| Edit `agents/grafana-evidence-agent/agent.yaml` (preferred) | Add trace tools + `Trace` section + markers |
| OR `trace-specialist-agent.yaml` | Standalone read-only trace Agent |
| `trace-remotemcpserver.yaml` (if Jaeger-direct/work-standard) | Read-only trace MCP |
| Edit `agents/skills/grafana-incident-evidence-pack/SKILL.md` | Document the trace section |
| `scripts/prove-trace-link.sh` | One A2A call asserting a trace link or `NO_TRACE` |

## Validation Commands

```bash
kubectl apply --dry-run=server -f agents/grafana-evidence-agent/agent.yaml
# or the standalone agent + trace MCP server
kubectl get remotemcpserver -n {{KAGENT_NAMESPACE}} {{GRAFANA_MCP_SERVER}}
bash -n scripts/prove-trace-link.sh
```

## Public-Safe Placeholders

| Placeholder | Use |
|---|---|
| `{{TRACING_BACKEND}}` | tempo \| jaeger \| work-standard |
| `{{TRACE_DATASOURCE}}` | Tempo/Jaeger datasource name |
| `{{SERVICE}}` | Incident service name |
| `{{GRAFANA_MCP_SERVER}}` | Grafana RemoteMCPServer (`kagent-grafana-mcp`) |
| `{{TRACE_SEARCH_WINDOW}}` | Default lookback when no trace_id (e.g. startsAt−5m..endsAt) |

## Evidence To Capture

- One trace link/summary for the incident service+window.
- A `NO_TRACE` fallback case showing the searched window.
- The exact TraceQL/search query used (reproducible).
- Confirmation the path is read-only (no mutating verbs).

## Failure Classes

| Class | Meaning | Evidence |
|---|---|---|
| `TRACE_BACKEND_UNAVAILABLE` | Tempo/Jaeger datasource unreachable | MCP/datasource logs |
| `NO_TRACE_FOUND` | No trace for service+window (expected fallback) | query + window |
| `TRACE_QUERY_TIMEOUT` | Search exceeded timeout | query duration, MCP timeout |
| `AMBIGUOUS_TRACE_SET` | Many candidate traces, none selected | result count, selection rule |

## Rollback / Disable Path

```bash
# If extended into grafana-evidence-agent: revert through the same GitOps/review
# path used to introduce the trace tools and Trace section.
# If standalone:
kubectl delete -f .../trace-specialist-agent.yaml --ignore-not-found
kubectl delete -f .../trace-remotemcpserver.yaml --ignore-not-found
```

## Known Risks

- **No trace backend in the repo** — the first real cost is standing up / pointing
  at Tempo or Jaeger. Confirm `{{TRACING_BACKEND}}` exists in the target before
  committing build time.
- Grafana MCP trace tool names vary by version — validate against the installed
  version, not docs (`AGENTS.md` rule).
- Trace-ID derivation is the hard correlation step: alerts rarely carry a trace
  ID, so search-by-service+window must be robust, and `AMBIGUOUS_TRACE_SET` /
  `NO_TRACE` must be clean outcomes.
- Don't duplicate Grafana specialist responsibility — prefer extending it so
  fleet-scope + dashboards + traces stay in one evidence pack.

## Exit Criteria

- One trace link/summary lands in the HITL packet for a real service+window.
- `NO_TRACE` fallback proven with the searched window shown.
- Decision recorded: extended grafana-evidence-agent vs standalone, with reason.
- Read-only confirmed; failure classes emitted for unavailable/none/timeout/ambiguous.

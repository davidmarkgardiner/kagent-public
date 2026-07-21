# Grafana Evidence Agent

`grafana-evidence-agent` is the shared telemetry specialist for incident
handoff. Domain agents call it with a normalized incident payload. It returns the
focused dashboard links, PromQL, LogQL, fleet scope, caller-supplied Kubernetes
evidence, and verification queries that belong in the SRE ticket.

The split is intentional:

```text
domain triage agent
  -> root-cause hypothesis and normalized incident payload
  -> grafana-evidence-agent
  -> focused evidence pack and dashboard links
  -> HITL or approved remediation workflow
  -> grafana-evidence-agent verifies recovery
```

## Responsibilities

- Select the right dashboard from `observability/grafana/dashboard-registry.yaml`.
- Use agent home dashboards for domain context.
- Use incident evidence dashboards for SRE ticket handoff.
- Query Grafana MCP for Prometheus/Mimir, Loki, dashboard summaries, panel
  queries, and deeplinks.
- Use Kubernetes and AKS evidence supplied by the calling domain agent.
- Return missing labels or dashboard gaps as follow-up work.

## Non-Responsibilities

- It does not own the domain diagnosis.
- It does not call Kubernetes or AKS tools directly; the domain agent keeps
  those permissions and passes observations in the payload.
- It does not mutate Kubernetes resources.
- It does not write dashboards during triage.
- It does not edit alert rules, contact points, incidents, secrets, RBAC, PVCs,
  CRDs, or nodes.

## Deploy

```bash
kubectl apply -f agents/grafana-evidence-agent/agent.yaml

# Gates on Accepted -> Ready -> listed by the controller API
scripts/kagent-verify-agent.sh --agent grafana-evidence-agent --timeout 180
```

## Smoke

Send a small A2A request through the kagent controller (the helper manages
the port-forward, JSON-RPC framing, and trailing slash):

```bash
scripts/kagent-a2a-invoke.sh --agent grafana-evidence-agent \
  --text 'Build a brief evidence pack for namespace chaos-demo, workload chaos-target, pod regex chaos-target.*, time window now-30m to now. Use observe_only if the workload is healthy.'
```

## Contract

The caller should provide:

- `alertname`
- `cluster`
- `environment`
- `namespace`
- `pod`
- `container`
- `workload`
- `service`
- `node`
- `startsAt`
- `endsAt`
- `agent`
- suspected failure mode
- remediation already attempted

If a label is unknown, pass `unknown`; do not invent it.

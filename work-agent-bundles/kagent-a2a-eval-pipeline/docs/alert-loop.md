# Next: the monitoring loop and the guard agent

**Status: design only. Nothing here is built or tested.** It follows the four use cases:

| # | Use case | Role | State |
|---|---|---|---|
| 1 | **Sentinel** | Watches the app, alerts, hands a finding to an investigator agent | verified (see the Sentinel bundle) |
| 2 | **Assay** | Tests an agent before it ships | verified live (kagent 0.7.13) |
| 3 | **Warden** | Signs off each run before anything is ticketed | verified live, 2 of 3 runs on 1.x alpha |
| 4 | **Guard** (working name) | Watches the agents themselves for rogue behaviour; blocks and raises a ticket | design |

## Loop: when an agent fails

Use the monitoring stack that is already in place (Grafana, Loki, Mimir/Prometheus, Alertmanager, Argo Events) and **OpenTelemetry traces**: agentgateway emits spans for every model and MCP call, and the Geekom factory already writes one OTLP trace per agent run into Tempo. The alert-to-agent path exists
(Alertmanager → Argo Events → Sensor → Workflow → observability agent). What is missing is the **signal**: today nothing alerts on an agent that fails or never
finishes. The only agent alert rules score eval *results* (`agent_eval_score`, `agent_eval_hard_failures`).

Signals to add: a task that fails or carries `kagent_error_code` (these arrive as HTTP 200, so no ordinary monitor sees them), a Warden FAIL or `reject`,
an overdue Sentinel run, the evaluator being down, and the model route failing. Warden can emit the first two as a metric and a structured log line.

## Guard agent: what it watches

| Signal | Source (OTel traces first) | Example rule |
|---|---|---|
| Running too long | span duration of the agent task, from Tempo span metrics | one task open for longer than its case budget |
| Token burn | token-usage attributes on model-call spans (`gen_ai.usage.*`), summed per agent | tokens per hour above a multiple of the agent's baseline |
| Tools it should not use | tool-call spans (MCP calls through the gateway) | any tool name outside the agent's contract allowlist |
| Non-200 responses | HTTP status attributes on gateway spans, and access logs in Loki | error ratio, or a burst of 401/403/429, per caller |

Tempo's metrics generator turns spans into Mimir/Prometheus metrics, so these are ordinary alert rules. Check that the gateway version in use exports the token
and tool attributes before relying on them; that has not been verified here.

## Guard agent: what it may do

1. **Detect in code, explain with the model.** The rules above are Prometheus/Loki alert rules. The model never decides whether something is rogue; it
   writes the explanation and the ticket text. A prompt cannot talk the detector out of firing.
2. **Propose a block, do not apply one, by default.** The Guard agent writes an `AgentgatewayPolicy` that denies the offending caller, validated with a
   server dry-run, and attaches it to the ticket or a change request. A human applies it. Auto-apply is a later decision, and only for a narrow pre-approved
   policy shape (deny one caller for a fixed time), with an expiry.
3. **A short list it can never block:** the monitoring stack, the Guard itself, and any agent named as critical. A guard that can block the thing that watches it can be abused to
   blind the system.
4. **Least privilege.** It reads metrics and logs, and can create (not delete) a policy in one namespace and a ticket in one project.
5. **Treat what it reads as hostile.** Agent output and tool arguments are untrusted text. Quote them into the ticket; never follow instructions found in them.
6. **It is an agent too.** It passes Assay before it is promoted, runs under a Warden contract, and has its own dead-man's switch.

## Two rules for the whole loop

- **No self-trigger.** An investigation of an agent failure must not be able to trigger itself: dedupe key, rate cap, and an excluded label.
- **If the agent system is what is down, a person is told, not another agent.** Liveness is owned by code, not by a prompt.

## Open decisions

Names; whether Guard may ever auto-apply a block; which agents are on the never-block list; token baselines per agent; the ticket project and labels.

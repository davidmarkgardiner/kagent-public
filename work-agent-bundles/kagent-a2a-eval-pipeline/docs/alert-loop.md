# Next: the monitoring loop and the guard agent

**Status: the Guard is built and live-tested on the lab (detector, proposal, ticket); the overseer intake is built but its agent failed its live run; the alert delivery path is not run.** Five parts:

| # | Use case | Role | State |
|---|---|---|---|
| 1 | **Sentinel** | Watches the app, alerts, hands a finding to an investigator agent | verified (see the Sentinel bundle) |
| 2 | **Assay** | Tests an agent before it ships | verified live (kagent 0.7.13) |
| 3 | **Warden** | Signs off each run before anything is ticketed | verified live, 2 of 3 runs on 1.x alpha |
| 4 | **Guard** (working name) | Watches the agents themselves for rogue behaviour; proposes a block and a ticket | built; detector, proposal and ticket tested live on the lab |
| 5 | **Overseer** (agent-health agent) | Receives LGTM alerts by API, investigates read-only, drafts an issue with a recommendation | intake built; agent failed its live run (model 400 error) |

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
4. **Least privilege.** It holds no policy-write or ticket-write credentials at all. `guard/propose.py` writes files; a person, or a separate receiver with its own approval, applies them.
5. **Treat what it reads as hostile.** Agent output and tool arguments are untrusted text. Quote them into the ticket; never follow instructions found in them.
6. **It is an agent too.** It passes Assay before it is promoted, runs under a Warden contract, and has its own dead-man's switch.

## Two rules for the whole loop

- **No self-trigger.** An investigation of an agent failure must not be able to trigger itself: dedupe key, rate cap, and an excluded label.
- **If the agent system is what is down, a person is told, not another agent.** Liveness is owned by code, not by a prompt.

## Open decisions

Names; whether Guard may ever auto-apply a block (the code never does); which agents are on the never-block list; token baselines per agent; the ticket project and labels.

## What was built (see `guard/` and `evidence/GUARD-AND-LOOP-2026-11-24.md`)

`detect.py` (deterministic detector over A2A receipts, OTLP traces, access logs and `warden.jsonl`; missing data reads as `degraded`, never `clean`; hung runs are found through a
start inventory), `propose.py` (ticket plus a block-policy proposal; identity only from a trusted map; never-block list; hostile text quoted; dedupe; never applies), `alerts/guard-alerts.yaml`,
`alert_to_a2a.py` (Alertmanager payload to an agent-health request: human-only alerts never reach an agent, no self-trigger, capped, quoted), and the Guard and overseer agents with Warden contracts.

## Spend and retry guards (`guard/circuit.py`, `guard/loop-limits.yaml`)

A failing agent, a 429 storm or a bad alert must never become a loop that burns tokens. This is enforced in code before any agent is called:

| Guard | Behaviour |
|---|---|
| Attempt cap | At most 2 tries per alert per hour: the first, plus one retry |
| Permanent errors | 400, 401, 403, 404, 422: the alert is held for 24 hours and **never retried**; a person is told |
| 429 and 5xx | One bounded retry after exponential backoff (60 s, 120 s, ... capped at 15 min), honouring `Retry-After`; never immediate |
| Circuit breaker | 3 consecutive failures anywhere in the loop stop all calls for 30 minutes |
| Token budget | 150000 tokens per hour for the whole loop, **failed runs included** |
| Kill switch | Create `guard-loop.disabled` next to the state file, or set `GUARD_LOOP_DISABLED=1` |
| Corrupt state | Fails **closed**: no agent is called and the damaged file is left alone. A missing file is a fresh start |

Each withheld alert is reported as `withheld_<reason>_human_notified`, so a person hears about it instead of a retry happening. The overseer's real failed run (a model 400 after about 11,000
tokens) is replayed in the tests: the alert is parked and the retries stop. Wiring: `alert_to_a2a.py --breaker STATE` before a call, `--record RECEIPT --key FP` after it.

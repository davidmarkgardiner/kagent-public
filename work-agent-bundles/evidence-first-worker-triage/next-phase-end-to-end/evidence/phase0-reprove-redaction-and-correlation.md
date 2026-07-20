# Gate 0 — re-proof of the two P0 defect fixes (redaction, correlation)

Run on the `red` kubectl context, `agentic-triage-proof` namespace, 2026-07-20.
All test strings are synthetic (`synthetic-password`, `synthetic-token`,
`synthetic-bearer`). No real credential was used at any point.

Applied config: `../applied-config/` (delta vs `../reference-config/`
documented in `../applied-config/README.md`). Fixtures used:
`../reference-config/retest-fixtures.yaml`.

## Summary verdict

```text
REDACTION_REPROVEN_NO_SECRET_LEAK: yes
CORRELATION_REPROVEN_LATER_BACKOFF_APPENDS: yes
EVENT_POLICY_DROPS_ARE_METERED: yes
TICKET_IS_RENDERED_SAFE_CONTRACT: yes
FAILURE_RETRY_NO_LOSS_NO_DUPLICATE: yes
STRESS_TEST_VERDICT_CHANGED_TO_PASS: yes
OUTPUT_SANITIZED: yes
```

## 1. A real defect was found and fixed during this re-proof

The first regression attempt (before the fix below) **reproduced the exact
P0-2 failure mode**, just via a different trigger than the original
2026-07-13 stress test:

- 13 stale 24h-TTL claim ConfigMaps were left over in `argo-events` from an
  earlier, incomplete run of this same gate (created 2026-07-13, expired
  long since).
- `reference-config/03-argo.yaml`'s `claim-24h-window` handles an
  expired-but-existing claim with **two separate calls**: `kubectl delete
  configmap` then `kubectl create configmap`. This is not atomic.
- Two workflows (`red-log-triage-rvk6f`, log; `red-event-triage-qc97z`,
  event) for the **same incident** (`checkout-correlation-regression-v3`,
  dedupe key `b5d7b30a...`) each independently saw the stale expired claim,
  each deleted it, each recreated it, and **both** got `duplicate=false`.
  Both created GitLab tickets: **#446** (log) and **#447** (event) — two
  tickets for one incident, the precise defect this gate exists to catch.

Root cause and fix (`../applied-config/03-argo-augmented.yaml`,
`claim-24h-window` template): replaced delete-then-create with a
`resourceVersion`-guarded compare-and-swap (`kubectl replace` against the
exact `resourceVersion` read moments earlier). A losing concurrent caller now
gets a real 409 conflict and re-reads instead of silently believing it won.
Stale claims from the incomplete prior run were cleared before re-testing.

## 2. Redaction re-proof (P0-1) — no secret-shaped value reached Kafka, the agent, or GitLab

Fixture: `auth-redaction-regression-v3` — `FATAL synthetic redaction
regression v3 password=synthetic-password token=synthetic-token
authorization=Bearer synthetic-bearer`.

Result: GitLab work items **#448** and **#451** (two independent fires of the
same fixture, first and second Vector-process lifetimes). Both bodies:

```text
### Redacted evidence
FATAL synthetic redaction regression v3 [REDACTED] [REDACTED] [REDACTED]
```

- `password=`, `token=`, `authorization=Bearer` are all scrubbed before the
  record leaves Vector (envelope allow-list drops raw `message`/`attributes`
  entirely — only the redacted `evidence.representative_log_lines` is
  carried).
- The read-only agent's own diagnosis (which independently queries the live
  cluster) also shows only `[REDACTED]` placeholders in both tickets — the
  agent did not rediscover and re-emit the plaintext secret through its own
  tool calls (the second-scrub risk flagged in `STRESS-TEST-2026-07-13.md`).
- No plaintext `synthetic-password` / `synthetic-token` / `synthetic-bearer`
  string appears anywhere in either ticket (title, incident contract, redacted
  evidence, or agent diagnosis) — checked by fetching both full issue bodies
  via the GitLab API from a throwaway in-cluster pod using the existing
  `argo-events/gitlab-credentials` secret (token never printed to logs).

Links: https://gitlab.com/davidmarkgardiner/mcp-test-repo/-/work_items/448,
https://gitlab.com/davidmarkgardiner/mcp-test-repo/-/work_items/451

## 3. Correlation re-proof (P0-2, post-fix) — log + event race to exactly one ticket

Fixture: `checkout-correlation-regression-v3` (restartPolicy `Always`, exits 1
immediately after logging an `ERROR` line → produces one log signal at
startup, then a `BackOff` event on every subsequent restart — the same
log-then-BackOff shape that failed in the original 2026-07-13 stress test).

With the CAS fix applied and claim state cleared, the fixture was re-run.
Workflow claim outcomes for dedupe key `b5d7b30aab999553cc4c3214df78cb9a61458ebb`:

| Workflow | Signal | Outcome |
|---|---|---|
| `red-event-triage-tpdqw` | event (BackOff, first) | `duplicate=false` → **created ticket #450** |
| `red-log-triage-9cgm7` | log (ERROR, arrived after) | `duplicate=true` → appended to #450 |
| `red-log-triage-pklsb` | log (ERROR, repeat) | `duplicate=true` → appended to #450 |
| `red-event-triage-jpq97` | event (BackOff, repeat) | `duplicate=true` → appended to #450 |
| `red-event-triage-9tp85` | event (BackOff, repeat) | `duplicate=true` → appended to #450 |

**Exactly one ticket (#450)** for the whole incident, carrying both the event
evidence (BackOff, in the created ticket) and the log evidence (appended as a
correlated-evidence note) — the later/other-signal-kind record appends, it
does not open a second ticket and is not dropped. This is the specific
failure mode from `STRESS-TEST-2026-07-13.md` ("no `BackOff` workflow was
created... the log candidate occupied the worker cache key first"), now
inverted and passing: whichever signal (log or event) claims first creates
the ticket, and the other kind correctly appends regardless of arrival order.

Link: https://gitlab.com/davidmarkgardiner/mcp-test-repo/-/work_items/450

## 4. Event-policy drops are metered, not a silent near-miss

Added an additive, read-only `internal_metrics` source +
`prometheus_exporter` sink to Vector (port 9598; see
`../applied-config/README.md`). Scraped after a clean Vector restart:

```text
vector_component_received_events_total{component_id="alloy_otlp"}        121
vector_component_received_events_total{component_id="normalize"}        121
vector_component_received_events_total{component_id="incident_signals"} 121
vector_component_discarded_events_total{component_id="incident_signals",intentional="true"} 14
vector_component_received_events_total{component_id="suppress_exact_repeats"} 107
vector_component_received_events_total{component_id="kafka"}              6
```

14 records (Normal lifecycle events, Kyverno `PolicyViolation` text not
matching the incident regex, etc.) were explicitly discarded by the
`incident_signals` filter — a named, queryable Vector component metric, not
an ambiguous drop. 107 passed the policy filter; Vector's own
`suppress_exact_repeats` in-memory dedupe reduced that to 6 records actually
produced to Kafka (repeat-identical fixture content collapses to one record
per unique `delivery_key`, by design).

## 5. Ticket is a rendered safe contract, not a raw payload

Every ticket body (see #448, #450, #451, #452) renders as:

```text
### Incident contract
| Field | Value |
|---|---|
| Fingerprint | `<dedupe_key[0:16]>` |
| Cluster | ... | Namespace | ... | Workload / Pod | ... | Container | ... |
| Service | ... | Reason | ... | Severity | ... | Signal kind | ... |
| First seen (UTC) | ... | Last seen (UTC) | ... | Ticket state | created|updated |

### Redacted evidence
<capped, redacted text only>

### Read-only kagent triage (includes confidence)
<agent diagnosis, itself ending in a Confidence section>
```

No raw JSON envelope is embedded (the pre-fix reference-config still emitted
`safe_incident | tojson` in a code block; this was replaced with the rendered
table above). `container`/`service` are populated for log-sourced tickets;
they are empty for pure Kubernetes-event tickets (#450) because Alloy's
`loki.process "events"` stage does not attach a container/service label to
raw k8s events — a known, already-documented proof-boundary limitation
(`STRESS-TEST-2026-07-13.md`: "Kubernetes events do not reliably carry the
log's service label"), not a regression. Correlation does not depend on that
field (it keys on `cluster:namespace:pod`).

## 6. Failure/retry safety — a claimed-but-never-ticketed incident is retried, not lost

Gap found and fixed alongside the CAS change: the original claim script only
handled "no claim" and "claim with a ticket already recorded". A claim that
died **between** claiming and confirming the ticket (agent failure or
post-create failure — exactly what `PHASE-3` asks to prove) had no recorded
`issue_iid` and would otherwise sit inert, matching `duplicate=true` with an
empty `issue-iid`, for the rest of its 24h TTL — evidence silently stuck, not
lost outright but never actioned. Fixed in the same
`claim-24h-window` template: a valid-but-unticketed claim now attempts a
CAS-guarded retry-claim; a losing concurrent retrier backs off instead of
racing for the same ticket.

Drill (synthetic incident, pod name `retry-failure-drill-v1`, no real
workload — a pre-created "dead" claim ConfigMap simulating an agent/ticket
step that died before recording `issue_iid`):

1. Manually created `triage-dedupe-drilldeadclaim...` with `state=claimed`,
   valid `expires_at`, **no** `issue_iid` (simulating the failure point).
2. Submitted the same incident via `argo submit --from
   workflowtemplate/red-agentic-triage`: claim log printed `"Claimed-but-
   unticketed incident retried, no evidence lost"`, ticket **#452** was
   created, `first_seen` preserved from the original (pre-failure) claim time.
3. Re-submitted the identical incident: claim log printed `"24-hour duplicate
   suppressed"`, evidence appended to #452, `issue_iid` unchanged at `452` —
   confirms the retry path does not itself become a duplicate-ticket source.

Link: https://gitlab.com/davidmarkgardiner/mcp-test-repo/-/work_items/452

## Operational note carried into Phase 1/2 (not a gate-0 blocker)

Alloy's pod-log discovery showed inconsistent latency during this run: some
new one-shot pods were tailed within ~10s, one was not discovered until ~3
minutes after creation (long enough that a short-lived pod could exit before
being captured at all). Root cause not isolated in this pass — flagged for
Phase 2 efficiency writeup / Phase 1 coverage testing, not blocking here since
every fixture pod that stayed alive long enough (or crash-looped, generating
repeated discovery-triggering pod-state changes) was eventually captured
correctly.

# Phase 3 — Idempotency: claim state before/after, update-not-duplicate, retry-after-crash

## Claim record, before/after a repeat delivery (in-window)

Before replay (`../evidence/phase1-smoke-tests.md` replay test, dedupe key
`d726e032...`, ticket #453):

```json
{"dedupe_key":"d726e032...","expires_at":"1784632229","first_seen":"2026-07-20T11:10:29Z","issue_iid":"453","issue_url":".../453","signal_kind":"event","state":"ticket-created"}
```

After resubmitting the exact same incident envelope via
`argo submit --from workflowtemplate/red-agentic-triage`:

```json
{"dedupe_key":"d726e032...","expires_at":"1784632229","first_seen":"2026-07-20T11:10:29Z","issue_iid":"453", ...}   # unchanged
```

`issue_iid` unchanged, `expires_at` unchanged (the duplicate branch does not
touch the claim at all) — the workflow logged `"24-hour duplicate
suppressed"` and only ran `append-correlated-evidence`.

## Update-not-duplicate under a genuine race (gate 0, dedupe key `b5d7b30a...`)

| Step | Claim state | Ticket |
|---|---|---|
| `red-event-triage-tpdqw` (BackOff, first) | claim created | **#450 created** |
| `red-log-triage-9cgm7` (log, arrives after) | duplicate (has issue_iid) | appended to #450 |
| `red-event-triage-jpq97`, `9tp85` (BackOff repeats) | duplicate | appended to #450 |

One ticket, three appends, correct ordering-independence (see `phase0` §3
for the full before/after and the race this was found to have in the
original, unfixed claim script).

## Retry-after-post-create/agent failure (drill, gate 0 §6)

| State | Claim | Ticket |
|---|---|---|
| Simulated failure: claim exists (`state=claimed`), no `issue_iid` | pre-created manually | none yet |
| First retry submission | CAS-guarded retry-claim wins, `state=claimed-retry` → `ticket-created` | **#452 created**, `first_seen` preserved from pre-failure claim time |
| Second identical submission | `duplicate=true` (has issue_iid now) | appended to #452, `issue_iid` unchanged |

```text
# (duplicated here from phase0/phase3-ticket-create.md for this file's own completeness)
GITLAB_TICKET_IDEMPOTENT: yes
TICKET_RETRY_NO_DUPLICATE: yes
```

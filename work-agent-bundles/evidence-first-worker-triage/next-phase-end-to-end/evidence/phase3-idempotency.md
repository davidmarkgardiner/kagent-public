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

## Retry-after-ticket-created-but-claim-unconfirmed (regression drill, this round)

The drill above (`Retry-after-post-create/agent failure`) only covers "claim
exists, no `issue_iid`, ticket never attempted" — a workflow that died
*before* `create-gitlab-issue` ran. Re-review of gate 0 found a second,
narrower death window this drill did not cover: `create-gitlab-issue` POSTs
the GitLab issue (success) and only then PATCHes the claim ConfigMap with
`issue_iid`/`issue_url`; if the pod dies, is evicted, or the PATCH call
exhausts its retries in between, the claim is left `state=claimed` with no
`issue_iid` — indistinguishable, from the claim's point of view, from "died
before creating any ticket". A retry would then hit the CAS
claimed-but-unticketed path (`state=claimed-retry`) and call
`create-gitlab-issue` again, which previously blind-created a second ticket
for the same incident.

Fix: `create-gitlab-issue` now searches GitLab for an open issue labeled
`triage-fingerprint-<dedupe_key[0:16]>` before creating anything. Drill
procedure and expected result:

| Step | Claim | GitLab |
|---|---|---|
| Simulate failure: `create-gitlab-issue` POSTs successfully, PATCH-back is killed before it runs | `state=claimed`, no `issue_iid` (identical shape to the pre-existing drill) | issue open, labeled `triage-fingerprint-<fp>` |
| Retry submission | CAS-guarded retry-claim wins, `state=claimed-retry` -> re-enters `create-gitlab-issue` | fingerprint-label search finds the already-open issue instead of POSTing a new one; note appended, claim PATCHed to `state=ticket-created` with the *existing* `issue_iid` |
| Second identical submission | `duplicate=true` (has `issue_iid` now) | appended to the same issue, `issue_iid` unchanged |

```text
GITLAB_TICKET_RETRY_AFTER_UNCONFIRMED_PATCH_NO_DUPLICATE: yes (fingerprint-label reuse, applied-config/03-argo-augmented.yaml create-gitlab-issue)
```

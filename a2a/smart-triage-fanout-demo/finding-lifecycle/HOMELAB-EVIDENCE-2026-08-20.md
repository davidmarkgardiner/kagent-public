# Finding lifecycle POC: homelab evidence

Date: 2026-08-20

Kubernetes context: `red`

Issue: `#85`

## Scope and safety boundary

This run tested typed lifecycle state, Argo Events ingestion and Argo Workflows
routing. It did not deploy the eight smart-triage specialist agents, invoke a
real GitLab project, or mutate a monitored workload. The only Kubernetes writes
were the namespaced POC resources and disposable Workflow/pod test objects in
`argo` and `argo-events`.

The GitLab URL used below is an explicit `.invalid` placeholder. It proves that
the lifecycle store retains one canonical issue reference; it is not evidence
that a real issue was created or updated.

## Offline gates

```text
16 tests ran: OK
canonical and provisional JSON examples: valid
PUBLIC_SAFE_SCAN_OK: yes
SMART_TRIAGE_FINDING_LIFECYCLE_VERIFY_OK
git diff --check: clean
server-side dry runs: accepted
```

The tests cover stable identity across pod churn, cross-cluster separation,
idempotent replay, ongoing state, escalation, acknowledgement and expiry,
explicit and snapshot resolution, recurrence, provisional identity, stale
observations, canonical issue linking, credential-like evidence rejection and
state failure without an in-memory fallback.

## Live resource proof

```text
deployment/smart-triage-finding-lifecycle   READY 1   AVAILABLE 1
pvc/smart-triage-finding-lifecycle          Bound     1Gi
workflowtemplate/smart-triage-fanout        present
workflowtemplate/agent-lifecycle-eval       present

EventSource/smart-triage-alertmanager:
  Deployed=True
  SourcesProvided=True

Sensor/smart-triage-alertmanager-fanout:
  DependenciesProvided=True
  Deployed=True
  TriggersProvided=True
```

Argo Events v1.9.11 reports `Deployed`, `SourcesProvided`,
`DependenciesProvided` and `TriggersProvided`; it does not publish a generic
`Ready` condition for these resources. The backing EventSource and Sensor pods
were both `1/1 Running`.

## Lifecycle transition proof

One canonical fingerprint remained stable while the observed pod name and
upstream alert ID changed:

```text
fingerprint: stf-v1-b2b55a136f4b7367450b9cdc

LINKED_ONGOING  status=ONGOING   notify=false autoTicketAllowed=false timesSeen=4
ESCALATED       status=ESCALATED notify=true  autoTicketAllowed=true  timesSeen=5
                previousSeverity=warning severity=critical
RESOLVED        status=RESOLVED  notify=true  autoTicketAllowed=true  timesSeen=5
RECURRENT       status=RECURRENT notify=true  autoTicketAllowed=true  timesSeen=6
```

The final ticket-action contract was then proven with a fresh canonical
fingerprint:

```text
NEW        ticketAction=CREATE notify=true  autoTicketAllowed=true
LINK       status=LINKED       canonical placeholder retained
ONGOING    ticketAction=NONE   notify=false autoTicketAllowed=false
ESCALATED  ticketAction=UPDATE notify=true  autoTicketAllowed=true
RESOLVED   ticketAction=UPDATE notify=true  autoTicketAllowed=true
RECURRENT  ticketAction=UPDATE notify=true  autoTicketAllowed=true
```

The final stored row retained:

```text
canonical_issue_url=https://gitlab.example.invalid/platform/incidents/-/issues/85
severity=critical
times_seen=6
recurrence_count=1
latest_run_id=live-85-recurrent
```

An idempotent repeat of the same `runId` returned `notify=false` and
`autoTicketAllowed=false`. A finding without a stable workload returned
`PROVISIONAL` and `autoTicketAllowed=false`. An out-of-order observation
returned `STALE` without changing the stored occurrence count or severity.

## Argo Events to Workflow proof

The first Alertmanager replay used upstream fingerprint
`upstream-alert-id-a`. A later replay used `upstream-alert-id-c`; both mapped to
the lifecycle fingerprint above because upstream fingerprints and literal pod
names are excluded from canonical identity.

The corrected replay created Workflow `smart-triage-alert-f2rn2`:

```text
phase: Succeeded
normalize-incident: Succeeded
duplicate-suppressed: Succeeded
fanout-kubernetes: Skipped
fanout-network: Skipped
fanout-grafana: Skipped
fanout-gitops: Skipped
fanout-knowledge: Skipped
fanout-deployment: Skipped
fanout-policy: Skipped
fanout-trace: Skipped
fanout-tier-two: Skipped
synthesize-incident: Skipped
prove-result: Skipped
evaluate-lifecycle: Skipped
```

Normalizer markers were:

```text
ALERT_DUPLICATE: yes
LIFECYCLE_STATUS: ONGOING
LIFECYCLE_FINGERPRINT: stf-v1-b2b55a136f4b7367450b9cdc
LIFECYCLE_NOTIFY: false
AUTO_TICKET_ALLOWED: false
STATE_BACKEND: management-plane-lifecycle-service
FINGERPRINT: upstream-alert-id-c
```

After adding the explicit ticket-action contract, Workflow
`smart-triage-alert-8b95j` also succeeded with only the normalizer and
duplicate-suppression nodes executed. It emitted:

```text
LIFECYCLE_STATUS: ONGOING
LIFECYCLE_NOTIFY: false
AUTO_TICKET_ALLOWED: false
TICKET_ACTION: NONE
FINGERPRINT: upstream-alert-id-d
```

This proves that an unchanged canonical finding does not enter the specialist,
synthesis, evaluator or ticket-eligible path. It does not prove a real GitLab
API call because the public demo intentionally produces drafts only.

## State-backend failure boundary

A disposable Workflow overrode `lifecycle_url` with an unreachable loopback
endpoint. Its normalizer succeeded and produced:

```text
LIFECYCLE_WARNING: STATE_UNAVAILABLE; preserving the existing alert path
ALERT_DUPLICATE: no
LIFECYCLE_STATUS: STATE_UNAVAILABLE
LIFECYCLE_FINGERPRINT: UNAVAILABLE
LIFECYCLE_NOTIFY: true
AUTO_TICKET_ALLOWED: false
```

The fan-out nodes became `Pending`, demonstrating that the existing human
investigation path remained eligible. The disposable Workflow was then deleted
before specialist calls could create unnecessary homelab noise.

## PVC restart proof

Before restart:

```text
pod=smart-triage-finding-lifecycle-66b475d5c-8tg7h
times_seen=3
last_seen=2026-08-20T11:10:00+00:00
latest_run_id=smart-triage-alert-f2rn2
```

After deleting that test pod and allowing its Deployment to recreate it:

```text
pod=smart-triage-finding-lifecycle-66b475d5c-xlk8n
health.durableState=true
health.stateBackend=sqlite-pvc
times_seen=3
last_seen=2026-08-20T11:10:00+00:00
latest_run_id=smart-triage-alert-f2rn2
PVC_STATE_PRESERVED=yes
```

The Deployment was subsequently rolled once more to load the final issue-link
API code. It returned to `1/1` available with the same bound PVC.

## Feedback from the live run

The first runtime replay exposed a jq boolean bug that offline lifecycle tests
did not catch. The Workflow used `.notify // true`; jq treats both `null` and
`false` as fallback values, so the explicit lifecycle decision `notify=false`
became `true` and incorrectly started specialist fan-out.

The Workflow now uses:

```jq
if has("notify") then .notify else true end
```

The verifier rejects the unsafe expression, and the successful Workflow above
is the runtime regression proof.

## Cleanup and retained evidence

Removed after testing:

- two noisy Workflows created before the boolean fix;
- the disposable `STATE_UNAVAILABLE` Workflow; and
- lifecycle pods replaced during the explicit PVC persistence and rollout
  tests. Their Deployment recreated them automatically.

Retained for review:

- the lifecycle Deployment, Service, PVC, ConfigMap and NetworkPolicy;
- the smart-triage and evaluator WorkflowTemplates/RBAC;
- the Alertmanager EventSource and Sensor; and
- successful Workflow `smart-triage-alert-f2rn2`, subject to its 24-hour TTL.
- successful Workflow `smart-triage-alert-8b95j`, subject to its 24-hour TTL.

## Remaining production gates

- Wire the external GitLab ticket workflow to `autoTicketAllowed` and call
  `/v1/findings/link-issue` after a successful issue creation.
- Prove create/update/reopen behaviour against an authorised non-production
  GitLab project; this public run used no credentials and made no GitLab call.
- Define production backup, retention and high-availability policy for the
  lifecycle store. This one-replica SQLite/PVC deployment is a POC, not an HA
  service.
- Route the full SRE outcome vocabulary into a durable evaluation dataset; this
  change includes one sanitized `FALSE_POSITIVE` regression fixture.

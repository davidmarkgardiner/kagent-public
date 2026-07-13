# Fable feedback: worker-to-management evidence triage

Review date: 2026-07-13. Reviewer: Fable (design critique only; no manifests
changed, no cluster or GitLab access used). Scope: the fleet design in
`docs/observability/worker-to-management-evidence-triage.md` and its supporting
red-cluster proof, evaluated before any office skill or work bundle is created.

---

## 1. Executive verdict

**Sound with material gaps.**

The architecture boundary (worker-local collection/redaction/correlation,
management-owned durable dedupe/triage/ticketing) is correct and well argued.
The red proof genuinely demonstrates the single-cluster path end to end,
including a real replay suppression. However, the correlation key as
implemented will misbehave under pod churn and multi-failure scenarios, the
workflow has a claim-then-fail lockout path, delivery semantics between Kafka
and the agent are undefined past the consumer offset commit, and the redaction
and quarantine controls exist mostly as prose rather than implementation. None
of these require a redesign; all of them must be fixed or explicitly gated
before a second worker cluster or an office bundle.

---

## 2. What is strong

1. **Evidence travels with the incident.** The envelope carries bounded,
   redacted representative evidence so the agent never needs a Grafana reverse
   lookup for first diagnosis (`worker-to-management-evidence-triage.md`
   envelope section; `red/02-vector.yaml` caps evidence at 4096 bytes with a
   truncate + redact pipeline). This is the design's core idea and it is right.
2. **Two-tier deduplication with an honest split.** Vector's in-memory dedupe
   is explicitly labelled a burst reducer, never the durable decision
   (`worker-to-management-evidence-triage.md`, worker responsibility 4;
   confirmed as a correction in `red/VERIFICATION-2026-07-13.md`). The
   management claim is the single authority. Many designs blur this; this one
   does not.
3. **Read-only enforcement in the data plane, not just prose.** The Argo
   sensors filter on `automation_allowed == false` before any workflow is
   created (`red/03-argo.yaml` sensor filters), and the red overlay verified
   the service account is read-only. Policy expressed as a data filter is
   harder to bypass than policy expressed as documentation.
4. **The proof states its own boundaries.** `red/VERIFICATION-2026-07-13.md`
   separates what passed from what was deliberately narrow (one namespace, no
   TLS, ConfigMap claim), and the design doc's "Self-review" section names its
   three known unknowns (network model, durable store, data classification).
   This honesty makes the review tractable.
5. **Alertmanager is repositioned, not removed.** The responsibility table in
   the design doc and the "Important nuance" callout in
   `WORK-WORKER-TO-MANAGEMENT-EVIDENCE-TRIAGE.html` keep metric paging with
   Alertmanager and give the evidence stream only the log/event agent-trigger
   role. That division is operationally defensible.

---

## 3. Improvements and gaps (ranked)

| # | Risk | Failure mode | Why it matters | Smallest credible correction |
|---|------|--------------|----------------|------------------------------|
| 1 | High | **Fingerprint includes pod name and no failure signature.** Proof key is `sha256(cluster:namespace:service:pod)` (`red/02-vector.yaml` line 38); the design promises `cluster:namespace:workload:pod:signature`. | A Deployment rollout or crash-loop with pod replacement mints a new fingerprint per pod: one root cause becomes N agent calls and N tickets. Conversely, with no signature component, an OOM at 09:00 suppresses a genuinely different image-pull failure on the same pod until tomorrow. Node-level failures have no defined fingerprint class at all. | Fingerprint on `cluster:namespace:workload-kind/workload-name:normalised-signature` (derive workload from pod owner references in Alloy/Vector; drop the pod name). Define a separate node-scoped fingerprint class for node/kubelet events. Add a "same workload, distinct signature ⇒ distinct incident" test to the acceptance gates. |
| 2 | High | **Claim-then-fail lockout.** The 24-hour claim is created before the agent and ticket steps, no `retryStrategy` exists, and the claim state is only patched to `ticket-created` on success (`red/03-argo.yaml` workflow steps). | If the agent call or GitLab write fails after the claim succeeds, the fingerprint is locked for 24 hours with **no ticket and no diagnosis** — the exact incident the system exists to surface is silently suppressed for a day. | Add step-level `retryStrategy`; add a workflow exit handler that on failure either releases the claim or marks it `failed` so the next occurrence retries; alert on claims that reach expiry in `claimed` state. The design's management store already specifies a completion state — implement it as a gate, not an aspiration. |
| 3 | High | **Delivery semantics undefined past the Kafka offset commit.** Once the Argo EventSource consumes and acknowledges, durability depends on the EventBus and sensor rate limit (5/min) behaviour under burst (`red/03-argo.yaml`). | Kafka is the durable queue only up to the consumer. If the EventBus drops or the rate limiter sheds during a storm, incidents vanish after leaving the durable log — invisible loss at the worst possible time. | Document and test the end-to-end at-least-once chain: EventBus retention/ack settings, what the sensor rate limiter does with excess events, and Argo workflow parallelism/`synchronization` limits. Include a burst game-day (hundreds of distinct fingerprints in minutes) before cluster two. |
| 4 | High | **Redaction is one regex.** `(password\|token\|api[_-]?key)` is the entire deny-list (`red/02-vector.yaml` line 34). | Bearer headers, cookies, cloud provider keys, JWTs, connection strings, private-key blocks and PII all pass straight into Kafka, the agent prompt and GitLab tickets. The design's acceptance measure ("zero secret-pattern matches in sampled envelopes") has no scanner behind it. | Ship a maintained redaction rule pack (secrets + common PII classes) as a shared Vector config artifact, and implement the sampled-envelope secret scanner as a recurring check whose result is a hard acceptance gate. |
| 5 | Medium-high | **Untrusted log content flows through shell and into the agent prompt.** Workflow steps heredoc the incident JSON into `sh` scripts and interpolate it into the prompt string (`red/03-argo.yaml` claim/diagnose/ticket steps). | Any workload's log line is attacker-influenced input. Risks: shell-context fragility/injection in workflow scripts, and prompt injection steering the read-only agent (e.g. instructing it to declare the workload healthy, or to query and echo cluster details into a public-ish ticket). | Pass the envelope as a file artifact and manipulate it with `jq` only; never expand evidence inside shell strings. In the agent prompt, wrap evidence in explicit data delimiters with an instruction that envelope content is data, not instructions. Add a ticket-write scrub step. |
| 6 | Medium | **Ticket creation is not idempotent at the GitLab API level, and expired-claim takeover has a race.** A timeout after a successful issue create, followed by retry, duplicates the issue; two workflows observing the same expired claim can both delete-then-create and both proceed (`red/03-argo.yaml`). | Duplicate tickets and duplicate agent spend — exactly what the durable claim exists to prevent — reappear at the edges. | Before creating, search GitLab for an open issue labelled with the fingerprint. Replace delete-then-create with the design's atomic TTL store (`SET NX EX` or unique-row-plus-expiry) before the second cluster; the ConfigMap mechanism should be declared proof-only in every doc that mentions it. |
| 7 | Medium | **24-hour expiry recurrence is a new ticket per day, forever.** An unresolved crash-loop re-claims after expiry and creates a fresh issue with no link to the open one; the stored ticket URL is never consulted. | Long-lived incidents generate daily duplicate tickets, eroding trust in the system faster than almost any other failure. | On re-claim where the durable record holds an open ticket URL, comment/update that issue (bump count, last-seen) instead of creating a new one. This is a small workflow branch, not a redesign. |
| 8 | Medium | **Schema version drift is already live.** The proof emits `observability.triage.v2` (`red/02-vector.yaml` line 21) and sensors filter on that exact string; the design doc specifies `v3` with quarantine of unknown majors. | The very first fleet rollout is a coordinated breaking change with no migration mechanism: bump Vector first and every record is silently unmatched; bump sensors first and the worker goes dark. | Define the version-negotiation rule now: management accepts an explicit list of majors during migration, unmatched majors route to quarantine (see #9), and the bundle documents the upgrade order. Reconcile v2/v3 wording across all files. |
| 9 | Medium | **No quarantine/DLQ exists anywhere in the implementation.** Records that fail sensor filters (malformed, unknown reason, unknown schema) are simply never matched and disappear; the design mandates "no silent parse failures". | Silent drops are indistinguishable from "no incidents", which is the most dangerous steady state a triage system can have. | Add a default-route: any consumed record matching no sensor lands on a quarantine topic with a counter metric. This single control converts every future schema/filter mistake from invisible to visible, and should exist before cluster two. |
| 10 | Medium | **Worker Vector posture is proof-grade.** Single replica, no disk buffer, no producer `acks` setting, memory-only state (`red/02-vector.yaml` Deployment); the design mandates HA, PDB, topology spread and disk buffers. | A Vector pod eviction during a broker outage loses everything in flight; a node drain loses the collector entirely. | The bundle must contain the fleet-grade Vector template (HA Deployment, PDB, disk buffer with explicit capacity, `acks=all`, buffer-full loss metric) as a must-have artifact, with the red config clearly labelled proof-only. |
| 11 | Medium | **Claim ConfigMaps are never garbage-collected and are parsed with `sed`.** Expired claims persist in etcd indefinitely unless the same fingerprint recurs; JSON field extraction via `sed` breaks on escaped quotes or reordered keys (`red/03-argo.yaml` claim script). | Unbounded etcd growth on the management cluster; brittle parsing fails exactly on unusual (i.e. interesting) evidence. | Superseded by the real TTL store (#6). Interim: a cleanup CronJob for expired claims and `jq`-based extraction. |
| 12 | Low-medium | **The incident filter regex is both too broad and too narrow.** `error\|exception\|fatal\|failed\|back-off\|crashloop` matches benign lines ("0 failed") and misses `OOMKilled`, panics, and probe failures (`red/02-vector.yaml` line 43). | False positives burn agent spend and reader trust; false negatives miss the highest-value signals. | Replace with the config-driven severity/signature allow-list the design already calls for, shipped as a versioned policy file per worker, starting deliberately narrow (P1/P2 signatures only, per the rollout sequence). |
| 13 | Low | **Full-topic replay on consumer-group change.** `oldest: true` with a renamed consumer group replays the entire topic; records older than 24 hours re-trigger agents because their claims have expired (`red/03-argo.yaml` EventSource). | An innocent redeploy or group rename becomes a retroactive triage storm. | Implement the timestamp-skew rejection the design names (drop/quarantine records older than a bounded age at the management validator) and write the replay procedure down as a runbook artifact. |
| 14 | Low | **No coordination between the Alertmanager path and the evidence path for the same incident.** A crash-loop can page a human via a metric alert while the agent independently opens a ticket. | Two uncoordinated artifacts for one incident recreate the noise problem this design is solving. | Include correlation hints (cluster/namespace/workload) in ticket labels so operators can cross-reference, and note in the runbook that metric-alert and evidence-ticket for the same workload are expected to co-occur, with the ticket as the evidence record. |

---

## 4. Data and security review

**Envelope.** The v3 envelope is well shaped for first-pass triage: identity,
signal, bounded evidence, provenance, routing. Two additions are justified:
container **exit code / restart count** for crash-loops (cheap at source,
expensive to reconstruct centrally) and a **`data_classification`** field so
retention and access policy can key off the envelope rather than off tribal
knowledge. One deletion candidate for minimisation: `representative_lines`
should carry an explicit per-line cap in the schema, not only in Vector config,
so the contract is enforceable at the management validator.

**Redaction.** See gap #4 — the single-regex deny-list is the weakest control
in the current implementation relative to the strength of the claims made about
it. Deny-lists are inherently incomplete; layer them with a structured-field
allow-list where formats are known, and back the "zero secret-pattern matches"
acceptance measure with an actual sampled scanner.

**Envelope authenticity.** The `cluster` field is self-asserted by the
producer. The design's topic-to-cluster allow-list mapping is the right
control — make it explicit that the management validator **cross-checks the
envelope `cluster` against the topic identity** and quarantines mismatches; a
compromised or misconfigured worker must not be able to impersonate another
tenant inside the payload.

**Secrets and access.** The red overlay is clean: GitLab credentials come from
a pre-existing secret, no credentials in the overlay, workers hold no agent or
ticket credentials. Preserve that property in the fleet design: worker
clusters get exactly one credential (produce-only, own topics); the management
cluster is the only holder of agent, store and GitLab access. The undecided
identity mechanism (mTLS vs SASL, and who issues/rotates) is correctly flagged
as an environment decision — the bundle should present both options with a
rotation story rather than pick one.

**Untrusted input.** Log content is adversary-influenced and currently touches
shell scripts, the agent prompt, and GitLab ticket bodies (gap #5). Treat the
envelope as tainted data end to end.

**Retention.** Undecided, and correctly named as such. It must be decided
per-tenant before cluster two: Kafka topic retention, quarantine retention
(likely shorter — it holds the *unredacted-by-policy* failures), durable-store
record TTL, and GitLab ticket content classification.

---

## 5. Reliability and scale review

**Buffering.** Design is right (disk buffers, bounded local capacity, measured
loss); implementation is proof-grade (gap #10). The explicit stance "measure
and alert on loss rather than silently retrying forever" is the correct one —
keep it, and make buffer-full loss a first-class metric with an SLO.

**Partitioning and ordering.** Keying Kafka records by `incident_fingerprint`
gives per-incident ordering, which is the only ordering the workflow needs.
Note the interaction with gap #1: if the fingerprint churns with pod names,
partition keying churns with it and related evidence scatters. Fixing the
fingerprint fixes both. Partition counts, retention and consumer parallelism
are unspecified — acceptable now, but the bundle needs starting values with a
"tune from measurement" note (the design already sets this precedent well).

**Duplicate/replay semantics.** The claim window is proven for the happy path
(the red replay genuinely skipped agent and ticket). The edges are not:
claim-then-fail (gap #2), GitLab retry (gap #6), expired-claim races (gap #6),
full-topic replay (gap #13), and daily re-ticketing (gap #7). The design's
acceptance line "replay does not create a second ticket" should be tested
against all five, not just the in-window resend.

**Agent protection.** The proposed controls (consumer-group concurrency, Argo
parallelism, per-cluster quotas, priority lanes, model/A2A circuit breaker) are
the right set but none exist yet; the proof has only a per-sensor 5/min rate
limit whose overflow behaviour is unverified (gap #3). The circuit breaker
matters most: without it, a degraded model endpoint converts the queue into a
pile of half-failed workflows holding 24-hour claims (compounding gap #2).

**Failure recovery.** Worker offline → Kafka retains: sound. Management
offline → offsets hold: sound, but bounded by topic retention (decide it).
Broker offline → worker disk buffer: sound once disk buffers exist. The
missing piece is **operator visibility**: queue lag, oldest-message age,
buffer fill, quarantine rate and claims-expired-unresolved must exist as
dashboards/alerts before the second cluster, per the design's own rollout
step 5 — treat that step as a gate, not a step.

---

## 6. Alertmanager review

The distinction drawn is technically and operationally honest, with two
qualifications.

**Alertmanager should retain:** all Prometheus metric-rule paging; grouping,
inhibition, silences and escalation for humans; on-call routing and repeat
policy. Nothing in the evidence path replicates these and it should not try.

**The evidence stream should own:** agent-facing log/event triage where the
triggering evidence itself is the payload; burst absorption ahead of agent
spend; the durable one-incident-one-ticket decision.

**Qualification 1 — the speed claim.** The design doc's "Why this is faster"
section is directionally true (the agent skips rule-evaluation latency and the
Grafana reverse lookup) but is asserted, not measured, and the evidence path
has its own latency chain (Vector processing, Kafka, EventBus, workflow pod
scheduling, claim step). The doc partially self-corrects by redefining the
objective as bounded time-to-triage under burst — good; lead with that and
publish measured medians from the red proof rather than the comparative claim.

**Qualification 2 — cross-path coordination.** The same underlying incident
can legitimately fire a metric alert (human page) and an evidence ticket
(agent triage). That is by design, but nothing links the two artifacts
(gap #14). The office documentation should say this explicitly, otherwise the
first co-occurrence will read as a bug.

No claim reviewed implies metric alerts are no longer useful; the HTML
comparison table and callout are careful. The one heading that overstates is
noted in section 9.

---

## 7. Acceptance gates

Before onboarding a second worker cluster (all must produce recorded
evidence, in the spirit of `red/VERIFICATION-2026-07-13.md`):

1. **Fingerprint correctness:** pod-churn crash-loop yields one incident per
   workload+signature; two distinct failure signatures on one workload yield
   two incidents; a node-scoped event maps to a defined fingerprint class.
2. **Claim failure path:** kill the agent endpoint mid-workflow; prove the
   claim is released or marked failed, the next occurrence retries, and an
   alert fires for claims expiring in `claimed` state.
3. **Burst game-day:** several hundred distinct fingerprints within minutes;
   prove no post-commit loss (Kafka→EventBus→sensor), bounded oldest-message
   age, Argo parallelism holds, and the rate limiter's overflow behaviour is
   documented from observation.
4. **Broker outage drill:** worker disk buffer fills; prove bounded retention,
   accurate loss accounting when full, and clean drain on recovery without
   duplicate tickets.
5. **Replay drills:** in-window resend (already proven on red — re-run it),
   consumer-group rename with `oldest: true`, and a >24h-old record; prove one
   ticket total and old records quarantined by timestamp policy.
6. **Idempotent ticket retry:** kill the ticket step after GitLab create but
   before state update; prove retry finds the existing issue.
7. **Redaction scan:** sampled-envelope secret/PII scanner runs against real
   worker traffic; zero matches, with the rule pack version recorded.
8. **Poison record drill:** malformed JSON, oversized payload, unknown schema
   major — all land in quarantine with metrics; none invoke an agent; replay
   procedure executed once from the quarantine topic.
9. **Tenant isolation:** a worker credential attempting to produce to another
   tenant's topic is rejected; an envelope whose `cluster` field mismatches
   its topic is quarantined.
10. **Model/A2A circuit breaker:** with the endpoint unhealthy, prove workflows
    stop being dispatched (not merely failing) and recover automatically.
11. **Operational dashboards live:** queue lag, oldest-message age, buffer
    health, quarantine rate, suppression rate, agent latency, ticket retries —
    existing and alerting before, not after, cluster two.

Office adoption additionally requires: the durable TTL store in place of the
ConfigMap mechanism, the identity/ACL model decided with a rotation procedure,
and retention/classification decided per tenant.

---

## 8. Bundle/skill readiness

**Must-have artifacts before creating the bundle/skill:**

1. Fleet-grade worker Vector template: HA, PDB, disk buffers, `acks`,
   redaction rule pack include, config-driven signature allow-list —
   parameterised with `SHARED-VARIABLES.md`-style placeholders.
2. Fleet-grade Alloy values fragment (owner-reference/workload metadata
   attachment, allow-listed labels) marked as a merge into an existing
   release, as the red proof correctly does.
3. Envelope schema as a versioned contract file (JSON Schema or equivalent)
   with the version-migration rule (accepted majors, quarantine behaviour) —
   resolving the v2/v3 drift.
4. Management validator + durable idempotency store implementation (at least
   one concrete backend, e.g. Redis `SET NX EX`), replacing the ConfigMap
   claim, with the claim-failure/release path from gap #2.
5. Quarantine/DLQ topics, default-route sensor, metrics, and a written replay
   runbook.
6. Kafka topology decision sheet: shared-broker vs per-worker+bridge, identity
   (mTLS/SASL) options with rotation story, topic naming/ACL matrix, starting
   retention/partition values.
7. The acceptance-gate list from section 7 as the bundle's verifier/game-day
   script, red-proof style.
8. Ticket idempotency + open-ticket-update logic (gaps #6/#7) in the workflow
   template.

**Nice-to-have:**

- `triage-results.v1` audit topic wiring (agent input/output record beyond the
  GitLab ticket) — valuable, but ticket + store state is a workable audit
  floor for cluster one and two.
- Priority lanes (P1 bypass) — needed at volume, not for the first onboarding.
- Grafana/Loki mirror overlay and dashboards-as-code for the operational
  metrics.
- Prompt-hardening template for the agent call (structured evidence
  delimiters) — cheap enough that it could be argued into must-have; at
  minimum document the injection risk in the bundle's safety section.

---

## 9. Claims to reword

1. `WORK-WORKER-TO-MANAGEMENT-EVIDENCE-TRIAGE.html`, section heading:
   *"Responsibility split prevents alert storms."* — Nothing shown prevents
   storms; the controls bound and absorb them, and gap #1 currently amplifies
   them. Safer: **"Responsibility split contains alert storms."**
2. `WORK-WORKER-TO-MANAGEMENT-EVIDENCE-TRIAGE.html`, verdict chip:
   *"One agent call / 24h"* — Proven only for an identical dedupe key on red;
   pod churn breaks it today. Safer: **"Target: one agent call per incident
   fingerprint per 24 h (proven per-key on red)."**
3. `docs/observability/worker-to-management-evidence-triage.md`, heading:
   *"Why this is faster"* — Comparative speed is asserted, not measured, and
   the section itself pivots to the better objective. Safer heading: **"Why
   this needs no second lookup"**, with measured red-proof latencies added
   when available.
4. `observability/alloy-vector-kafka-triage/red/02-vector.yaml`, comment:
   *"Logs and Kubernetes events for the same pod become one incident."* — The
   implementation suppresses the second signal while the first is cached; it
   does not merge evidence, and the cache is a 1000-entry LRU. Safer: **"First
   signal for a key wins while cached; later signals are suppressed, not
   merged. Durable correlation happens at the management claim."**
5. `observability/alloy-vector-kafka-triage/red/README.md`: *"a replay may
   create a no-op workflow but cannot invoke the agent or create another
   GitLab ticket in that window."* — True for the proven in-window resend;
   "cannot" overstates given the expired-claim race and claim-then-fail path.
   Safer: **"will not invoke the agent or create another ticket in that
   window, provided the claim store is healthy; edge cases (claim failure,
   expiry races) are addressed in the fleet design."**
6. `docs/observability/worker-to-management-evidence-triage.md`, volume table:
   *"zero secret-pattern matches in sampled envelopes"* — Currently an
   acceptance measure with no scanner and a one-regex deny-list behind it.
   Keep the measure, but add: **"backed by a maintained redaction rule pack
   and an implemented sampling scanner"** so the claim cannot be read as
   already satisfied.

---

## Recommendation for the next author

**Create the office skill and work bundle after named small fixes — do not
create them from the current artifacts as-is, and do not wait for further
red-cluster proof.**

The red proof has done its job: the path, the read-only boundary, and the
happy-path replay suppression are facts. The design document is a strong
decision record. What blocks responsible replication is a short, concrete
list, all identified above and none architectural: fix the fingerprint
(gap #1), close the claim-then-fail lockout (gap #2), ship a real redaction
rule pack with a scanner (gap #4), add the quarantine default-route (gap #9),
and commit to the durable TTL store with the version-migration rule
(gaps #6/#8). Those five, plus the section 8 must-have artifacts, are the
bundle. Everything else — burst behaviour, broker drills, circuit breaker,
tenant-isolation proof — belongs in the section 7 acceptance gates and gates
the **second worker cluster**, not the bundle's creation.

Distinguish clearly in every bundle document between the proven red-cluster
fact (one cluster, one namespace, ConfigMap claim, plaintext in-cluster
transport) and the proposed fleet design (multi-tenant Kafka, durable store,
mTLS/ACLs). The current drafts mostly do this well; the reworded claims in
section 9 close the remaining gaps.

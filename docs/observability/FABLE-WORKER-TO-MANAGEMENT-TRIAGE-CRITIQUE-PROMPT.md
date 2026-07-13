# Fable critique prompt: worker-to-management evidence triage

## Purpose

Review the proposed worker-cluster Alloy/Vector to management-cluster Kafka,
Argo and kagent triage design before it becomes a work-office replication skill
or work bundle. Find concrete improvements, missing controls, unsafe
assumptions, operational gaps and unclear claims. This is a design critique
only: do not modify manifests, apply resources, contact GitLab, or use cluster
credentials.

The red-cluster proof has shown this path for one log and one Kubernetes
`BackOff` event:

```text
Alloy -> Vector -> Redpanda -> Argo EventSource/Sensor
      -> 24-hour claim -> read-only kagent agent -> GitLab work item
```

The next design moves collection and first-stage Vector processing to every
worker cluster, while the triage agent and ticket writer run in a management
cluster. Grafana/Loki remain optional mirrors and Alertmanager remains useful
for human-facing metric paging. The proposal is not to use Alertmanager as the
primary trigger for raw log/event agent triage.

## Read first

1. `docs/observability/worker-to-management-evidence-triage.md`
2. `WORK-WORKER-TO-MANAGEMENT-EVIDENCE-TRIAGE.html`
3. `observability/alloy-vector-kafka-triage/README.md`
4. `observability/alloy-vector-kafka-triage/red/README.md`
5. `observability/alloy-vector-kafka-triage/red/02-vector.yaml`
6. `observability/alloy-vector-kafka-triage/red/03-argo.yaml`
7. `observability/alloy-vector-kafka-triage/red/VERIFICATION-2026-07-13.md`
8. `work-agent-bundles/README.md`

## Review boundaries

- Treat the red proof as evidence for a single-cluster implementation only.
- Do not assume a particular office network, broker, identity provider, cloud
  service or retention policy. Identify what must be decided.
- Do not recommend direct agent mutation; triage stays read-only and
  remediation remains a separately approved workflow.
- Do not recommend removing Alertmanager wholesale. Evaluate the separation of
  its human paging role from evidence-first agent triage.
- Keep every suggested manifest, endpoint, secret and hostname public-safe.

## Questions to answer

1. Is worker-local Alloy + Vector with management-cluster triage the right
   boundary for resiliency, latency, security and operational ownership?
2. Does the proposed incident envelope contain enough evidence and provenance
   for first-pass triage without Grafana reverse lookup? What must be added or
   removed for data minimisation?
3. Is the log/event correlation key safe? Challenge the proposed fingerprint
   inputs, cross-pod incidents, rollouts, node-level failures, and repeated
   incidents after the 24-hour window.
4. Is Vector assigned only the work it should own? Identify which controls must
   be durable and central rather than in-memory/local.
5. Assess the Kafka design: topic/tenant isolation, cluster identity,
   authentication, ordering, retention, replay, DLQ/quarantine, network
   partitions, and backpressure.
6. Assess management processing: atomic idempotency, Argo retry semantics,
   agent concurrency, ticket idempotency, model/A2A failure, and auditability.
7. Is the Alertmanager distinction technically and operationally honest?
   Identify claims that overstate speed or imply that metrics alerts are no
   longer useful.
8. What operational signals, SLOs and game-day tests are required before
   onboarding a second worker cluster?
9. What is missing before this can responsibly become an office skill and a
   self-contained work bundle?

## Required feedback artifact

Create one public-safe repository document at:

```text
docs/observability/FABLE-WORKER-TO-MANAGEMENT-TRIAGE-FEEDBACK.md
```

Do not overwrite the design or critique prompt. The feedback document must not
contain office hostnames, cluster names, IP addresses, tokens, credentials or
copied sensitive evidence. It is the durable README-style review record for the
next person deciding whether to create the work bundle and skill.

Use this exact structure in that document:

1. **Executive verdict:** sound / sound with material gaps / redesign required.
2. **What is strong:** up to five specific design choices, with file evidence.
3. **Improvements and gaps:** ranked table with risk, failure mode, why it matters, and
   the smallest credible correction.
4. **Data and security review:** envelope, redaction, retention, tenancy,
   secrets and access boundaries.
5. **Reliability and scale review:** buffering, partitioning, ordering,
   duplicate/replay semantics, agent protection and failure recovery.
6. **Alertmanager review:** what it should retain responsibility for, and what
   should move to the evidence stream.
7. **Acceptance gates:** concrete tests/evidence required before a second
   worker cluster or office adoption.
8. **Bundle/skill readiness:** exact artefacts that should exist before we
   create them. Separate must-have from nice-to-have.
9. **Claims to reword:** quote the exact file/claim and provide safer wording.

Finish with a short **Recommendation for the next author** section: state
whether to create the office skill/work bundle now, after named small fixes, or
only after further proof. Do not produce implementation changes beyond the
feedback document. Be direct where assumptions are weak and distinguish a
proven red-cluster fact from a proposed fleet design.

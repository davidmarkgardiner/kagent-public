---
name: evidence-first-worker-triage
description: Replicate a guarded Alloy and Vector worker-cluster evidence path to Kafka and a management-cluster Argo/kagent triage workflow. Use when preparing, reviewing, rendering, or validating an evidence-first log and Kubernetes-event triage pilot that must avoid Alertmanager as the agent trigger, preserve read-only safety, and meet the Fable fleet-control gates.
---

# Evidence-First Worker Triage

Use this skill to implement and prove a **parallel, non-production**
worker-to-management triage pilot. Run both Alloy and a worker-local Vector
aggregation layer in each worker cluster; management owns the Kafka consumer,
durable decision, Argo, read-only agent and ticket writer:

```text
Alloy -> Vector -> Kafka -> management Argo -> read-only kagent -> GitLab
```

Do not use it to alter Alertmanager routes, replace Grafana/Loki, grant agent
mutation tools, or deploy to production.

## Start

1. Read `work-agent-bundles/evidence-first-worker-triage/FRONT-SHEET.md`.
2. Read `FABLE-FEEDBACK-RESPONSE.md` and `DESIRED-STATE.md` in that bundle.
3. Run the bundle verifier:

   ```bash
   bash work-agent-bundles/evidence-first-worker-triage/scripts/verify-bundle.sh
   ```

4. Inspect the live target before rendering. Alloy, Vector, Confluent Kafka
   and Argo may already be installed; discover and reuse their namespaces,
   credentials, CA references, topic, EventBus and service accounts rather
   than installing duplicates.
5. Create an approved values file from
   `work-agent-bundles/evidence-first-worker-triage/templates/pilot-values.env.example`;
   keep it outside Git.
6. Run the gate and renderer from the bundle:

   ```bash
   bash scripts/preflight-gates.sh --values /secure/pilot-values.env
   bash scripts/render-pilot-templates.sh --values /secure/pilot-values.env --out /tmp/evidence-first-pilot
   ```

The renderer only creates reviewable files. Review, customise, server-side dry
run and apply the resulting additive configuration as directed by the work
bundle's execution prompt.

## Required decisions

Stop and report `STATUS: BLOCKED_BY_CRITIQUE_CORRECTIONS` unless the values
file records all of the following:

- critique corrections accepted;
- approved durable TTL backend;
- approved worker-to-management identity model;
- approved evidence classification/retention reference;
- explicit non-production worker scope.

Use `references/fleet-control-gates.md` for the mandatory control and evidence
matrix. Treat the red overlay as a single-cluster proof reference, not as the
deployment template.

## Safe execution sequence

1. Validate scope, data classification, identity, network and topic ACLs.
2. Render templates to a non-repository directory, review every diff, then
   apply the approved additive configuration.
3. Prove worker collection is read-only and namespace-scoped.
4. Implement and prove redaction, fingerprinting, quarantine, management validation and
   durable claim **before** connecting the agent/ticket steps.
5. Prove one controlled log and one warning event through the complete path.
6. Run failure drills: claim failure, post-ticket-create retry, stale replay,
   consumer replay, burst, broker outage and unhealthy agent endpoint.
7. Create GitLab work items with safe evidence when authorised; otherwise
   create GitLab-ready issue files in the bundle evidence directory.
8. Complete the desired-state verdict and evidence index.

Do not call the result green if a workflow merely exists or if the happy-path
replay alone succeeds.

## Output contract

Return:

```text
STATUS: ready_for_review|blocked|pilot_complete
BLOCKERS: <none or exact owner/permission/control>
RENDER_DIR: <local uncommitted path>
DESIRED_STATE_VERDICT: green|amber|red
EVIDENCE_INDEX: <path>
ALERTMANAGER_CHANGED: no
REMEDIATION_ENABLED: no
OUTPUT_SANITIZED: yes
```

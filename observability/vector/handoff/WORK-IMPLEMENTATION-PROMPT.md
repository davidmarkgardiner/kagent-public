# Work Implementation Prompt: Vector Routing Rollout

You are implementing the Vector routing pattern in a private/work environment.
Do not copy public test values directly. Replace placeholders with approved
environment values and follow local change-control rules.

## Objective

Deploy and verify this event flow:

```text
Alertmanager / Grafana / Alloy
  -> raw Kafka topic
  -> Vector normalize / filter / route / dedupe
  -> normalized Kafka topic
  -> Argo EventSource
  -> Argo Sensor
  -> Argo Workflow
  -> selected agent or escalation path
```

The immediate goal is to prove that routing decisions can be made from message
content such as `namespace`, `service`, `pod`, `alert_name`, `reason`,
`severity`, `cluster`, and `environment`.

## Required Inputs

Before changing anything, identify:

- management cluster context
- cluster where Grafana/Alertmanager runs
- Kafka bootstrap endpoint
- raw topics currently used by Alertmanager, Grafana, and Alloy
- normalized topic names to create
- Kafka service account/API key strategy
- Argo namespace and EventBus
- existing Alertmanager/Grafana contact point configuration
- existing Argo WorkflowTemplate used for triage
- approved target agents and their invocation method

Do not print or commit real API keys, tokens, tenant IDs, subscription IDs,
private hostnames, or internal URLs.

## Public Repo Starting Point

Use these public files as implementation references:

- `observability/vector/README.md`
- `observability/vector/manifests/01-vector-alertmanager-normalizer.yaml`
- `observability/vector/manifests/02-argo-alertmanager-triage-topic.yaml`
- `observability/vector/manifests/03-argo-routing-verification.yaml`
- `observability/vector/examples/`
- `observability/vector/tests/`

## Implementation Steps

1. Recreate or verify the Kafka topics.

   Minimum topics:

   ```text
   alertmanager-events
   alertmanager-events-triage
   k8s-events
   ```

   Optional later topics:

   ```text
   alerts-platform-triage
   alerts-security-triage
   alerts-application-triage
   ```

2. Create or update Kafka credentials in Kubernetes Secrets.

   Required secret shape for the sample manifests:

   ```text
   namespace: argo-events
   secret: confluent-credentials
   keys:
     bootstrap
     key
     secret
   ```

3. Deploy Vector in the management cluster.

   Start with the normalized alert path:

   ```text
   alertmanager-events
     -> vector-alertmanager-normalizer
     -> alertmanager-events-triage
   ```

4. Deploy the normalized-topic Argo EventSource and Sensor.

   Start with a parallel Sensor so the current raw path can be compared before
   it is disabled.

5. Deploy the routing verification workflow.

   This should only process synthetic `routing_test: "true"` records and should
   not call GitLab, Teams, Mattermost, ServiceNow, or a real agent.

6. Run route tests.

   Verify at least:

   | Case | Expected target |
   |---|---|
   | app namespace + service | application or SRE triage agent |
   | platform namespace or control-plane pod event | platform ops agent |
   | security/compliance alert | security hardening agent |
   | missing service/owner | fallback SRE triage agent |

7. Update the production triage workflow contract.

   The production workflow should receive the full normalized envelope, not
   only `body.alertmanager`, so it can use:

   ```text
   target_agent
   route_key
   routing_reason
   automation_allowed
   incident_candidate
   dedupe_key
   namespace
   service
   pod
   ```

8. Disable or narrow the old raw-topic Sensor once the normalized path is
   accepted.

## Verification Commands

Adapt these to the private environment.

Run deterministic local tests:

```bash
observability/vector/tests/run-vector-example-tests.sh
```

Validate Kubernetes manifests:

```bash
kubectl apply --dry-run=server \
  -f observability/vector/manifests/01-vector-alertmanager-normalizer.yaml \
  -f observability/vector/manifests/02-argo-alertmanager-triage-topic.yaml \
  -f observability/vector/manifests/03-argo-routing-verification.yaml
```

Check rollout:

```bash
kubectl -n argo-events rollout status deploy/vector-alertmanager-normalizer
kubectl -n argo-events get sensor vector-routing-verification
kubectl -n argo-events get workflows -l event-type=route-verification
```

## Acceptance Criteria

The rollout is acceptable when:

- raw Kafka topics retain the original event for replay/audit
- Vector publishes normalized records with `schema_version:
  observability.triage.v1`
- routing fields are present and correct
- duplicate test records share the same `dedupe_key`
- route-verification workflows succeed for the required route cases
- the production workflow can consume the full normalized envelope
- write-capable automation is default-deny and only enabled by an explicit
  Argo-side allowlist tied to vetted runbooks
- Kafka principals are least-privilege: Vector reads raw and writes normalized;
  Argo reads normalized only
- old raw-topic triggering is disabled, narrowed, or explicitly documented as
  comparison/replay only
- dashboards or logs can show route counts and workflow outcomes
- no secret values or private endpoints are committed

## Evidence To Capture

Capture:

- topic list and partition/retention settings
- Vector rollout status
- Vector logs showing clean startup
- EventSource logs showing consumption from the normalized topic
- Sensor logs showing route-test trigger processing
- route-verification workflow names and parameters
- before/after workflow counts for duplicate/noisy events
- any failed route decisions and the corrected rule

## Stakeholder Value Measures

Track these over time:

- alerts received
- alerts suppressed by Vector
- workflows created
- workflows completed successfully
- workflows requiring human escalation
- ServiceNow incidents created by the system
- ServiceNow incidents avoided or auto-resolved before ticket creation
- MTTA from alert received to workflow started
- MTTR from alert received to workflow completed or escalated
- route distribution by `target_agent` and `route_key`

For deflection, prefer recording a normalized automation outcome with a
correlation ID. If the organization requires ServiceNow evidence, create a
low-noise record or task tagged as automation-deflected rather than opening a
normal incident for every resolved alert.

# Catent Alertmanager to Confluent Routing

This note answers the design question for the Catent/kagent alert workflow:
when Alertmanager sends webhooks into Vector, and Vector classifies,
deduplicates, enriches, and publishes Kafka records, do not create Kafka topics,
webhooks, or agent entrypoints per namespace. Keep the transport small and
stable, then route by normalized labels.

## Recommendation

Use topics by payload contract and operational priority, not by namespace.

For the Alertmanager-to-Vector-to-agent workflow, the recommended production
shape is:

| Topic | Required | Purpose |
|---|---:|---|
| `incident-triage-requests` | yes | Normalized, deduplicated work items from Vector ready for Argo/kagent routing. Use the existing `alertmanager-events-triage` name until the topic is renamed. |
| `incident-triage-results` | recommended | Agent verdicts, workflow status, human approval state, and audit trail. |
| `incident-triage-dlq` | recommended | Invalid, unroutable, or repeatedly failing records. |
| `alertmanager-events-raw` | optional | Raw Alertmanager webhook copies emitted by Vector only if replay/audit requires a raw Kafka topic. |

The existing Vector homelab path already publishes normalized records to
`alertmanager-events-triage`. Treat that as the current implementation of
`incident-triage-requests`. Keep `k8s-events` separate for Kubernetes-event
records. Do not make Alertmanager publish to Kafka first unless there is a
separate Kafka-first source path to preserve.

Short answer: with Alertmanager going directly to Vector, start with **one
required alert workflow topic** after Vector normalization. Make it **three
workflow topics** with results and DLQ when production auditability and failure
handling matter. Add a raw alert topic only when replay/audit requires it. Do
not make one topic per namespace.

## Why Not One Topic Per Namespace?

Namespace count changes frequently. If topics are created per namespace, every
new namespace becomes a Kafka ACL, retention, consumer-group, Terraform, and
runbook change. It also makes cross-namespace incidents harder because the
router has to merge many queues before it can understand the incident.

Namespace should be a field on the event:

```json
{
  "cluster": "{{CLUSTER_NAME}}",
  "namespace": "{{NAMESPACE}}",
  "service": "{{SERVICE_NAME}}",
  "severity": "critical",
  "platform_tier": "core",
  "target_agent": "platform-core-sre",
  "route_key": "{{CLUSTER_NAME}}:{{NAMESPACE}}:{{ALERT_NAME}}"
}
```

That lets Vector and Argo fan out to the right agent without changing Kafka
topology.

## Webhook Strategy

Use one Alertmanager webhook into Vector per environment or trust boundary, not
per namespace.

Good webhook boundaries:

- `prod` vs `nonprod`
- management cluster vs workload clusters
- regulated platform area vs general application area
- separate Confluent cluster/account where the security boundary requires it

Poor webhook boundaries:

- one webhook per namespace
- one webhook per application team
- one webhook per agent

Prometheus or Grafana alert rules should attach durable routing labels such as
`namespace`, `severity`, `owner_team`, `service`, and `platform_tier`.
Prometheus `external_labels` should attach fleet-wide context such as `cluster`,
`environment`, and `region` when that data is not already in the rule labels.
Alertmanager should route and group on those labels and send the webhook to
Vector. Vector should preserve the raw payload in the normalized record, derive
missing routing fields where it can do so safely, and emit a normalized triage
request to Kafka.

## Label Application

Labels should be applied at the earliest reliable source, then Vector should
make the routing contract explicit.

| Field | Preferred source | Vector behavior |
|---|---|---|
| `alertname` | Prometheus/Grafana alert rule | Copy to `alert_name`; default to `AlertmanagerAlert` only as a fallback. |
| `cluster` | Prometheus external label, Grafana label, or webhook environment | Copy through; do not invent a real cluster name. Use `unknown` if unavailable. |
| `environment` | Prometheus external label or alert rule label | Copy through; use for severity/incident classification when present. |
| `namespace` | Alert rule label from Kubernetes metric/log context | Copy through; use for platform/application/housekeeping routing. |
| `pod` / `service` | Alert rule labels | Copy through; use `service` for route and dedupe keys when stable. |
| `severity` | Alert rule label | Copy through; normalize to the agreed vocabulary such as `critical`, `warning`, `info`. |
| `owner_team` | Alert rule label or namespace inventory enrichment | Copy through if present; otherwise leave blank or `unknown`. |
| `platform_tier` | Namespace inventory, alert rule label, or Vector lookup table | Use to distinguish `core`, `critical`, `standard`, and `housekeeping`. |
| `route_domain` | Vector-derived | Set to values such as `platform`, `application`, `security`, or `fallback`. |
| `target_agent` | Vector-derived from namespace/tier/service rules | This is the actual agent routing decision. |
| `route_key` | Vector-derived | Build from route domain, environment, namespace, service, severity, and target agent. |
| `dedupe_key` | Vector-derived | Build from cluster, namespace, service, and alert name or fingerprint. |
| `queue_priority` | Vector-derived | Set to `p0`, `p1`, `p2`, or `p3` from severity, namespace class, environment, and service criticality. |
| `automation_allowed` | Vector default plus Argo allowlist | Default to `false`; only explicit policy should permit write-capable remediation. |

Alertmanager contributes `groupLabels`, `commonLabels`, and per-alert `labels`
in the webhook payload. Those labels should already exist before Alertmanager
receives the alert. Alertmanager can choose the receiver based on labels, but it
should not be treated as the primary enrichment engine.

## Routing Model

Route in this order:

1. **Ingest:** Alertmanager sends one webhook into Vector.
2. **Preserve:** Vector keeps the original Alertmanager payload under `raw` or
   `alertmanager` in the normalized record.
3. **Normalize:** Vector maps Alertmanager labels into
   `observability.triage.v1`.
4. **Deduplicate:** Vector computes a stable `dedupe_key` from cluster, namespace,
   alert name, and service.
5. **Classify:** Vector sets `platform_tier`, `severity`, `automation_allowed`, and
   `target_agent`.
6. **Publish:** Vector writes the normalized event to
   `incident-triage-requests` or the current `alertmanager-events-triage` topic.
7. **Fan out:** Argo/kagent invokes the specialist agent based on
   `target_agent`, not the Kafka topic.
8. **Record:** write workflow and agent results to `incident-triage-results`.
9. **Quarantine:** invalid or unroutable messages go to `incident-triage-dlq`.

## Backend Routing

Kafka does not give priority semantics inside one topic. If everything lands on
one normalized topic, priority has to be expressed in the payload and enforced
by the consumers. For Catent, that means Vector should write routing fields,
then Argo should split work by Sensor filters and WorkflowTemplates.

Use this normalized routing contract:

| Field | Example values | Purpose |
|---|---|---|
| `route_domain` | `platform`, `application`, `network`, `security`, `housekeeping`, `fallback` | Broad ownership lane. |
| `namespace_class` | `core`, `critical-app`, `standard-app`, `housekeeping` | Namespace importance independent of alert severity. |
| `queue_priority` | `p0`, `p1`, `p2`, `p3` | Backend queue order and rate-limit class. |
| `target_agent` | `platform-core-sre`, `app-critical-sre`, `app-standard-sre`, `housekeeping-sre` | Agent that should receive the context. |
| `workflow_class` | `critical-triage`, `standard-triage`, `housekeeping-triage`, `quarantine-review` | Argo workflow path. |
| `automation_allowed` | `false`, `true` | Whether the workflow may proceed beyond read-only analysis. |

The first routing decision belongs in Vector because Vector sees every inbound
alert before Kafka and already owns filtering, dedupe, normalization, and
classification. Argo should not rediscover whether `kube-system` is core or
whether `informer` is low priority; it should receive that decision as fields.

## Namespace Classes

Keep namespace classification in a small managed mapping, not hardcoded across
many Sensors.

| Namespace class | Examples | Default route |
|---|---|---|
| `core` | `kube-system`, `cert-manager`, `external-secrets`, `flux-system`, `istio-system`, `monitoring` | `platform-core-sre`, normally `p0`/`p1`. |
| `critical-app` | app namespaces labeled `platform_tier=critical` | `app-critical-sre`, normally `p0`/`p1`. |
| `standard-app` | normal product/team namespaces | `app-standard-sre`, normally `p2`. |
| `housekeeping` | low-risk batch, reporting, informer-style namespaces | `housekeeping-sre`, normally `p3` unless severity is genuinely critical. |

The namespace class should come from namespace labels or an inventory file that
Vector can load. Alert rules may provide `platform_tier`, but Vector should be
able to override unsafe or missing values from the authoritative namespace
inventory.

## Agent Routing Hierarchy

Use a small two-step routing decision:

1. **Symptom/domain override first** for cross-cutting platform failures.
2. **Namespace owner fallback second** for ordinary namespace-local incidents.

That keeps routing simple while avoiding a common failure mode: sending a DNS,
scheduling, provisioning, or networking incident to an application namespace
agent just because the alert happened to mention an app pod.

Recommended first-pass agent lanes:

| Route signal | Example symptoms | Primary agent | Fallback |
|---|---|---|---|
| DNS/network | CoreDNS errors, DNS latency, service discovery failure, ingress 5xx, endpoint missing, network policy deny, packet drop | `networking-triage-agent` | affected namespace agent |
| Scheduling/capacity | `FailedScheduling`, node pressure, taints/tolerations, quota, PDB blocking, cluster autoscaler/NAP issues | `platform-scheduling-agent` or `platform-core-sre` | affected namespace agent |
| Provisioning/GitOps | Flux failures, Helm release failure, KRO/ASO reconcile, namespace onboarding failure, cert workflow failure | `platform-provisioning-agent` | namespace agent |
| Security/policy | Kyverno/Gatekeeper deny, image vulnerability, admission failure, policy report | `security-hardening-agent` | affected namespace agent |
| Namespace-owned app | CrashLoopBackOff, app latency, app errors, deployment rollout in a non-platform namespace | namespace specialist or `app-standard-sre` | `sre-triage-agent` |
| Core namespace | `kube-system`, `cert-manager`, `external-secrets`, `flux-system`, `istio-system`, `monitoring` without a stronger symptom override | namespace/platform specialist | `platform-core-sre` |
| Unknown owner | missing namespace/service/team, malformed labels, unsupported event type | `sre-triage-agent` or quarantine workflow | human review |

This gives the workflow a clear ordering:

```text
if symptom_domain in [dns, network, ingress]:
  target_agent = networking-triage-agent
elif symptom_domain in [scheduling, capacity]:
  target_agent = platform-scheduling-agent
elif symptom_domain in [provisioning, gitops, aso, kro, flux]:
  target_agent = platform-provisioning-agent
elif symptom_domain in [security, policy, admission]:
  target_agent = security-hardening-agent
elif namespace has a registered namespace_agent:
  target_agent = namespace_agent
elif namespace_class == critical-app:
  target_agent = app-critical-sre
elif namespace_class == housekeeping:
  target_agent = housekeeping-sre
else:
  target_agent = sre-triage-agent
```

The symptom domain can be derived from alert labels, alert name, Kubernetes
event reason, log rule metadata, or a small Vector lookup table. The important
part is that Vector emits both the decision and the explanation:

```json
{
  "target_agent": "networking-triage-agent",
  "routing_reason": "event_reason=DNSLookupFailure overrides namespace=payments",
  "namespace_agent": "payments-agent",
  "route_domain": "network",
  "handoff_allowed": true
}
```

The namespace agent is still useful. The networking agent can triage DNS and
service-discovery evidence first, then hand off to `payments-agent` if the root
cause is application configuration. For the first implementation, keep that
handoff as a recommendation in the workflow output rather than automatic
multi-agent chaining.

## Agent Roster To Start With

Do not create a specialist for every possible error. Start with a small roster
that maps to real skills and ownership boundaries:

| Agent | Owns | Typical skills/tools |
|---|---|---|
| `platform-core-sre` | core namespaces, control-plane signals, platform service health | Kubernetes read tools, Grafana/Loki evidence, platform runbooks |
| `networking-triage-agent` | DNS, ingress, service discovery, network policy, packet drops | AKS networking guidance, CoreDNS checks, service/endpoints, ingress, CNI evidence |
| `platform-scheduling-agent` | failed scheduling, quota, node pressure, autoscaler/NAP, PDB constraints | scheduler events, node/pod capacity, quotas, cluster autoscaler/NAP runbooks |
| `platform-provisioning-agent` | Flux, Helm, KRO, ASO, namespace/cluster onboarding workflows | GitOps status, Argo workflow status, KRO/ASO status, Flux reconciliation |
| `security-hardening-agent` | policy/admission/security events | Kyverno/Gatekeeper/policy reports, image/advisory context, default-deny remediation |
| `app-critical-sre` | critical application namespaces without stronger symptom override | app logs, deployment history, service dependencies, owner runbooks |
| `app-standard-sre` | normal application namespaces | app logs, deployment status, common Kubernetes troubleshooting |
| `housekeeping-sre` | low-priority operational/batch/informer-style namespaces | lightweight triage, batching, noise review |
| `sre-triage-agent` | unknown owner, malformed labels, unsupported routes | broad read-only triage and human escalation |

As the system matures, namespace-specific agents can sit behind the app lanes.
The router does not need to know every skill detail; it needs to choose the best
first expert and preserve enough context for that expert to continue.

## Argo EventSource and Sensor Shape

Recommended first implementation:

1. One Kafka EventSource reads the normalized topic, such as
   `incident-triage-requests` or the current `alertmanager-events-triage`.
2. Multiple Sensors subscribe to that EventSource event and filter by
   `queue_priority`, `route_domain`, `namespace_class`, or `target_agent`.
3. Each Sensor creates a different WorkflowTemplate with different rate limits,
   approval gates, and agent prompts.
4. Filters must be mutually exclusive unless duplicate workflow creation is
   intentional.

Example lanes:

| Sensor | Filter | Workflow | Rate limit |
|---|---|---|---|
| `catent-p0-platform-critical` | `queue_priority in [p0,p1]` and `route_domain in [platform,security,network]` | `critical-platform-triage` | high, no batching. |
| `catent-p1-app-critical` | `queue_priority in [p0,p1]` and `namespace_class=critical-app` | `critical-app-triage` | medium/high. |
| `catent-p2-standard-app` | `queue_priority=p2` and `route_domain=application` | `standard-app-triage` | lower, backpressure allowed. |
| `catent-p3-housekeeping` | `namespace_class=housekeeping` or `queue_priority=p3` | `housekeeping-triage` | low, batch or scheduled review. |
| `catent-quarantine-review` | malformed, unknown owner, missing cluster/namespace, unsafe labels | `quarantine-review` | low, human review. |

Do not run several Kafka EventSources with the same consumer group and expect
each to see every message. Kafka consumers in the same group share partitions.
Use one EventSource and several Sensors for normal fan-out. Use separate
EventSources only when there is a hard isolation reason, and give each its own
consumer group if it must receive a full copy of the stream.

Concrete reference YAML for this pattern is in
[`catent-argo-sensor-routing-examples.yaml`](catent-argo-sensor-routing-examples.yaml).
It is an example contract, not a manifest that has been server-side dry-run
against the target work cluster.

## Verification Status

The repo has verified the underlying pieces, but not the exact multi-lane Sensor
set above as a production deployment.

Verified in the existing Vector bundle:

- A normalized Kafka topic can be consumed by an Argo Kafka EventSource.
- A Sensor can filter normalized records and create a Workflow.
- A direct Alertmanager webhook can enter Vector, publish
  `alertmanager-events-triage`, and trigger `alert-triage-vector-*`.
- A synthetic route-verification Sensor can pass normalized fields including
  `target_agent`, `route_key`, `routing_reason`, `severity`, and `dedupe_key`
  into a WorkflowTemplate.

Not yet verified as a complete production path:

- Multiple lane Sensors with mutually exclusive filters for `p0`, `p1`, `p2`,
  and `p3`.
- WorkflowTemplates named `critical-platform-triage`,
  `critical-app-triage`, `standard-app-triage`, and `housekeeping-triage`.
- The production triage workflow consuming the full normalized envelope instead
  of only the nested Alertmanager payload.
- Priority starvation behavior under load.

So the answer is: **yes, Sensor filtering has been verified in action for the
single normalized Sensor and route-verification Sensor; the exact multi-lane
backend routing pattern is the next manifest to test, not something already
proven end to end.**

## When To Split The Topic

One normalized topic plus multiple Sensors is the right starting point. Split
topics only when the platform needs a real operational boundary:

- P0 traffic is delayed by standard or housekeeping volume.
- Separate teams must own different consumers and ACLs.
- Retention differs by lane.
- A route has a separate compliance or security boundary.
- Kafka partitioning cannot keep up with peak volume.

The first split should be by priority or route domain, not namespace:

```text
incident-triage-critical
incident-triage-standard
incident-triage-housekeeping
```

or:

```text
incident-triage-platform
incident-triage-application
incident-triage-security
```

Until one of those conditions is true, keep the single normalized topic and make
the Argo Sensors do the backend organization.

## Agent Split

Use different agents, but do not expose each agent as a different Kafka queue.
The router should select agents from metadata.

Recommended first pass:

| Route | Example namespaces | Agent |
|---|---|---|
| Core platform | `kube-system`, `cert-manager`, `external-secrets`, `flux-system`, `istio-system`, `monitoring` | `platform-core-sre` |
| Application critical | namespaces labeled `platform_tier=critical` | `app-critical-sre` |
| Application standard | normal team namespaces | `app-standard-sre` |
| Housekeeping | backup, cleanup, reporting, low-risk batch namespaces | `housekeeping-sre` |
| Network/security | ingress, mesh, policy, identity, DNS symptoms | `network-security-sre` |

This keeps the operational split where it belongs: in agent capability and
permission boundaries. Read-only agents can inspect broadly. Write-capable
remediation should stay behind Argo Workflow service accounts and human approval
gates.

## Metrics, Logs, Kubernetes Events, and Community Events

Do not stream all metrics or logs into the agent workflow. Let Prometheus,
Mimir, Loki, and Grafana keep the high-volume telemetry. Kafka records should
carry the alert, labels, links, and evidence pointers the agent needs.

Use separate raw topics only when the payload contract is different:

| Signal | Suggested handling |
|---|---|
| Alertmanager alerts | Alertmanager webhook directly into Vector, then normalized Kafka record to `incident-triage-requests` / `alertmanager-events-triage`. |
| Kubernetes events | Keep separate as `k8s-events` when they are raw Kubernetes-event-shaped records, or route them through Vector if they need the same `observability.triage.v1` contract. |
| Metrics | Alertmanager should emit alert state and labels; do not publish raw metric streams to the agent path. |
| Logs | Keep in Loki; include log query links or selectors in the normalized request. |
| Community/user events | Use a separate raw source topic only if the payload is not Alertmanager-shaped, then normalize into `incident-triage-requests`. |

## Partitioning and Consumer Groups

Use a partition key that keeps related incident records ordered:

```text
{{CLUSTER_NAME}}:{{NAMESPACE}}:{{SERVICE_NAME}}:{{ALERT_NAME}}
```

Use consumer groups by processing stage, not by namespace:

| Consumer group | Reads | Responsibility |
|---|---|---|
| `catent-triage-router` | `incident-triage-requests` / `alertmanager-events-triage` | Create Argo workflows or invoke the kagent front door. |
| `catent-results-indexer` | `incident-triage-results` | Persist status, dashboards, reports, or GitLab/Teams summaries. |

## Minimal Decision

For the current Catent workflow, use this:

```text
Alertmanager webhook -> Vector HTTP receiver -> normalized Kafka topic

incident-triage-requests  normalized agent work items
                           current equivalent: alertmanager-events-triage
incident-triage-results   recommended audit/status stream
incident-triage-dlq       recommended failure quarantine
alertmanager-events-raw   optional raw replay/audit stream from Vector
```

Keep `k8s-events` as a separate existing source topic. Add source-specific raw
topics later only when a source has a genuinely different payload contract or
security boundary.

See the rendered diagram in
[`catent-alertmanager-confluent-routing.svg`](catent-alertmanager-confluent-routing.svg)
and the Mermaid source in
[`catent-alertmanager-confluent-routing.mmd`](catent-alertmanager-confluent-routing.mmd).

For the label-to-Argo routing view, see
[`catent-label-routing-argo.svg`](catent-label-routing-argo.svg)
and the Mermaid source in
[`catent-label-routing-argo.mmd`](catent-label-routing-argo.mmd).

For the high-level agent selection hierarchy, see
[`catent-agent-routing-hierarchy.svg`](catent-agent-routing-hierarchy.svg)
and the Mermaid source in
[`catent-agent-routing-hierarchy.mmd`](catent-agent-routing-hierarchy.mmd).

For a more readable visual board, open
[`catent-routing-architecture.html`](catent-routing-architecture.html).

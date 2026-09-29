# Onboard {{TEAM_NAME}} to shared Confluent Kafka

## Request summary

**Owning team / contact:** {{TEAM_NAME}} / {{TEAM_CONTACT}}
**Business problem and expected outcome:** {{PROBLEM_AND_OUTCOME}}
**Environment:** {{ENVIRONMENT}}
**Requested go-live date:** {{DATE}}
**Platform/Kafka owner:** {{PLATFORM_OWNER}}

We request a separate Kafka topic and consumer group on the approved shared Confluent cluster. The topic is the data and access boundary; the group is this application's independent offset and work-sharing boundary. This request does not give the team access to the kagent triage topic or its credentials.

## Producer and topic form — requester completes

| Field | Answer |
| --- | --- |
| Proposed topic name, following platform naming rules | `{{TEAM_TOPIC}}` |
| Producer application and owning workload identity | {{PRODUCER_APP_AND_IDENTITY}} |
| Will the team produce, consume, or both? | {{PRODUCE_CONSUME_BOTH}} |
| Producer tool under consideration | {{VECTOR_CLIENT_SDK_CONNECTOR_OTHER}} |
| Event type and reason for publishing | {{EVENT_DESCRIPTION}} |
| Sample synthetic record / schema version | {{SANITIZED_SAMPLE_AND_SCHEMA_VERSION}} |
| Message key / ordering requirement | {{KEY_AND_ORDERING}} |
| Serialization / Schema Registry requirement | {{JSON_AVRO_PROTOBUF_AND_COMPATIBILITY}} |
| Classification and redaction rules | {{DATA_CLASSIFICATION_AND_REDACTION}} |
| Estimated peak records/sec and max record size | {{RATE_AND_SIZE}} |
| Requested retention, partitions and replay need | {{RETENTION_PARTITIONS_REPLAY}} |
| Runtime location and network path | {{WORKLOAD_LOCATION}} |

## Consumer-group form — requester completes

| Field | Answer |
| --- | --- |
| Proposed stable consumer-group name | `{{TEAM_CONSUMER_GROUP}}` |
| Consumer application and owning workload identity | {{CONSUMER_APP_AND_IDENTITY}} |
| Exact topic(s) to subscribe to | `{{TEAM_TOPIC}}` |
| Consumer tool under consideration | {{ARGO_EVENTS_VECTOR_CLIENT_SDK_CONNECTOR_FLINK_OTHER}} |
| What will happen to each record? | {{CONSUMER_OUTCOME}} |
| Initial position for a new group | {{LATEST_OR_APPROVED_BOUNDED_REPLAY}} |
| Replicas / expected processing delay | {{REPLICAS_AND_LATENCY}} |
| Retry, invalid-record and dead-letter behavior | {{ERROR_HANDLING}} |
| Idempotency / duplicate side-effect key | {{EVENT_ID_AND_IDEMPOTENCY_PLAN}} |
| Lag monitoring and on-call owner | {{LAG_OWNER}} |

**Integration decision:** The requesting team owns the producer and consumer implementation. Please describe why the chosen tools fit the problem. Examples include Vector for telemetry publishing, an application Kafka client for business events, a managed source/sink connector for supported systems, Argo Events for Kubernetes workflow triggers, and Flink/Kafka Streams for stream transformation. The platform team supplies the Kafka boundary, not the business logic.

## Platform owner / form submission checklist

- [ ] Confirm cluster, naming strategy, topic strategy, retention, partitions and schema settings in the workplace portal.
- [ ] Confirm whether the portal's identity-pool field maps to the requesting workload identity and which service account owns each API key.
- [ ] Create/approve topic `{{TEAM_TOPIC}}`; do not add a new group to the existing triage topic by default.
- [ ] Grant producer principal `{{TEAM_PRODUCER_PRINCIPAL}}` write access to this topic only, if producing.
- [ ] Grant consumer principal `{{TEAM_CONSUMER_PRINCIPAL}}` read access to this topic and read access to group `{{TEAM_CONSUMER_GROUP}}`, if consuming.
- [ ] Confirm approved network reachability, TLS and authentication mechanism.
- [ ] Deliver endpoint `{{KAFKA_BOOTSTRAP_ENDPOINT}}`, schema details and scoped credential(s) through the approved secret channel. **Do not paste API keys or secrets into this ticket.**
- [ ] Agree a temporary smoke-test group/topic or approved test marker and its cleanup.
- [ ] Record support contact, rotation ownership and lag/quotas/retention expectations.

## Acceptance evidence

- [ ] The topic exists with agreed configuration; ACL/RBAC review shows only the requested producer/consumer scope.
- [ ] A synthetic marker with `test_id={{UNIQUE_TEST_ID}}` is acknowledged by an authorized producer; topic, partition and offset are recorded.
- [ ] An authorized consumer in `{{TEAM_SMOKE_GROUP}}` receives the matching marker; the production group is untouched during this smoke test.
- [ ] The team's chosen integration processes one marker as intended; duplicate/replay behavior is checked before production use.
- [ ] Producer errors, consumer lag, schema failures and the dead-letter/error path have a named owner.
- [ ] Redacted result and date are attached here; credentials remain in the secret system.

## Optional smoke commands

Run only after the platform owner has approved the test topic/group and the Confluent CLI is configured with the approved profile and scoped credentials. Do not pass secrets as CLI arguments or put them in this ticket. The plain JSON marker is suitable only if the topic contract permits it; otherwise use the approved schema-aware test producer.

```bash
# Terminal A: start an authorized, temporary consumer group first
confluent kafka topic consume {{TEAM_TOPIC}} --group {{TEAM_SMOKE_GROUP}}

# Terminal B: interactively send one synthetic marker, then Ctrl-D
confluent kafka topic produce {{TEAM_TOPIC}}
# At the input prompt enter:
# {"schema_version":"{{SCHEMA_VERSION}}","test_id":"{{UNIQUE_TEST_ID}}","kind":"onboarding-smoke"}
```

**Result:** {{PASS_FAIL_AND_REDACTED_EVIDENCE_LINK}}
**Open items:** {{OPEN_ITEMS}}

## References

- Local guide: `docs/observability/confluent-team-onboarding-guide.html`
- Existing workplace interpretation: `docs/observability/work-confluent-onboarding-guide.md`
- Confluent ACL examples: https://docs.confluent.io/cloud/current/security/access-control/acls/examples.html
- Confluent consumer-group behavior: https://docs.confluent.io/cloud/current/client-apps/consumer.html
- Argo Events Kafka EventSource: https://argoproj.github.io/argo-events/eventsources/setup/kafka/

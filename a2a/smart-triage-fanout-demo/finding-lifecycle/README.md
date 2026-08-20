# Smart-triage finding lifecycle POC

This management-plane service replaces the demo's create-once ConfigMap dedupe
with typed, durable incident state. It does not read or change incident
workloads and does not create GitLab issues itself.

## Contract and decisions

`finding.schema.json` defines the public input contract. A canonical identity
is derived outside the model from:

```text
subscription scope / cluster / namespace / stable workload / domain / reason
```

The upstream Alertmanager fingerprint, model-written title and literal pod name
are deliberately excluded. A finding without a proven stable workload is
`PROVISIONAL`: it remains visible to humans but is not stored as a canonical
incident and cannot automatically create a durable ticket.

The API returns `NEW`, `ONGOING`, `ESCALATED`, `ACKNOWLEDGED`, `RESOLVED`,
`RECURRENT`, `PROVISIONAL`, `STALE` or `RESOLUTION_UNKNOWN`. An idempotent replay
of the same run does not notify twice. A complete snapshot can resolve findings
that are absent only inside its explicitly declared target/domain coverage.

## API

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Prove the SQLite/PVC backend is available and durable |
| `GET /v1/findings` | Return bounded lifecycle metadata; no raw logs or credentials |
| `POST /v1/findings/evaluate` | Validate and classify one firing/resolved finding |
| `POST /v1/findings/acknowledge` | Record an actor and acknowledgement expiry |
| `POST /v1/findings/link-issue` | Attach the HTTPS canonical issue reference after the ticket workflow creates it |
| `POST /v1/reports/evaluate` | Evaluate a complete bounded snapshot and resolve absent findings |

Requests larger than 256 KiB are rejected. Evidence, tools and recommended
actions have schema limits, and credential-like strings are rejected before
state is written.

See [HOMELAB-EVIDENCE-2026-08-20.md](HOMELAB-EVIDENCE-2026-08-20.md) for the
validated lifecycle transitions, Argo Events/Workflows run, PVC restart proof,
failure boundary and the integration defect found during the live test.

## Failure boundary

The service uses a one-replica Deployment and PVC-backed SQLite database in the
Argo Workflows namespace. This is deliberately small for the POC. It is not a
multi-replica production database.

The calling WorkflowTemplate treats timeout, connection failure and non-200
responses as `STATE_UNAVAILABLE`. It continues the existing human alert and
investigation path, but sets `AUTO_TICKET_ALLOWED: false` and makes no durable
dedupe claim. It never silently falls back to in-memory state.

## Validate

```bash
python3 -m unittest discover \
  -s a2a/smart-triage-fanout-demo/finding-lifecycle/tests -v
kubectl kustomize a2a/smart-triage-fanout-demo/finding-lifecycle
kubectl apply --dry-run=server \
  -k a2a/smart-triage-fanout-demo/finding-lifecycle
```

`jsonschema` is required only by the offline schema test. The deployed service
uses Python's standard library and enforces the same public contract without
downloading packages at startup.

## Homelab

Use the explicit homelab context; do not rely on the current kubectl context:

```bash
kubectl --context {{HOMELAB_CONTEXT}} apply \
  -k a2a/smart-triage-fanout-demo/finding-lifecycle
kubectl --context {{HOMELAB_CONTEXT}} rollout status \
  -n argo deployment/smart-triage-finding-lifecycle
```

Homelab evidence must include the API response for every claimed transition,
the state observed after a pod replacement, the Argo Workflow normalize log,
and the `STATE_UNAVAILABLE` negative case. Rendering or rollout success alone
is not acceptance.

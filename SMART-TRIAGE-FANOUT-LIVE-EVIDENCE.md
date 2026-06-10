# Smart Triage Fan-Out Live Evidence

Capture date: 2026-06-01
Scope: Alertmanager-triggered smart-triage fan-out PoC with all integration spikes
Cluster: approved non-production demo cluster, name redacted
Namespace: `argo`

This file is the durable evidence snapshot for the PR. It records Alertmanager
ingestion, duplicate suppression, the expanded eight-specialist fan-out, HITL
resume, final proof markers, and lifecycle eval.

Evidence boundary: the workflow execution, node table, Argo resume, duplicate
suppression, and lifecycle eval are live demo evidence. Some specialist outputs
inside the public demo are synthetic spike contracts. In particular, knowledge
citations and the no-docs fallback markers prove the marker contract, not a live
doc2vec/querydoc retrieval against an indexed KB.

## Full All-Spikes Workflow Proof

Alert replay:

```bash
ALERT_FINGERPRINT=smart-triage-alert-replay-all-spikes-20260601 \
ALERT_STARTS_AT=2026-06-01T18:30:00Z \
  a2a/smart-triage-fanout-demo/scripts/replay-alert.sh
```

Replay output:

```text
ALERT_REPLAYED: yes
ALERT_SOURCE: alertmanager
FINGERPRINT: smart-triage-alert-replay-all-spikes-20260601
```

Workflow:

```text
workflow: smart-triage-alert-b8gkz
namespace: argo
status: Succeeded
progress: 14/14
duration: 4 minutes 58 seconds
```

Node table:

```text
normalize-incident       1m   ALERT_DUPLICATE: no
fanout-gitops            17s  SPECIALIST_GITOPS: completed
fanout-grafana           27s  SPECIALIST_GRAFANA: completed
fanout-knowledge         49s  SPECIALIST_KNOWLEDGE: completed
fanout-network           40s  SPECIALIST_NETWORK: completed
fanout-kubernetes        26s  SPECIALIST_KUBERNETES: completed
fanout-deployment        37s  SPECIALIST_DEPLOYMENT: completed
fanout-trace             31s  SPECIALIST_TRACE: completed
fanout-policy            38s  SPECIALIST_POLICY: completed
synthesize-incident      17s  INCIDENT_SYNTHESIS: completed
wait-for-human-review         Resumed by: map[User:kubernetes-admin]
finalize-approved        4s
prove-result             5s
evaluate-lifecycle       6s   score=1.0 passed=true
```

Proof markers from `prove-result`:

```text
SMART_TRIAGE_FANOUT: started
SPECIALIST_KUBERNETES: completed
SPECIALIST_NETWORK: completed
SPECIALIST_GRAFANA: completed
SPECIALIST_GITOPS: completed
SPECIALIST_KNOWLEDGE: completed
SPECIALIST_DEPLOYMENT: completed
SPECIALIST_POLICY: completed
SPECIALIST_TRACE: completed
CITATIONS: docs/platform-kb/runbooks/checkout-api-crashloop.md#chunk-1
KNOWLEDGE_NO_RELEVANT_DOCS_CASE: validated
DEPLOYMENT_VERDICT: bad_deploy
POLICY_REMEDIATION_SAFETY: blocked
TRACE_FALLBACK: NO_TRACE
INCIDENT_SYNTHESIS: completed
HITL_REQUIRED: yes
HITL_STATUS: resumed
KB_UPDATE_MR: dry_run_after_hitl
REMEDIATION_MODE: gitops_or_workflow_only
OUTPUT_SANITIZED: yes
SMART_TRIAGE_PATTERN: proven
```

Lifecycle eval:

```text
wrote /work/output/lifecycle-run.json
score=1.0 passed=true json=/work/output/pod-crashloop-hitl-remediation.smart-triage-alert-b8gkz.json
```

Verification commands while the workflow is retained:

```bash
argo get -n argo smart-triage-alert-b8gkz
kubectl logs -n argo pod/smart-triage-alert-b8gkz-prove-result-617723633 -c main
kubectl logs -n argo pod/smart-triage-alert-b8gkz-evaluate-lifecycle-283900295 -c main
a2a/smart-triage-fanout-demo/scripts/prove-knowledge-citation.sh smart-triage-alert-b8gkz
a2a/smart-triage-fanout-demo/scripts/prove-deployment-readonly.sh smart-triage-alert-b8gkz
a2a/smart-triage-fanout-demo/scripts/prove-policy-summary.sh smart-triage-alert-b8gkz
a2a/smart-triage-fanout-demo/scripts/prove-trace-link.sh smart-triage-alert-b8gkz
```

## Per-Spike Evidence

Spike 1, alert ingestion:

```text
ALERT_INGESTED: yes
ALERT_SOURCE: alertmanager
INCIDENT_NORMALIZED: yes
ALERT_DUPLICATE: no
FINGERPRINT: smart-triage-alert-replay-all-spikes-20260601
```

Spike 8, knowledge/runbook retrieval:

```text
SPECIALIST_KNOWLEDGE: completed
EVIDENCE_SOURCE: synthetic-platform-kb
CITATIONS: docs/platform-kb/runbooks/checkout-api-crashloop.md#chunk-1
ANSWER_GROUNDED: yes
NO_RELEVANT_DOCS_CASE: validated
KB_UPDATE_MR: dry_run_after_hitl
```

The citation and `NO_RELEVANT_DOCS_CASE` markers above are synthetic public-demo
markers. Before claiming live KB retrieval in a work environment, run one real
querydoc cited-hit query and one out-of-corpus fallback query.

Spike 5, deployment state:

```text
SPECIALIST_DEPLOYMENT: completed
EVIDENCE_SOURCE: synthetic-flux
APP_RESOLVED: checkout-api
DESIRED_REVISION: demo-rev-42
LIVE_REVISION: demo-rev-42
DRIFT: no
HEALTH: degraded
VERDICT: bad_deploy
CURRENT_STATE_VERIFIED: yes
```

Spike 6, policy/security context:

```text
SPECIALIST_POLICY: completed
EVIDENCE_SOURCE: synthetic-kyverno
POLICY_REPORTS_READ: yes
BLOCKERS: require-reviewed-remediation
WARNINGS: image-tag-not-pinned
VULN_FINDINGS: critical=0 high=1 medium=2
REMEDIATION_SAFETY: blocked
CURRENT_STATE_VERIFIED: yes
```

Spike 4, trace context:

```text
SPECIALIST_TRACE: completed
EVIDENCE_SOURCE: synthetic-tempo-contract
TRACE_ID: NONE
TRACE_QUERY: service=checkout-api namespace=demo-payments window=2026-06-01T17:03:30Z..2026-06-01T17:13:30Z
TRACE_URL: none
FALLBACK: NO_TRACE
CURRENT_STATE_VERIFIED: yes
```

Trace note: this public repo does not include a live application Tempo or Jaeger
backend. The live run proves the workflow contract, evidence marker, and
`NO_TRACE` fallback path. Work lift-and-shift must replace the synthetic trace
contract with the approved tracing backend.

## Duplicate Suppression Proof

The same Alertmanager payload was replayed a second time with fingerprint
`smart-triage-alert-replay-checkout-api`. It created a small workflow and
stopped before specialist fan-out.

```text
workflow: smart-triage-alert-k4m2p
namespace: argo
status: Succeeded
progress: 2/2
duration: 20 seconds
```

Suppression markers:

```text
ALERT_INGESTED: yes
ALERT_SOURCE: alertmanager
INCIDENT_NORMALIZED: yes
ALERT_DUPLICATE: yes
FINGERPRINT: smart-triage-alert-replay-checkout-api
DUPLICATE_SUPPRESSED: yes
SMART_TRIAGE_DEDUP: suppressed
FANOUT_SKIPPED: duplicate_alert
REMEDIATION_MODE: gitops_or_workflow_only
```

## Validation Notes

- `kubectl apply --dry-run=server` passed for the Agent, WorkflowTemplate, RBAC,
  EventSource, and Sensor manifests.
- `kubectl create --dry-run=client` passed for the manual Workflow manifest.
- The Kyverno guardrail proposal renders through `kubectl kustomize`; this demo
  cluster does not have the Kyverno `ClusterPolicy` CRD installed, so
  server-side policy dry-run is intentionally not claimed.
- Read-only specialists have no `toolNames` entries containing mutating verbs.
- The Agent and EventSource manifests include a clearly marked lab-only
  control-plane toleration for saturated non-production clusters. Work
  environments should replace it with normal scheduling policy.

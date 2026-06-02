# A2A Demo Execution Review

Review date: 2026-06-01
Scope: `a2a/platform-memory-showcase-demo/`

## Summary

The platform-memory A2A demo is packaged as a copyable, public-safe showcase for
shared `memory-mcp` recall, A2A `contextId` continuity, and an Argo
suspend/resume human-review gate.

The current implementation is ready for PR review as a controlled demo package.
Client-side validation passes for the manifests and runner script. Live
execution also passed on an approved non-production demo cluster after
restoring the missing `memory-mcp` prerequisite and restarting the stale qwen
model pod. The live cluster name is redacted from this public review.

## Demo Requirements Checked

| Requirement | Current evidence | Review status |
|---|---|---|
| Seed synthetic incident into shared memory | `demo-memory-seeder-agent` used `memory-mcp` write tools and returned `MEMORY_WRITE: stored` | Live validated |
| Cross-agent recall through shared memory | `demo-memory-triage-agent` used read-only `memory-mcp` tools and returned `MEMORY_LOOKUP: hit` | Live validated |
| Preserve A2A continuity across HITL | Workflow captured `triage-before-approval` `context_id` and passed it to `triage-after-approval` | Live validated |
| Prove context reuse | `prove-result` compared before/after context IDs and emitted `A2A_CONTEXT_REUSED: yes` | Live validated |
| Human review gate | Workflow suspended at `wait-for-human-review` and was resumed by `kubernetes-admin` | Live validated |
| Public-safe / copy-replace package | Scenario uses synthetic namespace, deployment, fingerprint, and placeholder guidance | Review acceptable |
| One-command execution path | `scripts/run-demo.sh` checks prerequisites, applies agents/RBAC, submits, waits, resumes, and verifies success | Live validated |

## Validation Performed

```bash
bash -n a2a/platform-memory-showcase-demo/scripts/run-demo.sh
```

Result: passed.

```bash
kubectl apply --dry-run=client -f a2a/platform-memory-showcase-demo/agents.yaml
```

Result: passed for both kagent `Agent` resources.

```bash
kubectl apply --dry-run=client -f a2a/platform-memory-showcase-demo/workflow-rbac.yaml
```

Result: passed for ServiceAccount, Role, and RoleBinding.

```bash
kubectl create --dry-run=client -f a2a/platform-memory-showcase-demo/workflow.yaml
```

Result: passed. This uses `create`, not `apply`, because the workflow uses
`metadata.generateName`.

```bash
rg -n "(subscriptionId|tenantId|clientId|password|token|secret|https?://[^\\{\\s\\)]+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})" \
  A2A-DEMO-EXECUTION-REVIEW.md A2A-WORK-IMPLEMENTATION-PLAN.md \
  a2a/platform-memory-showcase-demo a2a/README.md DEMOS.md docs/kagent-memory/platform-memory/README.md
```

Result: no secrets or private identifiers found. Hits were public upstream
links, documentation warnings about secrets/tokens, and in-cluster demo service
URLs.

## Live Execution

Command executed:

```bash
KUBE_CONTEXT={{KUBE_CONTEXT}} MODEL_CONFIG=default-model-config \
  a2a/platform-memory-showcase-demo/scripts/run-demo.sh
```

Result:

```text
PASS: platform memory showcase workflow succeeded
Workflow: demo-platform-memory-jp2ql
Namespace: argo
Status: Succeeded
Progress: 5/5
Started: 2026-06-01T08:28:13Z
Finished: 2026-06-01T08:31:49Z
Duration: 3 minutes 36 seconds
```

Workflow node evidence:

```text
seed-known-incident     Succeeded
triage-before-approval  Succeeded
wait-for-human-review   Succeeded  Resumed by: map[User:kubernetes-admin]
triage-after-approval   Succeeded
prove-result            Succeeded
```

Proof markers observed in workflow pod logs:

- `MEMORY_WRITE: stored`
- `MEMORY_LOOKUP: hit`
- `A2A_CONTEXT_REUSED: yes`
- `HITL_STATUS: resumed`
- `WORKFLOW_MEMORY_PATTERN: proven`

Before- and after-approval triage used the same A2A context ID. The exact live
UUID is redacted from this public review; the workflow proof step compared the
real values and emitted `A2A_CONTEXT_REUSED: yes`.

```text
A2A context: {{A2A_CONTEXT_ID}}
```

## Runtime Notes

Prerequisite checks and fixes from the live run:

- `kagent` and `argo` namespaces existed.
- `agents.kagent.dev`, `modelconfigs.kagent.dev`,
  `remotemcpservers.kagent.dev`, and `workflows.argoproj.io` CRDs existed.
- `default-model-config` existed and was accepted.
- `RemoteMCPServer/memory-mcp` was initially missing, so the documented
  `mcp-memory-server` Helm chart was installed in `kagent`.
- The repo values use `storage.storageClassName: standard`. The homelab demo
  cluster does not have that StorageClass, so the live run used the
  homelab-only override `--set storage.storageClassName={{STORAGE_CLASS}}`.
- `RemoteMCPServer/memory-mcp` reconciled to `Accepted=True` and discovered
  `create_entities`, `create_relations`, `add_observations`, `read_graph`,
  `search_nodes`, and `open_nodes`.
- The first workflow attempt, `demo-platform-memory-lm86s`, failed at
  `seed-known-incident` with `curl: (28) Operation timed out after 180001
  milliseconds with 0 bytes received`.
- Root cause of the first attempt was the model backend: the kubeai
  `qwen3-14b` model pod was stale with `Ready: 0` after an earlier unhealthy
  GPU allocation. Deleting the stale model pod caused kubeai to recreate it;
  the replacement pod detected the GPU, loaded the model, and became Ready.
- The second workflow attempt, `demo-platform-memory-jp2ql`, succeeded.

## PR Notes

- The demo is intentionally recommendation-only. It does not create, update, or
  delete workload resources.
- The triage agent has read-only memory tools; only the seeder agent has memory
  write tools for this controlled demo.
- The workflow service account only receives Argo `workflowtaskresults`
  permissions required by workflow execution.
- The synthetic memory records were written to the live `memory-mcp` service
  and should be deleted or archived through the environment's memory retention
  process after the demo.
- Top-level docs now link the demo from `a2a/README.md` and the platform memory
  guide so reviewers can find the entry point.

## Self-Review Evidence Checklist

- [x] The demo scope is clear: shared memory lookup, A2A continuity, and Argo
  HITL only.
- [x] No secrets, private hostnames, subscription IDs, tenant IDs, or internal
  URLs are present.
- [x] The RBAC split is visible: agents handle chat/tool reasoning; the Argo
  workflow service account only receives workflow execution permissions.
- [x] The `memory-mcp` write path is limited to the controlled demo seeder
  agent; the triage agent is read-only.
- [x] The live evidence proves the intended behavior and does not rely only on
  client-side dry-run checks.
- [x] The runtime notes are explicit enough for another engineer to reproduce
  or troubleshoot the run.

## Reviewer Confirmation Checklist

- [ ] The synthetic memory records have an agreed retention or cleanup process.
- [ ] The homelab-only storage-class override is acceptable as runtime evidence
  and should not be copied into work manifests without replacement.
- [ ] The demo should remain recommendation-only and not grow cluster mutation
  permissions.
- [ ] The linked work implementation plan keeps production memory writes behind
  a curator workflow rather than letting general triage agents write directly.

## Reviewer Questions

1. Should the production version use the existing `memory-mcp` graph, or should
   the team introduce a hardened successor with database-backed writes before
   wider rollout?
2. Which alert fingerprint fields should be mandatory for memory lookup:
   source system, namespace, reason, involved kind, involved name, normalized
   message, or additional service ownership metadata?
3. Which human approval system should own resume decisions in work: Teams,
   ServiceNow, Git PR approval, or Argo UI for the first iteration?
4. What retention policy should apply to incident memory records and A2A
   context evidence?

## PR Verdict

Ready to send for PR as a live-executed demo package. The demo package itself
worked end to end once its documented prerequisites were present and the model
backend was healthy.

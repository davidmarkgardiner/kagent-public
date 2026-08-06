# Hermes/Kanban Kubernetes Agentic-Delivery Factory Workflow Contract

**Audience:** Hermes/Kanban integrator and Kubernetes platform owners

**Status:** Proposed design — planning contract only; it does not authorize or implement a deployment.
**Purpose:** Turn one bounded Kubernetes request into a reviewable, evidence-first, PR-ready handoff without claiming that a static check or an agent response proves a live cluster result.

## Claim labels

Every substantive claim in this document is marked with one of these labels:

| Label | Meaning |
| --- | --- |
| **Verified current capability** | Confirmed from the checked-out repositories or helper scripts named in this document. This is not proof that it is installed or working in any particular cluster. |
| **Proposed design** | Recommended contract for the Hermes/Kanban integration. It requires implementation and approval by the owners. |
| **Unknown / requires validation** | Deliberately not assumed. The integrator or platform owner must establish it with current evidence before use. |

## 1. Grounded starting point and non-goals

| Claim | Basis and implication |
| --- | --- |
| **Verified current capability** | This repository has `scripts/kagent-verify-agent.sh`, which gates a kagent Agent CR on `Accepted=True`, `Ready=True`, a controller API check, and an optional smoke invocation. |
| **Verified current capability** | `scripts/kagent-a2a-invoke.sh` invokes a kagent Agent through its A2A JSON-RPC endpoint and owns the port-forwarding path. It is suitable as an evidence-producing test helper when an approved context and safe prompt are supplied. |
| **Verified current capability** | `platform/agentgateway/preflight-check.sh` checks for required Agent Gateway CRDs for a supplied kube context; the Agent Gateway documentation also calls for version-specific CRD/runtime validation. |
| **Verified current capability** | The local Hermes operating materials use asynchronous jobs that produce a normalized envelope and an evidence pointer; they explicitly treat evidence as a prerequisite for a claim. |
| **Unknown / requires validation** | The exact Hermes Kanban card API, attachment API, lock/lease primitive, agent roster, model routes, installed MCP servers, kube contexts, clusters, namespaces, and access policies for this integration. |
| **Proposed design** | This contract adds a delivery coordinator adapter between Hermes/Kanban and the specialist agents. The adapter must enforce the gates below; it must not infer permission from a card title or free-text prompt. |

**Non-goals — Proposed design:** This contract does not create credentials, select a production target, grant RBAC, install a model provider, publish a pull request, or apply Kubernetes resources. A request remains a plan until its preflight and approval records are complete.

## 2. Operating invariants

| Invariant | Contract |
| --- | --- |
| **Proposed design** | One parent delivery card maps to exactly one immutable `delivery_id`, repository, branch, worktree path, target kube context, target namespace, change class, and acceptance-criteria version. A change to any of those values creates a new attempt or returns the card to intake. |
| **Proposed design** | One implementation lock exists for each `repo + branch + worktree` tuple. Only the Kubernetes/Helm builder may hold it; the coordinator releases it only when the builder child card reaches a terminal state. |
| **Proposed design** | Every stage writes a structured result envelope and durable, sanitized evidence before its child card can be marked complete. A narrative-only update is not a handoff. |
| **Proposed design** | Static validation and live-cluster proof are independent outcome fields. A successful render, lint, or dry run never upgrades `live_cluster_proof` to `passed`. |
| **Proposed design** | Agents use least privilege and separate identities: planning/review identities cannot write; a builder can write only its assigned worktree; a deployer can act only in the approved non-production context and namespace. |
| **Proposed design** | A missing approval, missing evidence, ambiguous target, or failed safety gate blocks the card. The coordinator must not substitute a different cluster, namespace, model, tool, or credential. |

## 3. Intake and scope contract

### 3.1 Required request record

**Proposed design:** The integrator must reject or return-to-intake a parent card unless it contains every required field below. Values shown in braces are placeholders, not assumed environment values.

| Field | Required content | Validation before work begins |
| --- | --- | --- |
| `delivery_id` | Immutable ID, for example `KDF-{{ID}}` | Unique in Kanban and artifact store. |
| Request and outcome | Problem statement, requested behaviour, non-goals, risk/change class, and measurable acceptance criteria | Planner confirms the criteria can be tested. |
| Repository binding | Canonical repository URL or local checkout identifier, base SHA, destination branch, and dedicated worktree path | Coordinator confirms repository exists and the worktree is not locked by another active delivery. |
| Scope binding | Exact allowed files/directories, allowed commands, allowed Kubernetes verbs, and rollback/cleanup scope | Builder receives no implied permission outside the allow-list. |
| Environment binding | `{{KUBE_CONTEXT}}`, `{{NAMESPACE}}`, environment classification, and owner approval reference | Preflight confirms the context resolves and the namespace is the approved one. |
| Test contract | Static checks, live tests if any, safe test input, expected observable result, and evidence required | Test agent confirms each check is executable or marks it unknown. |
| Approval contract | Named approval gates, approving role, expiry/time window, and explicit prohibited actions | Coordinator verifies approval before a gated child can run. |
| Safety data | Resource budget, time budget, retry budget, data classification, secret-handling rule, and cleanup plan | Preflight records pass/fail without exposing credentials. |

### 3.2 Execution classes

| Class | Examples | Unattended action | Explicit human approval required |
| --- | --- | --- | --- |
| **Proposed design: read-only discovery** | Repository inspection, manifest render, schema/lint checks, `kubectl get`/status/events/log retrieval in the approved context | Yes, after scope and credential preflight | Any access outside the bound repository/context/namespace or to sensitive data. |
| **Proposed design: isolated code authoring** | YAML/Helm/chart/test/docs changes in the dedicated worktree | Yes, after intake passes and the worktree lock is held | Expanding scope, changing dependencies, accessing secrets, or committing/pushing. |
| **Proposed design: reversible sandbox deployment** | Applying a new, namespaced, read-only test object; Helm install into an approved disposable namespace | Only if the parent card contains a current deployment approval and a verified cleanup plan | First deployment to a target, every production-like target, cluster-scoped changes, privileged workloads, or any action outside the approved allow-list. |
| **Proposed design: prohibited without approval** | Production deployment, deletion/scale-down/rollback of shared resources, CRD/RBAC/network-policy changes, secret reads/prints, external publication, push/PR creation | No | A named human owner must approve the exact action; otherwise the card blocks. |

### 3.3 Approval record

**Proposed design:** Store this machine-readable approval record on the parent card and include its hash in the deployment-child input:

```yaml
approval:
  approval_id: "{{APPROVAL_ID}}"
  approved_by_role: "{{HUMAN_ROLE}}"
  granted_at_utc: "{{TIMESTAMP}}"
  expires_at_utc: "{{TIMESTAMP}}"
  permitted_actions:
    - "apply namespaced manifests in {{KUBE_CONTEXT}}/{{NAMESPACE}}"
    - "run the listed read-only verification commands"
  prohibited_actions:
    - "production deployment"
    - "cluster-scoped or destructive changes"
    - "sensitive-output disclosure or external publication"
  acceptance_criteria_hash: "{{SHA256}}"
```

## 4. Specialist roles and access boundaries

**Proposed design:** The minimum factory has six specialist roles plus a non-creative coordinator. One identity may temporarily perform more than one role only if its access boundary is still enforced and the evidence/review role remains independent of the builder.

| Role | Responsibilities | May modify repo/YAML | May deploy | Required capabilities | Access boundary |
| --- | --- | ---: | ---: | --- | --- |
| Coordinator | Creates the parent/child DAG, validates intake, acquires/releases locks, routes envelopes, enforces gates and circuit breakers | No | No | Hermes/Kanban card, dependency, attachment, and lock/lease operations | Metadata only; no kube credential or repository write authentication material. |
| Planner/architect | Narrows scope, identifies manifests/charts and test path, writes acceptance criteria and risk plan | No | No | Read-only repository access; architecture/docs search | No git write, kube write, secret access, or deployment capability. |
| Kubernetes/Helm builder | Implements scoped YAML/Helm/test/documentation changes; runs local/static checks | Yes, dedicated worktree only | No | Git worktree, `kubectl kustomize`/Kustomize where applicable, Helm renderer/linter, repository helper scripts | No production context, no secret material, no push/PR permission. |
| kagent/Agent Gateway specialist | Validates kagent Agent/ModelConfig, Agent Gateway manifests and safe MCP/A2A configuration against the installed version | Yes, dedicated worktree only | No by default | Read-only access to `agents/`, `platform/agentgateway/`, `platform/aks-mcp/`; kagent and Agent Gateway schema/tool knowledge | No tool grant expansion, no credential changes, no deployment unless separately delegated. |
| Cluster test/validation agent | Runs approved preflight, deployment, status, functional test, rollback/cleanup verification; captures redacted output | No, except generated evidence | Yes, only under valid deployment approval | Approved kube context, namespace-restricted identity, `kubectl`, Helm if applicable, `scripts/kagent-verify-agent.sh`, `scripts/kagent-a2a-invoke.sh`, Agent Gateway preflight helper | Read-only by default; write verbs limited to the explicit namespaced manifest/Helm release and cleanup plan. |
| Evidence/review agent | Checks completeness, distinguishes static from live proof, checks redaction/public safety, compares result to acceptance criteria | No | No | Read-only repository, artifact store and Hermes attachments; optional browser/UI capture access | Cannot alter implementation, evidence, cluster, or approval state. |
| PR/handoff agent | Produces changed-file list, commit candidate, PR-ready summary, rollback notes, and owner checklist | May create a local commit only when explicitly approved | No | Git metadata and diff access; approved Git hosting integration only if explicitly requested | No push, PR creation, or external publication by default. |

**Unknown / requires validation:** Map the table to actual Hermes agent profiles, installed skills, MCP servers, kube contexts, service accounts, and repository/Git-host permissions. Do not represent a configured profile or an MCP server as available until the preflight evidence says so.

## 5. Kanban parent/child workflow

### 5.1 Exact card hierarchy and dependencies

**Proposed design:** Create one parent card and the following child cards. The coordinator must use dependencies rather than an informal checklist; a child is not dispatchable until every dependency is `done` and its input envelope validates.

```text
KDF-{{ID}}  Parent: Kubernetes delivery request
|
|-- 00-intake-and-lock                 [coordinator]
|-- 01-plan-and-test-contract          [planner]                 depends: 00
|-- 02-build-change                    [builder + specialist]    depends: 01
|-- 03-static-validation               [builder]                 depends: 02
|-- 04-deployment-preflight            [cluster validator]       depends: 03
|-- 05-approved-deploy                 [cluster validator]       depends: 04 + human approval
|-- 06-functional-test-and-cleanup     [cluster validator]       depends: 05
|-- 07-evidence-review                 [independent reviewer]    depends: 03, 04, 06
`-- 08-pr-ready-handoff                [handoff agent]           depends: 07
```

**Proposed design:** For a request that explicitly has no deployment approval, child `05` is `not-applicable` with the approval absence recorded; children `06` and `07` must then state `live_cluster_proof: not-run`, not `passed`. The parent can still reach `PR-ready` but not `live-validated`.

### 5.2 States, handoffs, and blocks

| State | Meaning and allowed transition |
| --- | --- |
| **Proposed design: `intake`** | Parent exists but mandatory fields are being collected. No specialist execution. |
| **Proposed design: `ready`** | Intake schema, target binding, and lock check passed; next dependency may dispatch. |
| **Proposed design: `in-progress`** | Exactly one assigned role holds the child card. A heartbeat/lease must remain current. |
| **Proposed design: `awaiting-approval`** | Work is prepared but a named human approval is required; no deployment/release action may start. |
| **Proposed design: `review`** | An independent reviewer is checking the envelope and attached evidence. |
| **Proposed design: `blocked`** | A fail-closed condition or required human decision exists. The card includes a machine-readable reason and next owner. |
| **Proposed design: `done`** | Acceptance criteria for that child and its required evidence are complete. |
| **Proposed design: `failed`** | A non-retryable attempt failed; evidence and cleanup outcome are retained. |
| **Proposed design: `cancelled`** | Owner intentionally stopped the delivery; locks are released and no success claim is made. |

**Proposed design:** A block record must contain `reason_code`, `observed_at_utc`, `evidence_path`, `next_owner`, `required_decision`, and `safe_resume_point`. Recommended reason codes are `INTAKE_INCOMPLETE`, `LOCK_HELD`, `APPROVAL_MISSING`, `CREDENTIAL_UNAVAILABLE`, `TARGET_UNHEALTHY`, `MODEL_UNAVAILABLE`, `RATE_LIMIT`, `STATIC_VALIDATION_FAILED`, `DEPLOYMENT_FAILED`, `LIVE_TEST_FAILED`, `CLEANUP_FAILED`, and `EVIDENCE_MISSING`.

### 5.3 Structured stage-result envelope

**Proposed design:** Each child publishes this sanitized JSON/YAML-equivalent envelope to its card and the artifact store. Fields are references or hashes; credentials, tokens, raw Secret data, private addresses, and unrestricted logs are forbidden.

```yaml
schema_version: "kdf.stage-result.v1"
delivery_id: "KDF-{{ID}}"
child_id: "03-static-validation"
attempt: 1
status: "done" # done | blocked | failed | cancelled
claim_label: "Proposed design"
repo:
  revision: "{{BASE_OR_COMMIT_SHA}}"
  branch: "{{BRANCH}}"
  worktree: "{{SANITIZED_WORKTREE_IDENTIFIER}}"
target:
  kube_context: "{{KUBE_CONTEXT}}"
  namespace: "{{NAMESPACE}}"
  classification: "{{NON_PRODUCTION_OR_UNKNOWN}}"
result:
  static_validation: "passed" # passed | failed | not-run
  live_cluster_proof: "not-run" # passed | failed | not-run
  acceptance_criteria: []
evidence:
  manifest: "artifacts/KDF-{{ID}}/03-static-validation/summary.md"
  files: []
  sha256: []
redaction:
  checked: true
  method: "{{REDACTION_CHECK}}"
handoff:
  next_child: "04-deployment-preflight"
  constraints: []
  rollback_or_cleanup_status: "not-applicable"
```

### 5.4 Locking, retries, and circuit breakers

| Situation | Required behaviour |
| --- | --- |
| **Proposed design: worktree lock** | Coordinator atomically acquires `repo@branch@worktree` before dispatching `02-build-change`; a live lock contains holder, delivery ID, lease expiry, and last heartbeat. A conflicting active lock blocks the new card rather than sharing a worktree. |
| **Proposed design: stale lock** | Do not automatically steal it. Mark `LOCK_HELD`, notify the owner, and require an explicit recovery decision backed by evidence that no writer remains active. |
| **Proposed design: transient model/API failure** | At most two bounded retries with exponential backoff, unchanged inputs, and a fresh result envelope. Then block as `MODEL_UNAVAILABLE` or `RATE_LIMIT`. |
| **Proposed design: static validation failure** | No blind retry. Return to `02-build-change` only with a documented changed-file diff and a new attempt number. |
| **Proposed design: Helm/apply failure** | Stop automatic progression, collect status/events/redacted logs, execute only the pre-approved rollback/cleanup action, and block. No second apply until a human has reviewed the failure. |
| **Proposed design: evidence upload/attachment failure** | The stage cannot be `done`. Retain the local sanitized artifact, report its hash/path, and block as `EVIDENCE_MISSING`. |
| **Proposed design: circuit breaker** | Pause all new deployment children for the bound target after two deployment failures, one cleanup failure, or a target-health failure in the same delivery. Human review is required to reopen it. |

## 6. Delivery stages and gates

| Stage | Required work | Pass condition | Required evidence | Claim label |
| --- | --- | --- | --- | --- |
| 00 — Intake and lock | Validate request schema, target binding, approval requirements, and exclusivity lock | All required fields exist and the lock is held or intentionally not needed | Sanitized intake record, lock record/hash, risk class, missing-field report if blocked | **Proposed design** |
| 01 — Plan | Identify change surface, static/live tests, rollback, and specific approvals | Acceptance criteria and safe test plan are executable or explicitly marked unknown | Plan, command allow-list, acceptance-criteria hash, risk/rollback plan | **Proposed design** |
| 02 — Author | Modify only allowed files in the dedicated worktree; consult specialist for kagent/Agent Gateway paths | Scoped diff exists and contains no secret/private-environment values | Changed-file list, diff/stat, author notes, source references | **Proposed design** |
| 03 — Static validation | Render Kustomize, run Helm template/lint where applicable, repository lint/tests, and schema checks | Every required static check passes or a failure is returned to build | Rendered manifests, Helm template output, lint/test logs, command exit codes | **Proposed design** |
| 04 — Deployment preflight | Verify model/provider route, credentials, target health, namespace and RBAC, rate/budget limits, and rollback readiness | Each mandatory preflight is currently evidenced as pass | Redacted preflight output, target health/status, authorization check, approval hash | **Proposed design** |
| 05 — Approved deploy | Apply/install only the approved scoped change into the bound non-production target | Resource/release reaches the defined ready state without unsafe side effects | Exact rendered input hash, command record, `kubectl`/Helm status, events, release revision | **Proposed design** |
| 06 — Functional test and cleanup | Execute the defined kagent/Agent Gateway/MCP/A2A path, collect controller/API proof, then clean up if required | Expected observable response plus baseline/cleanup check passes | Agent/controller history, API response, status/events/logs, cleanup proof | **Proposed design** |
| 07 — Evidence review | Independently verify completeness, redaction, acceptance mapping, and static/live separation | No evidence gap or unsupported claim remains | Review checklist, artifact index, gaps/decision record | **Proposed design** |
| 08 — PR-ready handoff | Package the verified diff and review result for a human to commit/push/open as appropriate | Handoff is complete; it makes no unperformed publication claim | Changed-file list, candidate commit SHA if created, PR body draft, rollback note, owner checklist | **Proposed design** |

### 6.1 Tooling-specific test rules

| Path | What can be used as proof | What is insufficient | Claim label |
| --- | --- | --- | --- |
| kagent Agent CR | `Accepted=True`, `Ready=True`, controller/API evidence, and an approved smoke invocation via `scripts/kagent-verify-agent.sh` | YAML validity, CR existence, HTTP 200 alone, or a screenshot without controller/result evidence | **Verified current capability** for the helper; **Proposed design** for the proof threshold |
| A2A | Sanitized request/response and successful result recorded from `scripts/kagent-a2a-invoke.sh`, paired with the relevant agent/controller evidence | A port-forward opening or an endpoint URL alone | **Verified current capability** for the helper; **Proposed design** for the proof threshold |
| Agent Gateway | `platform/agentgateway/preflight-check.sh --context {{KUBE_CONTEXT}}`, installed-version schema check, and an approved functional route test | A copied manifest or assumptions from a different Agent Gateway version | **Verified current capability** for preflight helper; **Proposed design** for the full test |
| MCP/RemoteMCPServer | Current CR/runtime status and a safe tool invocation permitted by the test plan | Declaring an MCP binding without observing a permitted call | **Unknown / requires validation** because installed MCP server and tool policy are environment-specific |
| Helm | `helm template`/`helm lint`, release status, resource readiness/events, and a pre-approved uninstall/rollback proof | Template output alone as a live install result | **Proposed design** |

## 7. Evidence contract and durable artifacts

### 7.1 Required distinction

| Outcome field | Definition | Minimum proof |
| --- | --- | --- |
| **Proposed design: `static_validation`** | The exact candidate revision rendered/linted/tested without proving a live cluster behaviour | Rendered manifest/Helm output, command line, exit code, timestamp, revision hash. |
| **Proposed design: `live_cluster_proof`** | The bound cluster/namespace accepted the approved change and the defined runtime behaviour was observed | Target identity, command/API record, resource/release status, events/logs as needed, functional response, timestamp, cleanup/baseline result. |

**Proposed design:** Do not collapse these fields into one status. A handoff must say `live_cluster_proof: not-run` when deployment was not approved or not possible.

### 7.2 Artifact layout

**Proposed design:** Use a durable, access-controlled artifact root selected by the integrator. The following is the required logical layout; `{{ARTIFACT_ROOT}}` must not be a developer-machine-only path.

```text
{{ARTIFACT_ROOT}}/kdf/KDF-{{ID}}/
  00-intake/
    request.redacted.yaml
    lock.json
  01-plan/
    delivery-plan.md
    acceptance-criteria.yaml
  02-build/
    changed-files.txt
    diff.patch
  03-static-validation/
    kustomize-rendered.yaml
    helm-template.txt
    helm-lint.txt
    test-output.txt
  04-preflight/
    preflight-summary.md
    target-health.txt
    authorization-check.txt
  05-deploy/
    input-manifest.sha256
    release-or-apply.txt
    kubectl-status.txt
    kubectl-events.txt
    redacted-logs.txt
  06-functional-test/
    agent-controller-history.txt
    a2a-or-api-response.redacted.json
    ui-proof.png
    cleanup-proof.txt
  07-review/
    evidence-review.md
    artifact-index.json
  08-handoff/
    pr-ready-summary.md
    rollback.md
    commit-and-pr-metadata.json
```

| Card | Attach or link | Required content |
| --- | --- | --- |
| **Proposed design: parent** | `artifact-index.json` plus review and handoff summaries | Delivery ID, target placeholders/identifiers, outcome fields, latest state, owner and approval references. |
| **Proposed design: 03 static validation** | Rendered output and static test/lint summary | Exact revision, command output/exit status, SHA-256 of key files. |
| **Proposed design: 04–06 deployment/test** | Preflight, status/events/logs, API/controller history, cleanup proof | Bound context/namespace identifier, timestamp, sanitized raw evidence and test assertion. |
| **Proposed design: 07 review** | Evidence review | Acceptance-criteria-to-evidence matrix and explicit gaps. |
| **Proposed design: 08 handoff** | PR-ready summary | Changed-file list, candidate commit/PR SHA only if actually created, rollback/cleanup status, human next action. |

**Proposed design:** Evidence must be sanitized before attachment. Store a hash and a redaction method with each artifact. Reject Secret data, authentication material, kubeconfig contents, internal hostnames/IPs, and unbounded log dumps. If evidence cannot be retained durably, the stage blocks; a machine-local path is not sufficient handoff evidence.

## 8. Reliability and safety gates

### 8.1 Mandatory preflight

| Check | Required result | Failure handling | Claim label |
| --- | --- | --- | --- |
| Agent/model/provider readiness | Required role profile and permitted model route have a current lightweight health result | Block; do not silently select a different model/provider | **Proposed design** |
| Kubernetes credential and target | Approved context resolves; identity is valid; environment classification is recorded | Block `CREDENTIAL_UNAVAILABLE` or `TARGET_UNHEALTHY` | **Proposed design** |
| Namespace and RBAC safety | Namespace exactly matches intake; `can-i`/equivalent checks cover only allowed verbs/resources | Block on mismatch or excess/unverifiable privilege | **Proposed design** |
| Cluster health | Control plane/API reachable and relevant target dependencies are not in an unhealthy state | Block; do not deploy to diagnose an unhealthy target unless a separate approved incident task says so | **Proposed design** |
| Agent Gateway prerequisites | Required CRDs are present in the bound context and installed-version assumptions are checked | Use `platform/agentgateway/preflight-check.sh --context {{KUBE_CONTEXT}}`; block on failure | **Verified current capability** for helper; **Proposed design** for gate policy |
| kagent prerequisites | Required Agent CR/controller checks and, where specified, safe smoke route are available | Use `scripts/kagent-verify-agent.sh` with the approved context/agent/prompt; block on failed prerequisite | **Verified current capability** for helper; **Proposed design** for gate policy |
| Resource, disk, time, and usage budgets | Free disk/worktree capacity, execution time, API rate, and permitted usage budget meet intake thresholds | Block `RATE_LIMIT` or resource-limit reason; never continue by consuming unapproved capacity | **Proposed design** |
| Evidence sink | Artifact root and Hermes attachment path are writable and sanitized | Block `EVIDENCE_MISSING` before deployment if live proof cannot be stored | **Proposed design** |

### 8.2 Fail-closed rules

| Condition | Required action |
| --- | --- |
| **Proposed design** — Model/provider unavailable or rate-limited | Retry only within the bounded retry rule; then block and preserve the failed result. Do not fall back to an unapproved model. |
| **Proposed design** — Helm release/apply fails | Stop, collect bounded diagnostics, run only the approved rollback/cleanup action, mark failed/blocked, and require human review before another deployment. |
| **Proposed design** — Target cluster or namespace is unhealthy/ambiguous | Do not deploy, test, or clean up beyond read-only diagnostics. Block with target-health evidence. |
| **Proposed design** — Required evidence is missing, unsafe, or cannot be redacted | Do not mark success and do not create a PR-ready live-validation claim. Block with an evidence recovery request. |
| **Proposed design** — A secret, private endpoint, or token appears in output | Stop attachment/publication, quarantine the artifact according to owner process, record only a safe incident reference, and require human handling. |
| **Proposed design** — A requested action is production, destructive, cluster-scoped, or externally publishing | Require explicit, current human approval tied to this delivery and exact action. Otherwise block. |

## 9. PR-ready handoff contract

**Proposed design:** `08-pr-ready-handoff` produces a handoff; it does not push, open a pull request, merge, or publish anything unless a separate explicit approval says so.

The handoff must contain:

1. Delivery ID, request summary, scope, risk class, and target binding.
2. Exact changed-file list and diff/stat; candidate commit SHA only if a local commit was actually created.
3. Acceptance-criteria matrix with separate `static_validation` and `live_cluster_proof` values.
4. Links/hashes for every required artifact, including rendered manifests and live evidence where run.
5. Deployment and cleanup/rollback outcome, including any remaining resources or unknowns.
6. Explicit list of blocked items, skipped tests, assumptions, and approvals still required.
7. A ready-to-paste PR title/body draft and named human next action.

## 10. Recommended safe proof of concept

### POC definition

**Proposed design:** Run one deliberately small, non-production, reversible delivery only after the platform owner supplies an approved `{{KUBE_CONTEXT}}` and `{{POC_NAMESPACE}}` and preflight proves the required controller/model route exists.

The POC is: **add a new scoped, read-only kagent smoke Agent manifest and its test fixture in this repository; render and statically validate it; deploy it only to `{{POC_NAMESPACE}}`; invoke it with one benign A2A prompt; capture controller/API evidence; then remove the POC resources and prove cleanup.** If the selected environment has an approved Agent Gateway route, include its preflight and a safe routed request; otherwise record that branch as `not-run` rather than fabricating it.

This exercises intake, worktree locking, specialist review, YAML authoring, kagent/A2A functional testing, evidence collection, independent review, cleanup, and PR-ready handoff without touching production or granting write-capable tools to the agent.

### POC acceptance criteria

| Criterion | Required result | Claim label |
| --- | --- | --- |
| Intake and lock | One complete request record, valid target approval, and no competing writer for the bound worktree | **Proposed design** |
| Authoring | Only pre-approved POC files change; no secret/private values are introduced | **Proposed design** |
| Static proof | Render/lint/check outputs are attached with revision hashes and pass | **Proposed design** |
| Deployment preflight | Approved non-production context/namespace, RBAC scope, model route, and evidence sink are currently evidenced | **Proposed design** |
| Live proof | Agent reaches `Accepted=True` and `Ready=True`, and the approved A2A smoke produces the defined safe result with controller/API evidence | **Verified current capability** for the available verification/invocation helpers; **Proposed design** for the POC pass threshold |
| Cleanup | POC objects are removed only as authorised and post-cleanup status shows the agreed baseline | **Proposed design** |
| Review/handoff | Independent review finds no unsupported live claim; Hermes shows links to the durable evidence and a complete PR-ready summary | **Proposed design** |

## 11. Integrator implementation checklist

| Decision or integration task | Status |
| --- | --- |
| Map the parent/child hierarchy, dependencies, terminal states, and block reason codes to the actual Hermes Kanban schema | **Unknown / requires validation** |
| Implement an atomic lock/lease keyed by repository, branch, and worktree; surface holder and expiry in Hermes Desktop | **Proposed design** |
| Implement the `kdf.stage-result.v1` envelope validation and prevent completion without required evidence | **Proposed design** |
| Configure sanitized, durable artifact storage and card attachments; verify retention and access controls | **Unknown / requires validation** |
| Create least-privilege identities and kube contexts for roles; verify with current RBAC evidence | **Unknown / requires validation** |
| Register the existing kagent and Agent Gateway helper scripts as approved validation tools, with context/namespace arguments supplied from intake | **Proposed design** |
| Run the POC and record actual results; only then promote any POC-related statement to verified current capability | **Proposed design** |

## References inspected for this contract

| Source | Relevance | Claim label |
| --- | --- | --- |
| `scripts/kagent-verify-agent.sh` | Existing kagent Agent readiness/controller/smoke gate | **Verified current capability** |
| `scripts/kagent-a2a-invoke.sh` | Existing A2A JSON-RPC invocation helper | **Verified current capability** |
| `platform/agentgateway/preflight-check.sh` and `platform/agentgateway/README.md` | Agent Gateway prerequisite and installed-version validation guidance | **Verified current capability** |
| `../agentic-os-system/README.md` and Hermes operating materials | Existing evidence-first asynchronous job-envelope pattern | **Verified current capability** |
| `AGENTS.md` | Public-safety, least-privilege, Kubernetes/Argo validation, and live-proof constraints for this repository | **Verified current capability** |

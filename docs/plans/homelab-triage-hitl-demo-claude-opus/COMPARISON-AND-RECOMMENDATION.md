# Home-lab triage HITL demo: comparison of four plans and recommendation

**Status:** planning review only. Nothing was built, deployed or run.
**Date:** 2026-09-30.
**Inputs:** four plans written independently from the same prompt
(`docs/plans/homelab-triage-hitl-demo/FOUR-AGENT-PLANNING-PROMPT.md`):

- `docs/plans/homelab-triage-hitl-demo/agent-1.md`
- `docs/plans/homelab-triage-hitl-demo/agent-2.md`
- `docs/plans/homelab-triage-hitl-demo/agent-3.md`
- `docs/plans/homelab-triage-hitl-demo/agent-4.md`

## Recommendation

**Use Agent 4's plan as the base and add five changes taken from the other plans.** Agent 4 is the most complete plan that stays within the prompt's requirements, and it has the lowest delivery risk:

- The approval is requested in Teams, and a human signs in to approve it.
- It does not need a Bot Framework registration.
- It does not change the prompt of the proven triage agent.
- Its first slice (P1) is safe to show on its own.

Its gaps are all things another plan already handles well. The five changes are listed under [The merged plan](#the-merged-plan).

The runner-up is **Agent 3**. It is cheaper (about 10½ days), needs no new service, and needs no inbound path into the home lab. However, it approves by pasting a phrase into a GitLab note, which does not meet the prompt's requirement for a Teams approval request that a human approves. Keep it as the fallback if no OIDC provider is available for the approval page.

## Claims checked in the repository

I spot-checked the shared findings before relying on them:

| Claim (made by all four plans unless noted) | Check | Result |
|---|---|---|
| Triage calls kagent directly, not through agentgateway | `work-agent-bundles/homelab-verified-triage-replication/config/05-triage-evaluation-settings.yaml:9` | Confirmed: `http://kagent-controller.kagent:8083/...` |
| Triage uses `kagent-tool-server`, not the Kubernetes MCP | same file, line 10 | Confirmed |
| The Teams HITL Sensor resumes whatever workflow the body names | `platform/teams-hitl/sensor.yaml:51,62` | Confirmed (`operation: resume`, `dataKey: body.workflow_name`). No `authSecret` in `eventsource.yaml` |
| The approval template's suspend has a 24-hour duration, and the comment assumes a timeout fails the workflow (Agent 2) | `platform/teams-hitl/workflow-approval-template.yaml:161-163` | Confirmed in the file. Argo documents that a suspend with a `duration` **resumes** when the time runs out, so `approved-execute` may run with no approval. Not yet tested on the installed Argo version |
| An `authSecret` pattern for Argo Events webhooks exists in the repo (Agent 4) | `platform/argo-events/sources/gitlab/04-eventsource.yaml:28,63` | Confirmed |

The two `platform/teams-hitl` defects are real problems in code that is already checked in, not just risks for this demo. They should be fixed or marked "do not use for real approvals", whichever plan is chosen.

## Where all four plans agree

These points are settled and do not need further debate:

1. **Keep the `observability.triage.v2` wire contract as it is.** `automation_allowed` stays `false`. Remediation uses its own proposal schema and never goes onto Kafka.
2. **One Pod crashlooping from a bad env value** gives one error log and one `BackOff` Event with the same Pod-based `dedupe_key`. Existing fixes F2 and F3 turn them into one ticket plus one appended note. Only the workflow that creates the ticket may start remediation.
3. **The workflow chooses the branch, not the model.** It reads Flux ownership labels (`kustomize.toolkit.fluxcd.io/name`, `helm.toolkit.fluxcd.io/name`) on the live object. This is also what stops Flux reverting a direct fix.
4. **The model suggests; fixed code makes the change.** The proposal is checked against a platform-owned policy. The server-side-apply object or Git diff is built from policy fields, never from model text.
5. **Two separate Kubernetes MCP deployments.** They have separate service accounts. The write side is limited by RBAC to `get` and `patch` on one named Deployment, with no `create`. The read side has a fixed list of six tools and blocks Secrets, ConfigMaps, ServiceAccounts, TokenRequests and RBAC objects.
6. **agentgateway cannot see tool arguments at request time.** So it restricts only the caller and the tool name, and the real limit is in Kubernetes. All four plans note that `resources_create_or_update` uses `Force: true`, which will take over fields owned by other managers.
7. **Resuming a workflow is not an approval.** After resume, the workflow checks a single-use decision tied to the proposal hash, and fails closed if it is missing.
8. **In the GitOps branch, Teams is only a link.** A bot with the Developer role opens the MR and cannot merge it. A human Maintainer merges in GitLab. The fix counts as successful only when Flux has applied a revision that contains the merge commit *and* the workload is healthy.
9. **Open items to check before building:** whether Flux is installed on `red`, the installed agentgateway, Argo and kagent versions, and the GitLab tier (required approvals need Premium).

## Where the plans differ

| Decision | Agent 1 | Agent 2 | Agent 3 | Agent 4 |
|---|---|---|---|---|
| Demo layout | Two namespaces (`hitl-demo-direct`, `hitl-demo-gitops`); env `DEMO_MODE=fail` | Existing `agentic-triage-proof` namespace, two Deployments; `PAYMENT_MODE=strict-v2` | Two namespaces; wrong `PAYMENTS_DB_PORT` vs `payments-db` Service | One namespace, two copies; `UPSTREAM_PORT=6380` vs `cache-sim:6379` |
| Diagnosis needs several reads | Partly (log plus Deployment spec) | Partly (log does not list valid values) | **Yes** (log, Service, Deployment) | **Yes** (log, Service, Deployment) |
| Changes to collection | Alloy and Sensor allowlists | **None** (namespace already allowed) | New Alloy and Sensors just for the demo; proven files not edited | Alloy scope in two places |
| Where the proposal comes from | New agent, new coordinator workflow | **Existing triage agent's prompt is patched** | New agent, new template reusing existing steps by `templateRef` | New planner agent in a child workflow |
| How the direct approval is made | Teams `Action.Execute` through a **Bot Framework bot** | OIDC approval page, Ed25519-signed decision | **GitLab note** with an exact phrase, polled by a scheduled workflow | OIDC broker (grown from `mock-bot`), signed JWS decision |
| Needs inbound access to the home lab | Yes (bot callback) | Approval page reachable on the LAN | **No** | Approval page reachable on the LAN |
| Limit on which fields can change | **Admission policy** (one field, no Flux objects, needs the digest annotation) | RBAC `resourceNames` plus admission on **Workflows and Agents** | RBAC plus **admission policy** (one field) | RBAC `resourceNames` only |
| Stops triage from creating a workflow that runs as the executor | Not addressed | **Yes** (admission on `Workflow`: template ref only, no inline templates or SA override) | Not addressed | Not addressed (`podSpecPatch` scoping only) |
| Remediation lock | Label check on the coordinator | Fixed workflow name plus execution claim | Ledger ConfigMap | **Lock per Deployment** (safe when Pods are replaced) |
| Kill switch for the whole feature | Namespace list | None | Separate Sensors | **Feature flag, off by default** |
| Handling of the suspend timeout | Duration = expiry + 60 s; post-resume check fails closed | **Knows it auto-resumes**; design is safe regardless | Duration = TTL; `verify-decision` returns `expired` | **Assumes the suspend fails on timeout** (wrong per Argo docs); `onExit` records the expiry |
| Direct fix fails verification | Label `hitl-failed` | **Automatic rollback** of the inverse change | Rollback proposal that needs fresh approval | Recommend rollback; needs fresh approval |
| GitOps MR review times out | Leave open | **Close the MR** | Suspend and doorbell | Leave open, release lock |
| Effort (engineer-days) | about 11–19 (depends on the bot) | about 12.5 | **about 10½** | about 12.5 |
| First slice | Phase 1 + 2 (intake plus proposal) | Phase 0–2, about 5.5 days (direct branch, `curl` approval) | P1, 2 days (diagnose and propose) | P1, 2.5 days (read-only planning) |

## Scoring

The scores run from 1 to 5, where 5 is best. The weights reflect the prompt: safety of write access and approval first, then fit with the requirements, then delivery risk.

| Criterion | Weight | A1 | A2 | A3 | A4 |
|---|---:|---:|---:|---:|---:|
| Write limit (RBAC, admission, no escalation) | 3 | 5 | 4 | 5 | 3 |
| Approval integrity (identity, replay, expiry, changed proposal) | 3 | 4 | 5 | 4 | 4 |
| Fit with "Teams approval request, then authenticated human approves" | 2 | 5 | 4 | 2 | 4 |
| Delivery risk (external dependencies, new code) | 2 | 2 | 3 | 5 | 4 |
| Leaves the proven triage path untouched | 2 | 4 | 3 | 5 | 5 |
| Correct about upstream behaviour | 2 | 4 | 5 | 4 | 3 |
| Fault needs genuine diagnosis | 1 | 3 | 3 | 5 | 5 |
| Operational controls (lock, flag, cleanup) | 1 | 3 | 3 | 3 | 5 |
| **Weighted total (out of 80)** | | **63** | **63** | **67** | **63** |

On raw score, **Agent 3 is highest** and the other three tie. Agent 4's score is held down mostly by three gaps that can be fixed by copying a paragraph from another plan:

- field-level admission;
- admission on Workflows;
- the suspend timeout behaviour.

Agent 3's weak point, approving in GitLab instead of Teams, is a design choice, not a gap. Changing it would mean redesigning its approval path. With the five changes below, Agent 4 scores 5 on write limits, 5 on approval integrity and 5 on upstream correctness, a total of **76**. That puts it ahead of Agent 3 while keeping Teams as the place where the approval starts.

Why not the others:

- **Agent 1** has strong ideas: the admission policy with a digest annotation, and the verifier workflow that records the decision before resuming. But its headline approval path needs a Bot Framework registration and `Action.Execute`, which the repo has never had. Without them, the Teams part must be labelled "simulated". That is the biggest single delivery risk in any of the four plans.
- **Agent 2** is the most rigorous about Argo behaviour, and it alone closes the "triage SA creates a workflow that runs as the executor" gap. But it patches the prompt and output extraction of the proven `diagnose-readonly` step, so the verified triage behaviour changes for every incident. It also rolls back automatically after a failed verification, which is a second write without a second approval.

## The merged plan

Base: **Agent 4** (`docs/plans/homelab-triage-hitl-demo/agent-4.md`). Keep its:

- demo layout (one namespace, two copies of the app);
- separate planner agent and child workflow;
- lock per Deployment and feature flag;
- OIDC approval broker grown from `platform/teams-hitl/mock-bot/`;
- polling on the GitOps branch;
- acceptance tests A-1 to A-26.

Then make these five changes.

### 1. Add an admission policy that allows one field (from Agents 1 and 3)

Add a `ValidatingAdmissionPolicy` bound to `k8s-mcp-write`'s username. It allows an `UPDATE` to `deployments/checkout-direct` only when all of these hold:

- no Flux labels on `oldObject`;
- replicas, images, command, args, resources, volumes and the service account are unchanged;
- the only env difference is `UPSTREAM_PORT`, with a value matching `^[0-9]{1,5}$`;
- the annotation `triage.platform.example/remediation-key` is present.

Set `failurePolicy: Fail`. If the env-list comparison in CEL proves too awkward, use Agent 1's fallback instead: the pod spec with `env` removed must equal the old one with `env` removed.

Add a second binding that denies every write from the read MCP's service account.

**Why:** RBAC `resourceNames` limits *which* object can change but not *what* changes, and a forced server-side apply can overwrite any field of that Deployment. The workflow building the object itself is a good control, but on its own it is only an application-level check.

Add acceptance tests for a denied change to image, to replicas, to a second env var, and to `checkout-gitops`, following Agent 3's T-B4.

### 2. Add admission on Workflows and Agents (from Agent 2)

Add admission policies:

- A `Workflow` that uses the `remediation-*` service accounts must reference `workflowTemplateRef: homelab-remediation`, with no inline `templates`, no `serviceAccountName` override and no `podSpecPatch`.
- Deny any `Agent`, `RemoteMCPServer` or `MCPServer` that references the write route or Service. This goes further than Agent 4's `scripts/validate-agent-cr.py` check, which runs only in CI.

**Why:** the triage service account has to be able to create the child workflow. Without this policy, anything that can create workflows could also start one that mounts the executor's token.

### 3. Fix the suspend timeout behaviour (from Agent 2)

Agent 4's expiry row says "on timeout, the suspend node fails". Replace it with this:

- The suspend auto-resumes at TTL + 60 s.
- `verify-decision` finds no approved JWS and records `expired`.
- The broker marks the approval `expired`.

Remove the `onExit` expiry handler.

Add Agent 2's Phase 0 test: a 30-second suspend with a `duration`, to record what the installed Argo version does.

Add Agent 1's rule that the first step after resume fails closed with "resumed without a valid decision". That covers a manual `argo resume`.

### 4. Close the MR when review times out (from Agent 2)

When the GitOps review times out, comment on the MR and close it, record `remediation-expired`, and release the lock. Leaving it open (Agent 4's default) allows a late merge that no workflow is watching, so Flux would apply it and the ticket would never be updated.

### 5. Keep Agent 3's approval path as a fallback, not the main path

Write Agent 3's GitLab-note approval up as the fallback. It uses the exact phrase `APPROVE-REMEDIATION <approval_id> <digest12>`, a scheduled job that polls GitLab to wake the workflow, and a create-only ledger. Use it only if no OIDC provider or approval page is available in the home lab.

`verify-decision` stays the one place where decisions are checked. Only its source changes, from the signed broker JWS to a GitLab note.

### Also fix outside the demo

These go in a separate PR, because the files are already checked in:

- Add `authSecret` to `platform/teams-hitl/eventsource.yaml`.
- Make the resume in `sensor.yaml` non-authoritative, or mark the directory "design only, do not apply".
- Fix the approval template's suspend so that a timeout leads to a failure branch, not to `approved-execute`.

## Merged build order

These are Agent 4's phases with the extra work added; estimates are in engineer-days.

| Phase | Scope | Effort |
|---|---|---|
| P0 | Agent 4's P0, plus Agent 2's suspend-duration test and Agent 1's check of how `resourceVersion` behaves in a server-side apply | 1 |
| P1 (**first slice**) | Read-only planning through agentgateway; policy verdict in the ticket; no write identity exists | 2.5 |
| P2 | Direct branch with a simulated human, **plus the admission policies from changes 1 and 2**, with their denial tests | 3.5 |
| P3 | Real OIDC approval page and Teams Workflows card (or Agent 3's GitLab-note fallback) | 1.5 |
| P4 | GitOps branch, including closing the MR on timeout | 3 |
| P5 | Rehearsal, evidence, public-safety scan | 1.5 |
| **Total** | | **about 13** |

P4 can run in parallel with P2 and P3 once P1 is done.

## Open decisions for the owner

1. **OIDC for the approval page:** is an Entra, Dex or Keycloak client with group claims available in the home lab? If not, use Agent 3's GitLab-note approval (change 5).
2. **GitLab tier** of the demo project. On Free, approval rules can't be enforced. Only "Maintainers merge" is enforced, and an approval check can only detect an unapproved merge afterwards.
3. **Is Flux on `red`?** If not, installing it becomes part of P4.
4. **Approval expiry times:** 30 minutes for the demo; the production value is still undecided.
5. **Separation of duties:** two test identities (approver and merger) versus one person, which must be stated in the evidence.

## Output

`/Users/davidgardiner/Desktop/repo/kagent-public/docs/plans/homelab-triage-hitl-demo-claude-opus/COMPARISON-AND-RECOMMENDATION.md`

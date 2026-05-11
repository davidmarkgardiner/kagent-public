# New Demo Agents — Knowledge Concierge + Incident Commander

**Date:** 2026-05-07
**Status:** Manifests written, NOT yet applied to any cluster
**Scope:** Two demo kagents extending the existing 11-specialist + remediation lineup

---

## Why these two

The shared AKS platform already demos SRE triage + remediation through 11
namespace specialists, a Teams-HITL gate, and GitLab issue creation. The next
two demos sit at the ends of the platform journey:

| Agent | Slot in the journey |
|---|---|
| **Knowledge Concierge** | "I have a question." First touch for any new tenant. Self-service Q&A over the platform docs. |
| **Incident Commander** | "Something's broken." Multi-agent orchestration during an incident — fans out to specialists, synthesises a comms-ready summary + remediation plan, gates via existing HITL flow. |

Together they cover *learn → act* — the natural arc on the platform.

---

## Files added (this drop)

| Path | Lines | Purpose |
|---|---|---|
| `kagent-triage/aks/knowledge-concierge-agent.yaml` | 80 | Q&A agent CRD. No k8s tools. Citation-required system prompt. |
| `kagent-triage/aks/build-knowledge-corpus.sh` | 75 (`0755`) | Idempotent script — packages `kagent-triage/docs/*.md` (13 files) into one `kagent-knowledge-corpus` ConfigMap. |
| `kagent-triage/aks/incident-commander-agent.yaml` | 102 | Synthesiser CRD. No tools (orchestration lives in the workflow). System prompt enforces `[DEMO MOCK]` label preservation. |
| `aks-mgmt-stack/holmes-argoworkflows/knowledge-query-workflow.yaml` | 305 | Workflow: ripgrep retrieval → A2A → optional Mattermost. |
| `aks-mgmt-stack/holmes-argoworkflows/incident-commander-workflow.yaml` | 600 | Workflow: fan-out (parallelism 3) → synthesise → pre-file GitLab → HITL → remediate → finalise. |

All files re-use the canonical patterns:

- A2A call shape from `aks-mgmt-stack/holmes-argoworkflows/kagent-sre-workflow.yaml:151-304`
- HITL gate shape from `ai-platform/teams-hitl/mock-bot/test-approval-workflow.yaml`
- Agent CRD shape from `kagent-triage/kro-agent.yaml`

---

## Architecture decisions (what's deliberate)

### 1. Workflow-side retrieval, not whole-corpus injection
The `kagent-triage/docs/` corpus is **13 markdown files, ~32K words**. Stuffing
the whole thing into the agent's `dataSources` for every query is wasteful
and risks exceeding the served context window for Qwen 14B.

Instead, the `knowledge-query-workflow` runs **ripgrep over the corpus**,
picks the top-3 highest-hit-count files for the user's question, and feeds
only those chunks (typically 3–5KB) into the agent's user message. The
agent's system prompt enforces "answer only from supplied chunks; cite the
source path."

This is small-scale RAG without an embedding model — deterministic,
demo-friendly, and easy to swap for pgvector once kagent v0.8.4+ unblocks
memory work.

### 2. Workflow orchestrates fan-out, agent synthesises
The Incident Commander **does not call other agents itself.** The Argo
workflow fan-outs to specialists in parallel and feeds their JSON outputs
into the synthesis agent.

**Trade-off accepted:** the demo voiceover has to position Incident
Commander as "the agent that turns evidence into comms + a plan", not "the
agent that runs the incident". A future iteration (post-GitLab-MCP, when
agent-callable A2A tooling exists) can let the agent itself drive the
fan-out.

The constraint that drove this: the user-chosen mock-data depth is "YAML
stubs only — no mock MCP server", which rules out an `a2a-dispatch` MCP
tool the agent could use.

### 3. Mock-data tagging, not mock-data hiding
Every stubbed value (recent deploys, on-call rota, similar past incidents,
comms channel) is prefixed `[DEMO MOCK]` in the workflow parameters. The
synthesis agent's system prompt has a HARD rule:

> Preserve the `[DEMO MOCK]` tag verbatim wherever you reproduce those
> values in the comms draft or remediation plan.

This is the explicit guardrail against the demo presenting stub data as
real signal — without it, a polished synthesised comms draft could mask
the fact that "the on-call is bob@platform" is fake.

### 4. GitLab issue filed BEFORE approval, not after
The HITL approval card can't carry a 5KB plan body — Adaptive Cards aren't a
large-document transport. Pattern:

1. Workflow synthesises the plan.
2. Workflow files GitLab issue with title `[PENDING APPROVAL]` and the
   **full plan in the body** — getting a stable URL.
3. Approval request to mock-bot carries `plan_url` (the GitLab link) plus
   `plan_summary` (first 800 chars of the plan).
4. After decision: workflow renames the issue to `[APPROVED]` /
   `[REJECTED]` and appends the remediation result as a comment.

This keeps the approval card small while preserving the full plan for
audit and review.

---

## Verified facts (from Codex review, applied 2026-05-07)

| Item | Verification |
|---|---|
| Istio agent names | `aks-istio-system-agent`, `aks-istio-ingress-agent` (file names drop the prefix; `metadata.name` keeps it) |
| Corpus size | 13 markdown files, 264,823 bytes, ~32K words — too large for prompt-injection without retrieval |
| Existing HITL request body | Only carries `tier`, `action`, `target`, `rationale` — extended here with `plan_url` + `plan_summary` |
| Existing sensor | Resumes workflow on approval only — does NOT propagate decision metadata |

---

## Deployment (when authorised — not yet applied)

```bash
# 1. Build the knowledge corpus ConfigMap from kagent-triage/docs/
./kagent-triage/aks/build-knowledge-corpus.sh
kubectl -n kagent get cm kagent-knowledge-corpus -o jsonpath='{.data._index\.txt}'
# Expect: index lines for all 13 docs

# 2. Apply the agent CRDs
kubectl apply -f kagent-triage/aks/knowledge-concierge-agent.yaml
kubectl apply -f kagent-triage/aks/incident-commander-agent.yaml

# 3. Apply the workflow templates
kubectl apply -f aks-mgmt-stack/holmes-argoworkflows/knowledge-query-workflow.yaml
kubectl apply -f aks-mgmt-stack/holmes-argoworkflows/incident-commander-workflow.yaml

# 4. Verify the agents are reachable via A2A
KAGENT="http://kagent-controller.kagent.svc.cluster.local:8083"
kubectl -n kagent run a2a-check --rm -it --image=curlimages/curl --restart=Never -- \
  curl -s -o /dev/null -w "%{http_code}" \
  $KAGENT/api/agents/kagent/knowledge-concierge
kubectl -n kagent run a2a-check --rm -it --image=curlimages/curl --restart=Never -- \
  curl -s -o /dev/null -w "%{http_code}" \
  $KAGENT/api/agents/kagent/incident-commander
# Expect: 200 each
```

---

## Demo flows

### Demo 1 — Knowledge Concierge

```bash
argo submit -n argo --from workflowtemplate/knowledge-query \
  --parameter question="How do we rotate secrets in this platform?" \
  --watch
```

**What to show on screen:**

- Step 1 (`retrieve`) prints the ripgrep pattern + top files chosen
- Step 2 (`ask`) prints the cited answer to stdout
- Expected: agent cites `SECRET-ROTATION-RUNBOOK.md` and possibly
  `SAD-COMPLIANCE-CHECKLIST.md`

**Other questions to try:**

- `"How do I onboard a new namespace?"` → expect `ONBOARDING-NEW-NAMESPACE.md`
- `"What's our RBAC pattern on the management cluster?"` → expect
  `SHARED-CLUSTER-RBAC.md` and `README-MANAGEMENT-CLUSTER.md`
- `"What kagent integrations does EASE need?"` → expect
  `EASE-INTEGRATION-QUESTIONS.md`
- `"What does the threat model say about workload identity?"` → expect
  `SAD-THREAT-MODEL.md`

### Demo 2 — Incident Commander

**Prereqs:** mock-bot deployed, `eventsource.yaml` + `sensor.yaml` from
`ai-platform/teams-hitl/` applied.

```bash
# Submit (workflow will suspend at HITL gate)
argo submit -n argo --from workflowtemplate/incident-commander \
  --parameter alert_summary="Pod CrashLoopBackOff in gitea" \
  --parameter target_agents="kube-system-agent,flux-system-agent" \
  --watch &

# Approve via mock-bot
kubectl exec -n argo svc/mock-bot -- sh -c \
  'APP=$(curl -s localhost:8080/pending | jq -r ".[0].approval_id") &&
   curl -X POST "localhost:8080/decide/$APP?decision=approved"'
```

**What to show on screen:**

- Fan-out step calls 2 specialists in parallel (per `parallelism: 3` cap)
- Synthesis step prints TL;DR / Evidence / Mock Context / Plan / Comms /
  Risk — every `[DEMO MOCK]` tag preserved
- GitLab issue filed as `[PENDING APPROVAL]` *before* approval
- Workflow suspends; mock-bot prompt visible on `/pending`
- After approval: GitLab issue title flips to `[APPROVED]`, remediation
  comment added, optional Mattermost post

---

## Known gaps (explicit)

### 1. Rejection path requires sensor extension
The current `teams-hitl` sensor (`ai-platform/teams-hitl/sensor.yaml`)
only calls `argo workflow resume` on approval. Rejection currently causes
the workflow's `wait-for-approval` step to time out (10 minutes) and the
workflow fails — GitLab issue stays `[PENDING APPROVAL]` forever.

**Fix when you want the rejection demo to work:**

- Extend the sensor to handle the `decision=rejected` callback variant by
  calling `argo workflow resume <wf> --parameter decision=rejected`
- Add a `decision` output parameter on `wait-for-approval`
- Add a conditional branch on `finalise-gitlab-issue` keyed on
  `decision == "rejected"` that flips the title to `[REJECTED]` and skips
  remediation

This is a ~15-line sensor diff plus a small workflow change. Not in scope
for this drop.

### 2. Adaptive Card / Logic App field passthrough
The workflow's approval-request body adds `plan_url` and `plan_summary`
fields to the existing schema. The mock-bot ignores unknown fields
gracefully, so smoke tests work. But the production Logic App + Adaptive
Card template (in `mission-control-shared/`) will silently drop the
fields until updated to reference them. Update target: a card that shows
the truncated summary inline plus a "View full plan" button linking to
`plan_url`.

### 3. No memory yet
Both agents are stateless across queries. Memory re-enable is gated on
kagent v0.8.4+ (per `HANDOVER-2026-05-05.md`). Once that lands, Knowledge
Concierge can remember previously-asked questions per session, and
Incident Commander can ground synthesis on past incidents from a real
store rather than the `[DEMO MOCK]` similar-incidents stub.

### 4. Specialist agent quality varies
The fan-out demo quality depends on which specialists you target. Empty or
low-quality responses from a specialist still show up in the synthesis
prompt — the synthesis agent will surface that as `_(no output)_` in
**Evidence**. For polished demos, target agents whose namespaces actually
match the alert (e.g. `kube-system-agent` + `flux-system-agent` for a pod
crash; `cert-manager-agent` + `external-secrets-agent` for a TLS issue).

---

## Reference: critical files re-used (don't re-invent)

| Concern | Source |
|---|---|
| A2A call template | `aks-mgmt-stack/holmes-argoworkflows/kagent-sre-workflow.yaml:151-304` |
| GitLab issue create / Mattermost notify | same file: `:307-610` |
| HITL suspend + resume | `ai-platform/teams-hitl/mock-bot/test-approval-workflow.yaml` |
| Agent CRD shape | `kagent-triage/kro-agent.yaml` |
| Specialist agent metadata names | `kagent-triage/aks/*.yaml` (verified — istio agents have `aks-` prefix) |
| Doc corpus | `kagent-triage/docs/*.md` (13 files, 32K words) |

---

## Next steps (roadmap-aligned)

1. **Apply to `{{CLUSTER_NAME}}` cluster** when authorised — five `kubectl apply`
   commands plus the corpus build.
2. **Run both demo flows** end-to-end and capture screenshots / asciinema
   for the slide deck.
3. **Sensor extension for rejection path** (~15-line diff) once a real
   demo of the rejection branch is needed.
4. **Logic App / Adaptive Card update** to surface `plan_url` +
   `plan_summary` once production HITL is wired in.
5. **Memory re-enable** once kagent v0.8.4+ ships — at which point both
   agents become net-better with persistent context.

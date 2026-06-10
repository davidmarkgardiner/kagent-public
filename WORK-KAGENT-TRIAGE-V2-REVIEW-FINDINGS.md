# Kagent Triage System v2 — Review Findings

Reviewer pass date: 2026-06-04. Scope: the 20 docs and implementation paths listed in
`WORK-KAGENT-TRIAGE-V2-REVIEW-PROMPT.md`. This is a read-only design/claims review. No
clusters were mutated, no MRs created, no new features built. Output is analysis plus a
prioritized checklist, per the prompt. File:line references point at the current tree.

---

## 1. Executive verdict

**Ready with gaps.**

v2 is a coherent step from "isolated specialists" to a connected AI-SRE posture. The
architecture hangs together: alert → deterministic Argo workflow → specialist fan-out →
commander synthesis → eval, with memory/A2A context threaded through. The safety model is
the strongest part of the package — production chaos is blocked at four independent layers
and read-only specialists are kept tool-less in the demo.

The gap is between what is *wired and earned live* and what is *contracted via hardcoded
markers*. Several headline capabilities — HITL enforcement, Grafana evidence, GitLab
remediation, knowledge-base citations, chaos-driven specialist fan-out — are currently
demonstrated by synthetic markers emitted unconditionally by workflow templates, not by
live backend calls. The execution-review docs are honest about this, but the top-level
`README.md` and a couple of handoff files state these as delivered v2 capabilities without
the caveat at the point of claim. Before handing to colleagues, close the labeling gap and
wire (or clearly mark as "pattern, not proven") the four synthetic paths. None of this is a
redesign — it is consolidation and honest relabeling.

---

## 2. What we have done

| Capability | Status | Repo evidence |
|---|---|---|
| Specialist fan-out + commander synthesis | Built, home-lab proven | `SMART-TRIAGE-FANOUT-WORK-HANDOFF.md` (9-specialist contract); `SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md` (workflow `smart-triage-alert-b8gkz`, 14/14 nodes, `INCIDENT_SYNTHESIS: completed`); `a2a/smart-triage-fanout-demo/agents.yaml` (specialists + commander as Agent CRs) |
| Alert ingestion + duplicate suppression | Built, live | `SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md` (two replays same fingerprint → `SMART_TRIAGE_DEDUP: suppressed`); `k8s/observability/k-agent-alert-triage-sensor.yaml` |
| A2A context + curator-only memory | Built, live | `a2a/platform-memory-showcase-demo/agents.yaml` (seeder has `create_entities/relations/add_observations`; triage agent only `search_nodes/open_nodes/read_graph`); markers `MEMORY_WRITE: stored`, `MEMORY_LOOKUP: hit`, `A2A_CONTEXT_REUSED: yes` |
| HITL suspend/resume plumbing | Built (Argo), not wired to bot | `platform/teams-hitl/sensor.yaml` (approve/reject/expire Sensors); `a2a/smart-triage-fanout-demo/workflow.yaml:660` |
| Grafana MCP evidence (read-only/on-demand) | Built (read-only tool set), invoked on-demand | `agents/grafana-evidence-agent/agent.yaml` (`list_datasources, search_dashboards, query_prometheus, query_loki_logs, generate_deeplink`); alert-triggered via sensor, not continuous |
| GitLab MCP remediation path | Built (write-capable agent + lite shim) | `a2a/smart-triage-fanout-demo/gitlab-mcp-agent.yaml`, `gitlab-lite-agent.yaml`, `gitlab-mcp-remotemcpserver.yaml` (`url: https://gitlab.com/api/v4/mcp`) |
| Knowledge base contract (citations + no-docs fallback) | Contract only, synthetic proof | `a2a/smart-triage-fanout-demo/agents.yaml:260,267,269,271` (`NO_RELEVANT_DOCS`, `CITATIONS:`, hardcoded) |
| Lifecycle evals + hard gates | Built | `observability/agent-evals/scripts/score-lifecycle-run.py` (hard gates: mutation-before-HITL, verification-missing, ticket-missing, wrong-namespace); golden cases `pod-crashloop-hitl-remediation.yaml`, `chaos-pod-delete.yaml` |
| Reporting: operator + management views | Built | `observability/agent-evals/grafana/agent-eval-scorecard-dashboard.json` (operator); `kagent-fleet-overview-dashboard.json` (management); `fleet-exporter/exporter.py` reads live K8s API |
| Chaos test manager (process skeleton) | Built as skeleton, lower-env injection proven once | `platform/argo-workflows/templates/chaos-test-lifecycle.yaml`; `WORK-CHAOS-TEST-MANAGER-EXECUTION-REVIEW.md`; `WORK-CHAOS-TEST-MANAGER-LIVE-EVIDENCE.md` (one live `chaos-demo-pod-delete`, `EVAL_SCORE: 1.0`) |
| Production-chaos safety (4 layers) | Built, enforced | schema enum (dev/test/staging only); `chaos/reliability/scripts/validate-reliability-configs.py:40`; `infra/byo-kagent/kyverno-policies/validate-chaos-test-safety.yaml:17` (`Enforce`), `:42-45` (prod block); `chaos-test-lifecycle.yaml:234-235` runtime guard |

---

## 3. Gap analysis (ranked by risk)

### HIGH

**G1 — HITL gate does not actually block in the demo workflow.**
`a2a/smart-triage-fanout-demo/workflow.yaml:660` and `:739` (and `workflow-template.yaml:640,718`)
emit `HITL_STATUS: resumed` unconditionally; the Teams bot endpoint/contact-point placeholders
are unresolved and the `request-approval`/`wait-for-approval` templates from
`platform/teams-hitl/` are not called in the fan-out DAG. The Argo suspend/resume machinery and
the eval hard gate (`score-lifecycle-run.py`, mutation-before-HITL) exist, but in the shipped
demo nothing waits for a human. *Why it matters:* "approval-gated remediation" is the central
safety claim; right now it is asserted, not enforced. *Small fix:* wire the existing approval
templates into the DAG, or add a loud `# DEMO: HITL synthesized` banner at those lines and state
in README that live blocking is work-side only.

**G2 — GitLab write isolation is prompt-only, not infrastructure-enforced.**
`gitlab-mcp-remotemcpserver.yaml` points at `https://gitlab.com/api/v4/mcp` with a single Secret
token; the "sandbox project only" constraint lives in the agent system message
(`gitlab-mcp-agent.yaml`), not in token scope or RBAC. *Why it matters:* a write-capable token
with org-wide scope behind a prompt is a real blast-radius risk if lifted to work as-is. *Small
fix:* document a dedicated sandbox project + project-scoped token as a required precondition, and
state explicitly that the public demo's isolation is prompt-level only.

**G3 — Knowledge base (doc2vec/querydoc) never actually ran.**
`agents.yaml:269` `CITATIONS: docs/platform-kb/runbooks/checkout-api-crashloop.md#chunk-1` and
`:271` `NO_RELEVANT_DOCS_CASE: validated` are hardcoded by a synthetic specialist. The citation
contract and no-docs fallback are well specified (`:260`) but unproven against a live index.
*Why it matters:* "cited runbook retrieval" is sold as a v2 capability. *Small fix:* either run
one real querydoc retrieval in home-lab (one cited hit + one out-of-corpus `NO_RELEVANT_DOCS`)
or relabel as "contract defined, retrieval not yet proven."

**G4 — chaos-test-lifecycle emits synthetic specialist/Grafana markers; fan-out is not wired
into the chaos loop.** `chaos-test-lifecycle.yaml:414-417` hardcodes `SPECIALIST_KUBERNETES/
NETWORK/GRAFANA/GITOPS: completed` and `:423` hardcodes `GRAFANA_EVIDENCE: ...`. The template
calls `agent-lifecycle-eval` but never invokes the 8-specialist fan-out. Yet
`WORK-CHAOS-TEST-MANAGER-LIVE-EVIDENCE.md:112-117` presents `SPECIALIST_*: completed` as
observed. *Why it matters:* it reads as "chaos triggered full triage fan-out," which did not
happen. *Small fix:* mark these markers synthetic in the template comment and in the live-evidence
doc, or add a step that actually calls the fan-out workflow with the ChaosResult as input.

### MEDIUM

**G5 — Eval does not gate ticket closure.** `KAGENT-EVAL-LIFT-AND-SHIFT-HANDOFF.md` specifies
making ticket closure conditional on eval pass/fail; the demo workflow collects the score but has
no conditional DAG routing on it. *Fix:* add pass/fail branch after the eval task (defer if it
needs a real ticketing backend).

**G6 — Native memory (PostgreSQL + pgvector) is blueprinted, not run.**
`WORK-MEMORY-KB-NEXT-HANDOFF-README.md` lists the config and the restart-survival test as
*requirements*; no home-lab execution evidence exists. The doc itself says do not claim complete
until recall survives a controller restart — that line should be surfaced in any status summary.

**G7 — Review-manager below-threshold routing never exercised.** The only live chaos run scored
`EVAL_SCORE: 1.0`, so the score < threshold branch into `agents/review-manager/` never fired.
*Fix:* add one deliberately-failing case to prove the routing.

### LOW

**G8 — assorted hygiene:** dedup ConfigMap cleanup/TTL undefined; synthetic memory-record
retention item left unchecked in `A2A-DEMO-EXECUTION-REVIEW.md`; HITL approval identity schema not
standardized (`Resumed by: kubernetes-admin` only); alert payload schema not validated in the
normalize step; `fleet-exporter/exporter.py` hardcodes the workflow-name allowlist; eval README
conflates Phase-1 (hand-written samples) with Phase-2 (audit-log/OTel population) input sources.

---

## 4. Overstated or unclear claims

| Claim (exact) | Where | Why risky | Safer wording / required evidence |
|---|---|---|---|
| "Grafana integration — agents can pull observability evidence" | `README.md:30` | Public proof is a synthetic Grafana marker; live MCP read not demonstrated in the main demo | "Grafana MCP pattern (read-only) — wired in agent config; live evidence is work-side" |
| "GitLab MCP integration — agents can interact with GitLab workflows" | `README.md:31` | Isolation is prompt-only; only the lite shim ran in public | "GitLab MCP remediation pattern — requires a sandbox project + scoped token; isolation is prompt-level in the public demo" |
| "Chaos-driven validation — controlled failure scenarios can prove the system can detect, triage…" | `README.md:35` | The chaos run did not invoke the triage fan-out; specialist markers were synthetic | "Chaos injection proven in lower-env (pod-delete); specialist fan-out from chaos is not yet wired" |
| HITL "blocks non-read-only until approval" | `KAGENT-EVAL-LIFT-AND-SHIFT-HANDOFF.md` + README:32 | Demo workflow hardcodes `HITL_STATUS: resumed` (`workflow.yaml:660`) | "HITL hard-gate logic exists in the eval; live blocking not wired into the demo workflow" |
| `SPECIALIST_KUBERNETES/NETWORK/GRAFANA/GITOPS: completed` presented as observed | `WORK-CHAOS-TEST-MANAGER-LIVE-EVIDENCE.md:112-117` | Hardcoded in `chaos-test-lifecycle.yaml:414-417`, not earned | Label these markers "synthetic (template-emitted)" in the evidence doc |
| `CITATIONS:` / `NO_RELEVANT_DOCS_CASE: validated` | `SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md` (from `agents.yaml:269,271`) | Synthetic; no live KB retrieval | "KB contract demonstrated with synthetic markers; live querydoc retrieval pending" |

The README's use of "can" is partially hedged, but the bullets sit under a "this iteration
evolves it into…" framing that a skimming reader takes as delivered. The fix is a one-line caveat
per synthetic capability, not a rewrite.

---

## 5. Local improvement checklist

Tag legend: **[M]** must-fix before handoff · **[S]** should-fix · **[D]** defer (feature work).

- **[M]** Wire the existing `request-approval`/`wait-for-approval` templates into the fan-out DAG,
  OR annotate `workflow.yaml:660/739` + README that HITL blocking is synthesized in the demo. (G1)
- **[M]** Document the GitLab sandbox-project + scoped-token precondition; state public isolation
  is prompt-only. (G2)
- **[M]** Relabel synthetic Grafana/GitLab/chaos-fan-out/KB claims in `README.md:30-35` and the two
  live-evidence docs so synthetic ≠ proven. (G3, G4, §4)
- **[M]** Add a "synthetic (template-emitted)" note above `chaos-test-lifecycle.yaml:414-423` and in
  `WORK-CHAOS-TEST-MANAGER-LIVE-EVIDENCE.md:112-117`. (G4)
- **[S]** Run one real home-lab querydoc retrieval (one cited hit + one `NO_RELEVANT_DOCS`) and
  capture it, or mark the KB path "contract-only" in the handoff. (G3)
- **[S]** Add one deliberately-failing lifecycle case to exercise review-manager routing. (G7)
- **[S]** Define dedup ConfigMap TTL/cleanup and synthetic-memory retention policy. (G8)
- **[S]** Standardize an HITL approval-identity field and an alert-payload schema check. (G8)
- **[S]** Make `fleet-exporter` workflow allowlist configurable; split eval README Phase-1 vs
  Phase-2 input sources explicitly. (G8)
- **[S]** Adopt one `EVIDENCE_TIER: home-lab|interim|work` marker convention across evidence docs.
- **[D]** Native PostgreSQL+pgvector memory with restart-survival proof. (G6)
- **[D]** Eval-gated ticket closure against a real ticketing backend. (G5)
- **[D]** Fleet selection / randomized multi-cluster chaos scheduling.
- **[D]** Production game-day chaos, node/network Litmus experiments, custom CRDs.

---

## 6. Work replication checklist (draft — high level only)

Not implementation instructions. A future work-side agent/engineer would need to:

1. Replace every public synthetic specialist with an approved live backend (Grafana, Hubble/
   network, deployment-state, policy, trace) while keeping the same marker contract.
2. Stand up a real knowledge index (doc2vec/querydoc) and prove a cited answer + a
   `NO_RELEVANT_DOCS` case before trusting knowledge output.
3. Provision a dedicated GitLab sandbox project and a project-scoped token; never reuse an
   org-wide token.
4. Wire HITL through the approved front door (Teams/Argo/Git approval) so remediation actually
   suspends until approval, and capture an approval-identity record.
5. Bind real read-only tools to specialists with restrictive `toolNames`; confirm no
   apply/patch/delete/exec leaks via the existing validation commands.
6. Install Kyverno on the target cluster so the production-chaos admission block is live (it was
   skipped on the Proxmox target).
7. Provision native memory (PostgreSQL+pgvector) and prove recall survives a controller restart
   before claiming durable memory.
8. Confirm agentgateway metric/label names against the live `/metrics` endpoint before trusting
   alerts and dashboards.
9. Re-run the full chaos loop end-to-end (GitOps MR → HITL resume → reporting → review-manager
   routing) — the public run stopped after injection + eval.

---

## 7. Final recommendation

Smallest set of changes to make this credible for SRE + platform engineering:

1. **Honest relabeling (half a day).** Add a one-line caveat at each synthetic capability in
   `README.md:30-35`, and mark the synthetic markers in `chaos-test-lifecycle.yaml:414-423` and the
   two live-evidence docs. This alone removes the biggest credibility risk.
2. **HITL truth (G1).** Either wire the approval templates into the demo DAG or clearly state the
   demo synthesizes HITL and live blocking is work-side. Do not ship "approval-gated" as proven
   while `HITL_STATUS: resumed` is hardcoded.
3. **GitLab precondition (G2).** One paragraph: sandbox project + scoped token required; public
   isolation is prompt-only.
4. **One real KB retrieval (G3)** if time allows, else relabel as contract-only.

Everything else (native memory, ticket-gating, fleet scheduling, production game-day) is genuine
feature work and should be explicitly deferred, not partially claimed. The skeleton and the
four-layer safety model are solid; the work to finish is consolidation and honesty about the
synthetic/live boundary, not architecture.

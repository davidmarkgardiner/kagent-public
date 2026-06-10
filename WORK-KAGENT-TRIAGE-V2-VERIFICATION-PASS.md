# Work Kagent Triage V2 Verification Pass

Date: 2026-06-04

Purpose: capture the current home-lab/local readiness state after the review
findings and consolidation pass. This is the answer to "where are we in the
flow, what is left locally, and what is left for the work agent?"

No clusters were mutated during this pass. The proof board was rendered through
a local HTTP server and captured with Playwright.

## Executive Readiness Verdict

**Ready for local prioritization; not yet final work handoff.**

The package now has a clear v2 story, honest proof tiers, a visual proof board,
Grafana metric coverage including BYO governance starter panels, and a
prioritized work-agent checklist. The remaining local question is whether to
turn the highest-value contracts into proofs before handoff: querydoc KB proof,
below-threshold review-manager routing, and deeper HITL/backend wiring.

## Capability Status

| Capability | Status | Current evidence | Next action |
|---|---|---|---|
| Smart triage fan-out | PROVEN | `SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md` | Keep as core demo proof |
| Grafana MCP evidence | CONTRACT | Read-only evidence-agent/docs exist; chaos loop uses synthetic marker | Prove live Grafana MCP query in target work lab, or run home-lab query if available |
| GitLab MCP sandbox/GitOps remediation | CONTRACT | Sandbox pattern and safety docs exist; work auth must be scoped | Work agent must use dedicated sandbox project and scoped token |
| HITL suspend/resume | PARTIAL | Smart-triage has a real suspend node; standalone mock workflow lints; live callback proof pending | Work agent must prove Teams/mock/curl callback path |
| Memory and A2A context | PROVEN | `a2a/platform-memory-showcase-demo/` and memory handoff | Work lab must prove durable backend separately |
| doc2vec/querydoc KB retrieval | PARTIAL | Static querydoc package validates; live query blocked by missing embedding key | Run with approved key locally or in work lab |
| Lifecycle eval and hard gates | PROVEN | `observability/agent-evals/`, lifecycle cases, score outputs | Keep wired into every demo/report |
| Chaos test manager lower-env run | PROVEN | `WORK-CHAOS-TEST-MANAGER-LIVE-EVIDENCE.md` | Keep synthetic fan-out caveat visible |
| Review-manager below-threshold routing | PROVEN | Below-threshold sample scores `0.575`, fails hard gates, and has a review-manager finding | Replicate with real work evidence |
| Grafana/Alloy dashboard metric coverage | PROVEN | Fleet dashboard JSON now includes core + BYO governance panels | Work agent must wire collectors/live metrics |
| BYO-agent onboarding with ToolGrant/ToolCatalogEntry | PARTIAL | One-folder demo renders Agent and ToolGrant manifests and verifies no delete/exec tools | Work agent must run live onboarding proof |
| SRE first-contact app onboarding demo | PROVEN_STATIC | One-folder demo validates SRE prompts, app profile, failure modes, BYO agents, chaos contract, and eval contract | Work agent must run live work-lab version end to end |
| BYO-agent chaos/remediation safety | CONTRACT | Policy model exists; live BYO remediation proof pending | Work agent must prove read/write separation and HITL |

## Local Work Completed In This Pass

- Reframed the package around Kagent triage system v2, not a holiday/autonomous
  handoff.
- Added `WORK-KAGENT-TRIAGE-V2-REVIEW-PROMPT.md`.
- Captured external-style findings in
  `WORK-KAGENT-TRIAGE-V2-REVIEW-FINDINGS.md`.
- Applied must-fix caveats for synthetic vs live evidence.
- Added `WORK-KAGENT-TRIAGE-V2-COMPLETION-CHECKLIST.md`.
- Added `WORK-KAGENT-TRIAGE-V2-FRONT-SHEET.md`.
- Added `WORK-KAGENT-TRIAGE-V2-PROOF-BOARD.html`.
- Added `WORK-KAGENT-TRIAGE-V2-SRE-OPERATING-GUIDE.md`.
- Added `WORK-KAGENT-TRIAGE-V2-SRE-WORKFLOW.html`.
- Added `WORK-KAGENT-TRIAGE-V2-SRE-FIRST-CONTACT.html`.
- Added `demos/sre-first-contact/` with SRE intake prompts, app profile,
  failure modes, BYO agent requests, expected manifests, chaos test, eval
  evidence contract, and verifier.
- Added `WORK-KAGENT-TRIAGE-V2-WORK-AGENT-CHECKLIST.md`.
- Added `WORK-KAGENT-TRIAGE-V2-WORK-AGENT-START-PROMPT.md`.
- Added `scripts/verify-kagent-triage-v2-handoff.sh`.
- Added BYO governance panels to
  `observability/agent-evals/grafana/kagent-fleet-overview-dashboard.json`.
- Updated `observability/agent-evals/FLEET-DASHBOARD.md` with BYO governance
  metric contracts.
- Added a deliberately failing `chaos-pod-delete` lifecycle sample and generated
  scorer output to prove below-threshold review-manager routing.
- Ran static doc2vec/querydoc validation and recorded the embedding-key blocker
  in `WORK-KAGENT-TRIAGE-V2-KB-QUERYDOC-PROOF.md`.
- Added `demos/byo-agent-showcase/` with request files, expected Agent and
  ToolGrant manifests, and dry-run verification scripts.
- Validated HITL YAML and offline-linted the standalone mock approval workflow;
  details in `WORK-KAGENT-TRIAGE-V2-HITL-PROOF.md`.

## Visual Verification

Rendered:

```text
http://127.0.0.1:8765/WORK-KAGENT-TRIAGE-V2-PROOF-BOARD.html
```

Screenshot:

```text
output/playwright/kagent-triage-v2-proof-board.png
```

Result: visual layout is readable at desktop size. The proof-tier, Grafana
coverage, SRE workflow, and BYO-agent integration sections fit without obvious
overlap.

## Current Priority Board

| Priority | Item | Owner | Status |
|---|---|---|---|
| P0 | Current-state review and caveat fixes | local | Done |
| P0 | Completion checklist | local | Done |
| P0 | Work-agent checklist | local | Done |
| P0 | Proof board visual | local | Done |
| P0 | Grafana dashboard includes BYO governance starter panels | local | Done |
| P1 | Real querydoc cited-hit + `NO_RELEVANT_DOCS` proof | local or work | Blocked locally by missing embedding key |
| P1 | Below-threshold eval/review-manager routing proof | local | Done |
| P1 | One-command BYO-agent demo folder | local | Done |
| P1 | First-contact SRE onboarding demo | local | Done |
| P1 | HITL mock workflow lint/proof contract | local | Done |
| P2 | Native Postgres/pgvector memory restart proof | work | Defer |
| P2 | Fleet/randomized chaos scheduling | work/future | Defer |
| P2 | Production game-day chaos | work/future | Defer |

## What Is Left For The Work Agent

The work agent should not rediscover the architecture. It should follow
`WORK-KAGENT-TRIAGE-V2-WORK-AGENT-CHECKLIST.md` and prove the same package
against approved work backends.

Minimum work-agent proof:

1. Runtime inventory.
2. Model path.
3. Smart triage fan-out.
4. HITL.
5. Grafana MCP.
6. Eval.
7. One lower-env chaos/regression run.
8. One first-contact app onboarding demo.
9. Safety check for tools and GitLab writes.
10. One report/dashboard artifact.

Strongly preferred work-agent proof:

1. doc2vec/querydoc cited hit and no-docs fallback.
2. Shared memory recall with curator-mediated writes.
3. BYO read-only triage agent onboarding.
4. BYO bounded remediation agent dry-run or live non-prod proof.
5. ToolGrant/policy denial proof.
6. Review-manager below-threshold routing.

## If Time Runs Short Locally

Stop after the P0 items already completed and hand over with the known caveats.
The highest-value optional local proof would be querydoc, because it removes one
of the most visible "synthetic citation" caveats from the review findings.

## BYO-Agent Demo Proof

Generated by:

```bash
bash demos/byo-agent-showcase/scripts/verify-demo.sh
bash demos/byo-agent-showcase/scripts/run-demo.sh --dry-run
```

Result:

```text
FORBIDDEN_TOOLS_ABSENT: yes
KUSTOMIZE_RENDERED: yes
BYO_AGENT_SHOWCASE_VERIFY: passed
BYO_DEMO_MODE: dry-run
BYO_AGENT_RENDERED: yes
```

## SRE First-Contact Demo Proof

Generated by:

```bash
bash demos/sre-first-contact/scripts/verify-demo.sh
```

Result:

```text
SRE_FIRST_CONTACT_YAML_OK: yes
RELIABILITY_CONFIG_VALID: yes checked=1
FORBIDDEN_TOOLS_ABSENT: yes
EVIDENCE_CONTRACT_READY: yes
SRE_FIRST_CONTACT_VERIFY: passed
```

## Local Handoff Verifier

Generated by:

```bash
scripts/verify-kagent-triage-v2-handoff.sh
```

Result:

```text
PASS Kagent triage v2 handoff package is locally consistent
NEXT: work agent must still prove live work-lab Grafana MCP, GitLab MCP,
querydoc, A2A, HITL, chaos, eval, and reporting evidence.
```

## Review-Manager Proof

Generated by:

```bash
PYTHONPATH=observability/agent-evals/scripts \
python3 observability/agent-evals/scripts/score-lifecycle-run.py \
  --case observability/agent-evals/lifecycle-cases/chaos-pod-delete.yaml \
  --run observability/agent-evals/results/sample/lifecycle/chaos-pod-delete-below-threshold.lifecycle-run.json \
  --output-dir observability/agent-evals/results/sample/lifecycle
```

Output:

```text
score=0.575 passed=false
```

Artifacts:

- `observability/agent-evals/results/sample/lifecycle/chaos-pod-delete-below-threshold.lifecycle-run.json`
- `observability/agent-evals/results/sample/lifecycle/chaos-pod-delete.sample-chaos-pod-delete-below-threshold.json`
- `observability/agent-evals/results/sample/lifecycle/chaos-pod-delete.sample-chaos-pod-delete-below-threshold.md`
- `chaos/reliability/reports/sample/review-manager-chaos-pod-delete-below-threshold.md`

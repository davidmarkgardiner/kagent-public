# Work Kagent Triage V2 Completion Checklist

Purpose: define what "done" means for the Kagent triage system v2 package
before it is handed to SRE and platform engineering colleagues. This checklist
turns the review findings into completion gates: verified work, visual proof,
Grafana metrics, SRE workflows, and BYO-agent integration.

This is still local consolidation. Work-cluster replication comes later.

## Target Outcome

Kagent triage system v2 should be credible when we can show:

1. What changed from v1 namespace specialists to v2 connected triage.
2. Which parts are proven locally/home-lab, which are skeleton contracts, and
   which need work-lab proof.
3. How an agent or engineer verifies the work is complete.
4. Presentation-ready HTML visuals for stakeholders and our own understanding.
5. Grafana dashboard coverage for the metrics SRE and management will need.
6. SRE workflows for controlled failure injection, triage, eval, reporting, and
   review-manager follow-up.
7. A BYO-agent path so teams can safely bring their own agents, tools, memory,
   and chaos/remediation tests into the shared v2 system.

## Completion Gates

| Gate | Done when | Evidence/artifact |
|---|---|---|
| Current-state review | Opus/review findings are captured and must-fix relabeling is applied | `WORK-KAGENT-TRIAGE-V2-REVIEW-FINDINGS.md`, README caveats |
| Verification agent pass | A fresh agent can read the repo and classify each v2 capability as `proven`, `contract`, `blocked`, or `defer` | `WORK-KAGENT-TRIAGE-V2-VERIFICATION-PASS.md` |
| Local handoff verifier | Human or work agent can run one command to validate the local/static handoff package before work-lab proof | `scripts/verify-kagent-triage-v2-handoff.sh` |
| HTML proof board | One static HTML artifact explains v1 -> v2, proof tiers, dashboards, SRE flows, and BYOA | `WORK-KAGENT-TRIAGE-V2-PROOF-BOARD.html` |
| Presentation entry points | Existing HTML demos are discoverable from README and portal | `index.html`, `WORK-STAKEHOLDER-DEMO-RUNBOOK.html`, `SMART-TRIAGE-FANOUT-PRESENTER.html` |
| Grafana metrics | Required metric families are listed and mapped to dashboards/collectors | This checklist, `observability/agent-evals/FLEET-DASHBOARD.md` |
| SRE chaos workflow | SRE can request a lower-env failure test and understand approval, injection, triage, eval, report, and review flow | `WORK-CHAOS-TEST-MANAGER-PLAN.md`, `chaos/reliability/LIVE-RUNBOOK.md` |
| BYOA workflow | Team-owned agents can be onboarded with ToolCatalogEntry, ToolGrant, policy, ModelConfig, memory, and A2A skills | `infra/byo-kagent/README.md`, `infra/byo-kagent/SHOWCASE-DEMO.md` |
| Safety | Direct mutation, broad GitLab writes, production chaos, and uncurated memory writes are blocked or explicitly marked unproven | schemas, Kyverno policies, docs caveats |

## Priority Board

Use this when time is short.

| Priority | Item | Why it matters |
|---|---|---|
| P0 | Visual proof board browser-verified | Gives a clear stakeholder and self-orientation surface |
| P0 | Verification-agent pass completed | Confirms another agent can classify proven vs contract vs blocked |
| P0 | Grafana dashboard JSON covers core triage/eval and BYO-governance panels | SRE needs one place to inspect readiness, scores, HITL, failures, and tool safety |
| P0 | Work-agent checklist exists | Lets the work-side agent replicate in priority order |
| P1 | Real querydoc cited hit plus `NO_RELEVANT_DOCS` proof | Turns KB from contract to proven; static package validates, live query needs embedding key |
| P0 | Below-threshold eval/review-manager proof | Proves weak runs route to follow-up |
| P1 | BYO-agent one-command demo folder | Makes SRE/team onboarding easier; dry-run local verification passes |
| P1 | HITL mock workflow proof contract | Separates real suspend, mock callback, and full Teams proof |
| P2 | Native Postgres memory restart proof | Larger work-lab hardening item |
| P2 | Fleet/randomized chaos scheduling | Feature work beyond local consolidation |

## Verification Agent Prompt

Use this after local fixes. It is a verification prompt, not an implementation
prompt.

```text
You are verifying whether the Kagent triage system v2 package is complete enough
for SRE/platform-engineering review.

Do not mutate clusters. Do not create GitLab MRs. Do not add new features.

Read:
- README.md
- WORK-KAGENT-TRIAGE-V2-REVIEW-FINDINGS.md
- WORK-KAGENT-TRIAGE-V2-COMPLETION-CHECKLIST.md
- WORK-KAGENT-TRIAGE-V2-PROOF-BOARD.html
- WORK-ZIP-AGENT-HANDOFF.md
- SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md
- WORK-CHAOS-TEST-MANAGER-LIVE-EVIDENCE.md
- observability/agent-evals/FLEET-DASHBOARD.md
- observability/chaos-test-manager/alloy/chaos-test-lifecycle.alloy
- infra/byo-kagent/README.md
- infra/byo-kagent/SHOWCASE-DEMO.md

For each capability, return one status:
- PROVEN: live/local evidence exists in this repo.
- CONTRACT: schema/workflow/marker exists, but live backend proof is pending.
- BLOCKED: required file, metric, policy, or workflow is missing.
- DEFER: valid future work beyond the current consolidation pass.

Capabilities:
1. Smart triage fan-out.
2. Grafana MCP evidence.
3. GitLab MCP sandbox/GitOps remediation.
4. HITL suspend/resume.
5. Memory and A2A context.
6. doc2vec/querydoc KB retrieval.
7. Lifecycle eval and hard gates.
8. Chaos test manager lower-env run.
9. Review-manager below-threshold routing.
10. Grafana/Alloy dashboard metric coverage.
11. BYO-agent onboarding with ToolGrant/ToolCatalogEntry.
12. BYO-agent chaos/remediation safety.

Return:
- Executive readiness verdict.
- Capability status table.
- Missing proof list.
- Files that need local edits before colleague handoff.
- Work-lab-only proof items.
```

## HTML Visualization Set

| Visual | Purpose | Status |
|---|---|---|
| `WORK-KAGENT-TRIAGE-V2-WORK-IMPLEMENTATION-CHECKLIST.html` | Interactive work-machine checkbox checklist prioritized for doc2vec/querydoc KB, A2A, GitLab MCP, Grafana MCP, and the remaining V2 proof queue | New |
| `WORK-KAGENT-TRIAGE-V2-PROOF-BOARD.html` | One-page proof board for v1 -> v2, proof tiers, SRE workflows, dashboards, BYOA | New |
| `output/playwright/kagent-triage-v2-work-implementation-checklist.png` | Playwright full-page screenshot of the implementation checklist | New |
| `output/playwright/kagent-triage-v2-proof-board.png` | Playwright full-page screenshot of the proof board | New |
| `index.html` | Static portal for all iteration artifacts | Existing, linked |
| `WORK-STAKEHOLDER-DEMO-RUNBOOK.html` | Stakeholder presentation/demo runbook | Existing |
| `SMART-TRIAGE-FANOUT-PRESENTER.html` | Smart-triage fan-out explainer | Existing |
| `docs/ai-grafana/iteration-review-chaos-agent-demo.html` | Chaos/Grafana agent review demo | Existing |
| `docs/ai-grafana/chaos-grafana-triage-dashboard.html` | Chaos triage visualization | Existing |
| `observability/agent-evals/agent-eval-scorecard-demo.html` | Eval scorecard walkthrough | Existing |
| `observability/chaos-test-manager/chaos-test-lifecycle-live.html` | Static live-run chaos lifecycle board | Existing |

## Grafana Metric Coverage

The fleet dashboard already defines the core score and incident metric contract
in `observability/agent-evals/FLEET-DASHBOARD.md`. For the complete v2 story,
Grafana should cover these families.

### Core Agent Inventory

```prometheus
kagent_agent_info{cluster,namespace,agent,role,capability,env_tier} 1
kagent_agent_ready{cluster,namespace,agent,role,capability,env_tier} 0|1
```

### Incident Funnel And HITL

```prometheus
kagent_incident_received_total{cluster,namespace,agent,workflow_name,run_id,failure_mode,env_tier}
kagent_incident_triaged_total{cluster,namespace,agent,workflow_name,run_id,failure_mode,env_tier}
kagent_remediation_attempted_total{cluster,namespace,agent,workflow_name,run_id,failure_mode,env_tier}
kagent_remediation_verified_total{cluster,namespace,agent,workflow_name,run_id,failure_mode,env_tier}
kagent_hitl_pending{cluster,namespace,workflow_name,run_id,approval_type,env_tier}
```

### Scores And Hard Gates

```prometheus
agent_eval_score{cluster,namespace,agent,case_id,run_id,env_tier}
agent_eval_hard_failures{cluster,namespace,agent,case_id,run_id,env_tier}
agent_lifecycle_eval_score{cluster,namespace,agent,case_id,run_id,workflow_name,env_tier}
agent_lifecycle_eval_passed{cluster,namespace,agent,case_id,run_id,workflow_name,env_tier}
agent_lifecycle_eval_hard_failures{cluster,namespace,agent,case_id,run_id,workflow_name,env_tier}
```

### Chaos/Test Manager

```prometheus
kagent_chaos_test_started_total{cluster,namespace,suite,test,failure_mode,env_tier}
kagent_chaos_test_completed_total{cluster,namespace,suite,test,failure_mode,verdict,env_tier}
kagent_chaos_test_recovery_seconds{cluster,namespace,suite,test,workload,env_tier}
kagent_chaos_review_manager_triggered_total{cluster,namespace,suite,test,reason,env_tier}
```

Source options: lifecycle proof markers, Litmus `ChaosResult`, Argo Workflow
labels, and the existing Alloy snippet in
`observability/chaos-test-manager/alloy/chaos-test-lifecycle.alloy`.

### BYO-Agent / Tool Safety

```prometheus
kagent_byo_agent_request_total{cluster,team,namespace,status}
kagent_toolcatalogentry_verified{cluster,tool,version,verified_by} 0|1
kagent_toolgrant_info{cluster,namespace,agent,tool_catalog_ref,expires_at} 1
kagent_toolgrant_expiring_total{cluster,namespace,agent,tool_catalog_ref}
kagent_agent_tool_denied_total{cluster,namespace,agent,tool,reason}
kagent_policy_violation_total{cluster,namespace,policy,resource_kind,reason}
```

Source options: ToolCatalogEntry/ToolGrant CRs, Kyverno PolicyReports, Agent
Gateway MCP authorization logs, and the BYO-kagent onboarding workflow.

## SRE Workflows To Show

### 1. Controlled Failure Request

```text
SRE asks: "Create a lower-env pod-delete failure for service X and prove the
agents detect and evaluate it."
  -> chaos-designer drafts ChaosTest
  -> policy validates namespace, labels, abort conditions, non-prod scope
  -> HITL approval
  -> GitOps syncs Litmus/Argo definition
  -> chaos-test-manager watches ChaosResult
  -> smart triage fan-out observes incident
  -> Grafana evidence and eval score are captured
  -> report generated
  -> score < 8 routes to review-manager
```

### 2. Bring Your Own Triage Agent

```text
Team submits BYO-agent request
  -> builder/orchestrator renders Agent + ToolGrant
  -> tool catalog verifies MCP tool version
  -> Kyverno blocks missing or dangerous grants
  -> Flux applies approved agent
  -> smoke test proves A2A skill and granted tools only
  -> Grafana inventory shows agent Ready and scored
```

### 3. Bring Your Own Remediation Agent

```text
Team requests bounded non-prod remediation agent
  -> remediation tools are separated from read-only triage tools
  -> HITL required before workflow or GitOps action
  -> policy blocks delete/exec/apply unless explicitly approved
  -> eval checks verification and ticket/report update
  -> memory write goes through curator path
```

## Local Gap Closure Order

1. Keep synthetic/live labels in place from the review findings.
2. Add or verify the HTML proof board.
3. Confirm the Grafana dashboard JSON contains panels for the metric families
   above, or document which panel/collector is pending.
4. Add one verification-agent pass using the prompt above.
5. Decide whether to run a real querydoc cited-hit and `NO_RELEVANT_DOCS` proof.
   Static validation is recorded in
   `WORK-KAGENT-TRIAGE-V2-KB-QUERYDOC-PROOF.md`; live query is blocked locally
   until an approved embedding key is supplied.
6. Below-threshold eval/review-manager routing is locally proven with
   `sample-chaos-pod-delete-below-threshold`.
7. Work-side replication checklist is now available at
   `WORK-KAGENT-TRIAGE-V2-WORK-AGENT-CHECKLIST.md`.
8. BYO-agent showcase folder is now available at `demos/byo-agent-showcase/`.
9. HITL proof status is recorded in
   `WORK-KAGENT-TRIAGE-V2-HITL-PROOF.md`.

# Kagent Triage System V2 Front Sheet

Date: 2026-06-04

Purpose: give the team a single starting point for the Kagent triage system v2
handoff. This page separates what is proven in the home lab, what is packaged
as a contract, and what must still be proven in an approved work lab before the
team treats the pattern as ready for broader use.

## Executive Position

Kagent triage v2 is no longer a single namespace debugging agent. It is now a
connected AI SRE workflow with specialist fan-out, observability evidence,
GitOps-aware remediation planning, HITL controls, lifecycle evaluation, shared
memory/context, KB retrieval, chaos-triggered validation, and BYO-agent
onboarding patterns.

The home-lab package is strong enough to use as a work-lab replication brief.
It is not a claim that work production is already wired. Work must still prove
the same contracts against approved work backends, identities, dashboards,
clusters, and GitLab/Grafana integrations.

## Start Here

Read these in order:

1. `WORK-KAGENT-TRIAGE-V2-VERIFICATION-PASS.md`
2. `WORK-KAGENT-TRIAGE-V2-PROOF-BOARD.html`
3. `WORK-KAGENT-TRIAGE-V2-WORK-AGENT-START-PROMPT.md`
4. `scripts/verify-kagent-triage-v2-handoff.sh`
5. `WORK-KAGENT-TRIAGE-V2-WORK-IMPLEMENTATION-CHECKLIST.html`
6. `WORK-KAGENT-TRIAGE-V2-WORK-AGENT-CHECKLIST.md`
7. `WORK-KAGENT-TRIAGE-V2-COMPLETION-CHECKLIST.md`
8. `WORK-KAGENT-TRIAGE-V2-SRE-OPERATING-GUIDE.md`
9. `WORK-KAGENT-TRIAGE-V2-ASTHERI-SRE-WALKTHROUGH.md`
10. `WORK-KAGENT-TRIAGE-V2-ASTHERI-SRE-REHEARSAL.md`
11. `WORK-KAGENT-TRIAGE-V2-SRE-WORKFLOW.html`
12. `WORK-KAGENT-TRIAGE-V2-SRE-FIRST-CONTACT.html`
13. `demos/sre-first-contact/README.md`
14. `WORK-KAGENT-TRIAGE-V2-HITL-PROOF.md`
15. `WORK-KAGENT-TRIAGE-V2-KB-QUERYDOC-PROOF.md`
16. `demos/kb-gitlab-mcp-update/README.md`
17. `demos/byo-agent-showcase/README.md`
18. `WORK-ZIP-AGENT-HANDOFF.md`

## What Is Proven In The Home Lab

| Area | Home-lab status | Evidence |
|---|---|---|
| Smart triage fan-out | PROVEN | Completed 14/14 workflow evidence and marker contract |
| Lifecycle eval | PROVEN | Passing and failing lifecycle samples with hard-gate output |
| Lower-env chaos run | PROVEN | Pod-delete chaos flow with recovery/eval evidence |
| Review-manager routing | PROVEN | Below-threshold score `0.575`, failed hard gates, review report |
| Grafana dashboard shape | PROVEN | Fleet dashboard JSON with core and BYO governance panels |
| BYO-agent packaging | PARTIAL/STATIC PROOF | One-folder demo renders Agent and ToolGrant manifests |
| HITL | PARTIAL | Real suspend pattern exists; mock approval workflow lints offline |
| Memory/A2A | PROVEN | A2A and memory showcase package exists |
| KB/querydoc | PARTIAL | Static package validates; live query waits on approved embedding key |
| KB updates through GitLab MCP | STATIC CONTRACT | Seed KB docs and acceptance test define branch/file/index/MR/reindex/citation proof |

## What Must Be Proven At Work

These are the minimum live proofs before calling the work-side implementation
credible:

1. Runtime inventory for kagent, Argo, agentgateway, Grafana/Mimir/Loki, Flux,
   Kyverno, and chaos tooling.
2. Real model call through the approved work model path.
3. Smart triage fan-out from a controlled alert or incident.
4. HITL suspend/resume with approver identity and workflow evidence.
5. Grafana MCP read-only metric, log, and dashboard lookup.
6. GitLab MCP sandbox branch/MR/comment using scoped auth.
7. KB update through GitLab MCP with index update, doc2vec/querydoc reindex,
   cited-hit proof, and no-docs fallback.
8. Lifecycle eval scoring with at least one pass and one below-threshold route.
9. One approved lower-env chaos or regression run.
10. Safety proof that general agents do not hold apply/delete/exec/write tools.
11. One report or dashboard artifact that SRE can show back to the team.

## Recommended Build Order Before Next Wednesday

| Order | Work item | Why it matters | Stop condition |
|---|---|---|---|
| 1 | KB/querydoc | This improves answer quality and trust | Cited hit and `NO_RELEVANT_DOCS` fallback captured |
| 2 | KB update through GitLab MCP | This proves agents can safely maintain the knowledge base | Branch, files, index, MR, reindex, citation, and fallback captured |
| 3 | Runtime and model inventory | Without this, every other proof is guesswork | Versions, namespaces, CRDs, and one model response captured |
| 4 | Smart triage replay | This proves the v2 orchestration story | Specialist fan-out completes and synthesis is captured |
| 5 | HITL callback | This proves safety before remediation | Non-read-only step cannot proceed without approval |
| 6 | Grafana MCP | This removes the biggest synthetic evidence caveat | PromQL, LogQL, and dashboard lookup captured |
| 7 | Lifecycle eval | This proves quality gates are enforceable | Passing and failing runs produce score reports |
| 8 | Lower-env chaos | This proves SRE can inject a controlled failure | Target recovers and eval/report are generated |
| 9 | GitLab MCP sandbox | This proves GitOps remediation can be proposed safely | Sandbox MR and comment created with scoped auth |
| 10 | BYO read-only agent | This proves teams can bring their own agent safely | Agent Ready, ToolGrant scoped, dangerous tools absent |
| 11 | Memory | This improves multi-agent continuity | Seed, recall, and curator-mediated write path captured |

If time tightens, stop after item 9. Items 10-11 are important, but the first
nine prove the KB, detect, triage, gate, evaluate, GitOps, and report flow.

## SRE Demonstration Script

Use this structure for the first team demo:

1. Show the proof board and explain the proof tiers.
2. Inject or replay one approved lower-env incident.
3. Watch smart triage fan out to specialists.
4. Show Grafana evidence attached to the run.
5. Show HITL preventing remediation until approval.
6. Show lifecycle eval scoring the run.
7. Show the generated report.
8. Show the BYO-agent folder and explain how a team would onboard a read-only
   triage agent with explicit ToolGrants.

For the cold-start version of the same demo, use
`demos/sre-first-contact/README.md` and
`WORK-KAGENT-TRIAGE-V2-SRE-FIRST-CONTACT.html`. That package starts from an SRE
bringing `checkout-api`, generates failure modes, renders BYO agents, proposes a
safe chaos test, and defines the eval evidence the work lab must return.

## Current Known Gaps

| Gap | Current handling | Close it by |
|---|---|---|
| Live work Grafana MCP evidence | Contract only in public package | Query approved work datasources and attach results |
| Live work GitLab MCP write proof | Sandbox pattern documented | Use scoped sandbox token/project only |
| GitLab MCP KB update loop | Static contract and seed docs exist | Run `demos/kb-gitlab-mcp-update/` through work GitLab MCP and querydoc |
| Full HITL callback path | Offline mock workflow linted | Prove Teams/mock/curl callback in work lab |
| Live querydoc proof | Static validation passes | Provide approved embedding key and run cited/fallback queries |
| BYO live apply | Static demo renders | Apply in non-prod and prove Agent Ready/ToolGrant enforcement |
| Native durable memory | Deferred | Prove Postgres/pgvector restart survival later |

## Done Definition

The work-side package is ready to leave with the team when the work agent or
engineer can return:

```text
STATUS: PASS
EVIDENCE:
- smart-triage workflow name and node evidence
- HITL approval ID and approver identity
- Grafana MCP metric/log/dashboard results
- GitLab sandbox MR or explicit BLOCKED reason
- lifecycle eval score report
- chaos/regression result and recovery evidence
- safety check showing dangerous tools are not granted broadly
GAPS:
- only non-critical P1/P2 items remain
NEXT_ACTION:
- named owner and smallest follow-up for each remaining gap
```

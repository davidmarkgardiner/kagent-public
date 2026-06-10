# Work Kagent Triage V2 Work-Agent Checklist

Purpose: give the future work-side agent or engineer a prioritized replication
checklist after the home-lab package is locally consolidated. This is the list
to walk through when deciding what matters most if time runs short.

Do not run this against production. Use an approved non-production work
environment and keep all work-specific values out of this public repo.

## Priority Summary

| Priority | Meaning | Decision rule |
|---|---|---|
| P0 | Must have before handoff is credible | Proves v2 detects, gates, evaluates, reports, and stays safe |
| P1 | Strongly preferred | Makes the demo richer and reduces follow-up risk |
| P2 | Defer unless time remains | Valuable production hardening or larger feature work |

## P0 - Must Prove

| Area | Work-agent task | Evidence to return | Status |
|---|---|---|---|
| Runtime inventory | Confirm kagent, Argo Workflows, Argo Events, agentgateway, Grafana/Mimir/Loki, Flux/GitOps, Kyverno, and Litmus/equivalent status | Namespaces, CRDs, controller versions | TODO |
| Model path | Prove a real chat completion through the approved work model path | Request/response through agentgateway or kagent ModelConfig | TODO |
| Knowledge RAG | Prove one cited doc2vec/querydoc hit and one `NO_RELEVANT_DOCS` fallback | Query outputs with source citation and fallback marker | TODO |
| KB update via GitLab MCP | Create or update Kagent triage v2 KB docs through GitLab MCP, update the index, reindex, and prove retrieval | GitLab MR URL, `INDEX.md` diff, reindex output, cited hit, fallback proof | TODO |
| Smart triage | Replay one alert or controlled incident and prove specialist fan-out | Workflow name, node table, proof markers, synthesis | TODO |
| HITL | Prove non-read-only action suspends and resumes only after approval | Approval ID, resume identity, workflow node evidence | TODO |
| Grafana MCP | Prove read-only metric, log, and dashboard lookup | PromQL result, LogQL result, dashboard link | TODO |
| GitLab MCP | Prove sandbox branch, MR, and comment using scoped work auth | Sandbox MR URL, token scope/project note | TODO |
| Eval | Prove lifecycle eval scores a run and enforces hard gates | Score report, hard-failure output if applicable | TODO |
| Chaos lower-env | Run one approved low-risk chaos/regression test | ChaosResult/equivalent, target recovery, eval score | TODO |
| SRE first-contact demo | Run the cold-start app onboarding path from app profile to agents, chaos, remediation plan, eval, and learning | Evidence bundle from `demos/sre-first-contact/` adapted to work lab | TODO |
| Reporting | Produce the per-run report and dashboard evidence | Markdown/GitLab/Grafana artifact links | TODO |
| Safety | Confirm no general triage agent has apply/delete/exec/write GitLab tools | Agent manifests, ToolGrant/toolNames, policy report | TODO |

## P1 - Strongly Preferred

| Area | Work-agent task | Evidence to return | Status |
|---|---|---|---|
| Memory | Prove shared memory recall across agent/session boundary | Seed, lookup, context reuse, curator path | TODO |
| BYO triage agent | Onboard one read-only team agent with ToolCatalogEntry/ToolGrant | PR/diff, Agent Ready, granted tools only | TODO |
| BYO remediation agent | Onboard or dry-run one bounded non-prod remediation agent | HITL gate, restricted tools, no delete/exec by default | TODO |
| BYO policy failure | Show missing ToolGrant or dangerous tool request is blocked | Kyverno/PolicyReport denial | TODO |
| Grafana BYO panels | Confirm ToolGrant, tool-denial, and policy-violation panels populate or mark collector pending | Dashboard screenshot or metric query | TODO |
| Review manager | Exercise one below-threshold case and route to review-manager | Finding/report/issue draft; home-lab sample exists for comparison | TODO |

## P2 - Defer Unless Time Remains

| Area | Work-agent task | Evidence to return | Status |
|---|---|---|---|
| Native memory | PostgreSQL + pgvector memory survives controller restart | Restart test and recall proof | DEFER |
| Eval-gated ticket closure | Block ticket closure unless eval passes | Ticket workflow evidence | DEFER |
| Fleet scheduling | Randomized multi-cluster chaos selection under policy | Fleet selector and scheduler evidence | DEFER |
| Production game day | Strict production chaos/game-day workflow | Formal approval and game-day controls | DEFER |
| Custom CRD/controller | Promote ChaosTest/ReliabilitySuite from config to CRD/controller | Controller design and runtime proof | DEFER |

## Work-Agent Output Format

For each item, return:

```text
STATUS: PASS | PARTIAL | BLOCKED | DEFER
EVIDENCE:
- commands run
- artifact links
- workflow names
- dashboard or report links
GAPS:
- exact missing value, permission, CRD, endpoint, image, or approval
NEXT_ACTION:
- smallest follow-up to close the gap
```

## Minimum Handoff Bar

If time runs short, finish these before anything else:

1. Runtime inventory.
2. Model path.
3. Knowledge RAG cited hit and fallback.
4. KB update through GitLab MCP and querydoc reindex proof.
5. Smart triage fan-out.
6. HITL.
7. Grafana MCP.
8. Eval.
9. One lower-env chaos/regression run.
10. One first-contact app onboarding demo.
11. Safety check for tools and GitLab writes.
12. One report/dashboard artifact.

Everything else is valuable, but those ten items prove the core v2 posture.

## Home-Lab Demo References

Use `demos/sre-first-contact/` as the cold-start acceptance test. It already
contains SRE prompts, an application profile, failure modes, BYO agent requests,
expected manifests, a lower-env chaos contract, an eval evidence contract, and a
verifier script.

Use `demos/byo-agent-showcase/` as the starting point. It already contains
request files, expected Agent and ToolGrant manifests, and scripts that prove
the demo renders and excludes delete/exec tools.

Use `demos/kb-gitlab-mcp-update/` as the KB update acceptance test. It contains
the GitLab MCP prompt, expected KB author agent, evidence contract, querydoc
proof contract, and local verifier for the branch/file/index/MR/reindex/citation
loop.

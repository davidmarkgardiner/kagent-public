# Work Kagent Triage V2 Review Prompt

Purpose: use this as the first-pass review brief for the current Kagent triage
system v2 iteration. The goal is to understand where we are, what we have done,
what is still weak, and which small gaps should be fixed locally before this is
packaged for colleagues.

This is not the work-side implementation handoff. Do not ask the review agent to
mutate clusters, apply manifests, create GitLab MRs, or start a new feature
build. The review should produce analysis and a prioritized checklist only.

## Current State In Plain English

The original setup had a set of specialist kagent agents. Each specialist could
understand and debug its own namespace or domain, which was useful, but the
system was one-dimensional: it relied on isolated specialists rather than a
dynamic, connected triage workflow.

This iteration is Kagent triage system v2. It turns that starting point into a
connected AI SRE posture:

- Smart triage fan-out routes an incident across Kubernetes, network, Grafana,
  GitOps, knowledge, deployment, policy, and trace specialists.
- Grafana MCP gives the agents read-only observability evidence instead of
  relying only on Kubernetes state.
- GitLab MCP gives a path to sandbox branches, MRs, comments, and GitOps-style
  remediation proposals.
- Memory and A2A context keep incident learning and specialist context from
  being lost between steps.
- The doc2vec/querydoc knowledge-base path gives cited runbook retrieval and a
  `NO_RELEVANT_DOCS` fallback contract.
- HITL gates prevent non-read-only action from happening without approval.
- Agent lifecycle evals score evidence quality, correctness, safety, HITL
  compliance, remediation verification, ticket hygiene, and hard failures.
- LitmusChaos and the chaos-test-manager skeleton provide controlled lower-env
  incidents so SRE can ask, "create this failure and show me the agents detect,
  triage, and support remediation."
- Grafana/Alloy reporting is the desired path for live visibility and
  management evidence.

The next step is review, not expansion: decide whether v2 is coherent, whether
any claims are overstated, and what small gaps should be closed before a work
replication checklist is finalized.

## Files To Read

Read these first:

1. `README.md`
2. `WORK-ZIP-AGENT-HANDOFF.md`
3. `WORK-TRIAGE-REMEDIATION-VERIFICATION-README.md`
4. `SMART-TRIAGE-FANOUT-WORK-HANDOFF.md`
5. `SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md`
6. `SMART-TRIAGE-FANOUT-EXECUTION-REVIEW.md`
7. `KAGENT-EVAL-LIFT-AND-SHIFT-HANDOFF.md`
8. `WORK-MEMORY-KB-NEXT-HANDOFF-README.md`
9. `WORK-MEMORY-KB-VERIFY-PROMPT.md`
10. `docs/ai-grafana/README.md`
11. `observability/agent-evals/README.md`
12. `platform/teams-hitl/README.md`
13. `chaos/litmus/WORK-INSTALL.md`
14. `WORK-CHAOS-TEST-MANAGER-PLANNING-PROMPT.md`
15. `WORK-CHAOS-TEST-MANAGER-PLAN.md`
16. `WORK-CHAOS-TEST-MANAGER-EXECUTION-REVIEW.md`
17. `WORK-CHAOS-TEST-MANAGER-LIVE-EVIDENCE.md`
18. `chaos/reliability/README.md`
19. `chaos/reliability/CONFIGURATION.md`
20. `chaos/reliability/LIVE-RUNBOOK.md`

Implementation paths to inspect if needed:

```text
a2a/smart-triage-fanout-demo/
a2a/platform-memory-showcase-demo/
agents/chaos-designer/
agents/chaos-test-manager/
agents/chaos-scheduler/
agents/reliability-suite-designer/
agents/reliability-reporting/
agents/review-manager/
agents/skills/fleet-selector/
chaos/litmus/
chaos/reliability/
docs/ai-grafana/
docs/platform-kb/
infra/byo-kagent/kyverno-policies/
observability/agent-evals/
observability/chaos-test-manager/
platform/agentgateway/
platform/argo-workflows/templates/
platform/teams-hitl/
```

## Copy/Paste Prompt For Opus

```text
You are reviewing our Kagent triage system v2 iteration.

Do not implement anything. Do not mutate clusters. Do not create GitLab MRs.
Your job is to understand the current state, review it critically, identify
gaps, and give us a practical checklist for what to improve locally before we
package this for colleagues.

Context:
- v1 had specialist agents that could debug their own namespaces/domains.
- v2 adds smart triage fan-out, Grafana MCP evidence, GitLab MCP, memory/A2A,
  doc2vec/querydoc knowledge retrieval, HITL, lifecycle evals, Litmus chaos
  validation, and the first chaos-test-manager/reliability-suite skeleton.
- The aim is to let SRE say, "create this failure and show me the agents detect,
  triage, evaluate, report, and support safe remediation."
- We are not trying to start major new features. We want to consolidate what is
  already here and close obvious gaps.

Read the files listed in WORK-KAGENT-TRIAGE-V2-REVIEW-PROMPT.md.

Review questions:
1. What have we actually built in this iteration?
2. Is the architecture coherent as a Kagent triage system v2, or are there
   disconnected pieces?
3. Are the safety boundaries clear enough: read-only specialists, HITL,
   GitOps/workflow-controlled mutation, curator-only memory writes, no
   production chaos by default?
4. Are the Grafana, GitLab, memory, knowledge-base, A2A, HITL, eval, and chaos
   pieces connected into one operating model?
5. Is the evidence separated clearly between local/skeleton/home-lab proof and
   work-lab proof still required?
6. Are any claims overstated or unsupported?
7. Can SRE understand how to interact with the system and request a controlled
   failure test?
8. Can platform engineering understand how to operate, validate, and improve it?
9. What small fixes would make the current package materially stronger before
   handoff?
10. What should be deferred because it is a major new feature?

Return this structure:

1. Executive verdict
   - ready / ready with gaps / not ready
   - one paragraph explaining why

2. What we have done
   - concise list of Kagent triage system v2 capabilities
   - map each capability to repo evidence or docs

3. Gap analysis
   - top gaps ranked by risk
   - for each: why it matters, where it appears, suggested small fix

4. Overstated or unclear claims
   - exact claim or file
   - why it is risky
   - safer wording or required evidence

5. Local improvement checklist
   - the checklist we should work through locally over the next few days
   - mark each item as must-fix, should-fix, or defer

6. Work replication checklist draft
   - high-level checklist for a future work-side agent or engineer
   - do not turn this into implementation instructions yet

7. Final recommendation
   - the smallest set of changes that would make this credible to hand to SRE
     and platform engineering colleagues
```

## Review Checklist

Use this board for the Opus review output and our local follow-up. This is a
review checklist, not a work-cluster execution checklist.

| Area | Review question | Expected evidence | Priority |
|---|---|---|---|
| Current-state story | Can someone explain v1 to v2 in five minutes? | README, this prompt, stakeholder/demo docs | Must-fix if unclear |
| Specialist fan-out | Are the specialist lanes and commander synthesis documented and evidenced? | Smart triage handoff, live evidence, execution review | Must-fix |
| Grafana MCP | Is observability described as read-only/on-demand or alert-triggered unless proven continuous? | AI Grafana docs, evidence agent docs | Must-fix |
| GitLab MCP | Are write-capable GitLab actions isolated to sandbox/GitOps specialist paths? | GitLab MCP demo, handoff docs | Must-fix |
| Memory | Are native memory, shared memory, and Git/RAG knowledge clearly separated? | Memory/KB handoff, platform memory docs | Must-fix |
| Knowledge base | Does doc2vec/querydoc require citations and a no-docs fallback? | KB handoff and verify prompt | Must-fix |
| HITL | Are non-read-only actions blocked until approval? | Teams HITL docs, workflow examples | Must-fix |
| Eval | Are hard gates and lifecycle scoring wired into the story? | Agent eval README, lifecycle cases, reports | Must-fix |
| Chaos test manager | Is the natural-language chaos flow a process skeleton, not a full test catalogue? | Chaos plan, reliability README, execution review | Must-fix |
| SRE interaction | Can SRE see how to request a controlled failure and read the result? | Chaos planning prompt, live runbook, reports | Should-fix |
| Reporting | Are operator live view and management evidence both covered? | Grafana/Alloy snippets, dashboard, eval metrics | Should-fix |
| Safety | Are production chaos and direct agent mutation blocked by default? | schemas, validation scripts, policy docs | Must-fix |
| Evidence claims | Are local/home-lab/work-lab claims clearly labeled? | live evidence and execution reviews | Must-fix |
| Work replication | Is there enough shape to later create the work-side checklist? | zip handoff, config docs, placeholders | Should-fix |
| Scope control | Are major new features separated from small consolidation work? | review output and plan boundaries | Must-fix |

## What We Should Do After The Review

1. Read the Opus findings.
2. Split them into:
   - local doc/checklist fixes;
   - small validation fixes;
   - real feature work to defer;
   - work-lab-only proof still required.
3. Patch the local repo artifacts for the first two categories.
4. Only then produce the work-side replication checklist/front sheet.

## Out Of Scope For This Prompt

- Running chaos against a work cluster.
- Creating production-ready chaos suites.
- Adding a new controller or CRD.
- Giving general triage agents write-capable Kubernetes or GitLab tools.
- Treating home-lab evidence as work-lab proof.

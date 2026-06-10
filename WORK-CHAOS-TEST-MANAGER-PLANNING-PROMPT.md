# Work Chaos Test Manager Planning Prompt

Purpose: paste this into a planning agent, for example Opus, to design the next
iteration of the Kagent v2 system. This is a planning prompt only. Do not ask
the planning agent to mutate clusters, create chaos experiments, open GitLab
MRs, or generate a full library of real chaos tests during the planning
session.

The core idea: after the smart-triage, Grafana, GitLab MCP, memory, knowledge
base, HITL, and evaluation work, we want a natural-language chaos/test design
loop and reliability test-suite backbone. This prompt is about the process and
operating model first, not locking in a catalogue of tests. An operator should
be able to say, in plain language, "here is my platform or application, here are
the things that can go wrong, build a test plan for each one", and the system
should plan, approve, inject, observe, triage, evaluate, score, report, and
remember the result.

## Copy/Paste Prompt

```text
You are planning the next iteration of our Kagent v2 AI SRE system.

Do not implement anything yet. Do not mutate any cluster. Do not create GitLab
MRs. Do not produce a locked list of real chaos tests to build today. Produce a
design and implementation plan that another engineer/agent can review before
build.

Read or assume the following repo context:
- README.md
- WORK-ZIP-AGENT-HANDOFF.md
- WORK-TRIAGE-REMEDIATION-VERIFICATION-README.md
- chaos/litmus/WORK-INSTALL.md
- SMART-TRIAGE-FANOUT-WORK-HANDOFF.md
- SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md
- KAGENT-EVAL-LIFT-AND-SHIFT-HANDOFF.md
- WORK-MEMORY-KB-NEXT-HANDOFF-README.md
- WORK-MEMORY-KB-VERIFY-PROMPT.md
- docs/ai-grafana/README.md
- observability/agent-evals/README.md
- platform/teams-hitl/README.md
- a2a/smart-triage-fanout-demo/README.md

Current state:
- v1 was a namespace-level triage agent.
- v2 added connected specialist fan-out, Grafana evidence, GitLab MCP,
  knowledge-base retrieval, shared memory/A2A continuity, HITL, chaos
  validation, and lifecycle evaluation.
- We already have a LitmusChaos handoff and a smart-triage workflow that can be
  driven by controlled incidents.

New capability to plan:

1. Natural-language chaos/test builder
   - An operator can say: "Build a chaos or regression test around this app,
     service, AKS feature, certificate-manager issue, ingress issue, network
     behavior, rollout behavior, policy failure, secret sync failure, etc."
   - A chaos designer agent turns that plain-language request into a safe,
     reviewable test specification.
   - The test can target lower environments first and must be scoped by
     namespace, workload labels, service ownership, SLO/SLA impact, and allowed
     experiment types.

2. Chaos/test manager agent
   - Oversees the test lifecycle end to end.
   - Gets the plan approved through HITL.
   - Injects or schedules the fault only after approval.
   - Watches what the triage system did.
   - Captures Grafana, Kubernetes, GitLab, knowledge-base, memory, and eval
     evidence.
   - Answers: What broke? Did smart triage detect it? What did it suggest? Was
     remediation safe? Did recovery pass? What was the score?

3. Recurring/randomized chaos scheduler
   - Plans sporadic chaos across opt-in lower environments or fleet slices.
   - Prefer GitOps: generate scheduled ChaosEngine/CronWorkflow/WorkflowTemplate
     definitions in GitLab, then Flux/Argo syncs them.
   - Alternative: a tightly scoped in-cluster scheduler agent can create
     schedules only in approved namespaces, but this must be justified against
     GitOps-first policy.
   - Randomization must be controlled by policy: allowlists, blackout windows,
     max concurrent experiments, blast-radius caps, stop conditions, and audit.

4. Learning loop
   - If a production issue was missed, convert it into a lower-environment chaos
     regression test.
   - Store the lesson in shared memory only through a curator path.
   - Add or update a knowledge-base runbook through a HITL-gated GitLab MR.
   - Add an eval fixture so future runs check whether the system detects and
     handles the same issue.

5. Reliability test-suite generation
   - An operator can provide a platform, AKS feature, shared component, or
     application and a list of expected failure modes.
   - The system should eventually generate a suite of tests, not just a single
     test, but this planning session should focus on the process, schema,
     guardrails, and observability.
   - The examples below are conceptual candidate areas, not committed scope and
     not a request to build the tests now.
   - Candidate platform areas:
     - AKS node autoscaler or node autoprovisioner;
     - virtual pod autoscaler;
     - certificate-manager;
     - external-secrets;
     - ingress/controller routing;
     - workload identity;
     - DNS;
     - network policy;
     - rollout and deployment state.
   - Candidate application areas:
     - setup manager;
     - external DRS;
     - any team-owned service with known failure modes.
   - Each test should produce an individual score and report.
   - Each suite should produce an aggregate reliability score and trend.

6. Real-time observability and reporting
   - As tests run, operators should see what is being injected, where, why,
     what the triage system detected, what remediation was proposed, whether
     recovery passed, and the current score.
   - Use the existing Grafana/Alloy observability direction as the default
     telemetry path. Plan what logs, metrics, events, traces, and annotations
     Alloy should collect from Argo, Litmus, kagent, agentgateway, GitLab MCP,
     Grafana MCP, and eval jobs.
   - Design dashboards that are useful during a live test and useful afterward
     for management reporting.

7. Review manager and daily reliability reporting
   - If a test scores below the benchmark, for example below 8/10, route it to
     a review-manager agent or workflow.
   - The review manager should classify the failure, explain what went wrong,
     propose backlog items, update the report, and optionally propose GitLab
     issues/MRs.
   - Daily or weekly reports should summarize which suites ran, scores, failed
     tests, recurring weak areas, improvements, and recommended next actions.
   - The reports should become part of the stabilization evidence for the
     shared unified Kubernetes platform.

Your output must be a planning pack with these sections:

1. Executive TLDR
   - Explain the idea in 8-12 bullets for stakeholders.
   - Make clear this is the next evolution after Kagent v2.

2. Proposed architecture
   - Name the agents/skills you recommend.
   - At minimum consider:
     - chaos-designer-agent
     - chaos-test-manager-agent
     - chaos-scheduler-agent
     - reliability-suite-designer-agent
     - reliability-reporting-agent
     - review-manager-agent
     - chaos-evaluator-agent or integration with existing lifecycle eval
     - memory-curator-agent
     - GitLab/GitOps specialist
     - Grafana evidence specialist
     - knowledge/runbook specialist
   - Show how they interact using A2A, Argo Workflows, Argo Events, GitLab MCP,
     Grafana MCP, LitmusChaos, Flux/GitOps, and evals.
   - Include Grafana Alloy as the telemetry collection path for chaos/test
     lifecycle observability.

3. Natural-language request contract
   - Define the user prompt shape.
   - Define required fields the agent must infer or ask for:
     - target environment
     - namespace
     - workload/service
     - experiment type
     - allowed blast radius
     - time window
     - rollback/abort conditions
     - expected detection signal
     - expected recovery signal
     - related runbook or incident memory
   - Define when the agent must stop and ask for clarification.

4. Chaos test specification
   - Design a YAML or JSON schema for a reviewable test spec.
   - Include:
     - metadata
     - owner
     - target selectors
     - experiment provider, for example Litmus
     - parameters
     - schedule
     - safety policy
     - expected observability signals
     - triage workflow to trigger
     - eval rubric
     - scoring benchmark
     - report destination
     - memory and knowledge-base update policy
   - Keep it environment-agnostic with placeholders.

5. Reliability suite specification
   - Design a YAML or JSON schema for a test suite made of many chaos or
     regression tests.
   - It must support platform-level suites and application-level suites.
   - Include:
     - suite name and owner;
     - platform/application under test;
     - feature areas;
     - failure modes;
     - generated test cases;
     - environment tiers;
     - schedule policy;
     - scoring weights;
     - benchmark threshold, default 8/10;
     - required dashboards;
     - reporting cadence;
     - review-manager routing rules.
   - Explain how this suite spec becomes GitOps-managed test definitions.

6. GitOps design
   - Recommend whether scheduled chaos should be committed as:
     - Litmus ChaosEngine manifests
     - Argo CronWorkflows
     - WorkflowTemplates plus parameter files
     - custom ChaosTest CRDs
     - custom ReliabilitySuite CRDs or config files
   - Explain the tradeoffs.
   - Define how GitLab MCP should create branches/MRs for chaos specs.
   - Define how GitLab MCP should create branches/MRs for reliability suites,
     review reports, failed-test issues, and backlog items.
   - Define how approvals, CODEOWNERS, MR templates, and policy checks fit.

7. In-cluster execution design
   - Define which service accounts execute chaos.
   - Define RBAC boundaries.
   - Define namespace allowlists and label selectors.
   - Define how experiments are triggered, monitored, cancelled, and cleaned up.
   - Define how to prevent production mutation by default.

8. Random/sporadic chaos policy
   - Design a safe randomization model.
   - Include:
     - opt-in labels
     - max concurrent experiments
     - minimum quiet period per service
     - blackout windows
     - business-hour policy
     - environment tiers
     - escalation and abort conditions
     - audit trail
   - Explicitly say whether production is out of scope for v1, or allowed only
     under strict game-day controls.

9. End-to-end workflow
   - Provide a concrete sequence for:
     - operator asks for a chaos test in plain language
     - chaos designer drafts spec
     - knowledge/memory lookup enriches it
     - HITL approval happens
     - GitLab MR is created
     - GitOps syncs it
     - chaos is injected
     - smart triage observes and responds
     - Grafana and Kubernetes evidence is captured
     - eval scores the run
     - memory/runbook/test fixture updates are proposed
   - Also provide a concrete sequence for:
     - operator provides an app/platform and a list of failure modes
     - reliability-suite designer generates a test suite
     - suite is reviewed and merged through GitLab/GitOps
     - tests run manually or on a schedule
     - Grafana shows live test progress through Alloy-collected telemetry
     - reports and scores are produced
     - low-scoring tests are routed to review manager

10. Evaluation design
   - Define scoring dimensions:
     - detection latency
     - correct specialist routing
     - quality of evidence
     - remediation recommendation safety
     - HITL compliance
     - recovery verification
     - knowledge citation quality
     - memory use correctness
     - GitLab hygiene
     - suite coverage of declared failure modes
     - reporting quality
   - Define hard failures:
     - no HITL before mutation
     - production target without explicit game-day approval
     - missing owner
     - missing rollback/abort condition
     - no Grafana or Kubernetes evidence
     - no eval result
     - unsafe output or secret leak
   - Define a benchmark model:
     - individual test score out of 10;
     - default pass threshold 8/10;
     - suite aggregate score;
     - trend over time;
     - automatic review-manager trigger below threshold.

11. Observability and dashboards
   - Design the telemetry model for real-time visibility.
   - Use Grafana Alloy as the collection backbone where possible.
   - Define metrics/logs/events/traces for:
     - test requested;
     - spec drafted;
     - HITL approved/rejected;
     - GitLab MR created/merged;
     - GitOps sync status;
     - chaos injection started/completed/aborted;
     - affected namespace/workload;
     - smart-triage workflow status;
     - specialist completion markers;
     - remediation recommendation;
     - recovery verification;
     - eval score;
     - review-manager routing.
   - Propose dashboard panels:
     - live chaos timeline;
     - active experiments by cluster/namespace/service;
     - reliability score by platform feature/application;
     - failed tests below 8/10;
     - MTTA/MTTR/detection latency;
     - specialist health and A2A/MCP errors;
     - GitLab MR/issue status;
     - recurring failure modes;
     - daily/weekly reliability trend.
   - Include what labels/tags are mandatory for drill-down.

12. Reporting design
   - Define report outputs:
     - per-test report;
     - per-suite report;
     - daily report;
     - weekly trend report;
     - stakeholder summary.
   - Define report fields:
     - suite/test name;
     - owner;
     - target;
     - failure mode;
     - injection result;
     - detection result;
     - triage result;
     - remediation recommendation;
     - recovery verification;
     - score;
     - threshold;
     - review-manager status;
     - linked Grafana dashboard;
     - linked GitLab MR/issue;
     - linked memory/runbook update.
   - Explain where reports should live: GitLab, object storage, Grafana
     annotations, Teams summaries, or a combination.

13. Review manager design
   - Define when review-manager-agent is invoked.
   - Define what it reviews:
     - low scores;
     - missing signals;
     - failed remediation;
     - flaky tests;
     - unsafe experiments;
     - missing runbooks;
     - repeated weak platform areas.
   - Define output:
     - root cause hypothesis;
     - whether the test was valid;
     - whether the system response was valid;
     - recommended backlog item;
     - GitLab issue/MR proposal;
     - memory proposal;
     - KB/runbook update proposal.

14. Memory and knowledge loop
   - Explain how findings become:
     - shared incident memory
     - knowledge-base runbook updates
     - regression chaos tests
     - eval fixtures
     - reliability suite updates
     - review-manager findings
   - Keep canonical runbooks in Git, not memory.
   - Keep shared memory writes behind a curator workflow.

15. Initial spike backlog
   - Propose 4-6 implementation spikes in order.
   - For each spike, include:
     - objective
     - artifacts to create
     - prerequisites
     - test command
     - proof markers
     - done criteria
     - risks

16. Minimal first demo
   - Pick one low-risk test, for example:
     - pod delete on a labelled demo workload
     - certificate-manager secret not renewing in a sandbox namespace
     - external-secrets sync failure
     - ingress route misconfiguration
     - rollout with bad image tag
   - Design the smallest demo that proves the whole loop without touching
     production.
   - Keep this to one or two candidate scenarios. Do not produce a full AKS or
     application test catalogue.
   - Also design the smallest suite demo concept:
     - one platform or app;
     - two or three declared failure modes;
     - two or three planned tests;
     - one deliberately below-threshold score;
     - one review-manager report;
     - one Grafana dashboard view.

17. Public-safe handoff
   - List every environment variable/placeholder required.
   - List images that may need mirroring.
   - List Kubernetes CRDs/controllers required.
   - List GitLab permissions required.
   - List Grafana/observability permissions required.

18. Open questions
   - Ask only questions that materially affect the design.
   - Do not ask for secrets.

Constraints:
- Public/sanitized docs only. Use placeholders for private values.
- Prefer GitOps for durable changes.
- Agents may submit workflows or MRs; workflow service accounts do execution.
- Read-only agents must not get write-capable GitLab, Kubernetes, or memory
  tools.
- Any remediation or chaos mutation requires HITL.
- Production chaos is out of scope unless explicitly designed as a future
  game-day mode with strict controls.
- This is process-first. The planning output should show how a human SRE or a
  controlled chaos scheduler could request, approve, inject, observe, score,
  and report tests. It should not over-index on enumerating every possible AKS
  or application failure mode.
- Use proven engines where possible. Prefer Litmus for Kubernetes chaos unless
  you justify Chaos Mesh, PowerfulSeal, custom Argo workflows, or another tool.
- Plan for observability as a first-class product surface, not an afterthought.
  Grafana dashboards and reports are part of done.
- A test below 8/10 must trigger review-manager handling in the proposed design.
- Do not produce vague architecture only. Produce a concrete plan we can hand
  back to Codex for review and implementation.

At the end, produce:
- a concise recommended architecture;
- the proposed agent/skill list;
- the proposed workflow sequence;
- the reliability suite specification;
- the Grafana/Alloy observability design;
- the reporting and review-manager design;
- the first 4-6 build spikes;
- the first demo scenario;
- proof markers;
- risks and mitigations;
- exact files you recommend Codex should create or modify next.
```

## What We Want Back For Review

Ask the planning agent to return a single planning document named:

```text
WORK-CHAOS-TEST-MANAGER-PLAN.md
```

The returned plan should be explicit enough that Codex can review it and then
implement the first spike without another discovery pass.

## Initial Architecture Bias

Use this only as a starting hypothesis. The planning agent may challenge it.

```text
plain-language request
  -> chaos-designer-agent
       -> knowledge lookup
       -> memory lookup
       -> draft ChaosTestSpec
  -> HITL review
  -> GitLab/GitOps specialist opens MR
  -> Flux/Argo syncs approved test
  -> chaos-test-manager-agent launches or watches experiment
  -> Litmus/Argo injects controlled fault
  -> smart-triage fan-out runs
  -> Grafana/Kubernetes/GitLab/knowledge/memory evidence captured
  -> lifecycle eval scores detection, triage, remediation, recovery
  -> memory curator and KB update MR proposed
```

## Suggested Proof Markers

The plan should refine these:

```text
CHAOS_REQUEST_PARSED: yes
CHAOS_SPEC_DRAFTED: yes
RELIABILITY_SUITE_DRAFTED: yes
FAILURE_MODES_MAPPED: yes
KNOWLEDGE_CONTEXT_ATTACHED: yes
MEMORY_CONTEXT_ATTACHED: yes
HITL_STATUS: approved
GITLAB_BRANCH: created
GITLAB_MR: created
CHAOS_SCHEDULE_CREATED: yes
CHAOS_INJECTION_STARTED: yes
CHAOS_INJECTION_COMPLETED: yes
SMART_TRIAGE_FANOUT: started
SPECIALIST_GRAFANA: completed
SPECIALIST_KUBERNETES: completed
INCIDENT_SYNTHESIS: completed
REMEDIATION_MODE: gitops_or_workflow_only
VERIFICATION_PASSED: yes
EVAL_SCORE: {{SCORE}}
SCORE_THRESHOLD: 8
REVIEW_MANAGER_TRIGGERED: yes|no
GRAFANA_DASHBOARD_UPDATED: yes
ALLOY_TELEMETRY_CAPTURED: yes
TEST_REPORT_CREATED: yes
SUITE_REPORT_CREATED: yes
DAILY_REPORT_UPDATED: yes
CHAOS_REGRESSION_CAPTURED: yes
KB_UPDATE_PROPOSED: yes
MEMORY_PROPOSAL_CREATED: yes
OUTPUT_SANITIZED: yes
```

## Review Standard

When Codex reviews the returned plan, it should check:

- Is GitOps the default for durable scheduled chaos?
- Are production and lower-environment modes clearly separated?
- Are write-capable tools isolated from read-only agents?
- Is HITL required before every mutation?
- Are random chaos controls strong enough?
- Is the eval loop concrete and testable?
- Are memory and knowledge-base responsibilities separated correctly?
- Are proof markers sufficient to prove the loop?
- Can the first spike be implemented from the plan without guessing?

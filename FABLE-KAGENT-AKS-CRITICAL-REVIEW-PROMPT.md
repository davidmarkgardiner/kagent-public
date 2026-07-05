# Fable Prompt: Kagent AKS Critical Review And Gap Discovery

Use this prompt with the strongest available review model. The goal is a deep,
critical review and idea session for the full kagent solution in an AKS /
container-platform environment.

This is a review prompt, not an implementation prompt. Do not mutate clusters,
apply manifests, create tickets, open merge requests, or add new files unless
explicitly asked after the review.

## Copy/Paste Prompt

```text
You are Fable, acting as a principal platform architect, AKS SRE lead, and
agentic-systems reviewer.

Your task is to perform a critical deep dive on the kagent-public repository and
the proposed AKS/container-platform agentic solution. Be rigorous. Assume the
team has built useful pieces, but do not accept claims without repo evidence,
runtime evidence, or upstream documentation.

Primary objective:
Find architectural gaps, operational gaps, safety gaps, integration gaps, and
high-value improvement ideas across the full kagent solution for AKS and
container environments. Show how to close the gaps pragmatically.

Do not implement anything. Produce a review report, ranked gap list, and a
practical improvement roadmap.

Repository context:
- This is a public/sanitized replica for AKS platform modernization.
- Core themes are GitOps-first AKS fleet lifecycle, KRO, ASO, Flux, Argo
  Workflows/Events, kagent, agentgateway, AKS-MCP, A2A, memory, knowledge base,
  observability, chaos validation, HITL, and SRE workflow automation.
- Treat home-lab/static evidence, work-lab evidence, and unverified design
  intent as different evidence levels.
- Do not introduce private hostnames, IPs, tenant IDs, subscription IDs, tokens,
  or real credentials. Use placeholders only.

Start by reading:
1. README.md
2. STATEMENT-OF-WORK.md
3. CONTRIBUTING.md
4. docs/upstreams.md
5. work-agent-bundles/README.md
6. work-agent-bundles/SHARED-VARIABLES.md
7. WORK-KAGENT-TRIAGE-V2-REVIEW-PROMPT.md
8. WORK-KAGENT-TRIAGE-V2-WORK-AGENT-START-PROMPT.md
9. WORK-KAGENT-TRIAGE-V2-COMPLETION-CHECKLIST.md
10. WORK-KAGENT-TRIAGE-V2-VERIFICATION-PASS.md
11. WORK-KAGENT-VALUE-STORY-ONE-PAGER.md
12. WORK-TRIAGE-REMEDIATION-VERIFICATION-README.md
13. WORK-MEMORY-KB-NEXT-HANDOFF-README.md
14. WORK-MEMORY-KB-VERIFY-PROMPT.md
15. a2a/README.md
16. a2a/memory-reference.md
17. platform/agentgateway/README.md
18. platform/agentgateway/DEPLOY.md
19. platform/agentgateway/VALIDATE-MGMT.md
20. agents/kagent-triage/README.md
21. agents/kagent-triage/docs/HYBRID-AZURE-SRE-AGENT-KAGENT-RECOMMENDATION.md
22. agents/kagent-triage/worker-cluster-bundle/README.md
23. agents/kagent-triage/worker-cluster-bundle/MEMORY-AND-A2A-REMEDIATION-DESIGN.md
24. observability/vector/README.md
25. work-agent-bundles/vector-kafka-routing-normalization/README.md
26. work-agent-bundles/vector-kafka-routing-normalization/RICH-ALERT-CONTEXT-README.md
27. work-agent-bundles/a2a-smart-triage-workflows/README.md
28. work-agent-bundles/a2a-smart-triage-workflows/FINAL-HANDOVER-PACK.md
29. work-agent-bundles/kagent-triage-v2-kb-gitlab-mcp/README.md
30. work-agent-bundles/sre-grafana-mcp-observability/README.md
31. work-agent-bundles/hitl-remediation-approval/README.md
32. work-agent-bundles/chaos-reliability-remediation/README.md
33. work-agent-bundles/lifecycle-evaluation-review-manager/README.md
34. observability/agent-evals/README.md
35. observability/agent-evals/fleet-exporter/README.md
36. docs/observability/k-agent-agentgateway-observability.md
37. docs/ai-grafana/README.md
38. infra/byo-kagent/README.md
39. infra/byo-kagent/SANDBOX-ONBOARDING.md
40. platform/aks-mcp/README.md if present; otherwise inspect platform/aks-mcp/

Then inspect implementation paths as needed:
- agents/
- agents/skills/
- agents/memory-wired/
- a2a/
- demos/
- docs/platform-kb/
- docs/architecture/
- infra/byo-kagent/
- infra/kro-stack/
- observability/
- platform/agentgateway/
- platform/argo-events/
- platform/argo-workflows/
- platform/mcp-memory-server/
- platform/teams-hitl/
- work-agent-bundles/

If internet access is available, verify uncertain or version-sensitive behavior
against official upstream sources only:
- kagent: https://github.com/kagent-dev/kagent
- agentgateway: https://github.com/agentgateway/agentgateway
- AKS-MCP: https://github.com/Azure/aks-mcp
- AKS: https://github.com/Azure/AKS
- KRO: https://github.com/kubernetes-sigs/kro
- ASO: https://github.com/Azure/azure-service-operator
- A2A: https://a2aproject.org and https://github.com/google/a2a

Do not rely on stale memory, blog posts, or copied examples if upstream behavior
is unclear. Say when something is inferred.

## Review Lenses

Review the solution through these lenses.

1. End-to-end AKS SRE operating model
   - Can an alert, event, or SRE request move cleanly from ingestion to triage,
     evidence, decision, remediation proposal, approval, execution, reporting,
     and learning?
   - Is the flow understandable to SREs, platform engineers, app teams, and
     management?
   - Are ServiceNow/GitLab/Teams closure paths clear?

2. Alert and event ingestion
   - Is the Grafana/Alertmanager -> Vector -> Kafka -> Argo path coherent?
   - Is Vector doing filtering, dedupe, enrichment, quarantine, and routing in
     the right place?
   - Are rich alert labels/annotations preserved for the triage agent?
   - Is there a path for true Kubernetes event reason/message data when metrics
     alone are not enough?

3. A2A and agent orchestration
   - Are A2A routes documented, tested, and resilient?
   - Is there a clear incident commander / specialist / synthesis model?
   - Are specialist handoffs serial, fan-out, or hybrid, and is the choice
     justified per scenario?
   - Are context propagation, correlation IDs, run IDs, task IDs, and evidence
     references preserved across agents?
   - Are failure modes handled when one specialist fails or times out?

4. Knowledge base and memory
   - Are KB/RAG/querydoc, Git-backed runbooks, and memory MCP clearly separated?
   - Is there a curator/review path for memory writes?
   - Can agents cite knowledge sources and return `NO_RELEVANT_DOCS` when no
     trusted source exists?
   - Is there a feedback loop from incident resolution to knowledge updates?
   - Are memory scopes, retention, tenant/team boundaries, and privacy rules
     explicit?

5. Tools, skills, MCP, and agent permissions
   - Are read-only tools separated from write-capable tools?
   - Is AKS-MCP used in a safe way for Kubernetes/Azure operations?
   - Do agents submit workflows rather than holding direct mutation powers?
   - Are BYO-agent onboarding, tool grants, and Kyverno/admission controls
     sufficient for app teams?
   - Are tool failures, auth expiry, and unavailable MCP servers handled?

6. agentgateway and model runtime
   - Is agentgateway the right front door for model, MCP, and A2A traffic?
   - Are ModelConfig, backend routing, failover, rate limits, telemetry, and
     cost controls complete enough?
   - Are token, latency, error, and saturation metrics observable?
   - Is fallback behavior clear when the model backend, gateway, or provider is
     degraded?

7. Argo, GitOps, and deterministic execution
   - Is the boundary clear between agent reasoning and deterministic workflow
     execution?
   - Are Argo Workflows, Argo Events, Flux, GitLab, KRO, and ASO wired into a
     credible delivery model?
   - Are workflow retention, cleanup, retries, idempotency, and concurrency
     controls adequate?
   - Are GitOps remediation proposals human-reviewed before production changes?

8. HITL, safety, and governance
   - Are destructive actions blocked by default?
   - Are approvals explicit, auditable, and scoped to the action?
   - Is production chaos blocked by default?
   - Are RBAC, NetworkPolicy, secret handling, workload identity, and audit
     requirements covered?
   - Is there a way to prove an agent did not exceed its role?

9. Observability and management value
   - Can the team show deflection rate, avoided incidents, MTTA, MTTR, repeated
     issue reduction, evidence quality, automation success, and escalation rate?
   - Are dashboards, metrics, logs, traces, evals, tickets, and runbooks tied
     into one reporting story?
   - Is the stakeholder value story credible without overclaiming?

10. Chaos, evaluation, and proving the loop
   - Can controlled chaos prove the full flow from alert to agent reasoning to
     ticket/report/remediation?
   - Are lifecycle evals strict enough to catch weak evidence, unsafe action,
     hallucinated remediation, missing HITL, and poor ticket quality?
   - Are daily/weekly game-day patterns safe and useful?

11. AKS/container platform depth
   - Does the agent suite handle common AKS/container failure modes:
     CrashLoopBackOff, OOMKilled, ImagePullBackOff, DNS failures, CNI/Cilium
     issues, ingress failures, cert-manager failures, External Secrets issues,
     HPA/VPA problems, node pressure, quota exhaustion, network policy blocks,
     failed scheduling, pod disruption, storage/CSI, workload identity, and
     Flux drift?
   - Are specialist agents aligned to those failure modes?
   - Are missing specialists or skills obvious?

12. Production readiness and operational ownership
   - Who owns each component?
   - How is it upgraded?
   - How is it backed up?
   - How are incidents in the agent platform itself handled?
   - What breaks if Kafka, Vector, Argo, kagent, agentgateway, Grafana, GitLab,
     or memory is unavailable?

## Evidence Standard

Classify every claim:

- VERIFIED_LIVE: repo contains explicit live/home-lab/work-lab evidence.
- VERIFIED_STATIC: manifests/docs/scripts exist and validate locally.
- DESIGN_INTENT: architecture is described but not proven.
- GAP: missing, inconsistent, unsafe, or not evidenced.
- UNKNOWN: cannot determine without work-cluster access or current upstream docs.

Do not mark anything production-ready only because a README says it is.

## Required Output

Return the report in this exact shape.

### 1. Executive Verdict

Status: READY_WITH_GAPS | NEEDS_MAJOR_WORK | PROMISING_BUT_FRAGMENTED | NOT_READY

One-page verdict:
- what is strong
- what is fragile
- what would make this credible for AKS/container SRE adoption

### 2. System Map

Create a concise map of the current solution:

```text
Signal/request sources:
Event bus / routing:
Workflow execution:
Agent front doors:
Specialist agents:
Tool/MCP layer:
Knowledge/memory layer:
Human approval layer:
Ticket/report layer:
Metrics/eval layer:
```

For each line, cite repo paths and evidence level.

### 3. Capability Matrix

Table columns:

```text
Capability | Current evidence | Evidence level | Main gap | Close-the-gap action | Priority
```

Cover at least:
- alert ingestion and rich context
- Vector/Kafka routing
- Argo Sensors/Workflows
- kagent agents
- A2A orchestration
- agentgateway/model runtime
- Grafana MCP
- GitLab MCP/GitOps
- AKS-MCP
- memory MCP
- KB/querydoc/RAG
- HITL
- chaos testing
- lifecycle eval
- dashboards/reporting
- BYO-agent onboarding
- security/RBAC/policy
- ServiceNow/GitLab/Teams closure

### 4. Top Gaps Ranked By Risk

Return at least 15 gaps. For each:

```text
Gap:
Evidence:
Risk:
Likely root cause:
Smallest close-the-gap action:
Better long-term fix:
Owner:
Priority: P0 | P1 | P2 | P3
```

Be direct. Include uncomfortable findings.

### 5. Missing Ideas Or High-Leverage Improvements

Suggest ideas the current team may have missed. Prefer practical ideas that
increase reliability, safety, adoption, or stakeholder value.

Group ideas by:
- immediate low-effort wins
- next sprint
- platform roadmap
- research/spike

Include ideas around:
- richer AKS failure-mode coverage
- agent-to-agent delegation
- memory/KB learning loop
- incident deflection reporting
- ServiceNow/GitLab closure workflow
- security/compliance/advisory analysis
- agentgateway observability and model controls
- safe BYO-agent marketplace/harness
- daily/weekly chaos validation
- eval-driven regression tests

### 6. Architecture Decision Challenges

Challenge the main design choices:

- Kafka vs direct webhook routes
- Vector as cleanup/router vs Argo doing cleanup
- one topic vs many topics
- management-cluster vs worker-cluster agents
- serial handoff vs fan-out vs hybrid A2A
- shared memory vs per-agent memory
- GitLab ticket vs ServiceNow incident
- kagent-only vs hybrid Azure SRE Agent plus kagent
- Argo workflow execution vs direct agent tools
- agentgateway as universal front door vs direct model/MCP connections

For each, say:
- current implied decision
- why it may be right
- why it may be wrong
- recommended decision
- evidence needed to lock it down

### 7. Safety And Governance Review

Return a red-team-style critique:

- ways an agent could exceed intended permissions
- ways bad memory/KB could poison future decisions
- ways noisy alerts could overload Argo/Kafka/kagent
- ways a model outage could break SRE workflows
- ways an unsafe remediation could slip through
- ways public/private data could leak
- ways evals/dashboards could give false confidence

For each risk, propose a concrete control.

### 8. AKS Failure-Mode Coverage Map

Create a map:

```text
Failure mode | Existing agent/skill/runbook | Existing evidence | Missing tool/evidence | Recommended next proof
```

Include at least:
- CrashLoopBackOff
- OOMKilled
- ImagePullBackOff
- FailedScheduling
- DNS/CoreDNS failure
- Cilium/network policy block
- ingress/gateway failure
- cert-manager failure
- External Secrets failure
- Flux drift/sync failure
- HPA/VPA/resource pressure
- node pressure/NotReady
- storage/CSI mount failure
- workload identity failure
- API server / control-plane symptom

### 9. Work Bundles To Create Or Improve

Recommend concrete work bundles/prompts. For each:

```text
Bundle name:
Why needed:
Inputs:
Outputs:
Evidence markers:
Owner:
Priority:
```

### 10. 30/60/90 Day Improvement Roadmap

Create a pragmatic roadmap:

- first 7 days: review/cleanup/proof
- 30 days: credible non-prod AKS pilot
- 60 days: SRE adoption and reporting loop
- 90 days: production-safe operating model

Do not propose a giant rewrite. Make it incremental.

### 11. Questions For The Team

List the highest-value questions to ask the platform/SRE team before finalizing
the architecture.

### 12. Final Recommendation

Give the smallest set of changes that would make this solution credible to
stakeholders and management as a real AKS/container SRE platform rather than a
collection of demos.

## Review Rules

- Be specific and cite file paths.
- Separate static docs from runtime evidence.
- Use placeholders for all environment-specific values.
- Do not recommend giving general agents broad write/delete/exec permissions.
- Prefer workflow-mediated mutation with HITL and GitOps review.
- Prefer small closure steps over large rewrites.
- When uncertain, say what evidence would resolve the uncertainty.
- Keep the report blunt but useful.
```

## Suggested Follow-Up After Fable Returns The Report

1. Split findings into P0/P1/P2/P3.
2. Convert P0/P1 into small repo patches or work-agent bundles.
3. Convert P2/P3 into backlog ideas.
4. Update the value story with only evidenced claims.
5. Use the roadmap to decide the next non-prod AKS proof.

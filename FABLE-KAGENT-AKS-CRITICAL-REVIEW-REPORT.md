# Kagent AKS Critical Review — Full Report

**Date:** 2026-07-05
**Model:** Fable 5
**Scope:** kagent-public repository (sanitized AKS platform-modernization codebase)
**Method:** Six parallel read-only code reviewers over docs/agents/platform/observability/bundles/infra slices + synthesis

---

## 1. Executive Verdict

**Status: PROMISING_BUT_FRAGMENTED**

**What is strong.** The safety *architecture* is right: read-only specialists, agents submit workflows while workflow service accounts hold mutation power, GitOps-mediated remediation, four-layer prod-chaos blocking, HITL suspend gates, and a lifecycle evaluator with real enforced hard-fail gates (`observability/agent-evals/scripts/score-lifecycle-run.py:136-204` — mutation-before-HITL, wrong-namespace, leak-regex, missing-approval all genuinely fail runs; independently reproduced). Several subsystems are near-production quality: the doc2vec→querydoc KB pipeline with curated GitLab-MR update loop, workload-identity automation (OIDC→ASO FederatedIdentityCredential, keyless, per-SA scoping), agentgateway model routing with live token metrics (`agentgateway_gen_ai_client_token_usage`), and real A2A context-continuity proof across a HITL suspend (`A2A-DEMO-EXECUTION-REVIEW.md:78-113`). The internal docs are unusually self-honest — DO-NOT-APPLY banners, synthetic-evidence caveats, threat docs that flag their own gaps.

**What is fragile.** Three things. First, **enforcement lag**: nearly every safety control is specified in prose/CRDs but not enforced at runtime — the HITL callback sensor validates only `body.decision` (anyone who can POST resumes any workflow), the approval tier is copied from the agent's own self-declared tier (`platform/teams-hitl/workflow-approval-template.yaml:186-194`), the shared memory server has zero authn/authz/NetworkPolicy with delete tools open to any pod, the ToolGrant Kyverno policy is self-bypassable via an author-set annotation, and the "gateway as MCP auth layer" is CRD-blocked on the installed version — today's effective security boundary is Istio IP allow-lists (shipped as placeholder CIDRs) plus client-side `toolNames`. Second, **synthetic evidence near top-line claims**: all 8 fan-out specialists emit `EVIDENCE_SOURCE: synthetic-*`, KB citations are hardcoded, the demo emits `HITL_STATUS: resumed` unconditionally, and 13 of 18 bundle "verifiers" grep for attestation strings rather than executing behavior. Third, **fragmentation**: four message brokers, three dedupe implementations, contested canonical ingestion path, 47+ top-level status docs restating truth differently, bundle index drift, and one committed-but-empty bundle directory.

**What would make it credible for AKS SRE adoption.** Not a rewrite — an enforcement-and-consolidation pass: (1) make HITL unforgeable and tier assignment config-driven; (2) put auth/NetworkPolicy in front of memory; (3) replace one synthetic specialist path with one real end-to-end live run (alert → real Grafana/K8s evidence → HITL block → GitOps MR) and label everything else honestly; (4) pick one canonical ingestion pipeline; (5) redact the sanitization leak. That is weeks, not months.

---

## 2. System Map

```
Signal/request sources:   Grafana/Alertmanager webhooks + Grafana Kafka contact point + Alertmanager→Kafka shim
                          (observability/confluent-cloud-pipeline/, observability/prometheus-alertmanager/) — VERIFIED_STATIC
                          K8s events via Alloy loki.source.kubernetes_events (observability/alloy-eventhub-pipeline/,
                          work-agent-bundles/alloy-k8s-events-kafka/) — VERIFIED_STATIC

Event bus / routing:      FOUR parallel: Confluent Kafka (canonical-by-investment), Azure Event Hub, Redpanda
                          (self-demoted), direct webhook→Argo Events (stated-canonical in k8s/observability/) — VERIFIED_STATIC, contested
                          Vector normalize/filter/dedupe/route (observability/vector/,
                          work-agent-bundles/vector-kafka-routing-normalization/) — VERIFIED_STATIC; routing fields unused downstream

Workflow execution:       Argo Events (NATS bus, replicas:1) → Sensors → Argo Workflows; smart-triage fan-out DAG
                          (a2a/smart-triage-fanout-demo/workflow.yaml) — orchestration VERIFIED_LIVE, specialist evidence SYNTHETIC

Agent front doors:        kagent controller + agentgateway routes /azure/v1 /openai/v1 /qwen/v1 /llm/v1
                          (platform/agentgateway/) — model path VERIFIED_LIVE (token metrics); MCP/A2A gateway policies CRD-BLOCKED

Specialist agents:        ~9 read-only namespace triage agents + incident-commander + 8 synthetic fan-out specialists
                          (agents/, a2a/) — VERIFIED_STATIC; cert-manager/test-ns/memory-wired k8s-agent hold write+delete+exec — GAP

Tool/MCP layer:           AKS-MCP helm chart (default readonly but reads all Secrets), GitLab MCP (sandbox shim live,
                          official API unauthorized), Grafana MCP (DESIGN_INTENT), querydoc MCP — VERIFIED_STATIC

Knowledge/memory layer:   docs/platform-kb + ai-platform/kagent-knowledge-base (doc2vec→sqlite→querydoc) — VERIFIED_STATIC, strongest subsystem
                          platform/mcp-memory-server — no auth, no scoping, shared graph, open delete — GAP

Human approval layer:     platform/teams-hitl Argo suspend/resume + 24h fail-safe — design VERIFIED_STATIC;
                          callback forgeable, tier self-classified, demo auto-resumes — GAP

Ticket/report layer:      GitLab MR path VERIFIED_LIVE (sandbox shim, real SHAs in SMART-TRIAGE-GITLAB-MCP-MR-DEMO.md);
                          ServiceNow/Teams closure — DESIGN_INTENT only

Metrics/eval layer:       observability/agent-evals scorer + hard gates VERIFIED_STATIC (reproduced); fed hand-written
                          samples; fleet-exporter equates workflow-Succeeded with remediation-verified; deflection/MTTA/MTTR — DESIGN_INTENT
```

---

## 3. Top Gaps Ranked By Risk

**Gap 1: Shared memory server has no authentication, authorization, scoping, or NetworkPolicy.**
- Evidence: `platform/mcp-memory-server/remotemcpserver.yaml:22` plaintext HTTP; `read_graph` dumps entire graph; `delete_entities`/`add_observations` reachable by any pod; known concurrent-write data loss (`docs/kagent-memory/README.md:44,75`).
- Risk: Any compromised or prompt-injected pod poisons or wipes the memory all triage agents trust.
- Smallest action: NetworkPolicy restricting :3000 to kagent agent pods; disable delete tools.
- Better fix: Gateway-mediated MCP with CEL authz + curator-only write path (already designed in `platform-memory/README.md`).
- **Priority: P0**

**Gap 2: HITL approval callback is forgeable.**
- Evidence: `platform/teams-hitl/sensor.yaml` validates only `body.decision`; HMAC layer commented out; Istio allowlist ships as `REPLACE_WITH_BOT_EGRESS_CIDR`; nonce/replay protections unimplemented; `mock-bot/app.py` exposes unauthenticated `/auto-approve/{id}`.
- Risk: Anyone who can POST resumes any suspended remediation.
- Smallest action: Enable HMAC AuthorizationPolicy + sensor filter on approval_id/signature.
- **Priority: P0**

**Gap 3: Approval tier is the agent's own self-declaration.**
- Evidence: `platform/teams-hitl/workflow-approval-template.yaml:186-194` — `FINAL_TIER="${PROPOSED_TIER}"`; tier decides whether a human is asked; T0/T1 auto-execute.
- Risk: Injected/hallucinating agent labels a destructive action T0 → executes with zero approval.
- Smallest action: ConfigMap action→tier lookup; unknown action floors to T4; ignore agent's proposal.
- **Priority: P0**

**Gap 4: Untrusted event text flows into agents holding delete/exec, with no HITL.**
- Evidence: `agents/kagent-triage/.../cert-manager-sensor.yaml` passes raw `body.message` to `cert-manager-agent` holding `k8s_delete_resource`+`k8s_execute_command`; same for test-ns agents; `agents/memory-wired/k8s-agent` is live/Ready with full write+delete+exec.
- Risk: Prompt injection via crafted event message → autonomous destructive action.
- Smallest action: Strip write/delete/exec from these three agents.
- **Priority: P0**

**Gap 5: Sanitization leak in committed audit doc.**
- Evidence: `work-agent-bundles/LIVE-WORK-AGENT-AUDIT-2026-06-07.md:47` contained a real secret-manager project/secret path before this execution pass; also internal DNS/codename style values and home-lab context names were present.
- Risk: Public repo violates its own public-safety rules.
- Smallest action: Redact to placeholders now.
- **Priority: P0**

**Gap 6: Onboarding workflows mint payload-controlled Kubernetes and Azure RBAC without review.**
- Evidence: `platform/argo-workflows/.../app-onboarding-template.yaml:820-857` binds payload `teamAdGroup`→payload `clusterRole`; `:1323-1381` creates Azure RoleAssignments at payload-supplied scope+roleDefinitionId; webhook→sensor→mutation with no human gate.
- Risk: Malicious/typo'd payload grants cluster-admin or Azure Owner.
- Smallest action: Allowlist permitted clusterRoles/roleDefinitionIds/scopes in the payload schema.
- **Priority: P0**

**Gap 7: BYO ToolGrant enforcement is bypassable and blind.**
- Evidence: `infra/byo-kagent/kyverno-policies/validate-agent-tool-grants.yaml:53-55` denial skipped by author-set annotation; no expiry/scope/catalog-resolution check; `mcp-dangerous-verb.yaml` reads empty status at admission; no policy validates tool-server ClusterRoles.
- Risk: Tenant agent escapes namespace via a broad-RBAC tool server.
- Smallest action: Make the apiCall rule authoritative; drop annotation escape.
- **Priority: P0**

**Gap 8: Synthetic evidence sits under top-line claims.**
- Evidence: All 8 specialists `EVIDENCE_SOURCE: synthetic-*`; `CITATIONS:` hardcoded; `prove-result` steps hardcode outcomes; demo emits `HITL_STATUS: resumed` unconditionally; no live fan-out transcript committed.
- Risk: Stakeholders read as delivered; credibility collapse when discovered.
- Smallest action: Prefix hardcoded markers `DEMO_SIMULATED_`.
- Better fix: One real end-to-end run committed as flagship evidence.
- **Priority: P1** (P0 if stakeholder demo imminent)

**Gap 9: LLM failover unproven; model path is a hard SPOF.**
- Evidence: `platform/agentgateway/backend-llm-failover.yaml` groups schema-gated; ModelConfig points at one endpoint; no client-side fallback; controller replicas:1, PDBs off.
- Risk: Provider/gateway outage = total agent outage mid-incident.
- Smallest action: Run failover 429 probe; until proven, document "provider outage = agent outage".
- **Priority: P1**

**Gap 10: Routing intelligence computed then ignored.**
- Evidence: Vector emits `target_agent`/`route_key`/`automation_allowed`; production sensor forwards `body.alertmanager` and ignores them.
- Risk: Agent selection is theater.
- Smallest action: Update prod Sensor/WorkflowTemplate to consume `target_agent`.
- **Priority: P1**

---

## 4. Capability Matrix (summary)

| Capability | Evidence | Level | Main gap | Action | Priority |
|---|---|---|---|---|---|
| Alert ingestion + rich context | Live 14/14 dedup 2/2 | VERIFIED_LIVE | `alerts[0]`-only; resolved dropped; truncated | Fan-out VRL; pass resolved-status | P1 |
| Vector/Kafka routing | Normalizer computes fields | VERIFIED_STATIC | Prod ignores routing; no quarantine | Consume fields; add quarantine | P1 |
| Argo Sensors/Workflows | Wiring sound, idempotent | VERIFIED_STATIC | No TTL/retention/mutex; silent drops | ttlStrategy + mutex | P1 |
| kagent agents | ~30 Agent CRs; 9 read-only | VERIFIED_STATIC | 3 hold delete+exec | Strip tools or gate behind HITL | P0 |
| A2A orchestration | ContextId continuity live | VERIFIED_LIVE | Evidence synthetic; DAG-wide failure | One live specialist; continueOn | P1 |
| agentgateway | Routes + metrics live | VERIFIED_LIVE | Failover unproven | Run 429 probe | P1 |
| Grafana MCP | Agent CR contract | DESIGN_INTENT | Evidence synthetic | One real query | P1 |
| GitLab MCP/GitOps | Sandbox MR live | VERIFIED_LIVE | Official unauthorized; isolation prompt | Project token + sandbox | P1 |
| AKS-MCP | Helm chart + toggle | VERIFIED_STATIC | readonly reads all Secrets | Drop from base rule | P0 |
| Memory MCP | Seeder/triage split live | VERIFIED_LIVE | No auth/scoping/NetPol; open delete | NetworkPolicy + curator-only | P0 |
| KB/querydoc | Full pipeline + curation | VERIFIED_STATIC | Citations hardcoded; query blocked | One real hit + NO_RELEVANT | P1 |
| HITL | Suspend real | GAP | Callback forgeable; tier self-classified | HMAC + config tiers | P0 |
| Chaos testing | Real Litmus + recovery | VERIFIED_LIVE | SA cluster-wide delete; unconnected | Namespace-scope Role | P1 |
| Lifecycle eval | Scorer + hard gates | VERIFIED_STATIC | Hand-written inputs; trusts self-report | Wire to real traces | P1 |
| ServiceNow/Teams closure | Metric contract only | DESIGN_INTENT | No integration exists | Decide: build or drop | P2 |
| BYO-agent onboarding | CRDs + 7 policies | VERIFIED_STATIC | Policy bypassable; tool-server unchecked | Fix rules; CI check | P0 |

---

## 5. Missing Specialists / High-Value Improvements

**Immediate (days):**
- Redact leak; prefix synthetic markers; strip write tools from 3 agents; NetworkPolicy memory; Argo TTL/retention; aks-mcp Secret rule; canonical status page.

**Next sprint:**
- One real end-to-end flagship run (alert → real Grafana/K8s → HITL block → GitOps MR → eval score).
- HITL hardening (HMAC callback, config tiers, negative test).
- Vector routing consume; quarantine topic; fan-out VRL.
- MTTA/MTTR from Argo timestamps.

**Platform roadmap:**
- Model-outage degraded mode (deterministic workflows without LLM).
- Rollback/safe-revert bundle.
- Node + workload-identity + storage + control-plane read-only specialists.
- Ticket-closure gate.

---

## 6. 30/60/90 Day Roadmap

**Days 1–7:** Redact leak, strip legacy write agents, drop aks-mcp Secret read, NetworkPolicy memory, Argo TTL, `DEMO_SIMULATED_` labels, fix SOW paths, declare canonical pipeline + status page.

**Days 8–30:** HITL hardening (HMAC, config tiers, negative tests); ToolGrant fixes; onboarding allowlists; flagship live run; routing consume; failover probe; Litmus namespace-scope.

**Days 31–60:** Real MTTA/MTTR in dashboard; eval harness fed real traces; weekly game day with committed evidence; two more live specialists; first app-team BYO; ServiceNow decision.

**Days 61–90:** HA pass (replicas, PDBs); degraded-mode runbooks; audit-trail proof; rollback bundle; specialists onboarded; prod limited to read-only triage + GitOps-proposal-only.

---

## 7. Questions For The Team

1. Ingestion: which stack is canonical? Can others be deleted?
2. ServiceNow: attainable in 60 days? If not, deflection value story lives on GitLab?
3. agentgateway version at work — ships MCP authz + A2A targets?
4. Agent platform on-call + incident process — who owns it?
5. cert-manager/test-ns write agents — intentional or legacy debt?
6. GitLab token scopes on four write-capable agents?
7. Prod tier policy: auto-execute tiers (T0/T1) or GitOps-proposal-only?
8. KB residency: OpenAI embedding egress acceptable or Azure-only?
9. Actual SRE pain points — match the specialist gap map?
10. Azure SRE Agent available at work — hybrid split live or parked?
11. Memory curation day-to-day — named curator role?
12. Evidence bar known to stakeholders — live proofs are home-lab, not work-lab?

---

## 8. Final Recommendation

Smallest change set to credible AKS SRE platform:

1. **Close enforcement holes** — forgeable HITL, self-classified tiers, unauthenticated memory, bypassable ToolGrant policy.
2. **Ship one real flagship run** — real alert → live specialist → genuine HITL block (with rejected-approval negative test) → real MR → lifecycle eval score.
3. **Strip legacy write agents + aks-mcp Secret grant.**
4. **One ingestion pipeline + one status page** — deprecate duplicates.
5. **Redact leak + harden leak-scan.**
6. **Eval loop consumes real traces** with independent verification artifact.

Architecture is sound. Needs its own rules enforced, one honest proof, and half as many copies of the truth.

---

**Generated:** 2026-07-05 by Fable 5 (Kagent AKS critical review)
**Method:** Six parallel read-only reviewers over docs/agents/platform/observability/bundles/infra, with evidence classification (VERIFIED_LIVE / VERIFIED_STATIC / DESIGN_INTENT / GAP / UNKNOWN).
**Deliverable:** Compact synthesis for programme lead + platform team decision.

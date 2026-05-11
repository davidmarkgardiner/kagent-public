# Roadmap — From Standalone Install to kagent Integration

Where Container Network Insights Agent fits in the broader AI platform, and
the plan for folding its diagnostic capabilities into our kagent triage system.

## Current state — Phase 1 (this directory, MS agent only)

- Microsoft Container Network Insights Agent installed as AKS extension
- Used by SREs interactively in the browser
- No integration with kagent, Argo Workflows, Teams approval, or lessons-learned DB
- Parallel path to the kagent triage/remediation pipeline

## Problem we're solving

Today the kagent pipeline handles general SRE triage well but is thin on
networking-specific diagnostics (DNS, CNI, packet drops, Hubble flows).
Microsoft's agent covers this depth but isn't programmatically integratable
(browser-only). We want the depth without giving up the automation loop.

## Phase 2 — Networking-triage kagent agent

Build a dedicated kagent Agent that mirrors the diagnostic patterns of the MS
agent, using AKS MCP (which both agents sit on top of) as the execution layer.

### Scope

| Capability | Cover in Phase 2? |
|---|---|
| DNS diagnostics (CoreDNS, Cilium FQDN policies, NodeLocalDNS) | ✅ |
| K8s networking (pod/svc/endpoint/policy analysis, Hubble flows) | ✅ |
| Packet drop analysis (NIC ring buffers, softnet, SoftIRQ) | ⚠️ Requires our own debug DaemonSet; defer to Phase 2b |
| Host-level network stats | ⚠️ Same — defer |

### Components to build

```
ai-platform/
├── container-network-insights/      ← YOU ARE HERE (Phase 1)
│   └── README / install / prompts
│
├── agentgateway/                    ← already exists
│
└── kagent-agents/                   ← NEW in Phase 2
    └── networking-triage-agent/
        ├── agent.yaml               (kagent Agent resource)
        ├── system-prompt.md         (derived from MS agent's diagnostic patterns)
        ├── skills/
        │   ├── dns-diagnostics/SKILL.md
        │   ├── k8s-networking/SKILL.md
        │   └── cilium-policy-review/SKILL.md
        └── README.md
```

### Agent design

```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: networking-triage-agent
  namespace: kagent
spec:
  description: Specialist agent for AKS networking diagnostics
  type: Declarative
  skills:
    gitRefs:
      - url: https://github.com/<org>/kagent-skills.git
        ref: main
        path: networking-triage-agent/skills
  declarative:
    modelConfig: agentgateway-azure-openai   # GPT for quality reasoning
    memory:
      modelConfig: agentgateway-qwen         # Qwen for cheap embeddings
      ttlDays: 30
    systemMessage: |
      You are a networking-specialist SRE agent for AKS.
      Use structured diagnostic workflows for DNS, K8s networking, and
      Cilium policies. Cite evidence from kubectl/cilium/hubble output.
      Never speculate — if evidence is insufficient, say so.
      Output a structured JSON report.
    tools:
      - type: McpServer
        mcpServer:
          apiGroup: kagent.dev
          kind: RemoteMCPServer
          name: aks-mcp
          toolNames:
            - call_kubectl
            - kubectl_get_resources
            - kubectl_describe_resource
            - cilium_status
            - cilium_policy_get
            - hubble_observe       # if ACNS enabled
          requireApproval: []       # read-only tools, no approval needed
      - type: McpServer
        mcpServer:
          apiGroup: kagent.dev
          kind: RemoteMCPServer
          name: lessons-mcp
          toolNames:
            - lessons_search       # retrieve past networking incidents
```

### Integration with Argo Workflows

```
Alert (prometheus → argo-events)
     │
     ▼
Argo Workflow: net-triage-workflow
     │
     ├─ STEP 1: classify alert as networking-related?
     │          (simple regex / label check, or Qwen classifier)
     │
     ├─ STEP 2: invoke networking-triage-agent via A2A
     │          → structured JSON report with root cause
     │
     ├─ STEP 3: tier classification (HITL framework)
     │          → T0/T1/T2/T3/T4 based on recommended action
     │
     ├─ STEP 4: Teams approval gate (if T2+)
     │
     ├─ STEP 5: remediation-agent executes (T0/T1) or
     │          SRE clicks approve → remediation-agent executes
     │
     └─ STEP 6: verify + write lesson to shared_lessons DB
```

## Phase 2b — Host-level diagnostics (later)

The MS agent has a Linux Networking plugin for NIC ring buffers, softnet,
etc. Replicating this requires:

- A DaemonSet with `hostNetwork`, `hostPID`, `NET_ADMIN` (like MS agent does)
- A small MCP server that execs into those pods on demand
- Delta-measurement logic (before/after snapshots)

Non-trivial. Defer until the agent proves its value on DNS + K8s networking
categories first.

## Phase 3 — Feedback loop with MS agent

SREs use the MS agent for deep interactive debugging. The diagnostic reports
they generate are gold-standard examples. Pipeline:

```
SRE uses MS agent in browser
     ↓
Copies diagnostic report into a ticket with tag `net-diag`
     ↓
Nightly Argo workflow reads tagged tickets
     ↓
Qwen summarizes into lesson format
     ↓
Writes to shared_lessons pgvector DB
     ↓
Our networking-triage-agent retrieves similar past lessons
     via lessons_search MCP tool on next incident
```

Over time, our kagent agent learns from the MS agent's interactive sessions
without any direct integration between them.

## What we WON'T build

- ❌ Programmatic wrapper around the MS agent (no API, would be brittle browser automation)
- ❌ Replacement for the MS agent in the browser (leave it as a power-user tool)
- ❌ Deep integration with Microsoft's extension (it's theirs; they may change it)

## Success metrics

How we'll know Phase 2 worked:

| Metric | Target |
|---|---|
| % of networking alerts auto-triaged (no human diagnosis needed) | > 60% |
| Mean time from alert → triage-agent-report | < 2 min |
| SRE time spent on routine DNS/policy diagnostics | ↓ 50% |
| Lessons DB entries from networking incidents | Growing by 5+/week |
| MS agent usage | Steady or declining as kagent covers routine cases |

## Timeline estimate

- **Phase 1 install + team adoption:** 1 week (install + prompts training)
- **Phase 2 networking-triage-agent build:** 2-3 weeks (prompt engineering is
  the expensive part; plumbing is ~1 day)
- **Phase 2b host-level diagnostics:** 2-4 weeks if we build it (likely defer)
- **Phase 3 MS-agent feedback loop:** 1 week (depends on shared_lessons DB existing)

## Dependencies on other workstreams

| Depends on | Status |
|---|---|
| kagent installed on cluster | ✅ done |
| agentgateway + ModelConfigs | ✅ done on red cluster; pending at work |
| AKS MCP server | ✅ in place |
| shared_lessons pgvector DB | ❌ not yet (Phase 2-adjacent) |
| lessons-mcp server | ❌ not yet (Phase 2-adjacent) |
| HITL / Argo approval framework | ❌ design discussed, not built |

Phase 2 can start as soon as Phase 1 proves useful and the MS agent's
diagnostic patterns are documented in prompt form. It doesn't strictly need
`shared_lessons` — that's Phase 3's job.

## Open questions

- **Namespace ownership:** which team owns the `networking-triage-agent`
  definition? Platform SRE? The same team that owns kagent today?
- **Skill source repo:** single `kagent-skills` repo with all agents, or one
  per agent? (Existing kagent agents seem to share.)
- **Prompt provenance:** if our system prompt is modelled closely on MS
  agent's observed behavior, is that a licensing concern? Probably not
  (they're describing a general diagnostic workflow), but worth flagging.

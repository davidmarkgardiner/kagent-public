# ASTHERI/SRE First-Time Walkthrough

Date: 2026-06-04

Purpose: give a first-time ASTHERI or SRE agent a practical, step-by-step route
for bringing an application onto Kagent triage v2, creating safe chaos tests,
showing bounded remediation, and producing evidence through dashboards,
reports, GitLab, knowledge, memory, and lifecycle evaluation.

This walkthrough assumes the operator knows nothing about the repo or triage
system. It starts from the question:

```text
I want to bring my application online.
I want to understand what might go wrong.
I want agents that can triage and remediate safely.
I want chaos to prove the system works.
I want Grafana dashboards, GitLab tickets/MRs, reports, KB, memory, and eval
evidence to show what happened.
```

Do not run this in production. The first live run belongs in an approved
non-production work lab.

## 0. Start Here

Open these first:

1. `WORK-KAGENT-TRIAGE-V2-SRE-FIRST-CONTACT.html`
2. `demos/sre-first-contact/README.md`
3. `WORK-KAGENT-TRIAGE-V2-SRE-OPERATING-GUIDE.md`
4. `WORK-KAGENT-TRIAGE-V2-WORK-AGENT-CHECKLIST.md`

Then run the local dry-run verifier:

```bash
bash demos/sre-first-contact/scripts/verify-demo.sh
```

Expected result:

```text
SRE_FIRST_CONTACT_VERIFY: passed
```

That proves the first-contact demo package is internally consistent before a
work-lab agent adapts it to a real application.

## 1. Understand The Roles

| Role | What it does | What it must not do |
|---|---|---|
| SRE/ASTHERI operator | Describes the app, approves chaos, reviews evidence | Run production chaos without approval |
| `sre-first-contact-agent` | Front-door liaison for intake, workflow coordination, evidence lookup, A2A, and eval collection | Directly mutate Kubernetes or invent missing proof |
| Read-only app triage agent | Understands one app/namespace and gathers evidence | Apply, patch, delete, exec, or write GitLab |
| Bounded remediation agent | Proposes non-prod remediation after HITL | Delete resources, exec into pods, bypass GitOps/HITL |
| Smart-triage specialists | Fan out across Kubernetes, Grafana, GitOps, KB, policy, network, trace | Claim live evidence unless they captured it |
| Eval/review-manager | Scores the run and routes weak evidence | Close work when hard gates fail |

The important safety boundary: triage agents diagnose; remediation agents
propose or execute only bounded non-production actions after HITL and through
approved workflows/GitOps.

## 2. Collect The Application Profile

Start with an application profile. The demo uses:

```text
demos/sre-first-contact/profiles/checkout-api.application-profile.yaml
```

For a real app, replace the public placeholders and app name with work-lab
values:

| Field | Example | Why it matters |
|---|---|---|
| Application name | `checkout-api` | Agent identity and reports |
| Namespace | `checkout-dev` | Scope boundary |
| Deployment/service refs | `deployment/checkout-api`, `service/checkout-api` | Kubernetes evidence |
| Owner/escalation | `{{TEAM_OWNER}}` | HITL and reporting |
| Grafana dashboard | `checkout-api-service-health` | Visual evidence |
| GitLab project/path | `{{GITLAB_PROJECT}}` | sandbox MR/ticket path |
| KB runbooks | `docs/platform-kb/runbooks/...` | querydoc citations |
| Memory policy | `curator-only` | safe learning loop |
| Forbidden tools | delete/exec | safety guardrail |

Prompt to use:

```text
I am an SRE bringing {{APP_NAME}} onto Kagent triage v2.
Read the application profile.
Identify likely failure modes.
Tell me which agents, tools, dashboards, GitLab paths, KB docs, memory paths,
chaos tests, HITL gates, and eval reports are required.
Do not propose production chaos.
Do not grant delete or exec tools.
```

## 3. Generate The Failure-Mode Catalogue

Use the app profile to produce likely failure modes. The demo file is:

```text
demos/sre-first-contact/failure-modes/checkout-api.failure-modes.yaml
```

The first catalogue should include:

| Failure mode | What to prove |
|---|---|
| CrashLoop after bad config/image | Kubernetes events, logs, recent GitLab/GitOps change, KB citation |
| Dependency timeout | Grafana latency/error signals, logs/traces, runbook citation |
| Pod loss and recovery | ChaosResult, pod event, replica recovery, eval score |

The selected first demo should be low risk. In this package, that is
`pod-loss-single-workload`, implemented as a lower-env pod-delete test.

## 4. Create The Front-Door SRE Agent

Use:

```text
demos/sre-first-contact/expected/sre-first-contact-agent.yaml
```

This is the agent the SRE can liaise with. It coordinates the demo but does not
hold broad mutation power.

It may use tools for:

- Argo workflow submission/status/logs
- Grafana metric/log/dashboard lookup
- querydoc KB lookup
- memory read/recall
- read-only GitLab lookup
- A2A coordination with specialist agents

Workflow submission is allowed only for approved non-production templates. The
front-door agent coordinates workflow execution; the workflow service account
holds the resource-changing permissions.

It must not hold:

- Kubernetes delete
- Kubernetes exec
- broad direct apply
- broad GitLab write
- production chaos controls

## 5. Create The App Agents

Use:

```text
demos/sre-first-contact/requests/checkout-triage-agent-request.yaml
demos/sre-first-contact/requests/checkout-remediation-agent-request.yaml
demos/sre-first-contact/expected/checkout-triage-agent.yaml
demos/sre-first-contact/expected/checkout-remediation-agent.yaml
demos/sre-first-contact/expected/checkout-toolgrants.yaml
```

The expected split:

| Agent | Scope | Tools |
|---|---|---|
| `checkout-triage-agent` | Read-only app triage | Kubernetes get/describe/logs/events, Grafana, querydoc, memory read |
| `checkout-remediation-agent` | Bounded non-prod remediation planning | Read tools, annotate/patch if HITL approved, sandbox GitLab MR, curator memory path |

Run the verifier before applying anything:

```bash
bash demos/sre-first-contact/scripts/verify-demo.sh
```

Look for:

```text
FORBIDDEN_TOOLS_ABSENT: yes
TOOLGRANT_COVERS_AGENT_TOOLS: yes
```

## 6. Prepare The Chaos Test

Use:

```text
demos/sre-first-contact/chaos/checkout-api-pod-delete.chaostest.yaml
```

The test should prove:

- target is non-production
- target namespace is explicit
- workload has chaos opt-in
- HITL is required
- rollback is known
- abort conditions are named
- Grafana signals are known
- lifecycle eval benchmark is `8`
- memory learning is curator-only
- KB update is HITL-gated MR

Validate the chaos spec:

```bash
python3 chaos/reliability/scripts/validate-reliability-configs.py \
  demos/sre-first-contact/chaos/checkout-api-pod-delete.chaostest.yaml
```

Expected:

```text
RELIABILITY_CONFIG_VALID: yes checked=1
OUTPUT_SANITIZED: yes
```

## 7. Run The Work-Lab Demo

Use this prompt with the SRE front-door agent:

```text
I am an ASTHERI/SRE operator bringing {{APP_NAME}} onto Kagent triage v2.

Use the application profile to generate failure modes.
Create or verify the read-only triage agent and bounded remediation agent.
Verify ToolGrants and policy controls.
Request HITL approval for the approved lower-env chaos test.
Inject the pod-delete scenario.
Run smart triage fan-out.
Gather Kubernetes, Grafana, GitLab/GitOps, KB, memory, and policy evidence.
Hold remediation behind HITL.
Propose GitOps/workflow remediation only.
Verify recovery.
Run lifecycle eval.
Route weak evidence to review-manager.
Return the evidence bundle.
```

The first live work-lab run should return:

```text
STATUS: PASS | PARTIAL | BLOCKED
APP:
TARGET_NAMESPACE:
SRE_FRONT_DOOR_AGENT_STATUS:
BYO_AGENT_STATUS:
TOOLGRANT_STATUS:
CHAOS_RESULT:
SMART_TRIAGE_RESULTS:
GRAFANA_EVIDENCE:
GITLAB_OR_GITOPS_EVIDENCE:
KB_EVIDENCE:
MEMORY_EVIDENCE:
HITL_EVIDENCE:
EVAL_SCORE:
REVIEW_MANAGER_ROUTE:
REPORT_LINK:
SAFETY_CHECK:
GAPS:
NEXT_ACTION:
```

## 8. What The Agent Should Show During The Demo

### Runtime Proof

Show:

- kagent namespace and Agent status
- Argo Workflows status
- agentgateway/ModelConfig path
- Grafana MCP availability
- GitLab MCP/sandbox auth model
- querydoc MCP availability
- memory MCP availability
- Litmus or equivalent chaos tooling

### Chaos Proof

Show:

- HITL approval before chaos continuation
- ChaosEngine/ChaosResult or equivalent result
- target workload disruption
- target workload recovery
- smart-triage workflow name
- specialist node table

### Remediation Proof

Show:

- whether remediation was required
- why the remediation path was safe
- HITL approval ID
- GitOps proposal, workflow action, or sandbox MR
- verification after remediation

If the target recovered without mutation, the correct remediation may be:

```text
No mutation required. Recovery verified. File report and update memory/KB only.
```

That is still a valid remediation outcome.

In that case, return:

```text
GITOPS_PROPOSAL_CREATED: not_required
```

### Visual Evidence

Show:

- Grafana dashboard link
- metric query result
- log query result
- optional trace or network fallback marker
- dashboard screenshot if available

Minimum Grafana evidence:

```text
GRAFANA_EVIDENCE_CAPTURED: yes
dashboard: {{GRAFANA_DASHBOARD}}
metric_query: {{PROMQL}}
log_query: {{LOGQL}}
```

### GitLab Evidence

Show one of:

- sandbox MR with proposed GitOps remediation
- issue/ticket comment with run summary
- explicit `BLOCKED` reason if scoped auth is missing

Do not use broad personal tokens. Use a sandbox project and scoped auth.

### KB/querydoc Evidence

Show:

- cited runbook hit, or
- explicit `NO_RELEVANT_DOCS` fallback

Do not invent citations. If querydoc is unavailable, return `BLOCKED` with the
missing MCP server, embedding key, or endpoint.

### Memory Evidence

Show:

- memory recall across the agent/session boundary
- curator-mediated learning update
- no direct uncontrolled memory write

Expected marker:

```text
MEMORY_LEARNING_CAPTURED: curator-only
```

### Eval Evidence

Use:

```text
demos/sre-first-contact/eval/checkout-api-demo-evidence-contract.yaml
```

The eval must fail if:

- remediation happened before HITL
- Grafana evidence is missing without fallback
- GitLab write happened outside sandbox/GitOps proposal path
- delete or exec tools were granted
- recovery verification is missing
- production target was selected

## 9. Reporting Package

Every run should produce a report that SRE can share.

Required report sections:

1. Summary verdict.
2. App and namespace.
3. Trigger source.
4. Failure mode.
5. Chaos result.
6. Smart-triage specialist results.
7. Grafana evidence.
8. GitLab/GitOps evidence.
9. HITL approval details.
10. Recovery/remediation result.
11. Lifecycle eval score.
12. Review-manager route if below threshold.
13. Memory/KB learning actions.
14. Gaps and next action.

Useful destinations:

| Destination | Purpose |
|---|---|
| GitLab issue/MR/comment | Engineering audit trail |
| Grafana annotation | Timeline marker on dashboard |
| Markdown report | Portable evidence |
| Teams/Slack notification | SRE visibility |
| Eval result JSON/Markdown | deterministic scoring |

## 10. Useful Questions For The SRE

Ask these before the first run:

1. Which application and non-production namespace are we onboarding?
2. Who owns the application and approves chaos?
3. What is the safest first failure to inject?
4. What dashboard should prove impact and recovery?
5. What GitLab project is safe for sandbox MR/ticket evidence?
6. Which runbooks should querydoc search?
7. Should memory learning be captured after this run?
8. What is the rollback if the chaos test does not recover?
9. What is the maximum acceptable disruption window?
10. What evidence would convince the team this is working?

## 11. Common Blockers

| Blocker | What to return |
|---|---|
| Grafana MCP unavailable | `BLOCKED: missing Grafana MCP endpoint or datasource` |
| GitLab auth not scoped | `BLOCKED: scoped sandbox GitLab auth required` |
| querydoc unavailable | `BLOCKED: querydoc MCP or embedding key missing` |
| memory backend unavailable | `PARTIAL: memory proof deferred; no write attempted` |
| HITL callback unavailable | `BLOCKED: approval path missing` |
| chaos CRDs missing | `BLOCKED: Litmus/equivalent CRDs missing` |
| unsafe tools granted | `FAIL: forbidden tool grant found` |
| eval below threshold | `PARTIAL: routed to review-manager` |

## 12. Completion Criteria

The walkthrough is complete when the SRE can show:

```text
APP_PROFILE_PARSED: yes
FAILURE_MODES_GENERATED: yes
SRE_FRONT_DOOR_AGENT_READY: yes
BYO_TRIAGE_AGENT_READY: yes
BYO_REMEDIATION_AGENT_READY: yes
TOOLGRANT_POLICY_VERIFIED: yes
CHAOS_APPROVED: yes
CHAOS_RESULT_VERDICT: Pass
SMART_TRIAGE_FANOUT: completed
GRAFANA_EVIDENCE_CAPTURED: yes
HITL_STATUS: resumed
GITOPS_PROPOSAL_CREATED: yes|not_required
RECOVERY_VERIFIED: yes
LIFECYCLE_EVAL_PASSED: yes
MEMORY_LEARNING_CAPTURED: curator-only
KB_UPDATE_PATH: hitl-gated-mr
OUTPUT_SANITIZED: yes
```

If any line cannot be proven live, the agent should return `PARTIAL` or
`BLOCKED` with the exact missing value and next action.

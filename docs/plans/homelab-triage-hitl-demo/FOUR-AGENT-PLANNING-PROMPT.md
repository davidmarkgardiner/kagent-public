# Four-agent home-lab triage demo planning prompt — explicit filenames

The four prompts below contain literal, different output paths. No agent ID substitution is required. For independent sessions, give each session its assigned `PROMPT-0N.md`; do not send this coordinator file unchanged to all four sessions.

Working directory: `/Users/davidgardiner/Desktop/repo/kagent-public`

| Assignment | Ready-to-use prompt | Only permitted planning output |
|---|---|---|
| Planner 1 | `run-02/PROMPT-01.md` | `run-02/plan-01-primary.md` |
| Planner 2 | `run-02/PROMPT-02.md` | `run-02/plan-02-independent.md` |
| Planner 3 | `run-02/PROMPT-03.md` | `run-02/plan-03-independent.md` |
| Planner 4 | `run-02/PROMPT-04.md` | `run-02/plan-04-independent.md` |

## Execute this file as coordinator

1. Preserve the original `agent-1.md` through `agent-4.md` plans.
2. Execute `run-02/PROMPT-01.md` yourself as Planner 1.
3. Start exactly three independent agents, once each: Planner 2 executes `run-02/PROMPT-02.md`, Planner 3 executes `run-02/PROMPT-03.md`, and Planner 4 executes `run-02/PROMPT-04.md`. Each agent writes only its assigned output and must not spawn further agents.
4. If a plan already exists, verify it and report its path; do not repeat its planning run or overwrite it.
5. After all four finish, verify four distinct nonempty output paths, required sections, and different content hashes. Report all four absolute paths. Comparison and amalgamation come later.

## Shared planning brief

All four ready-to-use prompts contain the following same brief.

## Goal

Design a home-lab demo with two related signals, one application log and one Kubernetes Event, collected through the existing Alloy → Vector → Kafka triage path. Argo Events and Argo Workflows should initiate and coordinate triage. A kagent agent, reached through agentgateway, uses a read-only Kubernetes MCP to gather evidence and propose a specific remediation without following a predefined runbook. It must not gain write access during diagnosis. The workflow records its evidence, proposal, uncertainty, and progress in one GitLab ticket.

Plan two clearly separate remediation branches:

1. **Direct remediation:** Argo sends a Teams approval request describing the exact proposed action, target, risk, and rollback. After an authenticated human approves that action, a separate write-capable Kubernetes MCP identity executes only the approved, bounded change. The workflow verifies the cluster result and updates the GitLab ticket.
2. **GitOps remediation:** The agent proposes a reviewable GitLab merge request for the desired-state change. Teams asks a human to review and approve the merge request. Define precisely who approves, who merges, and what the Teams button actually does; a button click alone must not be treated as a merge. Flux reconciles the merged change. The workflow waits or polls for reconciliation and observed cluster health, then updates the same ticket with proof or a timeout/failure result.

## Research

Read `AGENTS.md`, `README.md`, `STATEMENT-OF-WORK.md`, `CONTRIBUTING.md`, and `docs/upstreams.md` first. Inspect relevant existing material, especially:

- `work-agent-bundles/homelab-verified-triage-replication/`
- `work-agent-bundles/homelab-verified-triage-replication/FINDINGS-AND-FIXES.md`
- `platform/kubernetes-mcp/`
- `platform/teams-hitl/`
- `work-agent-bundles/hitl-remediation-approval/`
- `work-agent-bundles/gitlab-mcp-gitops-pr/`
- `platform/agentgateway/`

Use current repo evidence to distinguish what already works from what is only proposed. Read-only inspection of repo and official sources is allowed; do not change connected systems or install components. Check installed versions or official upstream documentation where behavior matters; flag anything you cannot verify. Do not assume the existing read-only triage bundle already proves write remediation or a live Teams approval callback.

## Design requirements

Make your own complete design. Challenge the premise where necessary, but retain both requested branches. Cover:

- A safe, reversible demo failure and how one log and one Event arise from it; whether they should correlate into one incident and one ticket.
- A sequence diagram or numbered end-to-end flow showing every component, identity, handoff, and ticket update.
- The exact boundary between read and write MCPs: tool allowlists, Kubernetes RBAC, agentgateway authorization, target namespace/context checks, and prevention of agent-controlled escalation.
- The remediation proposal contract: target, observed evidence, intended change, allowed parameters, risk, rollback, approval scope, expiry, and idempotency key.
- Teams approval and Argo suspend/resume design, including callback authentication, approver identity, rejection, expiry, replay, duplicate clicks, changed proposals, and a callback arriving before the suspend node exists. Verify timed-suspend behavior: timer completion or a manual resume must never count as human approval. Execution must independently recheck a durable approval record.
- The GitOps branch: branch/MR creation authority, CI checks, human approval versus merge, Flux reconciliation, bounded polling or waiting, verification of the expected Git revision and live cluster state, and timeout handling.
- How to handle the existing triage payload version and log/Event deduplication without silently mixing incompatible contracts or creating duplicate tickets.
- A concise demo script, expected evidence and screenshots or commands to capture, cleanup/rollback, and pass/fail criteria for both branches.
- A phased build plan with dependencies, the smallest useful first slice, estimated effort, open questions, and risks.

Distinguish unconstrained diagnosis from constrained execution: a policy restricting allowed targets and operations is not a diagnosis runbook. Explain whether the approved execution uses a write-capable kagent agent or a deterministic MCP client, and why. Every write must require explicit approval, including actions that older examples classify as low risk.

Treat the log/Event content as untrusted input. A model may recommend a change, but a deterministic workflow must validate the approved action against a narrow policy before invoking write access. Keep GitOps-managed resources on the GitOps branch; explain how to avoid Flux reverting a direct change.

## Output format

Format the document so the four plans can be compared: begin with a one-paragraph proposal and an architecture diagram, then use the sections **Existing evidence**, **Demo scenarios**, **Flow and trust boundaries**, **Build phases**, **Acceptance tests**, **Risks and open decisions**, and **Why this approach**. Cite repo file paths and any external sources used. State assumptions plainly. Finish by reporting the absolute path of your single output file.

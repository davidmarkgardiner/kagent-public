# Teams Approve/Deny Cards and kagent Session Resume

**Purpose:** Define a safe design for asking a human in Microsoft Teams to approve or deny one agent action, then continuing the correct delivery workflow. This document does not claim that a Teams adapter is already installed.

## What kagent provides

| Statement | Classification |
| --- | --- |
| kagent supports `requireApproval` on selected tools. A gated tool pauses until a human approves or rejects it. | **Verified current capability** — [Human-in-the-Loop guide](https://kagent.dev/docs/kagent/examples/human-in-the-loop) |
| On rejection, kagent returns the rejection reason to the agent so it can respond or adapt rather than execute the rejected tool. | **Verified current capability** — [Human-in-the-Loop guide](https://kagent.dev/docs/kagent/examples/human-in-the-loop) |
| A Hermes AgentHarness on Agent Substrate maps tool-approval prompts into kagent's human-in-the-loop flow. | **Verified current capability** — [Agent Harness](https://kagent.dev/docs/kagent/concepts/agent-harness) |
| kagent has a native Teams Adaptive Card approval adapter that securely resumes an arbitrary external session. | **Unknown / requires validation** — current public examples document UI approval and several chat integrations, not this adapter. |

## Two valid approval patterns

| Pattern | Best fit | What resumes | Status |
| --- | --- | --- | --- |
| Existing Teams to Argo callback | A delivery/remediation workflow where Argo owns the durable state and execution boundary | An Argo Workflow suspend node | **Verified checked-in design** — see [platform/teams-hitl](../../../platform/teams-hitl/README.md); live deployment still requires validation. |
| Teams to kagent approval bridge | A live agent/harness conversation where kagent owns the pending tool approval | The same kagent/Hermes approval/session path | **Proposed design** — requires a version-specific API contract and POC. |

## Proposed direct-resume flow

```text
Agent proposes one gated tool call
  -> kagent pauses at requireApproval
  -> approval bridge creates Teams Adaptive Card
  -> authorised human selects Approve or Deny
  -> Teams callback reaches the bridge
  -> bridge validates decision and correlation binding
  -> bridge submits the decision to kagent's supported confirmation path
  -> same pending session continues or receives the deny reason
  -> evidence is attached to Hermes/Kanban and, where relevant, Teams
```

The phrase **same session** means the action must be correlated to the pending kagent approval/session identity, not that a new chat is created and asked to repeat the task. The exact identifier and confirmation API are **unknown / requires validation** until tested against the installed kagent version.

## Approval binding contract

**Proposed design:** The bridge must persist one immutable approval record before sending a card. It must reject any callback that does not match every binding below.

| Binding | Why it matters |
| --- | --- |
| `approval_id` and one-time nonce | Prevent replay and duplicate approval. |
| kagent session/task and pending tool-call identity | Prevent a click approving a different conversation or tool call. |
| Delivery ID and artifact hash | Bind the decision to the reviewed plan, manifest, Helm diff, or command. |
| Exact cluster context, namespace, verb, and resource/release | Prevent scope substitution after the card is displayed. |
| Approver Entra identity and allowed group/role | Ensure the person clicking the button is authorised. |
| Issued/expiry timestamps | Prevent a stale card from acting later. |
| Decision and optional deny reason | Preserve the audit trail and let the agent adapt safely. |

## Fail-closed behaviour

| Event | Required outcome | Classification |
| --- | --- | --- |
| Approve is valid and current | Resume only the bound pending action, then record execution evidence | **Proposed design** |
| Deny | Send the reason to the pending agent/session; do not invoke the tool | **Verified current capability** for kagent denial handling; **Proposed design** for the bridge |
| Callback is expired, duplicated, unsigned, unauthorised, or does not match the binding | Reject it and leave the action unexecuted | **Proposed design** |
| Teams or bridge is unavailable | Timeout/block the pending action; alert the owner; do not auto-approve or bypass | **Proposed design** |
| kagent session is no longer resumable | Mark the approval unusable, create no new execution session automatically, and ask the user to start/review a fresh request | **Proposed design** |

## POC acceptance criteria

**Proposed design:** Use one non-production, reversible, namespaced write test and prove these conditions before adopting direct resume:

1. The agent reaches a real `requireApproval` pause for the intended tool.
2. The Teams card shows a human-readable, redacted summary and exact action hash.
3. An authorised Approve resumes that pending action exactly once and produces kagent/controller plus Kubernetes evidence.
4. Deny returns a reason to the agent and changes nothing in the namespace.
5. Duplicate, expired, and unauthorised callbacks cannot execute the action.
6. An intentionally delayed decision proves the required session/substrate lifecycle behaviour for the installed version.
7. The card, callback, decision, action result, and cleanup proof are linked from the Hermes/Kanban delivery card.

## Recommendation

**Proposed design:** Use the existing Argo suspend/resume design for workflow-level remediation and delivery pipelines first. Add direct Teams-to-kagent resume only where the user experience genuinely needs a live stateful agent conversation, and only after the POC proves the installed version's confirmation/resume contract.

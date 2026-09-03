# Kagent chat context compaction

This guide explains how to keep long-running kagent conversations below an
LLM's context-window limit. It is written against the repository's stable
kagent `v0.9.10` baseline.

## Short answer

Kagent supports automatic event compaction through the declarative Agent
configuration:

```yaml
spec:
  declarative:
    context:
      compaction: {}
```

Compaction is an Agent runtime setting, not a per-message option. Once it is
configured, it applies whether a conversation is driven through the kagent UI,
the chat API, or A2A.

In `v0.9.10`, the UI exposes **Context > Event Compaction** while creating or
editing an Agent. It does not expose a manual **compact this conversation now**
action in the chat, and the message API does not accept an equivalent flag.

## Runtime requirement

Use the Python declarative runtime:

```yaml
spec:
  type: Declarative
  declarative:
    runtime: python
```

Kagent `v0.9.10` accepts compaction configuration for the Go runtime but warns
that it is not implemented there and will be ignored. Confirm this again
against the installed kagent version before changing runtimes.

## Recommended starting configuration

The following is a starting point for a model with a context window of roughly
260,000 tokens and an Agent that performs database investigation:

```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: "{{AGENT_NAME}}"
  namespace: "{{KAGENT_NAMESPACE}}"
spec:
  type: Declarative
  description: Long-running, read-only database investigation Agent.
  declarative:
    runtime: python
    modelConfig: "{{AGENT_MODEL_CONFIG}}"
    systemMessage: |
      {{SANITIZED_SYSTEM_MESSAGE}}
    context:
      compaction:
        compactionInterval: 3
        overlapSize: 2
        tokenThreshold: 120000
        eventRetentionSize: 12
        summarizer:
          modelConfig: "{{SUMMARIZER_MODEL_CONFIG}}"
          promptTemplate: |
            Summarize the conversation while preserving:
            - exact database, schema, table, view, and column names
            - verified filters, counts, dates, and identifiers
            - decisions, constraints, and unresolved questions
            - tool failures and remaining work
            Distinguish verified facts from assumptions.
            Do not retain bulk row dumps; retain aggregates and references.

            {conversation_history}
```

Tune these values from observed prompt-token usage rather than treating them as
universal defaults. In particular, keep `tokenThreshold` well below the model's
maximum so there is room for system instructions, tool definitions, tool
results, reasoning, and the next answer.

### What the fields do

| Field | Behavior |
|---|---|
| `compactionInterval` | Compacts after this many new user-initiated invocations have been recorded. The CRD default is `5`. |
| `overlapSize` | Retains overlap from preceding invocations so adjacent summaries do not have a hard boundary. The CRD default is `2`. |
| `tokenThreshold` | Requests post-invocation compaction when the most recently observed prompt-token count reaches the threshold. |
| `eventRetentionSize` | Always retains this many of the most recent events. |
| `summarizer` | Uses an LLM to turn the compacted range into a summary. Without it, older compacted events are discarded. |

The UI in `v0.9.10` exposes the interval, overlap, token threshold, and event
retention fields. Configure `summarizer` through the GitOps-managed Agent
manifest so that database facts and decisions are summarized instead of simply
being removed.

## Recovering a conversation already near the limit

Compaction cannot reliably rescue a request that is already too large for the
model. The token threshold is evaluated after an invocation, so the current
request still has to fit.

If the existing conversation can still answer:

1. Ask it for a compact checkpoint containing exact schema facts, decisions,
   verified query findings, assumptions, and unresolved work.
2. Store that checkpoint in an approved durable location.
3. Enable Agent compaction through GitOps.
4. Start a new conversation with the checkpoint and the next concrete question.

If the existing conversation already fails with a context-length error, build
the checkpoint from the visible transcript and verified database evidence, then
start a new conversation. Do not edit kagent's PostgreSQL session records
directly as a recovery mechanism.

## Prevent database results from filling one invocation

Periodic compaction only runs between completed invocations. It cannot prevent
one very large database or MCP tool result from exhausting the window during a
single turn.

Apply limits at the tool and Agent-contract layers:

- select only required columns;
- use filtered aggregates for counts and statistics;
- require bounded pagination or `LIMIT` for row-returning operations;
- return a count and representative sample instead of a full dataset;
- place large exports in an approved data store and return only a reference and
  summary to the model;
- cap tool-result bytes or rows in the MCP server, rather than relying only on
  the prompt to request small results;
- keep the mounted tool allowlist narrow because tool schemas also consume
  context on every model request.

For exact or regulated database work, treat the database and retained evidence
as the source of truth. A compaction summary is intentionally lossy and should
not be the only record of important values or decisions.

## Verification

After the GitOps change reconciles:

1. Confirm the installed Agent CR contains the expected `context.compaction`
   values and `runtime: python`.
2. Confirm the Agent reports its normal Accepted and Ready conditions.
3. Start a disposable conversation and perform more invocations than the
   configured interval.
4. Check the runtime logs for compaction or summarizer failures without printing
   prompts, query results, credentials, or other sensitive data.
5. Confirm the Agent retains the required names, decisions, and unresolved work
   while old bulk results no longer appear in the model input.
6. Send a deliberately bounded database result and verify the Agent remains
   below the intended token threshold.

An accepted manifest or Ready Agent alone does not prove that compaction ran.
Use a disposable conversation and observed runtime behavior as the proof.

## OpenAI Responses API is a separate mechanism

OpenAI also provides `POST /responses/compact` and Responses API context
management for applications that directly own their OpenAI conversation state.
Kagent `v0.9.10` does not expose that provider-specific operation through its
chat message API. Use kagent's Agent-level ADK event compaction for kagent
conversations rather than assuming the OpenAI endpoint is automatically wired
through the ModelConfig or agentgateway route.

## Upstream references

- [Kagent Agents: Context Management](https://kagent.dev/docs/kagent/concepts/agents/#context-management)
- [Kagent v0.9.10 Agent context types](https://github.com/kagent-dev/kagent/blob/v0.9.10/go/api/v1alpha2/agent_types.go)
- [Kagent v0.9.10 Python runtime compaction wiring](https://github.com/kagent-dev/kagent/blob/v0.9.10/python/packages/kagent-adk/src/kagent/adk/types.py)
- [Kagent v0.9.10 Go-runtime feature warning](https://github.com/kagent-dev/kagent/blob/v0.9.10/go/core/internal/controller/reconciler/reconciler.go)
- [OpenAI compact response API](https://developers.openai.com/api/reference/resources/responses/methods/compact)

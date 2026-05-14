# kagent Memory on red

This note records the live findings from a homelab `red`/`kind-homelab` cluster on 2026-05-13.

## Summary

There are three different "memory" scopes to keep separate:

| Scope | What it means | red result |
|---|---|---|
| A2A session memory | Conversation history for one A2A `contextId` | Works |
| Native long-term memory API | Vector memories stored by `agent_name` + `user_id` | Works at API/storage layer |
| Native agent memory tools | `prefetch_memory`, `load_memory`, `save_memory`, auto-save | Not enabled on current agents; blocked by missing embedding-capable ModelConfig |

The live controller is `ghcr.io/kagent-dev/kagent/controller:0.8.0-beta4`. It uses SQLite with vector support enabled:

```text
DATABASE_TYPE=sqlite
DATABASE_VECTOR_ENABLED=true
SQLITE_DATABASE_PATH=/sqlite-volume/kagent.db
```

The SQLite volume is an `emptyDir` with `medium: Memory`, so the current red setup can preserve sessions and memories across chats while the controller pod is alive, but it is not a durable cross-controller-restart setup. For production cross-session and cross-restart memory, use PostgreSQL with vector support.

## Scenario Results

### 1. Same A2A Context Remembers

Test target: `hello-responder-agent`.

Flow:

1. Send token in first message.
2. Reuse returned `contextId` on the second message.
3. Ask for the token.

Evidence:

```json
{
  "contextId": "05aff3df-11c3-4f21-81ee-48695f06f9a9",
  "text": "stored",
  "session": "05aff3df-11c3-4f21-81ee-48695f06f9a9"
}
{
  "contextId": "05aff3df-11c3-4f21-81ee-48695f06f9a9",
  "text": "ORCHID-164422",
  "session": "05aff3df-11c3-4f21-81ee-48695f06f9a9"
}
```

The persisted session had 8 events with system, user, and agent authors.

### 2. New A2A Context Is Isolated

Flow:

1. Start a fresh A2A request without the previous `contextId`.
2. Ask for the previous token.

Evidence:

```json
{
  "contextId": "27e7bc36-f293-478d-8d98-a0b190e723b0",
  "text": "UNKNOWN",
  "session": "27e7bc36-f293-478d-8d98-a0b190e723b0"
}
```

### 3. Native Memory API Stores and Retrieves Across Sessions

The controller API stores memory by `agent_name` + `user_id`. The API requires callers to provide 768-dimensional vectors.

Evidence:

```json
{
  "id": "b0bf21c1-c7c8-4d8a-8156-816bfa0c14ca"
}
[
  {
    "id": "b0bf21c1-c7c8-4d8a-8156-816bfa0c14ca",
    "content": "Codex memory smoke: preferred namespace is platform-dev; scenario token homelab-memory-smoke.",
    "access_count": 0,
    "created_at": "2026-05-13T16:41:56Z",
    "expires_at": "2026-05-14T16:41:56Z"
  }
]
[
  {
    "id": "b0bf21c1-c7c8-4d8a-8156-816bfa0c14ca",
    "content": "Codex memory smoke: preferred namespace is platform-dev; scenario token homelab-memory-smoke.",
    "score": 0.9999999992412703,
    "metadata": {
      "source": "codex-smoke"
    },
    "created_at": "2026-05-13T16:41:56.250167219Z"
  }
]
```

The same test returned `[]` for a different agent name and `[]` for a different user ID, confirming isolation.

### 4. Full Native Agent Memory Is Not Yet Wired on red

Every current Agent in `kagent` has `spec.declarative.memory == null`.

Current ModelConfigs:

| Name | Provider | Model |
|---|---|---|
| `default-model-config` | OpenAI-compatible via LiteLLM | `kimi-for-coding` |
| `kgateway-kubeai` | OpenAI-compatible via kgateway/KubeAI | `gemma2-2b-cpu` |

The LiteLLM model list exposes only `kimi-for-coding`. An embeddings probe against that route did not produce embeddings, so a memory-enabled Agent would not yet be able to use `save_memory`, `load_memory`, `prefetch_memory`, or auto-save reliably.

## How To Reproduce

From this repo, while your kube context points at red:

```bash
bash a2a/scripts/kagent-memory-smoke.sh
```

Or run it remotely on a homelab host:

```bash
ssh <user>@<homelab-host> 'cd <path-to>/kagent-public && bash a2a/scripts/kagent-memory-smoke.sh'
```

## Build Plan To Enable Full Agent Memory

1. Add an embedding-capable ModelConfig, for example `text-embedding-3-small` through an OpenAI-compatible endpoint, Azure OpenAI embeddings, Ollama embeddings, or another provider supported by kagent's embedding client.
2. Enable memory on a low-risk test agent:

   ```yaml
   apiVersion: kagent.dev/v1alpha2
   kind: Agent
   metadata:
     name: memory-test-agent
     namespace: kagent
   spec:
     type: Declarative
     declarative:
       modelConfig: default-model-config
       memory:
         modelConfig: embedding-model-config
         ttlDays: 7
       systemMessage: |
         You are a memory test agent. Use save_memory for explicit user preferences and load_memory when asked to recall them.
   ```

3. Re-run the smoke script plus an agent-level test:
   - Session 1: ask the agent to remember a unique preference.
   - Confirm `/api/memories?agent_name=memory-test-agent&user_id=admin@kagent.dev` contains a saved fact.
   - Session 2: fresh A2A context asks for the preference.
   - Expected: recall succeeds through prefetch/load memory.
4. Move the controller database from in-memory SQLite to durable PostgreSQL before treating the result as cross-restart memory.

## Source Pointers

Current upstream source paths:

- `go/core/internal/httpserver/handlers/memory.go`
- `python/packages/kagent-adk/src/kagent/adk/_memory_service.py`
- `python/packages/kagent-adk/src/kagent/adk/tools/memory_tools.py`
- `python/packages/kagent-adk/src/kagent/adk/tools/prefetch_memory_tool.py`
- `python/packages/kagent-adk/src/kagent/adk/_session_service.py`
- `python/packages/kagent-adk/src/kagent/adk/converters/request_converter.py`


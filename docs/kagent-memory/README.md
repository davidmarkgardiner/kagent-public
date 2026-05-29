# kagent Memory on red

This note records the live findings from a homelab `red`/`kind-homelab` cluster on 2026-05-13.

## Summary

There are three different "memory" scopes to keep separate:

| Scope | What it means | red result |
|---|---|---|
| A2A session memory | Conversation history for one A2A `contextId` | Works |
| Native long-term memory API | Vector memories stored by `agent_name` + `user_id` | Works at API/storage layer |
| Native agent memory tools | `prefetch_memory`, `load_memory`, `save_memory`, auto-save | Not enabled on current agents; blocked by missing embedding-capable ModelConfig |

There is also a fourth repo-local option: the custom
[`memory-mcp`](../memory-integration.md) knowledge graph. It is not native
kagent memory. It is a shared MCP tool server that agents call explicitly.

The live controller is `ghcr.io/kagent-dev/kagent/controller:0.8.0-beta4`. It uses SQLite with vector support enabled:

```text
DATABASE_TYPE=sqlite
DATABASE_VECTOR_ENABLED=true
SQLITE_DATABASE_PATH=/sqlite-volume/kagent.db
```

The SQLite volume is an `emptyDir` with `medium: Memory`, so the current red setup can preserve sessions and memories across chats while the controller pod is alive, but it is not a durable cross-controller-restart setup. For production cross-session and cross-restart memory, use PostgreSQL with vector support.

## Comparison: Native kagent Memory vs Custom MCP Memory

Checked against the public kagent `origin/main` source on 2026-05-21
(`62bd3718`) and this repo's local manifests.

For a platform-level implementation guide that covers working memory, A2A
thread continuity, native kagent memory, shared episodic memory, procedural
memory, and Microsoft-aligned AKS deployment guidance, see
[`platform-memory/README.md`](platform-memory/README.md).

| Option | Best for | Storage / retrieval | Sharing model | Current status in this repo |
|---|---|---|---|---|
| A2A session memory | Remembering one conversation thread | Raw session events in the kagent database | Scoped to one A2A `contextId` | Works on `red` while the controller pod survives |
| Native kagent long-term memory | Per-agent, per-user preferences and facts | kagent controller memory API with 768-dim vectors; Postgres + pgvector for durable installs, SQLite/Turso for local/dev | Isolated by `agent_name` + `user_id` | API works on `red`; full agent tools still need an embedding-capable `ModelConfig` |
| kagent external `Memory` CRD | Referencing an external memory provider | `kagent.dev/v1alpha1` `Memory`; current public CRD supports `Pinecone` | Provider/index dependent | Not wired in this repo |
| Custom `memory-mcp` graph | Shared operational lessons, task history, incidents, and cross-agent context | MCP tools over a persistent knowledge graph (`create_entities`, `add_observations`, `search_nodes`, `open_nodes`, `read_graph`) | Shared by every agent granted the MCP tools | Deployed/wired through `platform/mcp-memory-server/` and `agents/memory-wired/`; has a known concurrent-write limitation |

### Recommendation

Use native kagent memory for low-friction personal or agent-local recall:
preferences, recently learned facts, and facts that should remain isolated to
one agent/user pair. It is the right path when you want `prefetch_memory`,
`load_memory`, `save_memory`, and auto-save to appear automatically from the
agent runtime.

Use the custom `memory-mcp` graph for shared platform memory: incidents,
remediation decisions, reusable findings, handoff state, and development
pipeline outcomes that multiple agents need to see. It is explicit, auditable
at the tool-call level, and can model entities and relationships, which native
kagent memory intentionally does not try to provide.

Do not use native kagent memory as the canonical platform knowledge base. Keep
platform documentation in Git and expose it through the doc2vec/querydoc MCP
pattern. Native memory is for remembered facts, not cited documentation.

### Combined Pattern

The two options can coexist if their responsibilities stay separate:

1. Native kagent memory recalls per-user and per-agent preferences.
2. `memory-mcp` stores shared lessons and entities that other agents may reuse.
3. Querydoc/RAG stores durable platform documentation with source citations.

For production, enable native memory only after the controller uses durable
PostgreSQL with pgvector and an embedding-capable `ModelConfig` exists. Keep
`memory-mcp` writes serialized or add a write queue before high-concurrency use,
because the current implementation can lose concurrent writes.

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

# Knowledge Base Agent Repo Access Pattern

## Question

How does a newly spawned knowledge-base chat agent get access to a Git-backed documentation repository inside its container so it can read the index and answer user questions?

## Short Answer

Containers do not automatically share files. The spawned agent gets repo access through one of these patterns:

1. A shared Kubernetes volume mounted into both the indexing job and the chat agent.
2. A `git-sync` sidecar or init container in the chat agent pod.
3. A dedicated document lookup service or MCP tool that owns the repo checkout and exposes search/read operations.

For this platform, the cleanest production pattern is usually:

```text
Nightly indexer CronJob
  -> pulls Git repo
  -> builds / refreshes index artifacts
  -> writes repo snapshot + index to a read-only shared volume or object store

Knowledge-base chat agent
  -> mounts the snapshot read-only, or calls a docs MCP service
  -> reads INDEX.md first
  -> opens relevant docs / sections
  -> answers with citations

Stale-doc PR agent
  -> separate write-capable component
  -> has GitHub credentials
  -> opens documentation PRs when approved
```

## Recommended Architecture

Use three distinct responsibilities:

| Component | Access | Purpose |
|---|---|---|
| `kb-indexer` CronJob | Git read credentials, write access to snapshot/index storage | Pulls repo nightly and builds the searchable docs snapshot |
| `kb-chat-agent` | Read-only access to snapshot/index | Answers user questions from docs |
| `kb-pr-agent` | GitHub write credentials | Opens stale-doc or missing-doc PRs after user feedback |

This keeps the chat agent simple and safe. It can answer questions, but it does not need credentials that can mutate GitHub.

## Option A: Shared PVC Snapshot

The nightly job writes a working tree and index files to a PersistentVolumeClaim.

```text
PersistentVolumeClaim: kb-repo-cache
  /repo
    docs/platform-kb/INDEX.md
    docs/platform-kb/aks/pod-security.md
    docs/platform-kb/aks/custom-domains.md
  /index
    sections.json
    manifest.json
```

The chat agent mounts the same PVC read-only:

```yaml
volumeMounts:
  - name: kb-repo-cache
    mountPath: /knowledge
    readOnly: true
volumes:
  - name: kb-repo-cache
    persistentVolumeClaim:
      claimName: kb-repo-cache
```

The agent is instructed:

1. Read `/knowledge/repo/docs/platform-kb/INDEX.md`.
2. Select candidate docs from that index.
3. Read only the relevant files or sections.
4. Answer with file path and heading citations.
5. If stale or incomplete, hand off to the PR workflow.

## Option B: `git-sync` Sidecar Per Agent Pod

The chat agent pod includes a sidecar that keeps `/knowledge/repo` updated.

```text
Pod
  git-sync sidecar -> writes /knowledge/repo
  kb-chat-agent    -> reads /knowledge/repo
```

This is simple for freshness, but every agent pod may clone or fetch the repo. It is best when the repo is small or agent pod count is low.

## Option C: Docs MCP / Lookup Service

Instead of mounting Git into every agent, run one small service that owns the repo checkout:

```text
kb-indexer / docs service
  -> keeps repo current
  -> exposes tools:
       docs.search(query)
       docs.read(path, heading)
       docs.refresh()

kb-chat-agent
  -> calls docs.search
  -> calls docs.read
  -> answers user
```

This is often the best fit for kagent-style systems because the spawned agent does not need filesystem assumptions. It just gets a tool grant to the docs MCP service.

## How a New Session Gets Access

When a user starts a chat and the platform spawns a knowledge-base agent, the agent runtime must provide one of these:

- A pod template with the `/knowledge` volume already mounted.
- A sidecar/init container that clones the repo before the agent starts.
- A tool grant that lets the agent call the docs lookup MCP service.

Without one of those, the new container has no access to the repo, even if another job pulled it earlier.

## Suggested Agent Instructions

The knowledge-base agent should have a strict lookup protocol:

```text
You answer platform documentation questions from the mounted knowledge repository.

Lookup protocol:
1. Read /knowledge/repo/docs/platform-kb/INDEX.md first.
2. Identify the smallest set of relevant documents.
3. Read those documents or sections.
4. Answer only from the retrieved docs.
5. Cite each answer with path and heading.
6. If the docs do not answer the question, say that and provide the support ticket path.
7. If the user reports stale or wrong docs, summarize the gap and hand off to the docs PR workflow.
```

## Why Not Let the Chat Agent Run `git pull`?

It can, but it is less clean:

- Every chat session needs Git credentials and network access.
- Concurrent sessions can fight over the same working tree.
- The chat agent gets more permissions than it needs.
- Startup latency increases.
- Reproducibility is weaker because the repo may change mid-session.

If using direct `git pull`, prefer a per-session clone in an ephemeral directory:

```text
/tmp/kb-session/<session-id>/repo
```

That avoids working-tree contention, but still gives every session Git/network responsibility.

## Practical Recommendation

For the first working version:

1. Add `docs/platform-kb/INDEX.md`.
2. Run a nightly `kb-indexer` CronJob that pulls the repo and writes a read-only snapshot/index.
3. Mount that snapshot into the knowledge-base agent at `/knowledge`.
4. Give the chat agent read-only access only.
5. Move PR creation into a separate write-capable PR agent or workflow.

For a more scalable version, replace the shared filesystem with a docs MCP service and grant the spawned knowledge-base agent only `search` and `read` tools.


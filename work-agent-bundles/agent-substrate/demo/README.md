# Reproducing the two Agent Substrate demos on a work cluster

Both demos have already been run and recorded in the home lab. This folder is
the handover: what each one shows, and how to produce the same evidence on a
work cluster.

| Demo | Shows | Reproduce with |
|---|---|---|
| **A. Session continuity** — "What Is an Agent Substrate? How It Sits Under kagent" | An agent stores a marker, its actor suspends, a later request in the same session restores the actor and returns the marker, and a second session gets a different actor that never saw it | This folder: [`run-memory-demo.sh`](run-memory-demo.sh) |
| **B. One front door** — "One Front Door, No Side Doors" | Team agents reach their own MCP backends through dedicated agentgateway listeners; a platform Substrate specialist answers through a fifth listener and its actor returns to Suspended with a new snapshot; rogue credentials and direct paths are refused | The sibling bundle [`kagent-agentgateway-tenant-isolation`](../../kagent-agentgateway-tenant-isolation/), via its `scripts/verify.sh` and `TEST-MATRIX.md` |

For how these two demos map onto a phase 1 work rollout (agentgateway in,
Entra ID deferred), see
[`../../kagent-agentgateway-tenant-isolation/PHASE1-WORK-EVIDENCE.md`](../../kagent-agentgateway-tenant-isolation/PHASE1-WORK-EVIDENCE.md).

### The published demonstrations

| Video | Watch | What it shows | Claims and evidence |
|---|---|---|---|
| A. Session continuity | https://www.youtube.com/watch?v=3BTzlDPiVfk | A marker stored, the actor suspended, the marker returned after restore, a second session isolated | [`VIDEO-CLAIM-MAP.md`](VIDEO-CLAIM-MAP.md), run receipt [`../evidence/LIVE-RUN-2026-09-14.md`](../evidence/LIVE-RUN-2026-09-14.md) |
| B. One front door | https://www.youtube.com/watch?v=eAJpU-oWUdg | Team lanes, the Substrate specialist answering, the actor returning to Suspended | [`../../kagent-agentgateway-tenant-isolation/video/CLAIM-MAP.md`](../../kagent-agentgateway-tenant-isolation/video/CLAIM-MAP.md) |

Watch A before running anything: it is the same sequence this folder
automates. [`RECORDING-RUNBOOK.md`](RECORDING-RUNBOOK.md) is how that video was
captured, including the stop conditions, if the work team wants its own
recording.

The original home-lab runs were kagent `0.10.0-beta7` with Substrate `v0.0.8`
(demo A, 14 September 2026) and kagent `0.10.1` with Substrate `0.0.9`
(demo B, 16 September 2026). The work cluster should pin its own versions and
record them; do not restate the home-lab versions as the work result.

## Demo A: session continuity and suspend/restore

### What it proves

1. A `SandboxAgent` reconciles into an `ActorTemplate` with a golden snapshot.
2. A request resumes the actor, it answers, and it **suspends again with a new
   snapshot**. The `SuspendActor` witness in the ate-api log is the proof, not
   the model's answer.
3. A later request in the **same session** restores the same logical actor and
   the session state is still there: it returns the marker.
4. A **different session** gets a different actor and does not inherit it.

### What it does not prove

- Not tenant isolation or a security assessment. It is functional separation
  between two synthetic sessions. Demo B is the isolation story.
- **Suspension is not deletion.** Snapshots and session data need their own
  retention and erasure controls.
- No density, latency, cost or scale result is measured. Do not repeat the
  upstream "~30x" figure as a work result.

### Prerequisites

- Substrate and kagent installed and healthy. For an air-gapped AKS cluster,
  use [`../aks-hardened/`](../aks-hardened/README.md), including its
  proof-of-concept path.
- `kagent-controller` running with at least one ready replica. It serves the
  A2A route and drives the actor resume.
- A WorkerPool with capacity. The home-lab pool had three replicas; avoid
  parallel fan-out on a small pool, which returns a capacity error. Keep the
  requests sequential, as the script does.
- An approved `ModelConfig` the agent can reach. The demo needs a real model
  answer, so the cluster's model route must work first.
- `kubectl` and `jq`, and a context you have named and checked.

### Run it

```sh
./run-memory-demo.sh --context <ctx> --model-config <approved-modelconfig>
```

Useful options: `--namespace` (default `kagent`), `--ate-namespace` (default
`ate-system`; use `kagent` when Substrate is installed as a kagent subchart),
`--endpoint` and `--token` when calls must go through agentgateway rather than
a port-forward to the controller, `--marker`, and `--keep` to leave the agent
in place.

The script applies [`sandboxagent-demo.yaml`](sandboxagent-demo.yaml), waits
for Ready, then sends three requests and writes a receipt directory containing
`results.tsv`, the raw A2A responses and the lifecycle logs. It deletes the
demo agent afterwards unless `--keep` is given, and touches nothing else.

Expected checks: `R00`–`R02` (pool, agent Ready, ActorTemplate with golden
snapshot), `P01` marker stored, `S01` suspended, `P02` marker returned in the
same session, `S02` suspended again, `P03` the second session does not inherit
the marker, `P04` the two context IDs differ.

Then fill in [`RECEIPT-TEMPLATE.md`](RECEIPT-TEMPLATE.md) from that directory.

### How the calls are made

kagent serves sandbox agents on their own A2A path, separate from ordinary
agents:

```
POST {endpoint}/api/a2a-sandboxes/{namespace}/{agent}/
{"jsonrpc":"2.0","id":"...","method":"message/send",
 "params":{"message":{"kind":"message","role":"user","messageId":"...",
 "contextId":"demo-session-01","parts":[{"kind":"text","text":"..."}]}}}
```

`contextId` is the session. Reusing it is what maps the second request onto
the same logical actor. The answer is the last agent text part in
`.result.history`.

Note for older clusters: on kagent `0.9.x` the ordinary `/api/a2a/...` path
returned 404 for sandbox agents, so this demo needs the `0.10.x`
`/api/a2a-sandboxes` route.

### Status of these commands

**The script was run end to end on the home-lab `red` cluster on
22 September 2026 and all nine checks passed**, against kagent `0.10.1` with
Substrate `0.0.9` in subchart mode (so `--ate-namespace kagent`), a
three-replica WorkerPool and a synthetic agent that was deleted afterwards:

```
R00 WorkerPool present                         kagent/kagent-default replicas=3
R01 SandboxAgent Ready                         Ready=True
R02 ActorTemplate Ready with golden snapshot   phase=Ready snapshot=present
P01 session one stored the marker              200 MARKER STORED
S01 actor suspended after request one          SuspendActor status:4 witness=true
P02 same session returned the marker           200 ORANGE-FALCON-17
S02 actor suspended again after request two    SuspendActor status:4 witness=true
P03 second session did not inherit the marker  200 NO MARKER IN THIS SESSION
P04 the two sessions used different context ids
```

It has not been run on a work cluster. The earlier home-lab recording was
driven through the kagent UI and API rather than this script.

### Deleting the demo agent needs the controller

A `SandboxAgent` carries the `kagent.dev/sandbox-agent-substrate-cleanup`
finalizer, which only the kagent controller can clear. The script waits for
the deletion to finish and warns if it does not. Do not scale the controller
down until the object is gone, or it will sit in `Terminating` until the
controller returns.

## Demo B: the front-door isolation story

Use the tenant-isolation bundle. Its `scripts/verify.sh` implements every gate
and writes its own receipt; `TEST-MATRIX.md` lists them. The beats in the
video map to these rows:

| Video beat | Rows |
|---|---|
| Five dedicated listeners, routes accepted | `S01`–`S03` |
| Team agent to its own MCP backend | `P01`–`P03` |
| Platform Substrate specialist answers through its own listener | `P04` |
| The specialist's actor returns to Suspended with a new snapshot | `S05` |
| No credential, wrong lane, rogue claims | `N20`, `N21`, `N22` |
| Direct paths to MCP, controller and the specialist refused | `N08`, `N15`, `N23` |

That bundle was written for the home-lab `red` cluster. On a work cluster,
read its `AKS-SUBSTRATE-PROMOTION.md` first: the gateway, listeners, tokens
and namespaces have to exist before `verify.sh` means anything.

## Keeping the recordings publishable

Both videos are sanitized reconstructions using synthetic data. If the work
run is recorded, keep to the same boundary:

- Synthetic agent, session and marker names only; no real prompts, incidents
  or tickets.
- No employer, customer, cluster, subscription, namespace-identifying or
  endpoint detail; no kubeconfig paths, tokens or terminal history on screen.
- Do not present a work environment as a public demonstration environment, or
  claim measurements that this run did not take.
- Keep snapshot URIs and full actor IDs in the private receipt only.

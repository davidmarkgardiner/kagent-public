# Agent Substrate demo receipt

**Date:**
**Cluster / context:** (name it; do not paste kubeconfig or endpoints)
**Run by:**

## Pinned runtime

| Component | Observed version or state |
|---|---|
| Kubernetes server | |
| kagent controller | |
| Agent Substrate | |
| SandboxAgent API | `kagent.dev/v1alpha2` |
| Agent Substrate API | `ate.dev/v1alpha1` |
| WorkerPool | name, configured replicas |

## Reconciliation

- SandboxAgent `Accepted` and `Ready` at generation:
- Generated ActorTemplate and phase:
- Golden snapshot present (yes/no; omit the URI from anything shared):

## Session one (continuity)

| Step | Request | Response | Actor state samples |
|---|---|---|---|
| 1 | remember `<MARKER>` | `MARKER STORED` | |
| 2 | "what marker did I ask you to remember?" | `<MARKER>` | |

- Same context ID used for both requests:
- `SuspendActor` witness after each request (status 4, new snapshot):

## Session two (separation)

| Step | Request | Response | Actor |
|---|---|---|---|
| 1 | ask for the marker | `NO MARKER IN THIS SESSION` | different actor id |

- Session one's actor remained Suspended:

## Limitations to keep attached to this receipt

- Functional separation between two synthetic sessions. Not a tenant-isolation
  or security proof.
- Suspension is not deletion. Snapshots and session data need their own
  retention and erasure controls.
- No density, latency, cost or production-scale result was measured.

# Next work-agent task: golden actor `ResumeActor` returns NotFound

**Current result:** the private team rehearsal stopped while building the
golden actor. The template had a generated golden actor ID, but the ATE API
returned `Actor <GUID> not found` during `ResumeActor`. No A2A marker request
or three-scene continuity receipt exists. The disposable canary was removed;
the shared team-demo WorkerPool remains in place. Report this as a **blocked
golden actor lifecycle**, not a successful team demo.

This is a **hypothesis-driven investigation**, not a diagnosis from the error
text alone. The team has seen a private-build persistence race before; ask
for that earlier incident, exact source/build, and its raw evidence. In public
Substrate v0.0.9, the [ActorTemplate controller](https://github.com/kagent-dev/substrate/blob/v0.0.9/cmd/atecontroller/internal/controllers/actortemplate_controller.go)
generates the ID, awaits `CreateActor`, writes the template status, then calls
`ResumeActor` with `ate-golden/<ID>`. The [store implementation](https://github.com/kagent-dev/substrate/blob/v0.0.9/cmd/ateapi/internal/store/ateredis/ateredis.go)
returns from `CreateActor` after the Redis `SETNX` result and reads the actor
with `GET`. The [resume workflow](https://github.com/kagent-dev/substrate/blob/v0.0.9/cmd/ateapi/internal/controlapi/workflow_resume.go)
loads the actor before worker assignment or gVisor activity. A private fork
may differ; inspect its exact source and running image digest.

## Copyable request to the work agent

```text
Please treat the team rehearsal as BLOCKED at golden actor creation/resume.
Do not restart the whole demo, alter the WorkerPool, reseed runsc, patch a
generated ActorTemplate, or add a sleep as a guessed fix. Preserve the failed
run's raw receipts first, including the earliest error before logs rotate.

1. Update the four private Markdown deliverables now. State that H02/P02
   failed at the golden actor boundary; P03 and the three A2A scenes were NOT
   RUN. Record the canary cleanup receipt and that the pool remains available.
   Keep any separately proven runsc/worker evidence scoped to its own run.

2. From the failed run, correlate one exact UTC timeline for the canary UID,
   ActorTemplate UID/generation/resourceVersion, golden actor ID, and request
   or trace ID: controller generated ID -> CreateActor request and response ->
   ActorTemplate status update -> ResumeActor request -> ATE API NotFound.
   Capture controller logs and the logs of every ATE API replica covering that
   window, plus relevant Valkey/Redis topology, restart/failover and error
   events. Record the exact atespace and actor name in both RPCs. Keep raw
   material in the approved private evidence store, with sanitized Markdown
   excerpts and links; do not paste secrets or unredacted store values.

3. Check the installed private source and running image digests against the
   source actually used for this build. Locate CreateActor, GetActor,
   ResumeActor, golden-actor reconciliation and deletion/cleanup paths. Link
   the prior persistence-race incident and fix commit, if one exists. Say
   exactly whether this failure matches that incident; do not infer it from
   the identical error string.

4. Establish the first missing state. In one approved disposable canary,
   instrument or use the installed read-only API to check GetActor for the
   same ate-golden/<ID> immediately after an acknowledged CreateActor and
   before ResumeActor. If multiple ATE API replicas exist, compare the result
   through each replica or show that all route to the same store. Record
   timestamps, response codes, store/backend identity and any concurrent
   DeleteActor. Do not scan, flush, or edit the shared Redis/Valkey store.

5. Return a short decision table: CreateActor acknowledged? actor readable
   immediately? readable from every API replica? exact ResumeActor ref the
   same? deletion/failover seen? first confirmed divergence? If the record
   existed but ResumeActor still returned NotFound, inspect the resume
   request and read path before calling it a write race.

6. Propose the smallest private-build or store-configuration fix with a
   regression test for CreateActor -> GetActor -> ResumeActor. Preserve the
   failing receipt. After review, run one fresh disposable canary through
   golden Ready, the three presenter A2A scenes and cleanup. Attach the new
   run ID and receipts. Keep the team demo verdict BLOCKED until that passes.
```

## Decision points for the returned report

| Observation | Next investigation |
| --- | --- |
| `CreateActor` failed, but the template advanced to resume | Controller/private-build status ordering or error handling. |
| `CreateActor` succeeded, but immediate `GetActor` on the same API/store is missing | Store write/read visibility, wrong key/atespace, deletion, failover or private persistence code. |
| One ATE API replica finds the actor and another does not | Backend topology/configuration, routing or stale reads across replicas. |
| `GetActor` succeeds but `ResumeActor` says NotFound | Compare exact atespace/name, resume read path, timing and concurrent cleanup. |
| Actor is found and resume reaches worker assignment | This blocker has moved; then inspect capacity, `atelet`, gVisor and `runsc` using the new error. |

The only acceptable “fixed” result is a new, timestamped private run showing
golden Ready **and** the three A2A continuity scenes with actor IDs. A delayed
retry, Ready condition or earlier home-lab result alone cannot close this
failure.

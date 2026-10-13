# Next work-agent request: public ate-controller image, A/B status divergence

The supplied ate-controller OCI index
`sha256:dc29e79987fe4177b92c8b30a4fa4f36f3cf1a80937b03a7a8cd3411f98693e5`
and amd64 manifest
`sha256:6e51675b7e2072365dca844d161a5404faad3c853e7992a73db67c1c6b0a488c`
match the public `ghcr.io/kagent-dev/substrate/atecontroller:v0.0.9`
registry objects. A private registry may mirror these same bytes. This
identifies the running image content more precisely than its `-SNAPSHOT`
label; the build-to-source attestation remains unreported.

In the [public v0.0.9 controller](https://github.com/kagent-dev/substrate/blob/v0.0.9/cmd/atecontroller/internal/controllers/actortemplate_controller.go),
`PhaseInitial` generates one `actorID`, requests `CreateActor` with that name,
then writes the **same** variable to `status.GoldenActorID` after successful
creation. `PhaseResumeGoldenActor` reads that status value. The public source
has one `GoldenActorID` assignment in the controller. A single successful
pass through this code cannot by itself explain `CreateActor(A)` followed by
status B. The preserved receipt has no status-write request or response, so
the cause remains unproven.

## Copy this request to the work agent

```text
The ate-controller OCI index and amd64 manifest you supplied match the
public Substrate v0.0.9 image. Please correct the component map: distinguish
the mirrored/public image bytes from the private registry name and snapshot
tag. Record the running Pod imageID and OCI index/manifest privately. Do not
continue to treat the missing private source checkout as the only path to
investigating this running controller.

For the failed ActorTemplate UID, correlate the complete interval from the
first PhaseInitial reconcile to the first ResumeActor(B). From every
ate-controller replica and every ATE API replica, enumerate each
CreateActor request/response for that template namespace/name, including A
and any B, with UTC time and request or trace ID. For every Kubernetes
ActorTemplate status update in the interval, show writer identity,
resourceVersion before/after, Phase and GoldenActorID before/after, request
result, and ActorTemplate UID. Use the approved audit record or equivalent
raw receipts. A final object snapshot does not identify the status writer.

Check whether A and B refer to the same ActorTemplate UID rather than only
the same reusable namespace/name. Show GetActor(A) and GetActor(B) results
from the original run if retained; otherwise mark those original-run checks
UNKNOWN. Do not infer 'no second create' from one replica's incomplete log.
State the first confirmed event that changed or introduced B, or the exact
missing audit/log source that prevents that conclusion. Separate a controller
retry/status conflict, another status writer, an ATE API store/routing issue,
and a receipt-correlation error as hypotheses until one has evidence.

If historical status-write evidence is unavailable, prepare one fresh
approved disposable canary with scoped lifecycle logging and Kubernetes
status-write audit capture. Keep synthetic IDs and raw receipts private.
Do not patch the controller merely to satisfy the A/B invariant until the
new run shows the failing transition. Then propose the smallest fix and a
failing regression test for that observed path. The team demo remains
BLOCKED; no A2A claim passes from the earlier run.

Return one concise table: UTC time, component/replica, ActorTemplate UID,
action, actor name/atespace, Phase/GoldenActorID, resourceVersion, result,
and private receipt link. Finish with CONFIRMED CAUSE or STILL UNKNOWN and
the single smallest next action.
```

This prompt is for the next evidence exchange. The [earlier identity handoff](GOLDEN-ACTOR-ID-MISMATCH-WORK-AGENT-PROMPT.md)
contains the eventual regression and three-scene A2A acceptance criteria.

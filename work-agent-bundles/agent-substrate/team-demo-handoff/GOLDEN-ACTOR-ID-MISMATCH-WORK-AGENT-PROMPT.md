# Work-agent follow-up: golden actor creation/resume identity mismatch

Use this after the work agent reported that `CreateActor` acknowledged one
golden actor but the controller called `ResumeActor` for another. The earlier
[`NotFound` investigation](GOLDEN-ACTOR-NOT-FOUND-NEXT-STEP.md) records the
blocked rehearsal. This follow-up asks for the exact private-build evidence
and a reviewable fix; the reported mismatch is not itself a verified patch.

## Copy this prompt to the work agent

```text
Please investigate the golden actor identity mismatch from the failed
Substrate team rehearsal and return a focused, evidence-backed update. You
reported that CreateActor acknowledged actor A while ResumeActor addressed
actor B. Preserve that failed run and its raw receipts. Keep the team demo
BLOCKED until a fresh end-to-end run passes.

First establish the exact identity contract in the installed private build.
For one ActorTemplate UID and one reconciliation, provide a UTC timeline and
sanitized values for: the controller's generated actor name and atespace;
CreateActor request; CreateActor response metadata.name and metadata.uid;
the GoldenActorID written to status (with resourceVersion); any retry or
restart; and ResumeActor request atespace/name and response. Link each row to
an access-controlled raw receipt. State the running controller image digest,
source commit, Substrate version and relevant private source locations. If
the original receipts lack a field, say MISSING; do not reconstruct it from
memory. Do not put internal identifiers, endpoints, logs, or credentials in
the public repository.

Be precise about name versus UID. In public Substrate v0.0.9, ResumeActor
looks up (atespace, metadata.name); metadata.uid is a separate value. Check
the installed private API before applying that assumption. Show the first
point where the name or atespace diverges. Also check whether a concurrent
reconcile, status conflict, controller restart, CreateActor retry, or cleanup
could produce the mismatch. Distinguish observed cause from hypotheses.

If the mismatch is confirmed, prepare the smallest private controller fix
that keeps one stable (atespace, actor name) across creation, persisted
GoldenActorID, retries, restart and resume. Make creation idempotent across
the window where CreateActor succeeded but status persistence or the response
failed. Do not persist metadata.uid as GoldenActorID unless the installed API
proves ResumeActor uses it. Do not use a sleep, blind retry, manual status
patch, or WorkerPool/runsc change to hide the mismatch.

Add a regression test that fails on the current private build and passes
with the proposed fix. Cover at least: normal create/read/resume; an
acknowledged create followed by reconciliation retry before status is saved;
restart or status-update conflict before resume; and a repeated reconcile
that must not create a second golden actor. Record the test command, before
and after result, and source diff/commit. If you cannot reproduce one case,
state the gap and why.

For this first reply, send a compact decision table with observed create
name, response name/UID, persisted GoldenActorID, resume name, first
divergence, and receipt links; then give the root-cause statement or the
smallest missing evidence, the proposed diff, test results, and next safe
step. If the evidence contradicts the identity hypothesis, stop and report
the actual first failed boundary. Do not claim the fix is live from a unit
test or an image build.

After the fix is reviewed and the approved non-production deployment path is
available, build and pin the private controller image by digest, then run one
fresh disposable canary. Capture golden Ready and the three presenter A2A
scenes: first marker response and suspension; same-session restore with the
same actor and marker; new session with a distinct actor and no inherited
marker. Attach run ID, UTC times, request/context/actor IDs, model-response
and lifecycle receipts, plus cleanup. Mark every unrun or failed gate
explicitly. Keep all private artifacts in the approved private evidence
location and return sanitized links here for our next review.
```

## Follow-up after the sanitized A/B handoff

The work agent has now reported `CreateActor(A)` succeeded, status held B,
and `ResumeActor(B)` returned `NotFound`. The next exchange needs to identify
the writer of B before treating the proposed idempotency change as the fix.
In [public v0.0.9 controller code](https://github.com/kagent-dev/substrate/blob/v0.0.9/cmd/atecontroller/internal/controllers/actortemplate_controller.go),
one generated `actorID` is sent to `CreateActor` and written to status; its
create response is ignored. The private build may differ.

### Copy this follow-up to the work agent

```text
Please find the exact write that put B into
ActorTemplate.status.GoldenActorID. For the same ActorTemplate UID, return a
UTC timeline of every CreateActor attempt and response, every status write
and resourceVersion, the controller replica and any restart, and the
ResumeActor(B) request. Identify the source of each row and link its private
raw receipt. Mark missing fields MISSING; the preserved ATE API log does not
by itself establish that no second CreateActor happened.

Check whether GetActor(A) and GetActor(B) succeed using an approved read-only
path on a fresh disposable reproduction. If the original run has no such
read receipt, say UNKNOWN for that run. Identify any other writer or status
patch path, including concurrent reconciles, a stale cached object, and a
status conflict. Show the first confirmed transition from A to B rather
than inferring it from the final status.

Identify the running private controller image digest and its matching source
commit or build provenance. Compare its create/status/resume path with the
public v0.0.9 controller. If matching source is unavailable, mark the root
cause and proposed controller fix UNVERIFIED and give the smallest way to
recover that provenance. Do not deploy a guessed patch.

For this reply, send a concise table with timestamp, ActorTemplate UID,
controller replica, action, actor name/atespace, resourceVersion, result,
and receipt link. Then state who wrote B, or the precise missing evidence;
provide the smallest proposed diff and a failing regression test only once
that write path is established. Keep internal names, endpoints, logs,
credentials, and raw manifests in the approved private evidence store.
The team demo remains BLOCKED until the fresh three-scene A2A canary passes.
```

## Next handoff: recover the running controller source

The second sanitized report confirmed the A/B divergence but has no
status-write timestamp, private source revision, diff, or regression test.
Do not repeat the same A/B summary as a root-cause finding. The next useful
result is source provenance for the running controller image.

### Copy this request to the work agent

```text
Please trace the running private controller image digest from the failed run
to its build pipeline and exact source revision. Check the approved GitOps
image reference, registry image metadata, CI build record, and source
checkout or archive. Return access-controlled links and a sanitized mapping
of image digest -> build job -> source repository/revision. If any link is
unavailable, identify the owner or build record needed to recover it. Do not
send private source, registry names, raw logs, or credentials by email or
commit them to the public repository.

Once you have the matching source, show the specific controller code paths
that generate the golden actor name, issue CreateActor, write
status.GoldenActorID, handle status-update failures and retries, and issue
ResumeActor. Identify the exact writer of B or state the remaining missing
evidence. Add a failing regression test that reproduces CreateActor(A)
succeeding while GoldenActorID(B) is saved before proposing a fix.

If the source revision cannot be recovered, report SOURCE PROVENANCE BLOCKED
with the attempted lookup and the smallest next action for its owner. Mark
the controller root cause and proposed fix UNVERIFIED. Do not build or deploy
a guessed patch. Keep the team demo BLOCKED until a fresh three-scene A2A
canary on the reviewed, digest-pinned build passes.
```

Public reference for the name/UID distinction:
[`ateapi.proto` at v0.0.9](https://github.com/kagent-dev/substrate/blob/v0.0.9/pkg/proto/ateapipb/ateapi.proto).
The work agent must verify the actual private build before changing it.

## Follow-up after the controller digest was supplied

The supplied `sha256:878a55478c1727e048d38154158aae41aa701149c6660f78696fe682c7495146`
matches the public `ghcr.io/kagent-dev/kagent/controller:0.10.1` OCI index.
The public `ghcr.io/kagent-dev/substrate/atecontroller:v0.0.9` OCI index is
`sha256:dc29e79987fe4177b92c8b30a4fa4f36f3cf1a80937b03a7a8cd3411f98693e5`.
These are different components. The public golden ActorTemplate phase code is
in **Substrate ate-controller**. An internal mirror can retain the public
digest, so the supplied digest does not identify the private ate-controller
build or prove its source revision.

### Copy this correction to the work agent

```text
The supplied sha256:878a5547...c7495146 resolves to the public kagent
controller 0.10.1 image index. Please verify which component owns the
golden ActorTemplate reconciliation in the installed build. For the failed
run, identify the actual running Substrate ate-controller container image
reference and imageID digest, its CPU architecture, and whether each digest
is an OCI index or a platform-specific manifest. Keep internal registry and
cluster names in the approved private evidence store; send sanitized
component-to-digest and receipt links here.

Map the running ate-controller digest to its build job and exact source
revision. Compare that source's PhaseInitial, GoldenActorID status write,
retry/status-conflict handling, and PhaseResumeGoldenActor with public
Substrate v0.0.9. If the running digest is an unmodified public image, say
so with registry and source evidence. If it is private, recover its matching
source. Do not treat the kagent controller digest as provenance for
ate-controller.

Then identify the write that saved B, or report the precise remaining gap.
Do not implement an idempotency fix or rebuild an image for the wrong
component. Keep the demo BLOCKED until a reviewed fix and fresh three-scene
A2A canary pass.
```

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

Public reference for the name/UID distinction:
[`ateapi.proto` at v0.0.9](https://github.com/kagent-dev/substrate/blob/v0.0.9/pkg/proto/ateapipb/ateapi.proto).
The work agent must verify the actual private build before changing it.

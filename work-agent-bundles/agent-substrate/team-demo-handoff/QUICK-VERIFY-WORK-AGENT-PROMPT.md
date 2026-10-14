# Ask the work agent to prepare a quick Substrate verification

Copy the request below into the work agent. Attach
[`QUICK-VERIFY-WALKTHROUGH-TEMPLATE.md`](QUICK-VERIFY-WALKTHROUGH-TEMPLATE.md)
and this folder's existing demo files. The agent should return a completed
**private** Markdown sheet and a runnable test for the actual environment.
You can then follow the sheet yourself.

## Copyable prompt

```text
Yesterday's final test reportedly passed. Please validate the current kagent
+ Agent Substrate installation and prepare a short demonstration I can run
myself. Treat the old failure as historical unless it recurs. Do not change
controllers, upgrade components, redeploy Substrate or diagnose a new fix
merely because earlier notes mention GoldenActorID/NotFound.

Use QUICK-VERIFY-WALKTHROUGH-TEMPLATE.md as the starting sheet. Inspect the
approved kube context and exact installed APIs, images and versions first.
Discover the actual namespaces, agent kind/name, WorkerPool, ModelConfig,
generated ActorTemplate, API/controller pods and UI/service routes. Record
running imageIDs as well as configured tags. Do not guess names from the
public examples. Separate kagent-controller from Substrate ate-controller.

Produce these files in the approved private project:
1. SUBSTRATE-QUICK-VERIFY.md, a completed copy-and-run Markdown walkthrough.
2. verify-substrate-canary.sh, a bounded repeatable test, plus its manifest
   and any required helper files, with exact usage and cleanup commands.
3. SUBSTRATE-QUICK-VERIFY-RESULTS.md, with today's actual observations and
   receipt links, plus the prior final-test receipt if available. If it is
   unavailable, say so; the fresh test can still establish current behavior.

Keep the walkthrough focused on a disposable synthetic canary in the
approved non-production scope. Use a unique name and harmless marker with
no write-capable MCP tools. Do not overwrite existing agents, change pool
capacity or alter authentication. Use the existing approved model route.
If execution scope is not approved, prepare the files and mark them NOT RUN.

For Substrate 0.0.9 with the installed kagent 0.10.x SandboxAgent API, inspect
audit-substrate-install.sh, run-memory-demo.sh and sandboxagent-demo.yaml.
Reuse them where compatible, but adapt hardcoded names, A2A endpoint,
response shape and lifecycle parsing. The current runner's PASS is partial:
it does not assert same/distinct actor IDs, does not check Session B's
suspension, and its log query may select only one API replica. Do not simply
rename its PASS to a full lifecycle result. For any other API/version pair,
build the equivalent test against the installed CRDs and version-matched
upstream source. Do not run the old SandboxAgent manifest against a 1.x API.

Make these checks explicit:
- Fresh canary reconciles to Accepted/Ready where supported, and its actual
  generated template has a usable golden snapshot. Capture creation and
  golden restore receipts with matching actor name and atespace.
- Session A stores a synthetic marker, completes a real model request and
  successfully suspends with a snapshot receipt.
- Session A's second turn uses the exact same context ID. After the first
  suspension, the same logical actor resumes, returns the exact marker and
  suspends again with a new operation receipt.
- Session B uses a new context ID and a distinct logical actor, returns
  exactly NO MARKER IN THIS SESSION and successfully suspends.
- Map the canary actor to its selected worker and configured gVisor runtime
  with a runtime receipt. State what is verified about runsc and what is
  unknown. A manifest, Ready condition or chat answer alone is insufficient.

Capture UTC times, request/message IDs, context IDs, actor name/atespace,
worker identity, snapshot receipts and response bodies for every turn.
For the v0.0.9 path use metadata.name with atespace for actor lookup, not
metadata.uid. Collect the relevant lifecycle logs from every API/controller
replica and relevant container, preserving pod identity and timestamps.
Match each operation to this run, session and actor. A template-prefix
match, unrelated suspension or HTTP 200 alone must not pass the test.
Check JSON-RPC errors and completed task state as well as response text.
Use bounded waits and stop at the first failed or unavailable witness;
record FAIL or UNKNOWN with the exact stage and exit nonzero.

Run the quick sequence once. If it passes, run two further fresh canaries
with new names and context IDs as a short recurrence check. Record all three
outcomes without discarding failures or retrying until green. Remove only
the resources this test created, with UID/ownership checks, and confirm
cleanup. Do not force-remove finalizers or delete shared snapshots/pools.

Keep the sheet to a few runnable blocks: target/preflight, canary, four
inspection pauses, result table, cleanup. Replace environment placeholders
in the private copy. Include tools, RBAC needs, expected outputs, bounded
timeouts, exact receipt location and failure instructions. Include the
runner's SHA-256 so I can rerun the same reviewed test. Never place secrets
in command arguments or print Secret values. Keep all real names, endpoints,
raw logs and completed workplace evidence private.

Report the narrow conclusion. A fresh passing lifecycle test establishes
that this path works now on this cluster. It does not establish why the old
failure stopped happening, permanent reliability, Full/Data memory fidelity,
MCP correctness, tenant isolation, gateway policy, performance or air-gap
behavior. Mark those NOT TESTED unless separately exercised. If the old
GoldenActorID mismatch returns, preserve the failing CreateActor/status/
ResumeActor receipts and stop before proposing or applying a repair.
```

The walkthrough is the operator's short sheet. The larger
[`HANDS-ON-WALKTHROUGH.md`](HANDS-ON-WALKTHROUGH.md) remains available for a
presenter-led session. No workplace test has been run by publishing this prompt.

# Buzz-backed kagent SDLC POC

This POC moves the bounded role chain from the Buzz delivery proof into
kagent while retaining Buzz as the signed, human-visible request, evidence and
approval thread.

```text
Buzz issue event -> durable controller -> kagent coordinator
                                      -> builder -> verifier -> documenter
                     <- structured result <- A2A context/task correlation
                     -> Buzz threaded result (never a merge decision)
```

## Deliberate boundary

The controller is deterministic and owns event deduplication, task correlation,
attempt budget, Git SHA, clean-checkout tests, staging proof and PR/merge
eligibility. kagent owns the bounded specialist reasoning sequence. This keeps
an LLM from becoming the authority for retries, Git state or production writes.

The POC role agents have no shell, Git, Kubernetes-write or merge tools. A
future repository MCP tool must be separately allowlisted and exercised in a
sandbox before those boundaries change.

## Model route

`k8s/model-route.yaml` adds an isolated `buzz-sdlc-kimi-k2-7-code` route and
ModelConfig. It does **not** alter the shared `kimi-backend`, `/kimi/v1`, or
`default-model-config`. The provider-facing identifier is `kimi-k2.7-code` as
requested for this POC. A live low-token smoke on 2026-07-28 returned
`model: kimi-k2.7-code`; Kimi requires temperature `1`, which the isolated
ModelConfig sets explicitly.

## Validate and run

```bash
python3 -m unittest -v a2a/buzz-kagent-sdlc-poc/test_delivery_controller.py
kubectl apply --dry-run=server -f a2a/buzz-kagent-sdlc-poc/k8s/model-route.yaml
kubectl apply --dry-run=server -f a2a/buzz-kagent-sdlc-poc/k8s/agents.yaml
```

After the isolated model smoke succeeds, apply the manifests and wait for the
four POC agents:

```bash
kubectl apply -f a2a/buzz-kagent-sdlc-poc/k8s/model-route.yaml
kubectl apply -f a2a/buzz-kagent-sdlc-poc/k8s/agents.yaml
kubectl wait --for=condition=Ready -n kagent \
  agent/buzz-sdlc-builder agent/buzz-sdlc-verifier \
  agent/buzz-sdlc-documenter agent/buzz-sdlc-coordinator --timeout=240s
```

`delivery_controller.py` takes a trusted, already-authenticated Buzz event JSON
and prints the safe threaded reply payload. `buzz_bridge.py` is the production
adapter seam: one supervised invocation reads one private channel, accepts only
`buzz-kagent-sdlc.v1` `sdlc.task.request` messages, invokes the controller and
posts a signed reply to the source event. It has no endpoint-selection field.
Run it under a supervisor on the host holding the bridge identity; credentials
remain environment variables, never task content or repository files.

```bash
BUZZ_BIN=/opt/buzz/buzz BUZZ_CHANNEL_ID={{PRIVATE_CHANNEL_UUID}} \
KAGENT_A2A_URL=http://127.0.0.1:8083/api/a2a/kagent/buzz-sdlc-coordinator/ \
LEDGER_PATH=/var/lib/buzz-kagent-sdlc/ledger.sqlite3 \
python3 a2a/buzz-kagent-sdlc-poc/buzz_bridge.py
```

`KAGENT_A2A_URL` must be the fixed
allowlisted coordinator endpoint, for example
`http://127.0.0.1:8083/api/a2a/kagent/buzz-sdlc-coordinator/`; it is never
accepted from an event.

The controller stores `source_event_id`, A2A request/context/task IDs and its
terminal result in SQLite. A repeated source event returns the original result
without invoking kagent again. Its reply always has `merge_eligible: false`:
the next issue adds the deterministic Git/test/staging gate before a real PR.

`live_smoke.py` creates two disposable identities and a private channel, sends
one schema-marked task, runs one bridge pass, verifies a threaded result, then
deletes the channel and removes both relay memberships. Run it only from the
trusted bridge host after a local port-forward to the fixed coordinator.

Every Buzz command is independently bounded by `BUZZ_COMMAND_TIMEOUT` (20
seconds by default). If kagent returns `input_required`, the bridge immediately
posts `sdlc.approval_required` with the stored task/context correlation; it
never waits for approval inside the worker or starts a new task.

## Cleanup

```bash
kubectl delete -f a2a/buzz-kagent-sdlc-poc/k8s/agents.yaml --ignore-not-found
kubectl delete -f a2a/buzz-kagent-sdlc-poc/k8s/model-route.yaml --ignore-not-found
```

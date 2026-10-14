# Substrate quick verification sheet

Copy this into the private work project as `SUBSTRATE-QUICK-VERIFY.md`.
The work agent fills the target table, adapts commands and attaches results.
The blocks below are a starting example for **Substrate 0.0.9 + kagent
0.10.x SandboxAgent**, using this folder's existing runner. For a different
API/version, the work agent must replace them with tested equivalents.

Expected duration: approximately 10 minutes when the model and workers are
available; stop if a bounded check times out. This creates a synthetic agent,
sends three model requests and deletes that canary. It does not install or
repair the platform. Copy the **whole folder**, including scripts and YAML.

## 1. Fill in the target

| Setting | Actual private value |
| --- | --- |
| Approved non-production kube context | `{{KUBE_CONTEXT}}` |
| Bundle directory | `{{BUNDLE_DIR}}` |
| kagent namespace / Substrate namespace | `{{KAGENT_NAMESPACE}}` / `{{ATE_NAMESPACE}}` |
| kagent / Substrate versions and running imageIDs | `{{VERSIONS_AND_DIGESTS}}` |
| Served agent kind / API version | `{{AGENT_KIND}}` / `{{AGENT_API_VERSION}}` |
| Approved ModelConfig | `{{APPROVED_MODELCONFIG}}` |
| Selected WorkerPool namespace/name | `{{WORKERPOOL_NAMESPACE}}` / `{{WORKERPOOL_NAME}}` |
| kagent controller service / UI route | `{{CONTROLLER_SERVICE}}` / `{{UI_ROUTE}}` |
| Substrate API/controller pods and containers | `{{LIFECYCLE_LOG_SOURCES}}` |
| Test script revision / SHA-256 | `{{TEST_REVISION_AND_SHA256}}` |
| Previous final-test time and receipt, if available | `{{PRIOR_RECEIPT_OR_UNAVAILABLE}}` |
| This run's UTC start / operator | `{{UTC_START}}` / `{{OPERATOR}}` |

Replace every `{{PLACEHOLDER}}` before running its block. Tools are `bash`,
`kubectl`, `jq`, `curl` and `shasum` or `sha256sum`. Access must allow API
discovery, reads of the relevant workload/status/logs, approved local
port-forwarding, and creation/deletion of the canary. It needs no Secret
value reads. Keep receipts in the approved private evidence location.

## 2. Check the target before creating anything

Use one terminal for the run. Start `bash` if your usual shell differs.
These reads name the context explicitly and do not switch your default.

```bash
bash
set -euo pipefail
cd '{{BUNDLE_DIR}}'
export SUBSTRATE_DEMO_CONTEXT='{{KUBE_CONTEXT}}'
export SUBSTRATE_DEMO_KAGENT_NS='{{KAGENT_NAMESPACE}}'
export SUBSTRATE_DEMO_ATE_NS='{{ATE_NAMESPACE}}'
export SUBSTRATE_DEMO_MODEL='{{APPROVED_MODELCONFIG}}'
export SUBSTRATE_DEMO_SUFFIX="$(date -u +%Y%m%d%H%M%S)-$$"
export SUBSTRATE_DEMO_AGENT="substrate-verify-${SUBSTRATE_DEMO_SUFFIX}"
export SUBSTRATE_DEMO_MARKER="SYNTHETIC-${SUBSTRATE_DEMO_SUFFIX}"
export SUBSTRATE_DEMO_RECEIPTS="$PWD/receipts/$SUBSTRATE_DEMO_SUFFIX"
umask 077
mkdir -p "$SUBSTRATE_DEMO_RECEIPTS"
kubectl config get-contexts "$SUBSTRATE_DEMO_CONTEXT"
kubectl --context "$SUBSTRATE_DEMO_CONTEXT" get --raw=/version
kubectl --context "$SUBSTRATE_DEMO_CONTEXT" api-resources --api-group=ate.dev
kubectl --context "$SUBSTRATE_DEMO_CONTEXT" api-resources --api-group=kagent.dev
bash ./audit-substrate-install.sh \
  --context "$SUBSTRATE_DEMO_CONTEXT" \
  --kagent-namespace "$SUBSTRATE_DEMO_KAGENT_NS" \
  --ate-namespace "$SUBSTRATE_DEMO_ATE_NS" \
  | tee "$SUBSTRATE_DEMO_RECEIPTS/preflight.txt"
```

Expect `SUBSTRATE_INSTALL_AUDIT=INSTALL_CHECK_PASS`. This is an installation
check. **Stop on FAIL or UNKNOWN**. The audit assumes standard 0.0.9 resource
names and `gvisor-default`; the work agent must adapt it for renamed objects.
Verify the selected WorkerPool and approved model before proceeding:

```bash
kubectl --context "$SUBSTRATE_DEMO_CONTEXT" \
  -n '{{WORKERPOOL_NAMESPACE}}' get workerpools.ate.dev '{{WORKERPOOL_NAME}}' -o yaml
kubectl --context "$SUBSTRATE_DEMO_CONTEXT" \
  -n "$SUBSTRATE_DEMO_KAGENT_NS" get modelconfigs.kagent.dev "$SUBSTRATE_DEMO_MODEL"
```

The runner relies on the kagent controller's default WorkerPool, service
`kagent-controller` on port 8083, the 0.x sandbox A2A route and standard log
format. Verify these locally before running. Do not assume the first pool
listed is the pool used by this canary. Do not scale a busy pool for this test.

## 3. Run one canary and inspect each pause

For the matching legacy environment, this is the existing example command.
The work agent should replace it with its stricter, environment-matched
`verify-substrate-canary.sh` command after rehearsal. This runner uses local
port 28083; it must be free. `--keep` retains the canary even if a later check
fails, so follow cleanup after collecting the receipt.

```bash
bash ./run-memory-demo.sh \
  --context "$SUBSTRATE_DEMO_CONTEXT" \
  --namespace "$SUBSTRATE_DEMO_KAGENT_NS" \
  --ate-namespace "$SUBSTRATE_DEMO_ATE_NS" \
  --model-config "$SUBSTRATE_DEMO_MODEL" \
  --agent "$SUBSTRATE_DEMO_AGENT" \
  --marker "$SUBSTRATE_DEMO_MARKER" \
  --receipt-dir "$SUBSTRATE_DEMO_RECEIPTS" \
  --keep --presenter
```

Use the approved UI or actor inventory in a second window. The work agent
fills in its exact route and private, copyable log/API inspection commands
below. Resume the runner only after recording the observation at each pause.

| Pause | What you should see | Actual observation / receipt |
| --- | --- | --- |
| Agent ready | Fresh agent, generated template Ready and golden snapshot. Matching create/status/restore identity; no golden `NotFound`. | `{{OBSERVATION_AND_RECEIPT}}` |
| Session A first turn | `MARKER STORED`, context A, actor A, completed model call, successful suspension and snapshot receipt. | `{{OBSERVATION_AND_RECEIPT}}` |
| Session A return | Same context A and logical actor A resumes after suspension, returns the exact marker, then suspends again. | `{{OBSERVATION_AND_RECEIPT}}` |
| Session B | New context B, distinct actor B, exact `NO MARKER IN THIS SESSION`, then successful suspension. | `{{OBSERVATION_AND_RECEIPT}}` |

Example read-only inspection of the newly created agent and its template:

```bash
kubectl --context "$SUBSTRATE_DEMO_CONTEXT" \
  -n "$SUBSTRATE_DEMO_KAGENT_NS" get sandboxagents.kagent.dev "$SUBSTRATE_DEMO_AGENT" -o yaml
kubectl --context "$SUBSTRATE_DEMO_CONTEXT" \
  -n "$SUBSTRATE_DEMO_KAGENT_NS" get actortemplates.ate.dev \
  -l "kagent.dev/sandbox-agent=$SUBSTRATE_DEMO_AGENT" -o yaml
cat "$SUBSTRATE_DEMO_RECEIPTS/status/session-ids.txt"
cat "$SUBSTRATE_DEMO_RECEIPTS/results.tsv"
```

Private commands supplied by the work agent:

```bash
# {{EXACT_ACTOR_INVENTORY_COMMAND_WITH_CONTEXT_AND_AUTH_PROCEDURE}}
# {{EXACT_ALL_REPLICAS_LIFECYCLE_RECEIPT_COMMAND}}
# {{EXACT_ACTOR_TO_WORKER_AND_GVISOR_WITNESS_COMMAND}}
```

**The existing runner's `SUBSTRATE_DEMO: PASS` is only a partial result.**
It checks response text, differing context IDs and two suspension witnesses.
It does not assert same/distinct actor IDs, Session B suspension or full
request-to-actor correlation across API replicas. Complete those checks
using the inventory and lifecycle receipts, or use the adapted runner.
Missing proof is UNKNOWN. A returned marker demonstrates session continuity;
it cannot distinguish restored process memory from stored chat history.

## 4. Record the result

| Check | Expected | Actual / private receipt | Verdict |
| --- | --- | --- | --- |
| Current target and installation | Correct context, compatible APIs and healthy selected components | `{{OBSERVED}}` | NOT RUN |
| Fresh golden lifecycle | Matching actor name/atespace in create, persisted status and restore | `{{OBSERVED}}` | NOT RUN |
| Session A first turn | Completed request and correlated suspension/snapshot | `{{OBSERVED}}` | NOT RUN |
| Session A return | Same actor restores, exact marker, second suspension | `{{OBSERVED}}` | NOT RUN |
| Session B | Distinct actor, no inherited marker, suspension | `{{OBSERVED}}` | NOT RUN |
| Runtime | Actor maps to selected worker and actual gVisor execution receipt | `{{OBSERVED}}` | NOT RUN |
| Recurrence check | Three fresh canaries, same reviewed runner, all outcomes retained | `{{RUN_IDS_AND_OUTCOMES}}` | NOT RUN |
| Cleanup | This run's canary removed, controller finalizer completes | `{{OBSERVED}}` | NOT RUN |

Use PASS, FAIL, UNKNOWN or NOT RUN. One successful canary proves this path
worked during this run. For the short recurrence check, repeat steps 2-5
twice with fresh suffixes after the first complete pass. Stop at the first
failure and keep its receipts. Do not erase a failed run with a retry.

Overall verdict: `{{PASS_FAIL_UNKNOWN_NOT_RUN}}`.
Prior failure cause: `{{KNOWN_WITH_RECEIPT_OR_UNDETERMINED}}`.
Full/Data state fidelity, MCP tools, gateway policy, isolation, performance
and air-gap behavior: NOT TESTED by this sheet.

## 5. Remove only the canary from this run

Confirm the name matches the fresh canary you created. Keep kagent-controller
running so its cleanup finalizer can finish. The adapted runner should save
and verify the created object's UID before deletion.

```bash
kubectl --context "$SUBSTRATE_DEMO_CONTEXT" \
  -n "$SUBSTRATE_DEMO_KAGENT_NS" get sandboxagents.kagent.dev "$SUBSTRATE_DEMO_AGENT" -o name
kubectl --context "$SUBSTRATE_DEMO_CONTEXT" \
  -n "$SUBSTRATE_DEMO_KAGENT_NS" delete sandboxagents.kagent.dev "$SUBSTRATE_DEMO_AGENT" \
  --wait=true --timeout=120s
kubectl --context "$SUBSTRATE_DEMO_CONTEXT" \
  -n "$SUBSTRATE_DEMO_KAGENT_NS" get sandboxagents.kagent.dev "$SUBSTRATE_DEMO_AGENT" \
  --ignore-not-found -o name
```

Expect successful deletion and empty output from the final successful read.
If deletion times out, capture status and stop. Do not remove finalizers or
delete shared infrastructure. Object deletion does not prove snapshot or
session-data erasure. Keep raw receipts and the completed sheet private.

## References

- Agent request: [`QUICK-VERIFY-WORK-AGENT-PROMPT.md`](QUICK-VERIFY-WORK-AGENT-PROMPT.md).
- Existing presenter guide: [`HANDS-ON-WALKTHROUGH.md`](HANDS-ON-WALKTHROUGH.md).
- [Official 0.x Substrate example](https://kagent.dev/docs/kagent/0.x/examples/agent-substrate/), https://kagent.dev/docs/kagent/0.x/examples/agent-substrate/.
- [Official Substrate concepts](https://kagent.dev/docs/kagent/0.x/concepts/agent-substrate/), https://kagent.dev/docs/kagent/0.x/concepts/agent-substrate/.

Published status: TEMPLATE ONLY. No current workplace result is implied.

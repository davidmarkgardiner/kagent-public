# Smoke after the clean bank reinstall

Run the gates below on the actual workplace installation. The saved personal
lab receipts establish the baseline; they do not count as a workplace pass.

## 1. Runtime smoke

Complete the prerequisite and reinstall guides. The synthetic Agent and
Full/Data counter templates must already have fresh usable goldens. Keep the
approved router port-forward open. Replace the private placeholders:

```bash
set -euo pipefail
cd '{{BUNDLE_DIR}}'
export PROOF_KUBECONFIG='{{DEDICATED_EVALUATION_KUBECONFIG}}'
export PROOF_ROUTER='{{LOCAL_ROUTER_FORWARD_URL}}'
export PROOF_SYSTEM_NAMESPACE='{{ACTUAL_SUBSTRATE_NAMESPACE}}'
export PROOF_AGENT_NAMESPACE='{{ACTUAL_AGENT_NAMESPACE}}'
export PROOF_AGENT_NAME='{{ACTUAL_SYNTHETIC_AGENT}}'
export PROOF_WORKER_POOL='{{ACTUAL_GVISOR_POOL}}'
export PROOF_FULL_TEMPLATE='{{ACTUAL_FULL_COUNTER_TEMPLATE}}'
export PROOF_DATA_TEMPLATE='{{ACTUAL_DATA_COUNTER_TEMPLATE}}'
# Set PROOF_ADK_TEMPLATE explicitly if multiple historical templates match.
bash ./smoke-test.sh
```

The runner checks the selected worker's VM/OS/architecture/kubelet, Kubernetes
version, exact deployed chart versions, worker image digest and readiness,
current Agent conditions and template policies/images. It discovers the actual
generated ADK template and runs:

| Sequence | Fresh actors | Required result |
| --- | --- | --- |
| Generated Go ADK | 3 | Same actor UID, golden restore, Full local pause/restore, Data external commit/restore, unchanged agent card |
| Full/Full counter | 1 | Memory/file counts `1/1, 2/2, 3/3`, same marker and actor UID |
| Data/Data counter | 1 | Memory/file counts `1/1, 1/2, 1/3`, same marker and actor UID |

Expect `RUNTIME_SMOKE=PASS` only after all five sequences finish Suspended
and release their worker assignments. The receipt directory contains node,
release, agent, template and operation evidence plus `smoke-result.json`.
Any nonzero command or assertion ends the sequence and records the stage.
This new orchestration wrapper is syntax/receipt-parser checked and calls
the helper exercised in the 46 real lab sequences. The wrapper itself has
not been run on any live cluster. The demonstration clusters were already
deleted when this wrapper was added; the earlier receipts validate the
underlying lifecycle helper, not a live run of this new wrapper.

## 2. Disconnected delivery and authentication

Return receipts for the image pulls and runtime delivery from
`PREREQUISITES.md`. Include the complete gVisor file hash/mode checks on the
selected node, actual worker-visible version and actor-to-worker mapping.
Exercise a fresh/cache-empty worker through the approved delivery mechanism;
do not rely solely on a node left warm by previous tests. Keep this test within
the dedicated evaluation node pool and use its approved preparation procedure.

Show the actual registry-authentication and issuer/JWKS discovery result,
storage access and the applicable deny-public-egress/flow evidence. If the
bank permits specific external endpoints, record those exceptions and describe
the network boundary accurately. A Ready worker or a cache hit alone does not
establish a strict air-gap pass.

## 3. Real-model application smoke

Use a separate fresh synthetic Agent bound to the approved real ModelConfig.
Use the installed version's actual UI/A2A route and normal authentication.
The work agent supplies private copyable commands and captures raw responses;
the old 0.x `run-memory-demo.sh` is not a 1.x test runner.

1. Session A receives a new harmless synthetic marker and returns a real
   model-generated answer. Capture request/context IDs and the mapped actor.
2. Ask again in the same session and verify the exact marker. Record the
   actual lifecycle between turns. If demonstrating suspension/restoration,
   require its correlated snapshot and resume receipts.
3. Session B has a new context ID and receives no marker. Verify it does not
   inherit Session A's marker and record its actual actor mapping. Different
   context IDs alone do not prove distinct actors or tenant isolation.

Check JSON-RPC errors and completed task state, not HTTP status alone. Capture
the real model route's correlated request/response receipt. Stop on failure.
Report the installed harness's actual actor/session behavior; do not invent
idle suspension or process-memory preservation from a successful chat answer.
Add an approved harmless read-only tool call only if tools are included in the
workplace claim. The reference bundle omitted MCP servers.

## 4. Completion table

| Gate | Workplace verdict / receipt |
| --- | --- |
| Cleanup and fresh state | `{{PASS_FAIL_UNKNOWN}}` / `{{RECEIPT}}` |
| Required platform/version/image parity | `{{PASS_FAIL_UNKNOWN}}` / `{{RECEIPT}}` |
| Runtime smoke, five fresh actors | `{{PASS_FAIL_UNKNOWN}}` / `{{RECEIPT}}` |
| Private actor-image authentication | `{{PASS_FAIL_UNKNOWN}}` / `{{RECEIPT}}` |
| Fresh-node gVisor delivery and network boundary | `{{PASS_FAIL_UNKNOWN}}` / `{{RECEIPT}}` |
| Certificate/issuer/JWKS and snapshot storage | `{{PASS_FAIL_UNKNOWN}}` / `{{RECEIPT}}` |
| Real-model application smoke | `{{PASS_FAIL_UNKNOWN}}` / `{{RECEIPT}}` |
| Optional claimed tool path | `{{PASS_FAIL_UNKNOWN_NOT_INCLUDED}}` / `{{RECEIPT}}` |

The work agent may report the complete bank smoke PASS only with receipts
for every required gate. Otherwise report the passing subset and the exact
remaining blocker. Benchmark after smoke, preserve all failed attempts and
clean up only the synthetic objects created by this test.

# Team walkthrough: one agent, two sessions, two actors

This is a canary for the pinned **Substrate 0.0.9 + kagent 0.10.x
`SandboxAgent`** deployment. It creates one synthetic agent, sends two requests
in one session and one in another, then checks the Substrate lifecycle. It is
the same sequence rehearsed in the home lab; this run produces a new receipt
for **your** cluster. It does not install or repair Substrate.

The kagent [Substrate example](https://kagent.dev/docs/kagent/0.x/examples/agent-substrate/)
uses a `SandboxAgent` and shows its actor inventory under **View → Substrate**.
The [concept guide](https://kagent.dev/docs/kagent/0.x/concepts/agent-substrate/)
describes the per-session actor and snapshot/restore lifecycle. Follow the
installed version's actual API if it differs from this pinned deployment.

**What the audience will see:** a declarative agent become Ready, its generated
template and golden snapshot, a first actor answer and suspend, the same actor
answer after restoration, then a second actor with separate session history.
This is the core live demo. The [capability scorecard](#5-capability-scorecard)
lists the extra features that require their own receipts; one memory exchange
does not verify every advertised feature or every kagent tool.

## 1. Name the target and check the installation

Run these on a workstation with `kubectl`, `jq`, and `curl`, from this repo.
Replace the placeholders with the approved context and ModelConfig name. The
commands deliberately name the context; check that it identifies the cluster
you intend to test.

```sh
cd work-agent-bundles/agent-substrate
set -o pipefail
kubectl config get-contexts
kubectl --context '{{KUBE_CONTEXT}}' cluster-info
./scripts/audit-substrate-install.sh \
  --context '{{KUBE_CONTEXT}}' \
  --ate-namespace '{{ATE_NAMESPACE}}' \
  --kagent-namespace '{{KAGENT_NAMESPACE}}' \
  | tee /tmp/substrate-install-audit.txt
```

Use `kagent` for `{{ATE_NAMESPACE}}` when Substrate is installed as the kagent
subchart; otherwise use its actual namespace (often `ate-system`). The audit
must report the required `workerpools.ate.dev`, `actortemplates.ate.dev`,
`sandboxconfigs.ate.dev`, and `sandboxagents.kagent.dev` CRDs and finish with a
pass. **`ate.dev` is an API group, not the literal name of one CRD.** If any
required CRD is missing, or the audit cannot read it, stop here. Record the
failure in the GitLab ticket; a prior lifecycle claim does not prove this
cluster currently has the required API.

Check the approved model route and capacity with the platform owner before
the canary. The sequence is serial, so one free declarative worker can be
enough; a busy or harness-occupied pool may need more capacity.

## 2. Present the synthetic agent and session sequence

The script applies [`sandboxagent-demo.yaml`](sandboxagent-demo.yaml), waits for
`Ready` and a generated `ActorTemplate` with a golden snapshot, then sends:

1. Session A: `Please remember this marker ...` → `MARKER STORED`.
2. Session A again, after a `SuspendActor` witness: `What marker ...?` → the
   exact marker.
3. Session B, with a different `contextId`: the same question →
   `NO MARKER IN THIS SESSION`.

Use a unique agent name and synthetic marker. `--keep` leaves this canary in
place long enough to inspect it in the UI; the script otherwise deletes it.
It refuses to replace an existing agent of the same name. Before running,
open the approved kagent UI in a second window, select **View → Substrate**,
and put the terminal beside it. The `--presenter` option pauses at four
observable beats. It requires an interactive terminal and `--keep`.

```sh
cd work-agent-bundles/agent-substrate/demo
./run-memory-demo.sh \
  --context '{{KUBE_CONTEXT}}' \
  --namespace '{{KAGENT_NAMESPACE}}' \
  --ate-namespace '{{ATE_NAMESPACE}}' \
  --model-config '{{APPROVED_MODELCONFIG}}' \
  --agent 'substrate-memory-canary-{{UNIQUE_SUFFIX}}' \
  --marker 'SYNTHETIC-{{UNIQUE_MARKER}}' \
  --keep --presenter
```

| Pause | Say and show | Write down before pressing Enter |
| --- | --- | --- |
| Agent Ready | “The agent definition has reconciled; here is its generated template, golden snapshot and finite WorkerPool.” | `SandboxAgent`/template names, Ready condition, snapshot presence, pool count. |
| First answer and suspension | “I asked this session to remember a harmless marker. Here is its real response; the actor has now suspended and freed its worker.” | Session A context ID, actor ID, `SuspendActor` success, snapshot receipt, worker slot. |
| Same-session return | “I am returning to the **same** session. The marker came back and the **same logical actor** suspended again.” | Same context and actor IDs, exact marker, second `SuspendActor` success. |
| New session | “This is a **different** session and actor. It has no marker from the first one.” | Session B context and actor IDs, exact `NO MARKER IN THIS SESSION`, two distinct IDs. |

The request lines in the terminal are the cue; the raw response and lifecycle
receipt are the proof. The script issues the requests after you press Enter.
If a check fails, stop the presentation and show the failure as observed.
Do not narrate an expected state as if it happened.

Do not put gateway credentials on the command line. The default local
port-forward goes directly to the kagent controller for this functional
check. An approved gateway endpoint can be tested separately using its
normal authentication procedure.

The script prints `Receipt: ...`. Save that directory **privately**. It has
`results.tsv`, exact session IDs, raw A2A responses, the applied agent and
ActorTemplate status, and lifecycle log samples. `SUBSTRATE_DEMO: PASS` means
the automated checks passed. A model answer alone is insufficient: the two
`SuspendActor` witnesses must also be `PASS`. The current script proves
different context IDs; complete step 3 to prove distinct actor IDs.
If you want an unattended rehearsal instead, omit `--presenter` and `--keep`;
the same checks run and the canary is removed automatically.

## 3. See the two actors yourself

Open your approved kagent UI, or, if a local port-forward is permitted:

```sh
kubectl --context '{{KUBE_CONTEXT}}' -n '{{KAGENT_NAMESPACE}}' \
  port-forward svc/kagent-ui 8001:8080
```

In a browser open `http://localhost:8001`, then **View → Substrate**. Filter
for the canary name. Record the actor ID associated with Session A and the
one associated with Session B. The exact context IDs are in the receipt's
`status/session-ids.txt` and A2A response bodies. Expect **two different actor
IDs** and a `Suspended` state after each request. Capture the inventory and
the corresponding lifecycle log line in the private receipt. If the UI does
not expose a session-to-actor mapping, use the platform's Substrate actor/API
logs to establish it; do not infer distinct actors from the two context IDs.
If neither source can establish the IDs, mark this proof **UNKNOWN**, even if
the memory questions answered correctly.

For a slower visual replay, select the canary in the UI and start a **new**
chat. Ask it to remember a fresh synthetic marker. Wait until its actor is
`Suspended` in **View → Substrate**, then return to that **same chat** and ask
for the marker. Start another **new chat** and ask the same question. Write
down each chat's actor ID and state transition. This UI replay is useful for
understanding the behavior; the script's explicit `contextId` and raw
responses are the repeatable machine receipt.

## 4. Complete the ticket evidence and clean up

Copy [`RECEIPT-TEMPLATE.md`](RECEIPT-TEMPLATE.md) into a GitLab Markdown note.
Fill each cell from this run, link or attach the privately stored receipt,
and include the audit result. Remove tokens, kubeconfig contents, internal
endpoints, snapshot URIs, and other private details before pasting in any
public issue. Record `FAIL` or `UNKNOWN` instead of filling a missing witness
with the home-lab example. The home-lab
[`LIVE-RUN-2026-09-14.md`](../evidence/LIVE-RUN-2026-09-14.md) shows the
**shape** of a completed session/actor record, not the result on your cluster.

After saving the actor evidence, delete only the canary you created:

```sh
kubectl --context '{{KUBE_CONTEXT}}' -n '{{KAGENT_NAMESPACE}}' \
  delete sandboxagent 'substrate-memory-canary-{{UNIQUE_SUFFIX}}' --wait=true
```

Keep `kagent-controller` running until the SandboxAgent cleanup finalizer
clears. Confirm the canary is gone. Do not delete the WorkerPool, template
CRDs, Substrate components, or any pre-existing agent as part of this test.

The result establishes a working **declarative SandboxAgent session path**.
The marker is a session-continuity demonstration; by itself it does not show
which bytes were retained in process memory versus a durable session store.
It does not measure density, latency, costs, tenant security, snapshot erasure,
or the separate `AgentHarness` path. For redeployment on another cluster, use
the pinned import/install instructions in [`../aks-hardened/README.md`](../aks-hardened/README.md)
and rerun both the install audit and this canary there; never carry over a
pass from a different cluster.

## 5. Capability scorecard

Show these as separate stations **only when the work agent has rehearsed them
on the exact installed version and attached a passing receipt**. The [full
workplace evidence template](../WORKPLACE-SUBSTRATE-KAGENT-PROOF-TEMPLATE.md)
has the test contract (P01–P13), and the [work-agent demo handoff](WORK-AGENT-DEMO-HANDOFF.md)
asks for a presenter copy and a GitLab-ready result. `NOT RUN` is an honest
outcome for a capability outside this demo.

| Capability | Audience-friendly demonstration | Evidence required |
| --- | --- | --- |
| Agent creation and kagent integration | Agent Ready → generated template/golden → A2A answer. | P01–P03: matching CR, template, request and actor IDs; real model response. |
| Suspension, restoration and session separation | The four pauses above. | P04, P07: status transitions, snapshots, same/different actor IDs and pool slot evidence. |
| Actual gVisor runtime and seeded `runsc` | Show the selected worker and verified runtime asset, including ATELET shared-volume path. | P08–P09: runtime mapping, file hash, executable mount/path, fresh-node seed and private network evidence if air-gap is claimed. |
| Tool use through kagent | Ask the sandbox agent to call one approved, harmless read-only tool. | P03: tool declaration, routed call ID, tool response and agent answer. The marker agent has no tool and cannot prove this row. |
| agentgateway front door, if deployed | Repeat an approved request through the configured listener and show its policy decision and routed actor. | Separate gateway receipt; this script's default controller port-forward bypasses that path. The [gateway demo](../../kagent-agentgateway-tenant-isolation/) has its own test matrix. |
| Full versus Data state | Use separate approved process-state and `durableDir` fixtures. | P05–P06: exact before/after assertions and checkpoint mode; the marker answer alone is insufficient. |
| Startup and worker efficiency | Compare observed restore times and finite-pool reuse with a stated baseline. | P10–P11: repeated timings, worker counts and workload resources; no borrowed “30x” claim. |
| Other agent forms and recovery | Demonstrate each installed and approved runtime or harness separately; rehearse a worker recovery on disposable scope. | P12–P13: installed-version support, end-to-end run and recovery receipts. |

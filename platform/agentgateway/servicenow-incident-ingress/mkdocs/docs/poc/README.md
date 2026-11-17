# Live proof: incident JSON → agentgateway → kagent A2A

**Passed on the dedicated Proxmox VM lab on 17 November 2026.** A caller POSTed
ordinary incident JSON to `/incidents/triage/`. Agentgateway transformed it into
an A2A `message/send` request and forwarded it to a regular declarative kagent
Go agent through the kagent controller. The agent made a real model request and
returned a completed A2A task containing the exact supplied fields.

Argo is not installed in the tested cluster: API discovery returned no resources
in the `argoproj.io` group. No EventSource, EventBus, Sensor or Workflow was used.

## Observed results

| Test | Observed result |
|---|---|
| Pre-wrapped A2A JSON through the gateway | Completed task; exact incident fields returned. |
| Raw incident JSON transformed by the gateway | HTTP 200; completed task; exact incident fields returned in 1.377 seconds. |
| Quotes and newline in the description | Preserved exactly in both completed agent responses. |
| Malformed JSON | HTTP 503 `internal error`; gateway transformation failed without selecting an upstream endpoint. |
| Unconfigured path | HTTP 404 `route not found`. |

The latency is one lab observation, not a performance benchmark. The malformed
payload result proves rejection, but its 503 status is unsuitable as the final
client-validation contract: clients might retry it. A production integration
should provide deliberate payload validation and an appropriate client error.

See [the structured result](evidence/result.json),
[raw-JSON A2A response](evidence/raw-json-response.json),
[pass-through response](evidence/a2a-pass-through-response.json),
[gateway request logs](evidence/gateway-access.log),
[agent execution logs](evidence/agent-executions.log), and
[model gateway logs](evidence/model-gateway-access.log).

Addresses, lab user metadata, and UUIDs in published evidence are replaced by
explicit placeholders. The incident fields and timestamps are preserved.

## Tested path and versions

```text
Proxmox synthetic JSON client -> loopback port-forward
  -> agentgateway 1.7.0 -> A2A -> kagent 0.10.4 Go agent
  -> existing model gateway -> real DeepSeek API
No Argo in this tested path.
```

- Kubernetes: `v1.35.0` on the dedicated VM's native lab cluster.
- Gateway data plane: `cr.agentgateway.dev/agentgateway:v1.7.0`, pinned in the
  result to digest `sha256:60216aafb03d37f94e952ff3d51d2f630a65b10ecaebdc0a864882f92610c45b`.
- Controller and regular Go runtime: kagent `0.10.4`, API `kagent.dev/v1alpha2`.
  This VM also has a separate kagent 1.x/Substrate installation; it was not the
  agent runtime used for this proof.
- Model: existing lab `approved-model` configuration (`deepseek-flash`) through
  the existing model gateway to `api.deepseek.com`. The two successful provider
  requests returned HTTP 200 and reported token usage in the model gateway logs.

This uses ordinary HTTP forwarding of A2A JSON-RPC. Native A2A-aware gateway
backend configuration is not required and was not tested.

## What the caller sends

[incident.json](incident.json) contains the actual synthetic input:

```json
{
  "sys_id": "synthetic-record-001",
  "number": "INC-POC-20261117",
  "priority": "2",
  "short_description": "Synthetic checkout API latency",
  "description": "Synthetic only. Summary contains \"quotes\" and a newline.\nNo production data.",
  "nonce": "RAW_JSON_A2A_20261117"
}
```

The sender supplies no JSON-RPC method, agent URL, or A2A message wrapper. The
route fixes the destination, and the AgentgatewayPolicy in
[resources.yaml](resources.yaml) constructs the wrapper using `json(request.body)`
and `toJson(...)`. It generates a fresh invocation/message ID with `uuid()`.

The raw-JSON route omits `contextId`, allowing the runtime to create a fresh
context. The pass-through control request supplies its own independent context.
Neither behaviour is a durable deduplication or retry guarantee.

While the lab gateway is deployed, the client call is:

```bash
curl --fail-with-body --max-time 90 \
  -H 'Content-Type: application/json' \
  --data-binary @incident.json \
  http://127.0.0.1:18880/incidents/triage/
```

The gateway forwards the resulting A2A message to the controller path
`/api/a2a/classic-agents/incident-ingress-poc/`. The separate pass-through route
uses that same path and accepts an already-wrapped A2A request.

## Reproduce in the same lab

Run on the lab host with its existing kubeconfig and this repository available.
The manifest expects these pre-existing lab resources:

| Resource | Purpose |
|---|---|
| GatewayClass `agentgateway` | Existing gateway controller and CRDs. |
| `classic-system/classic-controller` Service, port 8083 | Existing regular kagent controller. |
| `classic-agents/approved-model` ModelConfig and its existing Secret | Approved model connection; no credential is copied or created. |
| `agent-flow-demo/standalone-deepseek-model` Service | Existing model gateway, port 8081. |

Set the kubeconfig path and context to the intended lab. This script creates
temporary resources, invokes the real model twice, and removes its resources
on exit. Run it only when those actions are authorised for the chosen target.

```bash
export KUBECONFIG='{{LAB_KUBECONFIG}}'
LAB_CONTEXT='{{LAB_CONTEXT}}'
bash platform/agentgateway/servicenow-incident-ingress/poc/run.sh "$LAB_CONTEXT"
```

`{{LAB_KUBECONFIG}}` is the existing lab kubeconfig path and `{{LAB_CONTEXT}}` is
its intended context. If copying only this folder, set `A2A_HELPER` to an existing
copy of [the repo's A2A helper](../reference/kagent-a2a-invoke.sh).

[verify.py](verify.py) owns the loopback gateway port-forward, uses the shared
helper for the A2A control, POSTs the raw incident, checks terminal A2A state and
exact returned fields, then exercises the two failure cases. It stores new,
**unsanitized** receipts as `evidence/*.private.*`. Keep those local; sanitise them
before publication. A repeated run creates additional model calls. The verifier
generates fresh control-message/context IDs in memory on each run; the raw-JSON
gateway mapping generates its invocation IDs. If submitting
[a2a-request.json](a2a-request.json) manually, replace its example IDs first.

The individual manifests and verifier were exercised live. The packaged
`run.sh` sequence was then replayed from a clean state, including collision
checks, fresh control-message IDs, and automatic cleanup. See the
[replay result](evidence/replay-result.json).

## Environment recovery and least-privilege test setup

The Proxmox VM was initially stopped. After boot, the Kind node resolver contained
`0.0.0.0`, causing CoreDNS forwarding loops. The node resolver was corrected using
the VM's existing upstream DNS configuration, and CoreDNS was recreated. The
crash-looping regular kagent controller Pod was replaced after DNS recovery.
This restored the lab for the test; a durable host/Docker DNS fix was not made.

The first A2A submission reached the test agent but its model connection was
denied by the existing model NetworkPolicy. Its HTTP response was 200 while the
A2A task state was `failed`; the verifier correctly stopped. See the
[initial failed receipt](evidence/initial-model-network-denial.json).

A new temporary NetworkPolicy then permitted only this exact test agent's labels
and namespace to reach the existing model gateway on port 8081. The existing
policies were preserved. A separate successful run used a fresh A2A context.
No configured external tools or resource-changing RBAC were granted to the agent.

The test namespace, agent, generated workload, ServiceAccount, route grant, and
temporary model network rule were removed after evidence capture. See
[cleanup verification](evidence/cleanup.json). The VM was left running with DNS
and the existing controller healthy. The dedicated test endpoint is no longer
deployed; the manifests preserve the proof for replay.

## What remains outside this proof

- A real ServiceNow instance, incident-created trigger, and outbound authentication.
- An externally reachable URL, production TLS, JWT validation, and denial tests.
  The client reached the gateway through a loopback-only port-forward.
- A workplace deployment, other gateway versions, or kagent 1.x agent execution.
- Incident diagnosis quality, MCP/tool execution, or production remediation.
  The agent was instructed to return the synthetic fields as an intake witness.
- Asynchronous completion, persistence across restart, durable idempotency,
  retries after uncertain submission, rate/size limits, and ServiceNow write-back.

The evidence establishes that raw incident JSON can reach a real agent through
agentgateway and A2A without Argo or a custom receiver service. The production
integration still needs an owner for the lifecycle behaviours listed above.

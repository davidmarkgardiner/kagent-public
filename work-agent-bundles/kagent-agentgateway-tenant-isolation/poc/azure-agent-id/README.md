# Azure Agent ID onboarding PoC

This is a narrow, repeatable slice of the proposed **GitOps request → AACM → Agent ID binding → kagent Agent** flow. It deliberately does not pretend to know AACM's internal API. The two JSON examples define a proposed request/result contract for one `team-event/incident-adviser` MCP lane; map the real AACM response into that contract only after its owners confirm the fields.

## What the PoC proves now

- The renderer refuses a mismatched blueprint, unexpected MCP role, wrong ServiceAccount subject, or missing federation link.
- It produces a private Kustomize overlay with an Agent ID mapping, a dedicated ServiceAccount, and the required AKS Workload ID label. The ServiceAccount's `azure.workload.identity/client-id` is the **UAMI client ID**, not the blueprint or child Agent ID.
- An offline test runs `kubectl kustomize` on the actual `teams/event/agent.yaml` example and checks the rendered values. `azure_preflight.py` performs read-only Azure and Graph reachability checks without printing object IDs.

The current Azure CLI context passed that read-only preflight on 2026-09-24, but it is a user login on a Pay-As-You-Go subscription with **zero AKS clusters**. No Azure/Entra resource or Kubernetes workload was created. That result is not an AKS or AACM end-to-end pass.

## Run the safe checks

From this directory:

```sh
python3 azure_preflight.py
python3 -m unittest -v test_generate.py
```

To render the placeholder demonstration, use a fresh temporary location outside this public repository:

```sh
POC_OUTPUT_DIR=$(mktemp -d)/overlay
python3 generate.py --demo \
  --request request.example.json \
  --aacm-response aacm-response.example.json \
  --out "$POC_OUTPUT_DIR"
kubectl kustomize "$POC_OUTPUT_DIR"
```

Do not apply the placeholder output. For a real AACM result, omit `--demo`, use approved private input files with actual UUIDs, and choose an approved private output directory. The renderer refuses to write into this public repository or overwrite an existing directory. Review the generated diff before committing it to a private GitOps repository; **do not commit real tenant, subscription, Agent ID, or UAMI identifiers here**.

## What still needs a live proof

1. Confirm AACM's real request and response schema, its owner, and whether `grantedRoles` means **Entra API app-role assignments** rather than Azure RBAC or Kubernetes RBAC. Replace the proposed response adapter with the real approved call. Do not let the not-yet-running agent invoke AACM itself.
2. Confirm the identity owner has approved a blueprint and child Agent ID. The response must name the blueprint app ID, child Agent ID app and object IDs, UAMI client ID, exact MCP role, and both trust links. Read those objects back from Azure/Graph before treating `state: Ready` as evidence.
3. On a selected AKS cluster, prove the ServiceAccount OIDC token can obtain a UAMI assertion and the UAMI can authenticate the blueprint. Microsoft documents the two-stage token exchange with `fmi_path=<child Agent ID app ID>`; this PoC does not implement it yet.
4. Decide where token acquisition and refresh live. The rendered environment variables are **configuration only**. kagent `v0.10.1` can set a ServiceAccount, Pod labels, and environment variables, but its rehearsed `RemoteMCPServer` Secret header did not refresh in a running Pod. No component in this PoC turns those IDs into an MCP access token.
5. Do not share blueprint credential access across tenant Pods without a binding control. A blueprint credential can act for multiple child Agent IDs; merely injecting the intended child ID does not stop a Pod choosing another `fmi_path`. A trusted broker or a narrower credential boundary must be proven before a multi-agent rollout.
6. Complete a positive MCP call and negative wrong-role, wrong-audience, cross-agent, expiry, and Pod-restart tests through agentgateway. The current [`event-mcp-policy.yaml`](../../profiles/aks-entra/event-mcp-policy.yaml) checks issuer, audience, role and tool, but not a specific child Agent ID claim.

The broader [work-agent walkthrough](../../profiles/aks-entra/WORK-AGENT-START-HERE.md) and [credential findings](../../profiles/aks-entra/PRODUCTION-CREDENTIALS.md) are the handoff for those gates. Microsoft references: [AKS Workload ID](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview), [autonomous Agent ID token flow](https://learn.microsoft.com/en-us/entra/agent-id/agent-autonomous-app-oauth-flow), and [blueprint security model](https://learn.microsoft.com/en-us/entra/agent-id/agent-service-principals).

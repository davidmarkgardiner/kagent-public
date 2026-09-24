# Azure Agent ID onboarding PoC

This is a narrow, repeatable slice of the proposed **GitOps request → AACM → Agent ID binding → kagent Agent** flow. It deliberately does not pretend to know AACM's internal API. The two JSON examples define a proposed request/result contract for one `team-event/incident-adviser` MCP lane; map the real AACM response into that contract only after its owners confirm the fields.

## What the PoC proves now

- The renderer refuses a mismatched blueprint, unexpected MCP role, wrong ServiceAccount subject, or missing federation link.
- It produces a private Kustomize overlay with an Agent ID mapping, a dedicated ServiceAccount, and the required AKS Workload ID label. The ServiceAccount's `azure.workload.identity/client-id` is the **UAMI client ID**, not the blueprint or child Agent ID.
- An offline test runs `kubectl kustomize` on the actual `teams/event/agent.yaml` example and checks the rendered values. `azure_preflight.py` performs read-only Azure and Graph reachability checks without printing object IDs.
- On 2026-09-24, `provision_graph.py` created a dedicated Agent ID blueprint, blueprint principal, and child Agent ID in the signed-in tenant. `provision_access.py` created a dedicated test API with the `team-event.mcp.use` app role, assigned it to the child, created a dedicated resource group and UAMI, and added the UAMI-to-blueprint federated credential. Graph and Azure read-backs passed. Both scripts were rerun and adopted the same objects without duplicates.
- `prove_certificate_exchange.py` temporarily added a certificate to the **PoC blueprint**, obtained the blueprint exchange token and a child Agent ID resource token, and verified the child's object ID, API audience, and app role claims. It removed the certificate and verified cleanup. The private key was never written to disk. This is an authentication-protocol proof using a temporary local certificate, **not** a UAMI-token or AKS-workload-identity proof.

The Azure CLI context had exactly one accessible tenant/subscription and **zero AKS clusters**. The identity objects above remain in that tenant for review; no AKS cluster or Kubernetes workload was created. No AACM API was called: the Graph scripts stand in for the identity actions an approved AACM process would own. This is not an AKS or AACM end-to-end pass.

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

## Repeat the identity-only pilot

These commands mutate only the dedicated PoC identities and test API in the current Azure CLI tenant/subscription. Check that `az account show` points to the intended environment first. Use a **private directory outside the repository** for the state receipt, never a shared GitOps path. The default PoC name is fixed so reruns converge; inspect or clean up the existing PoC objects before changing it. `provision_access.py` creates a resource group and UAMI in `uksouth`, but no compute or AKS.

```sh
POC_STATE_DIR=$(mktemp -d)
python3 provision_graph.py --state-dir "$POC_STATE_DIR"
python3 provision_access.py --state-dir "$POC_STATE_DIR"
python3 prove_certificate_exchange.py --state-dir "$POC_STATE_DIR"
```

The certificate proof needs the Python `cryptography` package. It aborts if the blueprint already has certificates, and its cleanup is fail-closed: if the certificate set changes during the test, it refuses to overwrite it. The live run needed the x86_64 Python installation because the available arm64 Python had an incompatible `_cffi_backend` binary; that is a local dependency issue, not an Entra requirement. Do not copy the real `state.json` into this public repository or a chat transcript. Review Azure/Graph state before deleting the pilot objects.

## What still needs a live proof

1. Confirm AACM's real request and response schema, its owner, and whether `grantedRoles` means **Entra API app-role assignments** rather than Azure RBAC or Kubernetes RBAC. Replace the proposed response adapter with the real approved call. Do not let the not-yet-running agent invoke AACM itself.
2. Have the identity owner review the live pilot and approve the production naming, ownership, lifecycle, and least-privilege role mapping. The proposed AACM response must carry the blueprint app ID, child Agent ID app and object IDs, UAMI client ID, exact MCP role, and both trust links. Read those objects back from Azure/Graph before treating `state: Ready` as evidence.
3. On a selected AKS cluster, prove the ServiceAccount OIDC token can obtain a UAMI assertion and the UAMI can authenticate the blueprint. The local certificate test proved the two-stage `fmi_path=<child Agent ID app ID>` protocol but did **not** exercise that UAMI or the missing Kubernetes-to-UAMI federation credential.
4. Decide where token acquisition and refresh live. The rendered environment variables are **configuration only**. kagent `v0.10.1` can set a ServiceAccount, Pod labels, and environment variables, but its rehearsed `RemoteMCPServer` Secret header did not refresh in a running Pod. No component in this PoC turns those IDs into an MCP access token.
5. Do not share blueprint credential access across tenant Pods without a binding control. A blueprint credential can act for multiple child Agent IDs; merely injecting the intended child ID does not stop a Pod choosing another `fmi_path`. A trusted broker or a narrower credential boundary must be proven before a multi-agent rollout.
6. Complete a positive MCP call and negative wrong-role, wrong-audience, cross-agent, expiry, and Pod-restart tests through agentgateway. The current [`event-mcp-policy.yaml`](../../profiles/aks-entra/event-mcp-policy.yaml) checks issuer, audience, role and tool, but not a specific child Agent ID claim.

The broader [work-agent walkthrough](../../profiles/aks-entra/WORK-AGENT-START-HERE.md) and [credential findings](../../profiles/aks-entra/PRODUCTION-CREDENTIALS.md) are the handoff for those gates. Microsoft references: [AKS Workload ID](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview), [autonomous Agent ID token flow](https://learn.microsoft.com/en-us/entra/agent-id/agent-autonomous-app-oauth-flow), and [blueprint security model](https://learn.microsoft.com/en-us/entra/agent-id/agent-service-principals).

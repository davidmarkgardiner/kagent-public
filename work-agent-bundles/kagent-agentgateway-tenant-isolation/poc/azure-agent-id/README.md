# Azure Agent ID onboarding PoC

This is a narrow, repeatable slice of the proposed **GitOps request → AACM → Agent ID binding → kagent Agent** flow. It deliberately does not pretend to know AACM's internal API. The two JSON examples define a proposed request/result contract for one `team-event/incident-adviser` MCP lane; map the real AACM response into that contract only after its owners confirm the fields.

Use the [human checklist and message to send now](WORK-HUMAN-CHECKLIST.md), [Request 1 for the caller UAMI and A2A role](WORK-REQUEST-1-CALLER-UAMI-A2A.md), [Request 2 for the agent blueprint and MCP role](WORK-REQUEST-2-AGENT-BLUEPRINT-MCP.md), [combined work-form reference](WORK-FORM-BLUEPRINT-ACTION-REQUEST.md), [copy-ready work GitLab ticket](WORK-GITLAB-IDENTITY-TICKET.md), [identity-team implementation playbook](WORK-IDENTITY-IMPLEMENTATION-PLAYBOOK.md), [native Azure CLI and Graph examples](WORK-NATIVE-GRAPH-CLI-EXAMPLES.md), [who-can-call-what HTML diagram](WHO-CAN-CALL-WHAT.html) and its [Mermaid DAG source](WHO-CAN-CALL-WHAT.mmd), [current AKS HTML walkthrough](aks-agentid-e2e-walkthrough.html), and [sanitized live evidence](AKS-FULL-E2E-EVIDENCE-2026-09-25.md). The original [HTML walkthrough](architecture-walkthrough.html) and [request template](WORK-IDENTITY-REQUEST.md) are historical views of a superseded UAMI two-hop proposal. No work GitLab ticket has been submitted.

## What the PoC proves now

- The renderer refuses a mismatched blueprint, unexpected MCP role, wrong ServiceAccount subject, or missing federation link.
- The original renderer produces a private Kustomize overlay with an Agent ID mapping, a dedicated ServiceAccount, and an AKS Workload ID label. Its ServiceAccount `azure.workload.identity/client-id` is the **UAMI client ID**. This is a historical demonstration, **not a deployable work design**: the subsequent AKS pilot found the UAMI-to-blueprint exchange fails. The approved direct-federation design would annotate the ServiceAccount with the blueprint app client ID, or use a separately proven broker.
- An offline test runs `kubectl kustomize` on the actual `teams/event/agent.yaml` example and checks the rendered values. `azure_preflight.py` performs read-only Azure and Graph reachability checks without printing object IDs.
- On 2026-09-24, `provision_graph.py` created a dedicated Agent ID blueprint, blueprint principal, and child Agent ID in the signed-in tenant. `provision_access.py` created a dedicated test API with the `team-event.mcp.use` app role, assigned it to the child, created a dedicated resource group and UAMI, and added the UAMI-to-blueprint federated credential. Graph and Azure read-backs passed. Both scripts were rerun and adopted the same objects without duplicates.
- `prove_certificate_exchange.py` temporarily added a certificate to the **PoC blueprint**, obtained the blueprint exchange token and a child Agent ID resource token, and verified the child's object ID, API audience, and app role claims. It removed the certificate and verified cleanup. The private key was never written to disk. This is an authentication-protocol proof using a temporary local certificate, **not** a UAMI-token or AKS-workload-identity proof.

That was the 2026-09-24 identity-only state. On 2026-09-25, two disposable one-node AKS pilots exercised the Kubernetes and gateway path. Direct AKS ServiceAccount → blueprint federation issued child Agent ID tokens with the intended audience and role. The proposed AKS ServiceAccount → UAMI → blueprint chain failed with `AADSTS700231`, because the UAMI token was itself obtained via federation. The full pilot then used separate runtime, approved-caller, and rogue blueprints, authenticated A2A and MCP routes, Cilium NetworkPolicies, a deterministic model, and a dummy MCP. The approved caller completed A2A → Agent → MCP; missing/wrong-audience/missing-role and same-role wrong-child tokens were denied, as were direct rogue service calls and a forbidden tool. A newly minted runtime token worked after a Secret update and Agent Pod restart. This does **not** establish automatic refresh, expiry behavior, work-tenant AACM integration, production TLS/egress, or an approved token broker. The disposable AKS resources and additional pilot-only identities were deleted after the tests; the original identity-only PoC objects remain for review. No AACM API was called. See the [full receipt](AKS-FULL-E2E-EVIDENCE-2026-09-25.md), including a fail-open CEL mistake found and corrected by the negative test.

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
2. Have the identity owner review the live pilot and approve blueprint granularity, naming, ownership, lifecycle, and least-privilege MCP/A2A role mappings. The work AACM response must identify the blueprint, child Agent IDs, protected APIs, exact roles, and direct AKS federation. Read those objects back from Azure/Graph before treating `state: Ready` as evidence. A UAMI for other Azure access is a separate decision, not the blueprint middle hop.
3. Have the identity owner approve direct AKS ServiceAccount → blueprint federation or another supported credential broker. The UAMI middle hop failed in a live AKS pilot with `AADSTS700231` and must not be carried into the work design as if proven. Review blueprint-to-child isolation: a Pod with blueprint credential access may choose another child via `fmi_path` unless a narrower trust boundary or broker enforces the binding.
4. Decide where token acquisition and refresh live. The rendered environment variables are **configuration only**. kagent `v0.10.1` can set a ServiceAccount, Pod labels, and environment variables, but its `RemoteMCPServer` Secret header did not refresh in a running Pod. The lab used a temporary token-minting Job, Secret patch, and Pod restart; that is not a production broker or automatic renewal.
5. Do not share blueprint credential access across tenant Pods without a binding control. A blueprint credential can act for multiple child Agent IDs; merely injecting the intended child ID does not stop a Pod choosing another `fmi_path`. A trusted broker or a narrower credential boundary must be proven before a multi-agent rollout.
6. The disposable AKS pilot completed positive A2A/MCP, wrong-role, wrong-audience, wrong-child, forbidden-tool, direct-bypass, and Pod-restart tests. Repeat these in the work cluster and add **expiry/fail-closed** and automatic refresh tests. The checked-in [`event-mcp-policy.yaml`](../../profiles/aks-entra/event-mcp-policy.yaml) is a role-only example; bind the exact child ID in one CEL expression with the role before deployment.

The broader [work-agent walkthrough](../../profiles/aks-entra/WORK-AGENT-START-HERE.md) and [credential findings](../../profiles/aks-entra/PRODUCTION-CREDENTIALS.md) are the handoff for those gates. Microsoft references: [AKS Workload ID](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview), [autonomous Agent ID token flow](https://learn.microsoft.com/en-us/entra/agent-id/agent-autonomous-app-oauth-flow), and [blueprint security model](https://learn.microsoft.com/en-us/entra/agent-id/agent-service-principals).

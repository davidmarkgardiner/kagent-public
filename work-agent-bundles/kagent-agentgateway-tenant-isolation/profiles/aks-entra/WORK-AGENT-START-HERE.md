# Work-agent walkthrough: prepare kagent for Microsoft Entra Agent ID

Use this walkthrough to prepare the **agent side** of one tenant-isolated A2A-to-MCP lane at work. First inspect the current installation and propose the smallest change. Treat creation of Entra objects, Azure resources, cluster changes, and live token tests as later, separately approved steps. Do not infer permission to make those changes from access to an SPN.

The local rehearsal proved that an Agent ID token can pass the existing agentgateway policy, including a call where the kagent Agent used a **different Agent ID** for its own MCP request. It did **not** prove the work tenant, AKS workload identity, token refresh in kagent, or the Microsoft sidecar for a custom API. Start with [Agent ID rehearsal](AGENT-ID-REHEARSAL.md), [credential findings](PRODUCTION-CREDENTIALS.md), and the [AKS Entra overlay](README.md). The [phase-1 work evidence](../../PHASE1-WORK-EVIDENCE.md) says what the earlier isolation work actually established.

## 1. Inspect the current agent lane without changing it

1. Confirm which work environment, namespace, kagent release, agentgateway release, Gateway API CRDs, and agent/controller ownership are actually installed. Record versions and the owning team in an approved work record. The bundle targets kagent `0.10.1` and agentgateway `v1.5.0`; do not assume the work installation matches it.
2. Identify one pilot Agent and its `RemoteMCPServer`, generated runtime Deployment/Pod, ServiceAccount, Secret references, A2A route, MCP route, policies, and MCP tool. Use read-only Kubernetes inspection. Do not export Secret data, access tokens, full environment dumps, or private hostnames into this public repository.
3. Trace both authenticated hops: **caller Agent ID → A2A gateway → kagent Agent**, then **agent-owned Agent ID → MCP gateway → MCP server**. A single identity for both hops is not the tested design. Keep the agent's MCP tool permissions separate from the caller's A2A permissions.
4. Check whether the deployed kagent version still renders `RemoteMCPServer.spec.headersFrom` Secret values into the runtime at Pod creation. The rehearsal required a new Pod after a token change. Check the installed CRD and controller behavior rather than assuming the example is current.
5. Check how the generated Agent Pod can receive an approved ServiceAccount, workload-identity Pod label, and (if chosen) a local credential helper. Check whether admission, network policy, and Pod security allow that shape. Do not modify the controller or the Agent CR yet.

Use [`teams/event/agent.yaml`](../../teams/event/agent.yaml) and the [bundle architecture](../../ARCHITECTURE.md) as examples of the existing ownership boundary. Application teams should not gain write access to gateway policies or other tenants' credentials.

## 2. Choose a workable agent-side token path

1. For the pilot, document how the agent will obtain a fresh **agent-owned** token for the MCP API, how it will attach that token to each request, and how it will continue working after token expiry. Keep the credential on the blueprint or an approved workload identity, never on the Agent ID object.
2. Evaluate these three options against the *installed* kagent and agentgateway versions:
   - **Existing Secret header path:** a controlled token refresher updates the namespaced Secret and causes a safe kagent reconcile/new Pod before expiry. This fits the rehearsal's current kagent behavior but needs an operator, expiry/error handling, and namespace Secret-access review.
   - **In-Pod token helper:** the Agent obtains a header from a loopback-only helper on each call. Determine whether the installed kagent runtime can do this without a code change. The Microsoft Entra Auth SDK sidecar was **not** proven to return an Agent ID token for our custom API; its tested response had the blueprint principal or `AADSTS82001`. Do not select it until a work-environment token has the expected Agent ID `sub`.
   - **Gateway-side outbound credential:** check whether the installed agentgateway schema and runtime can obtain and attach the Agent ID token for the agent-to-MCP hop. This is research, not an implemented feature in this bundle. Keep the inbound caller policy distinct from outbound credential handling.
3. Recommend one option with an implementation sketch, owner, rollback, token-refresh test, and remaining unknowns. If none is supported without new code, report the exact integration gap. Do not insert a static long-lived access token as a production shortcut.
4. Align the Entra app role values with the policy files before rendering anything. The current [`event-a2a-policy.yaml`](event-a2a-policy.yaml) requires `team-event.a2a.invoke`; [`event-mcp-policy.yaml`](event-mcp-policy.yaml) requires `team-event.mcp.use`. One earlier lab run used `team-event.mcp.invoke`. Choose the exact work role with the identity and gateway owners; mismatched strings must fail closed.
5. Produce a **placeholder-only** Agent/ServiceAccount/RemoteMCPServer/gateway diff for review. Keep `{{TENANT_ID}}`, `{{API_APP_ID}}`, `{{UAMI_CLIENT_ID}}`, and other environment values unresolved in any public artifact. Validate rendered manifests against the installed CRDs before proposing an apply.

## 3. Establish what the current SPN can actually do

Use the approved work terminal, portal, or identity tooling for read-only checks. Record **permission names, scope, and owner**, not credential values or tenant identifiers, in the shareable handoff.

1. Confirm which principal the session uses and whether it is the intended SPN. Do not switch to a more powerful account silently.
2. Check its Azure RBAC assignments at the relevant AKS and resource-group scopes, including whether it can read or create a UAMI and its federated credential. Being able to read AKS does not imply permission to change cluster OIDC/workload-identity settings.
3. Separately check its Microsoft Graph **application permissions**, admin consent, ownership, and any relevant Entra directory roles for blueprint creation, blueprint-principal creation, Agent ID creation, API app roles, app-role assignments, and federated credential management. Azure RBAC does **not** grant those Graph permissions.
4. Check who owns the existing API app registrations, who can grant the A2A and MCP app roles, and which identity team owns sponsorship/consent decisions. Also identify any network/registry team needed for Entra token and JWKS access or mirrored images.
5. If a read/list operation fails, record the error and the intended scope. A denied listing does not prove that no assignment exists. Ask the authorized owner to confirm through their approved portal, Graph/PowerShell tooling, or identity workflow. Do not self-grant permissions or use another credential as a workaround.

Microsoft now documents a **Graph v1.0 blueprint-create API** with the `AgentIdentityBlueprint.Create` application permission; its current [create-agent-identity guide](https://learn.microsoft.com/en-us/entra/agent-id/create-delete-agent-identities) uses a different beta route for Agent ID creation than the older lab commands in this bundle. Verify the current API and least-privileged permission for **each** operation before requesting access. Start with the [blueprint-create API](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-post?view=graph-rest-1.0) and [Agent ID administration](https://learn.microsoft.com/en-us/entra/agent-id/manage-agent-identities-admin). Do not copy the September 2026 rehearsal's Graph POST commands into the work tenant unchanged.

## 4. Draft the Azure and Entra plan; do not execute it yet

1. Ask the identity owner to approve the pilot's blueprint, sponsor, blueprint principal, **caller Agent ID**, **agent-owned Agent ID**, API audiences, and exact app-role assignments. Use one Agent ID per distinct agent/caller role where the policy needs a separate `sub`.
2. Ask the AKS owner to confirm OIDC issuer and workload identity support for the chosen cluster. The proposed production credential path has **two** trust links: `AKS ServiceAccount → UAMI` and `UAMI → blueprint`. The first federated credential uses the cluster issuer and exact `system:serviceaccount:<namespace>:<serviceaccount>` subject; the second is on the blueprint and trusts the UAMI. Only the second link was configured in the local rehearsal, and neither link was exercised end to end on AKS. See [credential findings](PRODUCTION-CREDENTIALS.md) and [AKS workload identity](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview).
3. Define which approved owner will perform each operation if the SPN lacks rights. A portal, PowerShell, Graph client, or approved platform workflow is an alternate **tool for an authorized owner**, not a way around missing authorization.
4. Confirm the allowed egress to Entra's token endpoint and JWKS, internal image-mirror path, external TLS/ingress ownership, and whether the existing Gateway API CRDs can serve the Entra overlay. Do not replace shared Gateway API CRDs merely to satisfy this pilot; coordinate with their owner.
5. Write an ordered change plan and rollback for the identity objects, AKS trust links, token helper, Agent manifests, and gateway policy. Place all real object IDs, hostnames, certificate material, and tokens only in approved private work systems.

Stop here for review. The [AKS promotion guide](../../AKS-SUBSTRATE-PROMOTION.md) is a separate gate for the SandboxAgent/Agent Substrate lane; do not treat this Agent ID pilot as permission to deploy or change that runtime.

## 5. After explicit approval, implement and prove one pilot

1. Have the authorized identity and AKS owners create the reviewed Agent ID objects, exact app-role assignments, UAMI, and both federated credentials. Record ownership and rollback privately. Do not make the SPN's first failed write an invitation to broaden its rights.
2. Have the agent/gateway owners substitute approved private values into the reviewed pilot manifests, validate them against the installed CRDs with server-side dry-run, and apply them through the approved delivery flow. Keep the A2A caller route and agent-to-MCP route distinct. Add no direct backend access.
3. Exercise the chosen token helper before traffic is admitted. Verify its token refresh, expiry behavior, and failure mode. If a sidecar is chosen, inspect the actual `sub` of a custom-API token before allowing the agent to use it.

Collect private, redacted receipts for each check below before proposing expansion:

1. A token for the **caller Agent ID** has the expected issuer, A2A audience, `sub`/`oid`, `azp`, and A2A role; it reaches the pilot Agent through the gateway.
2. A different token for the **agent-owned Agent ID** has the MCP audience and exact MCP role; the Agent calls only its permitted MCP tool through the gateway.
3. No token returns `401`; a valid token without the needed role returns `403`; wrong audience and cross-lane tokens fail. Check that rejected MCP requests never reach the backend.
4. The agent keeps working across token expiry and Pod restart. A refreshed Secret alone is **not** accepted as proof if the running Pod still holds the old header.
5. Network and admission controls still prevent direct controller/MCP access and cross-tenant references. Confirm the accepted route points to the intended backend and that logs do not contain access tokens.

Do not claim production readiness from a successful Graph create, a green CR condition, or a single `200`. Report what was exercised, what remains untested, and how the changes can be rolled back.

## Return to the platform and identity owners

Give back one private work handoff containing the read-only inventory, SPN capability findings, recommended agent-side token path, placeholder-only manifests, Azure/Entra action list by owner, exact approvals needed, pilot test results (if authorized), rollback, and unresolved blockers. The first response can be a plan; no work-tenant or cluster mutation is required to complete the initial investigation.

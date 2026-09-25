# Work-agent walkthrough: prepare kagent for Microsoft Entra Agent ID

Use this walkthrough to prepare the **agent side** of one tenant-isolated A2A-to-MCP lane at work. First inspect the current installation and propose the smallest change. Treat creation of Entra objects, Azure resources, cluster changes, and live token tests as later, separately approved steps. Do not infer permission to make those changes from access to an SPN.

The local rehearsal proved that an Agent ID token can pass the existing agentgateway policy. A disposable AKS pilot then proved direct ServiceAccount-to-blueprint federation, approved Agent ID caller → A2A gateway → kagent Agent → MCP gateway → tool, same-role wrong-child denial, and direct-bypass NetworkPolicy. It did **not** prove the work tenant, AACM, production token refresh, or expiry behavior. The proposed ServiceAccount-to-UAMI-to-blueprint chain failed with `AADSTS700231`. Start with the [current AKS evidence](../../poc/azure-agent-id/AKS-FULL-E2E-EVIDENCE-2026-09-25.md), [visual walkthrough](../../poc/azure-agent-id/aks-agentid-e2e-walkthrough.html), [copy-ready identity ticket](../../poc/azure-agent-id/WORK-GITLAB-IDENTITY-TICKET.md), and [credential findings](PRODUCTION-CREDENTIALS.md). The [phase-1 work evidence](../../PHASE1-WORK-EVIDENCE.md) says what the earlier isolation work established.

## Give the identity team the exact AKS issuer and ServiceAccount

The identity team can create the blueprint, child Agent ID, API registration, and app roles before the AKS details are final. It needs the **exact** issuer and ServiceAccount subject before it adds the blueprint federated credential. First choose which workload acquires the child token. In the lab, the kagent Pod used a dedicated ServiceAccount. A separate token proxy would instead use its **own** ServiceAccount, so its name would appear in the federated credential. Do not send an assumed default ServiceAccount name.

In the approved work environment, read the AKS issuer without changing the cluster. Replace the placeholders locally and put the result only in the private ticket:

```sh
az aks show --resource-group '{{AKS_RESOURCE_GROUP}}' --name '{{AKS_CLUSTER_NAME}}' \
  --query '{issuer:oidcIssuerProfile.issuerUrl,oidcEnabled:oidcIssuerProfile.enabled,workloadIdentity:securityProfile.workloadIdentity.enabled}' \
  --output json
```

Select an explicit, dedicated ServiceAccount name in the private GitOps plan. For a kagent-owned token component, set `Agent.spec.declarative.deployment.serviceAccountName` to that name. If the Agent already runs, read both the declared and generated values:

```sh
kubectl -n '{{NAMESPACE}}' get agent '{{AGENT_NAME}}' \
  -o jsonpath='{.spec.declarative.deployment.serviceAccountName}{"\n"}'
kubectl -n '{{NAMESPACE}}' get deployment '{{AGENT_DEPLOYMENT_NAME}}' \
  -o jsonpath='{.spec.template.spec.serviceAccountName}{"\n"}'
```

If the Agent does not exist yet, those commands cannot establish the future subject. Agree the dedicated name with the AKS owner, add it to the reviewed manifest, and verify the generated Deployment after GitOps applies it. Give the identity team `system:serviceaccount:{{NAMESPACE}}:{{SERVICE_ACCOUNT}}` and the issuer **exactly as returned**, including a trailing slash. If the kagent Pod holds the credential, connect it through these fields:

```text
ServiceAccount.metadata.annotations["azure.workload.identity/client-id"] = {{BLUEPRINT_APP_ID}}
Agent.spec.declarative.deployment.serviceAccountName = {{SERVICE_ACCOUNT}}
Agent.spec.declarative.deployment.labels["azure.workload.identity/use"] = "true"
```

These are field mappings, not a complete manifest. If a separate proxy holds the credential, annotate **its** ServiceAccount and label **its** Pod instead; do not give the kagent Pod unnecessary blueprint access. Check the fields against the installed CRD and read them back after deployment. The old [`generate.py`](../../poc/azure-agent-id/generate.py) annotates a UAMI and is not a template for this direct path.

The identity owner creates the FIC and assigns the API role to the **child Agent ID principal**. The platform owner creates the ServiceAccount and Agent manifest, configures agentgateway, and proves the runtime token flow. Entra API app roles, Azure RBAC, and Kubernetes RBAC are different permissions. Do not ask for cluster-admin or broad Graph access merely to get an MCP API role.

## 1. Inspect the current agent lane without changing it

1. Confirm which work environment, namespace, kagent release, agentgateway release, Gateway API CRDs, and agent/controller ownership are actually installed. Record versions and the owning team in an approved work record. The bundle targets kagent `0.10.1` and agentgateway `v1.5.0`; do not assume the work installation matches it.
2. Identify one pilot Agent and its `RemoteMCPServer`, generated runtime Deployment/Pod, ServiceAccount, Secret references, A2A route, MCP route, policies, and MCP tool. Use read-only Kubernetes inspection. Do not export Secret data, access tokens, full environment dumps, or private hostnames into this public repository.
3. Trace both authenticated hops: **caller Agent ID → A2A gateway → kagent Agent**, then **agent-owned Agent ID → MCP gateway → MCP server**. A single identity for both hops is not the tested design. Keep the agent's MCP tool permissions separate from the caller's A2A permissions.
4. Check whether the deployed kagent version still renders `RemoteMCPServer.spec.headersFrom` Secret values into the runtime at Pod creation. The rehearsal required a new Pod after a token change. Check the installed CRD and controller behavior rather than assuming the example is current.
5. Check how the generated Agent Pod can receive an approved ServiceAccount, workload-identity Pod label, and (if chosen) a local credential helper. Check whether admission, network policy, and Pod security allow that shape. Do not modify the controller or the Agent CR yet.

Use [`teams/event/agent.yaml`](../../teams/event/agent.yaml) and the [bundle architecture](../../ARCHITECTURE.md) as examples of the existing ownership boundary. Application teams should not gain write access to gateway policies or other tenants' credentials.

## 2. Choose a workable agent-side token path

AKS Workload Identity itself is not the broken part. The blueprint federated credential is a persistent trust record. Kubernetes rotates the projected ServiceAccount token, and an Azure identity client can read the refreshed token file when it requests another Entra token. Our Agent ID path adds a second exchange using `fmi_path` and a child API token:

```text
Rotating AKS ServiceAccount assertion → blueprint exchange → child Agent ID API token → MCP Authorization header
```

In the tested kagent `0.10.1` path, `RemoteMCPServer.spec.headersFrom` resolved a Secret into the Agent runtime configuration. Updating the Secret did not replace that in-memory header until a new Agent Pod started. The missing component is a **dynamic child-token provider**, not a recurring FIC update or an OAuth refresh token to store. See [AKS Workload Identity](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview) and [Agent ID autonomous token acquisition](https://learn.microsoft.com/en-us/entra/agent-id/autonomous-agent-authentication-authorization-flow).

For the first work pilot, **evaluate a dedicated per-agent MCP egress proxy as the preferred dynamic path**. The proxy would own a dedicated ServiceAccount and blueprint FIC, read the current projected assertion at refresh time, run the two-stage exchange with the approved child `fmi_path`, cache the child API token until shortly before expiry, and attach it to each outbound MCP request to agentgateway. kagent would target that proxy instead of using `headersFrom` for an expiring API token. This design is a proposal, **not** an implemented or verified component. Before selecting it, prove that the installed kagent version can discover and use tools through the proxy, that the proxy preserves MCP streaming, and that NetworkPolicy and service authentication prevent another Pod from borrowing its credential. If the token holder changes from the kagent Pod to the proxy, update the ServiceAccount subject in the identity ticket **before** creating the FIC.

1. For the pilot, document how the agent will obtain a fresh **agent-owned** token for the MCP API, how it will attach that token to each request, and how it will continue working after token expiry. Keep the credential on the blueprint or an approved workload identity, never on the Agent ID object.
2. Compare the proposed per-agent proxy with these options against the *installed* kagent and agentgateway versions:
   - **Existing Secret header path:** a controlled token refresher updates the namespaced Secret and causes a safe kagent reconcile/new Pod before expiry. This fits the rehearsal's current kagent behavior but needs an operator, expiry/error handling, and namespace Secret-access review.
   - **In-Pod token helper:** the Agent obtains a header from a loopback-only helper on each call. Determine whether the installed kagent runtime can do this without a code change. The Microsoft Entra Auth SDK sidecar was **not** proven to return an Agent ID token for our custom API; its tested response had the blueprint principal or `AADSTS82001`. Do not select it until a work-environment token has the expected Agent ID `sub`.
   - **Gateway-side outbound credential:** check whether the installed agentgateway schema and runtime can obtain and attach the Agent ID token for the agent-to-MCP hop. This is research, not an implemented feature in this bundle. Keep the inbound caller policy distinct from outbound credential handling.
3. Choose a supported option with an implementation sketch, owner, rollback, token-refresh test, and remaining unknowns. Any dynamic token provider must re-read `AZURE_FEDERATED_TOKEN_FILE` when it refreshes, check the returned child `oid`, audience, and role, cache only until before expiry, and fail closed when renewal fails. Do not log token values. If none is supported without new code, report the exact integration gap. Do not insert a static long-lived access token as a production shortcut.
4. Align the Entra app role values with the policy files before rendering anything. The current [`event-a2a-policy.yaml`](event-a2a-policy.yaml) requires `team-event.a2a.invoke`; [`event-mcp-policy.yaml`](event-mcp-policy.yaml) requires `team-event.mcp.use`. One earlier lab run used `team-event.mcp.invoke`. Choose the exact work role with the identity and gateway owners. **Do not add the role and child `jwt.oid` as separate `Allow` expressions**: the AKS negative test found that they behaved as OR. Use one combined `"{{ROLE_VALUE}}" in jwt.roles && jwt.oid == "{{AGENT_OBJECT_ID}}"` expression and prove same-role wrong-child returns `403`.
5. Produce a **placeholder-only** Agent/ServiceAccount/RemoteMCPServer/gateway diff for review. Keep `{{TENANT_ID}}`, `{{API_APP_ID}}`, `{{BLUEPRINT_APP_ID}}`, and other environment values unresolved in any public artifact. For kagent `v0.10.1` trusted-proxy mode, the AKS pilot's [A2A route](event-a2a-direct-route.yaml) targeted the namespaced Agent Service with a ReferenceGrant; the older controller rewrite returned `401` without a trusted proxy identity. Validate the route, policy, and NetworkPolicy against the installed versions before proposing an apply.

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
2. Ask the AKS owner to confirm OIDC issuer and workload identity support for the chosen cluster. Ask the identity owner to review **direct** `AKS ServiceAccount → blueprint` federation, with the cluster issuer and exact `system:serviceaccount:<namespace>:<serviceaccount>` subject. A home-lab AKS pilot exercised this successfully; the proposed `ServiceAccount → UAMI → blueprint` chain failed with `AADSTS700231` and is not a valid default plan. Review whether a dedicated blueprint or trusted broker enforces the child Agent ID boundary. See the [identity ticket](../../poc/azure-agent-id/WORK-GITLAB-IDENTITY-TICKET.md) and [AKS workload identity](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview).
3. Define which approved owner will perform each operation if the SPN lacks rights. A portal, PowerShell, Graph client, or approved platform workflow is an alternate **tool for an authorized owner**, not a way around missing authorization.
4. Confirm the allowed egress to Entra's token endpoint and JWKS, internal image-mirror path, external TLS/ingress ownership, and whether the existing Gateway API CRDs can serve the Entra overlay. Do not replace shared Gateway API CRDs merely to satisfy this pilot; coordinate with their owner.
5. Write an ordered change plan and rollback for the identity objects, AKS-to-blueprint trust, token helper, Agent manifests, and gateway policy. Place all real object IDs, hostnames, certificate material, and tokens only in approved private work systems.

Stop here for review. The [AKS promotion guide](../../AKS-SUBSTRATE-PROMOTION.md) is a separate gate for the SandboxAgent/Agent Substrate lane; do not treat this Agent ID pilot as permission to deploy or change that runtime.

## 5. After explicit approval, implement and prove one pilot

1. Have the authorized identity and AKS owners create the reviewed Agent ID objects, exact app-role assignments, and direct ServiceAccount-to-blueprint federated credential (or another approved, proven broker design). A UAMI for unrelated Azure access is a separate decision. Record ownership and rollback privately. Do not make the SPN's first failed write an invitation to broaden its rights.
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

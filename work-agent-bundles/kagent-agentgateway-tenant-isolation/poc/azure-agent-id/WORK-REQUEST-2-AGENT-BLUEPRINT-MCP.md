# Request 2: Give child agents an inherited MCP permission

Copy this request into an approved private ticket. Replace every placeholder there. Do not put real tenant, identity, cluster, or service IDs in this public repository. This request covers the **running agent**. It does not grant a calling application access to the agent. Use [Request 1](WORK-REQUEST-1-CALLER-UAMI-A2A.md) for that work.

## Copy into the work request

**Title:** Create an Entra Agent ID blueprint and inherit the MCP app role for its child Agent IDs

**Environment and owner:** `{{ENVIRONMENT}}`; `{{REQUESTING_TEAM}}`; `{{BUSINESS_SPONSOR}}`

**Agent workload:** `{{AGENT_NAME}}` in AKS namespace `{{AGENT_NAMESPACE}}`

**Change requested from the Entra team:** Create or approve a dedicated Entra Agent ID blueprint and blueprint principal for the agents intended to share this MCP API permission. Create one runtime child Agent ID under that blueprint. Configure a federated identity credential on the **blueprint application** that trusts the exact AKS issuer and ServiceAccount subject below. Create or identify the protected MCP API app registration and service principal. Define or confirm the **application app role** `{{MCP_ROLE_VALUE}}` with `allowedMemberTypes: ["Application"]`. Declare that role in the blueprint's `requiredResourceAccess`, configure the MCP resource app in `inheritablePermissions` with roles enabled and delegated scopes disabled, and obtain an approved grant of that app role to the **blueprint principal**. Do not assign it directly to the child for this request.

**Agent identity objects:**

| Object type | Placeholder | Meaning |
|---|---|---|
| Agent ID blueprint application | `{{BLUEPRINT_NAME}}` | Credential-owning blueprint for this trust boundary. |
| Blueprint app/client ID | `{{BLUEPRINT_APP_CLIENT_ID}}` | Kubernetes ServiceAccount annotation and token request client ID. |
| Blueprint application object ID | `{{BLUEPRINT_APP_OBJECT_ID}}` | Graph application object for the FIC. This is not the client ID. |
| Blueprint principal object ID | `{{BLUEPRINT_PRINCIPAL_OBJECT_ID}}` | Entra tenant service principal receiving the MCP app-role grant. |
| Child Agent ID | `{{CHILD_AGENT_NAME}}` | Runtime agent identity created under the blueprint. |
| Child Agent ID object ID | `{{CHILD_AGENT_OBJECT_ID}}` | Expected token `oid`; the MCP role is inherited rather than directly assigned. |

**Agent AKS federation inputs supplied by the platform team:**

| Field | Placeholder |
|---|---|
| Cluster | `{{AKS_CLUSTER_NAME}}` |
| Exact AKS OIDC issuer, including any trailing slash | `{{AKS_OIDC_ISSUER}}` |
| Credential-holding workload | `{{AGENT_TOKEN_HOLDER}}` |
| Agent or token-proxy ServiceAccount | `{{AGENT_NAMESPACE}}` / `{{AGENT_SERVICE_ACCOUNT}}` |
| Federated subject | `system:serviceaccount:{{AGENT_NAMESPACE}}:{{AGENT_SERVICE_ACCOUNT}}` |
| Federated audience | `api://AzureADTokenExchange` |

If a dedicated token proxy acquires the child Agent ID token, use **its** ServiceAccount and namespace in the FIC. The runtime ServiceAccount annotation will reference `{{BLUEPRINT_APP_CLIENT_ID}}`, not the caller UAMI client ID. The caller UAMI from Request 1 is not a middle hop between the ServiceAccount and the blueprint. Our AKS pilot proved direct ServiceAccount-to-blueprint federation and found that ServiceAccount-to-UAMI-to-blueprint federation failed.

**Protected MCP API and permission:**

| Field | Placeholder | Meaning |
|---|---|---|
| MCP API app registration | `{{MCP_API_NAME}}` | Defines the permission. |
| MCP API app/client ID | `{{MCP_API_APP_CLIENT_ID}}` | Identifies the protected API application. |
| MCP API service-principal object ID | `{{MCP_API_SERVICE_PRINCIPAL_OBJECT_ID}}` | `resourceId` in the role assignment. |
| MCP API audience | `{{MCP_API_AUDIENCE}}` | Expected token `aud` at the gateway. |
| MCP app-role value | `{{MCP_ROLE_VALUE}}` | Expected token `roles` value. Pilot example: `team-event.mcp.use`. |
| MCP app-role ID | `{{MCP_ROLE_ID}}` | `appRoleId` in the role assignment. |
| Blueprint principal object ID | `{{BLUEPRINT_PRINCIPAL_OBJECT_ID}}` | `principalId` in the MCP app-role assignment. |
| Runtime child Agent ID object ID | `{{CHILD_AGENT_OBJECT_ID}}` | Expected token `oid` and platform gateway onboarding identity. |
| Permitted MCP tool | `{{ALLOWED_MCP_TOOL}}` | Gateway tool policy. Pilot example: `lookup_incident`. |

**Inheritance requested:** Make the approved MCP API application role inheritable by **all present and future child Agent IDs of this blueprint**. Limit this blueprint to the trust boundary whose children are intended to use `{{MCP_API_NAME}}`. For that resource app, configure application-role inheritance and no delegated-scope inheritance. Record the blueprint owner, current child inventory, future-child approval process, resource app, exact role grant, and revocation plan. `requiredResourceAccess` and `inheritablePermissions` are declarations, not grants; the administrator must also approve the role grant on the blueprint principal. In the current Entra API, `allAllowed` role inheritance includes later roles granted to this blueprint principal for the same resource app, so treat each later grant as access for all children and review it accordingly. Confirm the inherited role in a fresh child API token because it might not appear as a direct child assignment in Graph or the portal.

**Authorization outcome:** The agent acquires a child Agent ID token for `{{MCP_API_AUDIENCE}}`. The token must carry the child `oid` and inherited `{{MCP_ROLE_VALUE}}` in `roles`. Agentgateway will accept the approved child identity and role only on the MCP route, then allow only `{{ALLOWED_MCP_TOOL}}`. New children inherit the Entra role without another child app-role assignment; platform gateway and network onboarding remain separate. The app role is an API permission; Entra does not map it to an MCP tool name by itself.

**Why this is needed:** Agents intentionally created under this blueprint should share the MCP API permission without a new Entra role assignment for every child. The platform must still control which child identities and MCP tools can use its route; a role alone does not prove blueprint membership or grant a tool. No Azure subscription or resource-group RBAC is requested merely to call the MCP. If the MCP backend later needs to access an Azure resource, its execution identity needs a separate least-privilege Azure RBAC request.

**Return in the private ticket:** Blueprint app/client ID and object ID, blueprint-principal object ID, child Agent ID app/client and object IDs, child-to-blueprint link, FIC name and exact issuer/subject/audience, MCP API app/client and service-principal object IDs, MCP audience, role value and role ID, `requiredResourceAccess` and `inheritablePermissions` read-backs for that resource app, blueprint-principal app-role grant/consent read-back, current child inventory and future-child owner, sanitized fresh child-token claim summary, owner, sponsor, approver, review date, and revocation path. Do not return credentials or access tokens.

**Acceptance:** The chosen AKS ServiceAccount obtains a fresh child Agent ID token with expected `iss`, `aud`, inherited `roles`, and exact child `oid`, without a direct child app-role assignment. Agentgateway permits `{{ALLOWED_MCP_TOOL}}` for a platform-approved child and denies wrong audience, missing role, an unapproved child identity, and forbidden tools. Repeat the token and gateway checks as each additional child is onboarded. The platform team must also test token renewal and expiry behavior before production use.

## Desired state and definition of done

The chosen ServiceAccount federates directly to the blueprint application. The blueprint principal has an approved grant for `{{MCP_ROLE_VALUE}}` on `{{MCP_API_NAME}}`, and the blueprint declares the MCP API role in `requiredResourceAccess` and enables role inheritance in `inheritablePermissions`. A child Agent ID receives that role in a fresh MCP-audience token **without a direct child grant**. The platform's MCP gateway route accepts the exact onboarded child identity, inherited role, and approved tool. All present and future blueprint children inherit the Entra role, but each child still needs platform gateway onboarding before using this route.

Close the identity team's change when the blueprint, child link, FIC, API role, inheritance configuration, blueprint-principal grant, owner, future-child process, and revocation path have been read back in the private ticket. Close the platform verification only when the token and route tests below pass. The historical direct-child-grant pilot does not satisfy this inherited-grant test.

| Test from the agent token holder or an approved test client | Expected result and evidence |
|---|---|
| Exchange the projected ServiceAccount token through the blueprint and request a **fresh child** token for the MCP API | Expected tenant issuer, MCP `aud`, exact child `oid`, and inherited `{{MCP_ROLE_VALUE}}` in `roles`; no direct child assignment in the identity read-back. Record only sanitized claims. |
| Have the approved child call `{{ALLOWED_MCP_TOOL}}` through the MCP gateway | Gateway allows the request and MCP returns the expected bounded tool response; correlate gateway and MCP request logs. |
| Try no token, wrong audience, missing role, wrong child identity, and a forbidden MCP tool | Each call is denied before the protected tool executes; record gateway decision and absence of backend action. |
| In an approved pilot, create a second child under the same blueprint and obtain a fresh MCP token | The second child receives the inherited role without its own app-role grant. Gateway denies it until its exact identity and allowed tool are deliberately onboarded; then the permitted call succeeds. |
| Renew the child token across expiry, then test the agreed grant-revocation procedure with a **new** token | Renewal succeeds before production use; after revocation, a new token lacks the role or issuance is refused, and the gateway denies it. Previously issued tokens may remain valid until expiry. |

The Entra team owns or identifies the blueprint, child, API/role, FIC, inheritance configuration, grant, and their read-backs. The platform team owns token acquisition and renewal, gateway child/tool policy, network controls, and sanitized runtime evidence. The MCP owner confirms the tool and backend result. These owners jointly review the acceptance evidence.

## Identity-team mapping

For the app-role assignment, `principalId` is `{{BLUEPRINT_PRINCIPAL_OBJECT_ID}}`, `resourceId` is `{{MCP_API_SERVICE_PRINCIPAL_OBJECT_ID}}`, and `appRoleId` is `{{MCP_ROLE_ID}}`. The blueprint application holds the AKS FIC and declares the resource app eligible for inheritance. The protected MCP API application defines the role. The blueprint principal receives the approved grant; its child Agent IDs receive the inherited role in their API tokens. The gateway policy and Kubernetes network controls are separate platform changes.

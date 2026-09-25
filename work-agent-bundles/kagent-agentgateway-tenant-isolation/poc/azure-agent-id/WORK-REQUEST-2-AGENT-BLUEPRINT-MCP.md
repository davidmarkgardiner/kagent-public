# Request 2: Give one agent an identity and MCP permission

Copy this request into an approved private ticket. Replace every placeholder there. Do not put real tenant, identity, cluster, or service IDs in this public repository. This request covers the **running agent**. It does not grant a calling application access to the agent. Use [Request 1](WORK-REQUEST-1-CALLER-UAMI-A2A.md) for that work.

## Copy into the work request

**Title:** Create an Entra Agent ID blueprint and assign the MCP app role to the child Agent ID for `{{AGENT_NAME}}`

**Environment and owner:** `{{ENVIRONMENT}}`; `{{REQUESTING_TEAM}}`; `{{BUSINESS_SPONSOR}}`

**Agent workload:** `{{AGENT_NAME}}` in AKS namespace `{{AGENT_NAMESPACE}}`

**Change requested from the Entra team:** Create or approve a dedicated Entra Agent ID blueprint and blueprint principal for this trust boundary. Create one runtime child Agent ID under that blueprint. Configure a federated identity credential on the **blueprint application** that trusts the exact AKS issuer and ServiceAccount subject below. Create or identify the protected MCP API app registration and service principal. Define or confirm the **application app role** `{{MCP_ROLE_VALUE}}` with `allowedMemberTypes: ["Application"]`. Assign that role **directly to the runtime child Agent ID service principal**.

**Agent identity objects:**

| Object type | Placeholder | Meaning |
|---|---|---|
| Agent ID blueprint application | `{{BLUEPRINT_NAME}}` | Credential-owning blueprint for this trust boundary. |
| Blueprint app/client ID | `{{BLUEPRINT_APP_CLIENT_ID}}` | Kubernetes ServiceAccount annotation and token request client ID. |
| Blueprint application object ID | `{{BLUEPRINT_APP_OBJECT_ID}}` | Graph application object for the FIC. This is not the client ID. |
| Blueprint principal object ID | `{{BLUEPRINT_PRINCIPAL_OBJECT_ID}}` | Entra tenant service principal for the blueprint. |
| Child Agent ID | `{{CHILD_AGENT_NAME}}` | Runtime agent identity created under the blueprint. |
| Child Agent ID object ID | `{{CHILD_AGENT_OBJECT_ID}}` | Principal receiving the MCP app role and expected token `oid`. |

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
| Runtime child Agent ID object ID | `{{CHILD_AGENT_OBJECT_ID}}` | `principalId` in the role assignment and expected token `oid`. |
| Permitted MCP tool | `{{ALLOWED_MCP_TOOL}}` | Gateway tool policy. Pilot example: `lookup_incident`. |

**Inheritance requested:** Do **not** make the MCP role inheritable across a reused blueprint for this pilot. Assign it to `{{CHILD_AGENT_OBJECT_ID}}` only. If your process requires blueprint inheritance, stop and confirm that every current and future child of this blueprint should receive this role. Record the approved child set, resource app, grant, and revocation plan before enabling inheritance. A declaration in `requiredResourceAccess` or `inheritablePermissions` is not itself a grant.

**Authorization outcome:** The agent acquires a child Agent ID token for `{{MCP_API_AUDIENCE}}`. The token must carry the child `oid` and `{{MCP_ROLE_VALUE}}`. Agentgateway will accept that child identity and role only on the approved MCP route. Its MCP policy will allow only `{{ALLOWED_MCP_TOOL}}`. The app role is an API permission; Entra does not map it to an MCP tool name by itself.

**Why this is needed:** We need to prove that `{{AGENT_NAME}}` can use the approved MCP tool but another agent cannot use the same route, even if it has a similar role. No Azure subscription or resource-group RBAC is requested merely to call the MCP. If the MCP backend later needs to access an Azure resource, its execution identity needs a separate least-privilege Azure RBAC request.

**Return in the private ticket:** Blueprint app/client ID and object ID, blueprint-principal object ID, child Agent ID app/client and object IDs, child-to-blueprint link, FIC name and exact issuer/subject/audience, MCP API app/client and service-principal object IDs, MCP audience, role value and role ID, direct child app-role assignment read-back, owner, sponsor, approver, review date, and revocation path. Do not return credentials or access tokens.

**Acceptance:** The chosen AKS ServiceAccount obtains a fresh child Agent ID token with expected `iss`, `aud`, `roles`, and exact child `oid`. Agentgateway permits `{{ALLOWED_MCP_TOOL}}` and denies wrong audience, missing role, wrong child identity, and forbidden tools. The platform team must also test token renewal and expiry behavior before production use.

## Identity-team mapping

For the app-role assignment, `principalId` is `{{CHILD_AGENT_OBJECT_ID}}`, `resourceId` is `{{MCP_API_SERVICE_PRINCIPAL_OBJECT_ID}}`, and `appRoleId` is `{{MCP_ROLE_ID}}`. The blueprint application holds the AKS FIC. The protected MCP API application defines the role. The child Agent ID receives the role. The gateway policy and Kubernetes network controls are separate platform changes.

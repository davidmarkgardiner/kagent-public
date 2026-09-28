# Request 1: Let an AKS application invoke one agent

Copy this request into an approved private ticket. Replace every placeholder there. Do not put real tenant, identity, cluster, or service IDs in this public repository. This request covers the **calling application**. It does not create the agent's blueprint or grant the agent MCP access. Use [Request 2](WORK-REQUEST-2-AGENT-BLUEPRINT-MCP.md) for that work.

## Copy into the work request

**Title:** Assign an A2A invoke app role to the AKS caller UAMI for `{{AGENT_NAME}}`

**Environment and owner:** `{{ENVIRONMENT}}`; `{{REQUESTING_TEAM}}`; `{{BUSINESS_SPONSOR}}`

**Caller application:** `{{CALLER_APPLICATION_NAME}}` in AKS namespace `{{CALLER_NAMESPACE}}`

**Target agent:** `{{AGENT_NAME}}` and its protected A2A API `{{A2A_API_NAME}}`

**Change requested from the Entra team:** Create or identify the protected A2A API application and service principal. Confirm its Application ID URI and token audience `{{A2A_API_AUDIENCE}}`. Define or confirm the **application app role** `{{A2A_INVOKE_ROLE_VALUE}}` with `allowedMemberTypes: ["Application"]`. Assign that role to the service principal for the **caller UAMI** listed below. This A2A API is a separate protected resource; this request does not require an Agent ID blueprint or a child Agent ID. Do not assign the caller role to the runtime child Agent ID.

**Caller UAMI I will provide:**

| Field | Placeholder | Why it is needed |
|---|---|---|
| UAMI resource name | `{{CALLER_UAMI_NAME}}` | Azure user-assigned managed identity resource. |
| UAMI client ID | `{{CALLER_UAMI_CLIENT_ID}}` | Entra application identifier for the caller. Annotate the caller's Kubernetes ServiceAccount with it. |
| UAMI principal or service-principal object ID | `{{CALLER_UAMI_PRINCIPAL_OBJECT_ID}}` | Entra service-principal object identifier. Use it as `principalId` in the app-role assignment, not as the ServiceAccount annotation. |
| UAMI resource group | `{{CALLER_UAMI_RESOURCE_GROUP}}` | Azure resource group that holds the UAMI and FIC. |

**Caller AKS federation I will arrange with the platform team:**

| Field | Placeholder |
|---|---|
| Cluster | `{{AKS_CLUSTER_NAME}}` |
| Exact AKS OIDC issuer, including any trailing slash | `{{AKS_OIDC_ISSUER}}` |
| Caller ServiceAccount | `{{CALLER_NAMESPACE}}` / `{{CALLER_SERVICE_ACCOUNT}}` |
| Federated subject | `system:serviceaccount:{{CALLER_NAMESPACE}}:{{CALLER_SERVICE_ACCOUNT}}` |
| Federated audience | `api://AzureADTokenExchange` |
| FIC owner | `{{CALLER_UAMI_FIC_OWNER}}` |

The FIC for this request belongs on the **caller UAMI**. I will create it if my Azure access and change process permit it. The caller ServiceAccount will reference `{{CALLER_UAMI_CLIENT_ID}}`. The Pod will use the `azure.workload.identity/use: "true"` label. AKS mounts a projected ServiceAccount token; it does not mount the UAMI itself.

**Authorization outcome:** The application requests an Entra access token for `{{A2A_API_AUDIENCE}}`, not for Azure Resource Manager. That token must identify the caller UAMI and carry `{{A2A_INVOKE_ROLE_VALUE}}`. The application sends it to the protected A2A route. Agentgateway will verify the token issuer, audience, app role, and exact caller object ID before forwarding to `{{AGENT_NAME}}`. The platform-owned route and policy restrict access to this named agent; the Entra app-role assignment alone does not select an agent.

**Why this is needed:** We need to prove that this application can invoke `{{AGENT_NAME}}` but an unapproved application cannot. The Entra app-role assignment places the approved role in this caller's A2A API token. The gateway policy enforces access on each call and denies roleless tokens. Please confirm whether the protected API also requires app-role assignment before Entra issues a token. No Azure resource RBAC or Agent ID blueprint permission is requested for the caller in this ticket.

**Return in the private ticket:** A2A API app/client ID, service-principal object ID, Application ID URI, role value and role ID, the UAMI object ID used as `principalId`, the app-role assignment read-back, owner, approver, and revocation path. Confirm whether your team, my team, or the platform team owns the caller UAMI FIC. Do not return credentials or access tokens.

**Acceptance:** The caller obtains a fresh A2A-audience token with the expected `iss`, `aud`, `roles`, and `oid` claims. Agentgateway allows the approved caller and denies a missing token, wrong audience, missing role, or wrong caller identity. We will record sanitized claim summaries, not token values.

## Desired state and definition of done

The named AKS application uses its own ServiceAccount and UAMI to obtain a short-lived token for `{{A2A_API_AUDIENCE}}`. Entra has assigned `{{A2A_INVOKE_ROLE_VALUE}}` to that UAMI service principal. The platform's A2A gateway route accepts that role **and the exact approved UAMI object ID** for `{{AGENT_NAME}}`; the role by itself is insufficient to select or invoke the agent.

Close the identity team's change when the protected API, role, UAMI assignment, ownership, and FIC owner have been read back and returned in the private ticket. Close the platform verification only when a fresh workload token and gateway tests below pass. Object creation or a successful token request alone is not end-to-end proof.

| Test from the caller workload or an approved test client | Expected result and evidence |
|---|---|
| Obtain a fresh token for the A2A API; inspect claims without recording the token | Expected tenant issuer, A2A `aud`, UAMI `oid`, and `{{A2A_INVOKE_ROLE_VALUE}}` in `roles`; sanitized claim summary. |
| Invoke the named agent through its A2A gateway route with that token | Gateway allows the request and the named agent returns a valid response; gateway/agent request correlation recorded. |
| Repeat with no token, wrong audience, and a token missing the role | Each request is denied before reaching the agent; record gateway decision and absence of upstream invocation. |
| Repeat with a different caller identity, including one with the same role if available | Gateway denies it because its `oid` is not the approved UAMI; record the decision. |
| Revoke the UAMI's A2A app-role grant in an approved test window and obtain a **new** token | The new token lacks the role or token issuance is refused under the API's assignment policy; the gateway denies it. Do not use an already issued token as revocation proof. |

The platform team owns the ServiceAccount/UAMI federation, A2A route and policy, test clients, and sanitized gateway evidence. The Entra team owns or identifies the API/role and assignment, provides their read-backs, and confirms the FIC owner. The two teams jointly review the acceptance evidence.

## Identity-team mapping

For the app-role assignment, `principalId` is `{{CALLER_UAMI_PRINCIPAL_OBJECT_ID}}`, `resourceId` is `{{A2A_API_SERVICE_PRINCIPAL_OBJECT_ID}}`, and `appRoleId` is `{{A2A_INVOKE_ROLE_ID}}`. The app registration defines the role; the caller UAMI service principal receives it. The A2A route policy is a separate platform change.

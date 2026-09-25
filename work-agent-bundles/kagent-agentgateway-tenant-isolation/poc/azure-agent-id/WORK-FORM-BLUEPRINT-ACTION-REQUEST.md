# Work form draft: Agent ID blueprint and action-scoped API access

This is the combined reference for two independent requests. For two tickets, copy [Request 1: caller UAMI to agent A2A](WORK-REQUEST-1-CALLER-UAMI-A2A.md) and [Request 2: agent blueprint to MCP](WORK-REQUEST-2-AGENT-BLUEPRINT-MCP.md) separately. For one ticket, paste both sections under separate change items. Replace placeholders only in the approved **private** work request form. This is not an AECM/AACM schema or an approved work change. Do not put real client IDs, SPN/object IDs, cluster issuer URLs, internal service names, or contacts in this public file. Use the [full identity ticket](WORK-GITLAB-IDENTITY-TICKET.md) and [native Graph examples](WORK-NATIVE-GRAPH-CLI-EXAMPLES.md) if the identity team asks for implementation details.

## Title

Manual Entra Agent ID blueprint, AKS federation, and scoped A2A/MCP API-role assignments for `{{AGENT_NAME}}`

## Description of required change

We would like to pilot `{{AGENT_NAME}}` in AKS namespace `{{AGENT_NAMESPACE}}`. Please create or approve a dedicated Entra Agent ID blueprint and blueprint principal, create one runtime child Agent ID, and configure **direct** AKS ServiceAccount-to-blueprint federation. The credential-holding workload is `{{AGENT_TOKEN_HOLDER}}` (agent Pod or dedicated token proxy), using ServiceAccount `{{AGENT_SERVICE_ACCOUNT}}`. We need the child Agent ID to call only the approved protected MCP API, and a separately identified application/agent caller to invoke this agent's A2A endpoint.

Please use your approved manual identity process while AECM/AACM support for blueprint creation and these permission assignments is unavailable or unconfirmed. This request does not authorize an AKS deployment, broad Graph privileges for our AKS SPN, or copying credentials into Pods.

## AKS federation inputs

| Field | Value to provide privately |
|---|---|
| AKS cluster and environment | `{{AKS_CLUSTER_NAME}}`, `{{ENVIRONMENT}}` |
| Exact OIDC issuer, including trailing slash if present | `{{AKS_OIDC_ISSUER}}` |
| Credential holder | `{{AGENT_TOKEN_HOLDER}}` |
| Namespace / ServiceAccount | `{{AGENT_NAMESPACE}}` / `{{AGENT_SERVICE_ACCOUNT}}` |
| Federated subject | `system:serviceaccount:{{AGENT_NAMESPACE}}:{{AGENT_SERVICE_ACCOUNT}}` |
| Federated audience | `api://AzureADTokenExchange` |

The FIC belongs on the **blueprint application** for the agent runtime. Our AKS pilot proved ServiceAccount → blueprint directly; ServiceAccount → UAMI → blueprint failed. A separate calling application Pod may use ordinary AKS Workload Identity to its **own** UAMI or app principal to obtain the A2A token. These are two different federations and identities.

## Permission requests — please treat as distinct grants

| Direction and action | Protected Entra resource and permission | Principal receiving permission | Inheritance requested | Runtime enforcement |
|---|---|---|---|---|
| Application/agent caller → `{{AGENT_NAME}}` | `{{A2A_API_NAME}}`, audience `{{A2A_API_AUDIENCE}}`, **application app role** `{{A2A_INVOKE_ROLE_VALUE}}` (pilot example: `team-event.a2a.invoke`) | `{{CALLER_SP_OBJECT_ID}}` for `{{CALLER_APP_OR_UAMI_NAME}}`; provide its client ID separately | **None.** This is a caller grant, not a permission inherited by runtime child Agent IDs. | A2A agentgateway route verifies issuer, audience, role, and approved caller object ID. |
| `{{AGENT_NAME}}` → approved MCP API | `{{MCP_API_NAME}}`, audience `{{MCP_API_AUDIENCE}}`, **application app role** `{{MCP_ROLE_VALUE}}` (pilot example: `team-event.mcp.use`) | The specific runtime `{{CHILD_AGENT_ID_OBJECT_ID}}` | **Direct child assignment for this pilot.** Do not grant it to a shared blueprint principal as an inherited role without separate approval. | MCP agentgateway route verifies issuer, audience, role, exact child object ID, and allowed MCP tool name. |
| MCP/workflow → Azure resource, only if needed | `{{AZURE_RESOURCE}}`, exact Azure RBAC role and scope `{{AZURE_ROLE_AND_SCOPE}}` | `{{MCP_OR_WORKFLOW_EXECUTION_PRINCIPAL}}`, not the blueprint | Not a blueprint-inheritable API permission. | Azure resource authorization, plus backend/workflow policy. Defer until the resource owner confirms need and least privilege. |

The current pilot uses **one MCP API role plus a gateway tool allowlist**: `team-event.mcp.use` and only `lookup_incident`. Entra does not understand MCP tool names. If we later need separately approved actions such as `incident.read` and `incident.write`, the protected API owner must expose distinct app roles and the gateway/backend must enforce a reviewed role-to-tool mapping. A role name alone does not enforce a tool action. Write-capable operations must remain behind approved workflows and their own execution permissions.

## Blueprint inheritance decision

The other work request used “inheritable permissions.” Please confirm exactly which **resource application**, delegated scopes or application roles, consent/grant target, and child identities that referred to. In Microsoft Entra Agent ID, `requiredResourceAccess` and `inheritablePermissions` are declarations; neither alone is an authorization grant. When an admin grants an eligible API role to a blueprint principal and configures that resource app as inheritable, **all present and future child Agent IDs** can receive that role in their tokens. A direct grant to one child applies only to that child.

For this isolated pilot, please **do not make the MCP role inheritable across a reused/shared blueprint**. Prefer a direct assignment to the runtime child. If your process requires inheritance, pause for a security review and confirm that the blueprint is dedicated to exactly the set of children meant to share the same role. Record the effective roles in a newly issued child API token; inherited roles may not appear as direct assignments on the child in Graph/portal read-back. Do not assume “all allowed roles” means a fixed, per-tool permission list: later grants on the blueprint principal can also flow to children.

## Justification

We need to prove that an approved caller application can invoke only `{{AGENT_NAME}}`, and that this agent can call only `{{ALLOWED_MCP_TOOL}}` on `{{MCP_API_NAME}}`, without borrowing another agent's identity or reaching the backend directly. The blueprint/FIC establishes the runtime authentication path; the two Entra API-role grants establish who may obtain the relevant A2A and MCP permissions; platform-owned agentgateway and Kubernetes policies enforce the route, exact identity, tool, and network boundaries. No Azure subscription/resource-group RBAC is requested merely to call A2A or MCP.

## Please return in the private request

- Created/reused status, owner, sponsor, review date, revocation owner, blueprint app/client and object IDs, blueprint-principal object ID, and child Agent ID app/object IDs.
- Exact FIC name, issuer, subject, audience, and blueprint application on which it is installed.
- For **each API**: app/client ID, resource service-principal object ID, Application ID URI/token audience, role value and role ID, principal object ID receiving the role, direct-vs-inherited status, approver/admin-consent record, and read-back.
- Clarification of `{{EXISTING_SPN_OR_CLIENT_ID}}`: is it the AECM executor, the calling application's identity, a protected API registration, or something else? These have different jobs and must not be conflated.
- Whether the current AECM/AACM process can create the blueprint, child, FIC, protected API role, and direct child/caller assignments. If not, identify the approved manual executor and future automation intake contract.

The platform team will separately prepare GitOps changes for the ServiceAccounts, Agent, A2A/MCP routes and policies, `ReferenceGrant`, NetworkPolicy, and dynamic token renewal. Acceptance requires token-claim checks (`iss`, `aud`, `roles`, exact `oid`) and positive/negative A2A→Agent→MCP tests in the work environment. The home-lab AKS proof is not work-tenant approval or production-token-refresh evidence.

## Official Microsoft references

- [Blueprint inheritance and required resource access](https://learn.microsoft.com/en-us/entra/agent-id/concept-inheritable-permissions)
- [Configure inheritable permissions](https://learn.microsoft.com/en-us/entra/agent-id/configure-inheritable-permissions-blueprints)
- [Grant an app role to a service principal](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-post-approleassignedto?view=graph-rest-1.0)
- [Agent identities, blueprints, and Azure RBAC distinction](https://learn.microsoft.com/en-us/entra/agent-id/agent-service-principals)

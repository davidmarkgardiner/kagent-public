# Native Azure CLI and Microsoft Graph examples for the identity team

This is a **review template**, not an AACM schema or a script to run unchanged. An Entra Agent ID blueprint is a specialized Microsoft Graph application object, not an ARM/Bicep deployment template. The JSON request bodies are the closest native, declarative template for it. The identity team should use its approved AACM, portal, Graph, or CLI workflow and perform writes only after authorization. Put filled-in JSON and responses in an approved **private** location, never in this public repository. These examples were checked against Microsoft documentation; they have **not** been executed in the work tenant.

Use the [identity ticket](WORK-GITLAB-IDENTITY-TICKET.md) to agree owner, sponsor, blueprint reuse, role value, token holder, and AKS issuer first. The application/client ID (`appId`) and Graph object ID (`id`) are different: record both from each response. `az rest` uses the signed-in Azure CLI identity for Graph; it does not grant that identity the required Graph permission or Entra role. Confirm tenant, permissions, consent, and change approval privately before any `POST` or `PATCH`.

Ask the identity team to map its executor to the least-privileged permissions in the linked Microsoft operations: blueprint creation (`AgentIdentityBlueprint.Create`), blueprint-principal creation (`AgentIdentityBlueprintPrincipal.Create`), child creation (`AgentIdentity.Create.All`), and app-role assignment (`AppRoleAssignment.ReadWrite.All` plus `Application.Read.All`) are **separate** Graph grants. API app registration and FIC changes have their own application-write/ownership requirements. Delegated operations also require a supported Entra role or ownership; a subscription Owner assignment is not a substitute. The identity team must decide the exact permission and consent package for its AACM or human executor.

```sh
az account show --query '{tenantId:tenantId,name:name}' --output json
```

## 1. Blueprint application and principal

Create a private `blueprint.json` from this body. A named sponsor is required. Review whether a dedicated blueprint is needed: a holder of its credential can select children of that blueprint via `fmi_path`.

```json
{
  "displayName": "{{BLUEPRINT_NAME}}",
  "sponsors@odata.bind": [
    "https://graph.microsoft.com/v1.0/users/{{SPONSOR_USER_OBJECT_ID}}"
  ]
}
```

```sh
az rest --method POST --url 'https://graph.microsoft.com/v1.0/applications/microsoft.graph.agentIdentityBlueprint' --headers Content-Type=application/json --body @blueprint.json
```

Record the returned blueprint `id` as `{{BLUEPRINT_OBJECT_ID}}` and `appId` as `{{BLUEPRINT_APP_ID}}`. After checking that its principal does not already exist, create a private `blueprint-principal.json`:

```json
{"appId":"{{BLUEPRINT_APP_ID}}"}
```

```sh
az rest --method POST --url 'https://graph.microsoft.com/v1.0/servicePrincipals/microsoft.graph.agentIdentityBlueprintPrincipal' --headers Content-Type=application/json --body @blueprint-principal.json
az rest --method GET --url 'https://graph.microsoft.com/v1.0/applications/{{BLUEPRINT_OBJECT_ID}}/microsoft.graph.agentIdentityBlueprint'
```

Record the blueprint-principal `id` as `{{BLUEPRINT_PRINCIPAL_OBJECT_ID}}` and read it back:

```sh
az rest --method GET --url 'https://graph.microsoft.com/v1.0/servicePrincipals/{{BLUEPRINT_PRINCIPAL_OBJECT_ID}}/microsoft.graph.agentIdentityBlueprintPrincipal'
```

Do **not** use `az ad app create` for the specialized blueprint type; that command creates an ordinary application.

## 2. Protected MCP API application and application role

If an approved MCP API registration already exists, review and reuse it instead of creating a duplicate. Otherwise create a private `mcp-app-roles.json`. Generate a new role UUID under the identity team's process and replace `{{MCP_ROLE_ID}}`; agree the role value with the MCP owner. The role belongs to the API, not to the blueprint.

```json
[
  {
    "id": "{{MCP_ROLE_ID}}",
    "allowedMemberTypes": ["Application"],
    "description": "Invoke the approved MCP API",
    "displayName": "MCP use",
    "isEnabled": true,
    "value": "{{MCP_ROLE_VALUE}}"
  }
]
```

```sh
az ad app create --display-name '{{MCP_API_NAME}}' --sign-in-audience AzureADMyOrg --requested-access-token-version 2 --app-roles @mcp-app-roles.json
```

Record the returned API `appId` as `{{MCP_APP_ID}}` and object `id` as `{{MCP_APP_OBJECT_ID}}`. Set and read back the agreed audience, then create or confirm the resource service principal:

```sh
az ad app update --id '{{MCP_APP_ID}}' --identifier-uris 'api://{{MCP_APP_ID}}'
az ad sp create --id '{{MCP_APP_ID}}'
az ad app show --id '{{MCP_APP_ID}}' --query '{id:id,appId:appId,identifierUris:identifierUris,api:api,appRoles:appRoles}'
az ad sp show --id '{{MCP_APP_ID}}' --query '{id:id,appId:appId}'
```

Record the API service-principal object `id` as `{{MCP_SP_OBJECT_ID}}`. `api://{{MCP_APP_ID}}` is an example audience; if the MCP owner already has an approved Application ID URI, use and verify that instead.

## 3. Child Agent ID and MCP app-role assignment

Create a private `child-agent.json`. The blueprint link takes its **app/client ID**, not its object ID. Microsoft currently documents this typed endpoint in Graph v1.0; its broader admin guide still shows a beta example, so the identity team should confirm the version it supports before a work change.

```json
{
  "displayName": "{{AGENT_IDENTITY_NAME}}",
  "agentIdentityBlueprintId": "{{BLUEPRINT_APP_ID}}",
  "sponsors@odata.bind": [
    "https://graph.microsoft.com/v1.0/users/{{SPONSOR_USER_OBJECT_ID}}"
  ]
}
```

```sh
az rest --method POST --url 'https://graph.microsoft.com/v1.0/servicePrincipals/microsoft.graph.agentIdentity' --headers Content-Type=application/json --body @child-agent.json
```

Record the returned child `id` as `{{CHILD_AGENT_OBJECT_ID}}`. Assign the MCP role to **that child principal**, not to the blueprint or a UAMI. Create private `mcp-role-assignment.json`:

```json
{
  "principalId": "{{CHILD_AGENT_OBJECT_ID}}",
  "resourceId": "{{MCP_SP_OBJECT_ID}}",
  "appRoleId": "{{MCP_ROLE_ID}}"
}
```

```sh
az rest --method POST --url 'https://graph.microsoft.com/v1.0/servicePrincipals/{{MCP_SP_OBJECT_ID}}/appRoleAssignedTo' --headers Content-Type=application/json --body @mcp-role-assignment.json
az rest --method GET --url 'https://graph.microsoft.com/v1.0/servicePrincipals/{{CHILD_AGENT_OBJECT_ID}}/microsoft.graph.agentIdentity'
az rest --method GET --url 'https://graph.microsoft.com/v1.0/servicePrincipals/{{CHILD_AGENT_OBJECT_ID}}/appRoleAssignments'
```

This is a Microsoft Entra **API app role**, not an Azure subscription/resource-group RBAC role. `az role assignment create` and delegated-scope grants are not substitutes.

## 4. Direct AKS ServiceAccount federation on the blueprint

Do this only after the AKS owner confirms the exact OIDC issuer (including trailing slash) and the credential-holding ServiceAccount. If the token holder is a per-agent proxy, use **its** ServiceAccount. Create private `blueprint-aks-fic.json`:

```json
{
  "name": "{{FEDERATED_CREDENTIAL_NAME}}",
  "issuer": "{{AKS_OIDC_ISSUER}}",
  "subject": "system:serviceaccount:{{NAMESPACE}}:{{SERVICE_ACCOUNT}}",
  "audiences": ["api://AzureADTokenExchange"]
}
```

The ordinary Azure CLI application-FIC command accepts this JSON file. The `--id` here is the **blueprint app/client ID**:

```sh
az ad app federated-credential create --id '{{BLUEPRINT_APP_ID}}' --parameters blueprint-aks-fic.json
az ad app federated-credential list --id '{{BLUEPRINT_APP_ID}}'
```

The equivalent Graph collection is `POST https://graph.microsoft.com/v1.0/applications/{{BLUEPRINT_OBJECT_ID}}/federatedIdentityCredentials`. Do not substitute `az identity federated-credential create`: that targets a UAMI. The lab's AKS ServiceAccount → UAMI → blueprint chain failed with `AADSTS700231`; the successful AKS path was **ServiceAccount → blueprint directly**.

## 5. Identity-team read-back and platform handoff

Return the blueprint application and principal IDs, child Agent ID object ID and blueprint link, MCP API app and service-principal IDs, exact API audience, role value/ID and assignment, and exact FIC issuer/subject/audience **in the private ticket**. Record owner, approver, lifecycle, consent, and revocation path. Avoid returning credentials or access tokens. Object creation alone does not prove workload authentication.

The platform team then puts the **blueprint app/client ID** on the credential-holding Kubernetes ServiceAccount, enables AKS Workload Identity mutation on its Pod, and implements dynamic child Agent ID token acquisition/renewal. It must test the intended agent-to-MCP call and wrong-child, missing-role, wrong-audience, direct-backend, and expiry/revocation denials. The FIC is durable trust; short-lived tokens still need renewal. See the [work-agent walkthrough](../../profiles/aks-entra/WORK-AGENT-START-HERE.md) and [AKS evidence](AKS-FULL-E2E-EVIDENCE-2026-09-25.md).

## Microsoft references

- [Blueprint create](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-post?view=graph-rest-1.0), [blueprint principal create](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprintprincipal-post?view=graph-rest-1.0), [child Agent ID create](https://learn.microsoft.com/en-us/graph/api/agentidentity-post?view=graph-rest-1.0), and [Agent ID admin guide](https://learn.microsoft.com/en-us/entra/agent-id/create-delete-agent-identities)
- [Azure CLI `az rest`](https://learn.microsoft.com/en-us/cli/azure/reference-index?view=azure-cli-latest#az-rest), [`az ad app`](https://learn.microsoft.com/en-us/cli/azure/ad/app?view=azure-cli-latest), [`az ad sp`](https://learn.microsoft.com/en-us/cli/azure/ad/sp?view=azure-cli-latest), and [app federated credentials](https://learn.microsoft.com/en-us/cli/azure/ad/app/federated-credential?view=azure-cli-latest)
- [Graph app-role assignment](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-post-approleassignedto?view=graph-rest-1.0) and [app federated credential](https://learn.microsoft.com/en-us/graph/api/federatedidentitycredential-post?view=graph-rest-1.0)

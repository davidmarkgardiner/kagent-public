# Entra Agent ID, blueprints and gateway access

## Two requests, with separate permission checks

| Request | Identity acquiring the token | Audience and role | Gateway check |
| --- | --- | --- | --- |
| Calling application → SRE chatbot | Caller UAMI / service principal | A2A API and `sre.chat.invoke` | Exact caller identity, tenant, audience and role on the named SRE route |
| SRE agent → Kubernetes MCP | Child Agent ID through its dedicated blueprint | MCP API and `sre.kubernetes.read` | Exact child identity, tenant, audience, role and allowed MCP operation |

The blueprint holds credential configuration. Its child Agent ID carries the agent's permissions and audit identity. Sponsors identify the accountable human or group. The parent blueprint claim is useful audit context; do not use it alone to allow every child into an API.

The Microsoft token for these custom APIs is an OAuth access token encoded as a signed JWT. `jwtAuthentication` validates that same token. The gateway is not issuing another token in these examples. These policies require v2 custom-API tokens; configure and verify the API's `requestedAccessTokenVersion`, issuer, audience and actual claims accordingly. An ID token or a token issued for Microsoft Graph is not the access token for these APIs.

## Setup sequence and owners

1. **Identity owner:** register the protected A2A and MCP APIs and their application roles. Assign the invoke role only to the permitted calling application/UAMI.
2. **Identity owner:** create a dedicated Agent ID blueprint with an accountable sponsor/owner, then create the child Agent ID for this SRE agent.
3. **Identity owner:** grant the MCP read role directly to the named child for this bounded example. If blueprint permission inheritance is chosen, separately approve the shared trust/grant boundary and retain exact-child restrictions at the gateway.
4. **Identity and platform owners:** add the blueprint federated credential using [the Graph FIC payload](../identity/blueprint-federated-credential.json). Its issuer is the cluster's OIDC issuer, its subject is `system:serviceaccount:team-sre:sre-agent-token-holder`, and its exchange audience is `api://AzureADTokenExchange`. This is a Microsoft Graph object, not a Kubernetes resource.
5. **Runtime owner:** use [file 11](../11-blueprint-token-holder.yaml) for the selected token component. Its Pod must select that ServiceAccount and carry the Workload Identity label. The client ID annotation selects the blueprint, not the incoming application's UAMI.
6. **Runtime owner:** use supported Agent ID libraries or a reviewed implementation for the blueprint-to-child exchange. Acquire the blueprint exchange token with `fmi_path` selecting the child, then request the child token for the MCP API. Renew tokens before expiry. Ordinary Workload Identity injection alone does not implement the child exchange.
7. **Platform owner:** use [file 10](../10-entra-jwks.yaml) for trusted public keys; apply the reviewed route/policies in [12](../12-application-to-agent-policy.yaml) and [13](../13-agent-to-mcp-policy.yaml).
8. **Runtime/platform owners:** [file 06](../06-remote-mcp.yaml) demonstrates a version-specific Secret-backed Authorization header. The token component must populate the complete header value privately. Do not assume that updating a Secret makes a running agent reload it; verify the installed client's reload/reconnect behavior. This pack does not supply or prove an unattended token-refresh implementation.
9. **Destination owner:** retain the MCP's resource restrictions and downstream service-account RBAC. Review positive and negative access behavior and direct bypass paths before rollout.

The selected token-holder identity must not exceed the authority of administrators who control that namespace. Independent trust domains should use separate blueprint credential boundaries or a separately proven broker.

## What to point to in the policies

- `traffic.jwtAuthentication`: require and validate the Entra token. The trusted issuer/JWKS establish the signer, and the audience pins the intended API.
- `traffic.authorization.action: Require`: every identity/role condition is mandatory. Separate `Allow` expressions are OR alternatives.
- `jwt.azp` and `jwt.oid`: the exact app/child, using verified v2 access-token claims. The child Agent ID's app and object identifiers are the same in Microsoft's Agent ID model.
- `backend.mcp.authorization`: the permitted operation names. MCP implementation and resource RBAC still control arguments and data scope.

## Evidence boundary

The repository's ownership material records a disposable pilot using direct ServiceAccount-to-blueprint federation, a direct child grant and manual token update/restart. The complete workplace caller-UAMI/inherited-grant/automatic-refresh path remains target validation. This pack illustrates direct federation; it does not claim a new deployment or fresh tenant test.

## Official references

- [Access tokens](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens)
- [Agent identities](https://learn.microsoft.com/en-us/entra/agent-id/agent-identities)
- [Create a blueprint](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/create-blueprint)
- [Autonomous agent token acquisition](https://learn.microsoft.com/en-us/entra/agent-id/autonomous-agent-authentication-authorization-flow)
- [Agent token claims](https://learn.microsoft.com/en-us/entra/agent-id/agent-token-claims)
- [Gateway authorization](https://agentgateway.dev/docs/kubernetes/latest/documentation/security/authorization/)

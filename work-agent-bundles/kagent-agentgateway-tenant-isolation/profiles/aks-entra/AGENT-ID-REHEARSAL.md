# Microsoft Entra Agent ID: proven against the same gateway policy

Agent ID was reachable in a throwaway Entra tenant, and **agentgateway
accepted a real Agent ID token using this profile's policy unchanged**.

**Run on 2026-09-23.** Local kind cluster, Gateway API `v1.6.2` experimental,
agentgateway `v1.5.0`, [`event-a2a-policy.yaml`](event-a2a-policy.yaml) and
[`entra-jwks.yaml`](entra-jwks.yaml) with only the tenant and audience
placeholders substituted. No policy change of any kind was needed.

| Check | Caller | Result |
|---|---|---|
| Agent identity holding `team-event.a2a.invoke` | an **agent identity**, not an app registration | **200**, reached the backend; gateway logged `jwt.sub` as the agent identity's object id |
| Agent identity with no app role | a second agent identity under the same blueprint | **403** `authorization failed` |
| No credential | none | **401** |

That is the headline for planning: **moving from app registrations to Agent ID
does not touch the gateway, the policies, or the isolation gates.** The token
is a normal Entra v2 token — same issuer, same audience, `roles` claim — so
everything downstream is unchanged. Only how the identity is created and how
the token is obtained differ.

## The object model, as the API actually behaves

Three objects, created in this order. `agentIdentity` derives from
`servicePrincipal`, and `agentIdentityBlueprint` from `application`, so they
appear through casts on the existing collections in Microsoft Graph **beta**:

```sh
# 1. The blueprint. Sponsors are required; a create without one fails with
#    "No sponsor specified. Please provide at least one sponsor."
az rest --method POST --url "https://graph.microsoft.com/beta/applications" \
  --headers "Content-Type=application/json" \
  --body '{"@odata.type":"microsoft.graph.agentIdentityBlueprint",
           "displayName":"<name>",
           "sponsors@odata.bind":["https://graph.microsoft.com/beta/directoryObjects/<user-object-id>"]}'

# 2. The blueprint's principal. Without it, step 3 fails with
#    "The Agent Blueprint Principal for the Agent Blueprint does not exist".
az rest --method POST --url "https://graph.microsoft.com/beta/servicePrincipals" \
  --headers "Content-Type=application/json" \
  --body '{"@odata.type":"microsoft.graph.agentIdentityBlueprintPrincipal","appId":"<blueprint-app-id>"}'

# 3. The agent identity itself. It comes back with
#    servicePrincipalType "ServiceIdentity" and its own appId.
az rest --method POST --url "https://graph.microsoft.com/beta/servicePrincipals" \
  --headers "Content-Type=application/json" \
  --body '{"@odata.type":"microsoft.graph.agentIdentity","displayName":"<name>",
           "agentIdentityBlueprintId":"<blueprint-app-id>",
           "sponsors@odata.bind":["https://graph.microsoft.com/beta/directoryObjects/<user-object-id>"]}'
```

App roles are then assigned to the **agent identity's** service principal
exactly as for any other principal, which is what the gateway authorizes on.

**Credentials live on the blueprint, never on the agent identity.** Adding one
to an agent identity is refused: `PropertyNotCompatibleWithAgentIdentity —
Credentials are not supported for agent identities. All credentials must be
added to the agent identity blueprint.` One blueprint can impersonate many
agent identities; an agent identity has exactly one blueprint.

## The token flow

Two stages. The blueprint impersonates its child agent identity, which then
exchanges that token for a resource token:

```sh
# Stage 1: T1, the exchange token. fmi_path names the agent identity.
curl -X POST "https://login.microsoftonline.com/$TENANT/oauth2/v2.0/token" \
  -d "client_id=$BLUEPRINT_APP_ID" \
  -d "scope=api://AzureADTokenExchange/.default" \
  -d "fmi_path=$AGENT_APP_ID" \
  -d "grant_type=client_credentials" \
  --data-urlencode "client_secret=$BLUEPRINT_SECRET"

# Stage 2: the agent identity presents T1 and receives the resource token.
curl -X POST "https://login.microsoftonline.com/$TENANT/oauth2/v2.0/token" \
  -d "client_id=$AGENT_APP_ID" \
  -d "scope=api://$API_APP_ID/.default" \
  -d "client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer" \
  -d "grant_type=client_credentials" \
  --data-urlencode "client_assertion=$T1"
```

The resulting token carries `sub`, `oid` and `azp` of the **agent identity**,
`aud` of the API, and the `roles` claim the policy matches on.

Production credentials and the sidecar are covered separately in
[`PRODUCTION-CREDENTIALS.md`](PRODUCTION-CREDENTIALS.md): a certificate-backed
blueprint is proven, a managed identity is configured, and the sidecar has a
caveat worth reading before adopting it.

A client secret on the blueprint is a lab shortcut. Microsoft's guidance is a
managed identity or certificate as the blueprint credential. A later
certificate-backed exchange was proven; the Entra ID Auth SDK sidecar was also
tested, but did not return an Agent ID token for the custom API. See
[`PRODUCTION-CREDENTIALS.md`](PRODUCTION-CREDENTIALS.md) before selecting a
production token path.

## Also run on the red cluster

On 2026-09-23 the same identities were wired into the home-lab `red` rehearsal,
with **two** agent identities: one as the caller and one as the agent's own
identity for its MCP calls. Both lanes were switched to this Entra profile.

```
listener=event-a2a  status=200  jwt.sub=<caller agent identity>
listener=event-mcp  status=200  jwt.sub=<the agent's own agent identity>
```

The task completed and the answer carried the `INC-1001` fixture from the MCP
tool, so the whole path held with Agent ID at both hops. red was restored from
backups afterwards.

One trap: the first attempt failed with `failed to list MCP tools: Unauthorized`
because the agent Pod still held the previous token. kagent's controller renders
that credential into the agent, so a new token needs a reconcile and a fresh
Pod, not just a Secret update.

## What this does not cover

- **A work tenant.** This used a throwaway tenant with no licences at all
  (`subscribedSkus` was empty), which was enough for the identity and token
  flow. Conditional access, identity protection and governance for agents
  require **Microsoft Agent 365** licensing.
- **This first gateway run** did not cover a sidecar, managed identity,
  certificate, on-behalf-of or agent-user flow. Later certificate and sidecar
  tests are recorded in [`PRODUCTION-CREDENTIALS.md`](PRODUCTION-CREDENTIALS.md);
  AKS managed-identity exchange and agent-user flows remain unproven here.
- **kagent wiring.** The token was proven at the gateway, not yet issued from
  inside an agent Pod. The two-credential finding in
  [`LOCAL-REHEARSAL.md`](LOCAL-REHEARSAL.md) still applies: an agent also needs
  an identity for its own MCP calls.
- **Graph beta.** The commands above record the lab's beta routes, not a
  current work-tenant procedure. Microsoft now documents a v1.0 blueprint
  create route and a different beta Agent ID create route. Verify the current
  Graph APIs and least-privileged permissions before any work-tenant change.

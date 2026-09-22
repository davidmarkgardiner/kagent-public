# Entra rehearsal on a local cluster

Cluster local, identity in Azure. This moves the Entra profile from
"manifests that pass schema validation" to "real Microsoft-issued tokens,
accepted and rejected by the gateway for the right reasons", without a work
cluster, a public hostname or a corporate tenant.

**Run on 2026-09-22 and passed.** Environment: a local kind cluster, Gateway
API `v1.6.2` experimental, agentgateway `v1.5.0` (chart digests matched
[`../../platform/versions.lock`](../../platform/versions.lock)), a throwaway
Entra tenant, and this bundle's own [`event-a2a-policy.yaml`](event-a2a-policy.yaml)
and [`entra-jwks.yaml`](entra-jwks.yaml) with placeholders substituted.

## What it proved

| Check | Token | Result | Gateway's reason |
|---|---|---|---|
| Valid caller reaches the backend | app role `team-event.a2a.invoke` | **200** | request forwarded to the backend endpoint |
| No credential | none | **401** | `no bearer token found` |
| Wrong audience, same tenant | token for a second API app in the same tenant | **401** | `Error(InvalidAudience)` |
| Wrong issuer | v1 token (`sts.windows.net`) | **401** | `Error(InvalidIssuer)` |
| Foreign signing key | Microsoft Graph token | **401** | `Error(InvalidSignature)` |
| Authenticated but unauthorized | valid token, no `roles` claim | **403** | `authorization failed` |
| Cross-lane | valid token carrying `team-chat.a2a.invoke` | **403** | `authorization failed` |
| MCP route overlay | n/a | **accepted** | `mcp-route-patches.yaml` passes server-side dry run on Gateway API v1.6.2 |

The gateway fetched Microsoft's signing keys over the internet through the
`entra-jwks` backend and validated every token offline after that. Each
rejection is a distinct control, and each one names its own reason in the
gateway log, so a receipt can quote them.

The route overlay result closes the gap from the red run: on red it failed
against Gateway API v1.4, because the v1.6 CORS filter field did not exist
([`../../evidence/red/2026-09-16-entra-schema-dry-run.md`](../../evidence/red/2026-09-16-entra-schema-dry-run.md)).

## Two findings that will bite in a work tenant

**1. Set the API app to issue v2 tokens.** An app registration defaults to
`requestedAccessTokenVersion: null`, which is v1, and then the token's issuer
is `https://sts.windows.net/<tenant>/`, not the
`https://login.microsoftonline.com/<tenant>/v2.0` that the policies in this
profile expect. The gateway rejects it with `InvalidIssuer`. Either patch the
app:

```sh
obj=$(az ad app show --id "$API_APP_ID" --query id -o tsv)
az rest --method PATCH --url "https://graph.microsoft.com/v1.0/applications/$obj" \
  --headers "Content-Type=application/json" \
  --body '{"api":{"requestedAccessTokenVersion":2}}'
```

or set the v1 issuer in the policy. The profile README already warns to use
the v2 issuer only when the tokens really carry it; this is what that looks
like when it goes wrong. Allow a minute for the change to take effect.

**2. A v2 token's `aud` is the bare application ID**, not `api://<app-id>`.
The policies list both forms, which is why they work either way. Do not
"tidy" one of them away.

## Setting it up

Everything below is throwaway. Use a personal or sandbox tenant, never a
corporate one.

```sh
# 1. The API application, exposing one app role per lane.
cat > roles.json <<'JSON'
[{"allowedMemberTypes":["Application"],"description":"event lane",
  "displayName":"team-event.a2a.invoke","id":"<uuid>","isEnabled":true,
  "value":"team-event.a2a.invoke"}]
JSON
api=$(az ad app create --display-name kagent-poc-api --sign-in-audience AzureADMyOrg \
  --app-roles @roles.json --query appId -o tsv)
az ad app update --id "$api" --identifier-uris "api://$api"
az ad sp create --id "$api"
# then patch requestedAccessTokenVersion to 2, as above

# 2. One client application per lane, plus one with no role at all.
client=$(az ad app create --display-name kagent-poc-team-event \
  --sign-in-audience AzureADMyOrg --query appId -o tsv)
az ad sp create --id "$client"
az ad app credential reset --id "$client" --append --display-name poc \
  --years 1 --query password -o tsv > client-secret.txt   # keep out of git
chmod 600 client-secret.txt

# 3. Grant the app role to the client's service principal.
az rest --method POST \
  --url "https://graph.microsoft.com/v1.0/servicePrincipals/$CLIENT_SP_ID/appRoleAssignments" \
  --headers "Content-Type=application/json" \
  --body "{\"principalId\":\"$CLIENT_SP_ID\",\"resourceId\":\"$API_SP_ID\",\"appRoleId\":\"$ROLE_ID\"}"
```

A client with no assignment still receives a token here, just without a
`roles` claim, which is the 403 case above. If the API's service principal has
`appRoleAssignmentRequired` set, Entra refuses to issue at all — an earlier
denial, and also a valid control.

Cluster side: install Gateway API v1.6.2 experimental and agentgateway v1.5.0
as in [`../fresh-cluster/README.md`](../fresh-cluster/README.md), substitute
the tenant and application IDs into the policy files here, and apply them with
a Gateway, an HTTPRoute and any backend.

## Getting tokens into the existing verifier

`scripts/deploy.sh` and `scripts/verify.sh` read a `tokens.json` that
`render.py` mints for the disposable JWT profile. [`entra-tokens.sh`](entra-tokens.sh)
writes the same file shape from Entra, so the verifier logic does not change:

```sh
./entra-tokens.sh --tenant <tenant-id> --api-app-id <api-app-id> \
  --client event=<app-id>:<secret-file> --client chat=<app-id>:<secret-file> \
  --out tokens.json
```

## Why Gateway API is involved at all

agentgateway is the proxy; Gateway API is only one of the two ways to
configure it, and it is the way this bundle chose.

- **Kubernetes mode (this bundle).** Listeners are a `Gateway`, routes are
  `HTTPRoute`, and agentgateway's own `AgentgatewayPolicy` and
  `AgentgatewayBackend` attach to them. [`event-a2a-policy.yaml`](event-a2a-policy.yaml)
  targets `group: gateway.networking.k8s.io, kind: HTTPRoute`, so without
  Gateway API CRDs there is no object for the JWT policy to attach to.
- **Standalone mode.** agentgateway also takes a single config file with
  `binds -> listeners -> routes -> policies` and no Kubernetes CRDs at all.
  Substrate already runs it this way: the `atenet-router` sidecar is an
  agentgateway with a mounted `config.yaml`. Its published config schema
  contains `jwtAuth`, `jwks`, `issuer`, `authorization` and
  `mcpAuthentication`, so Entra token validation is expressible there too.

So Gateway API is a prerequisite of **this bundle's configuration style**, not
of agentgateway and not of Entra. If cluster-wide Gateway API CRDs are the
blocker at work, a standalone agentgateway with a config file is a route worth
testing. This bundle has not tested it, and the Kubernetes mode is what the
red evidence covers.

Only the MCP **CORS route filter** genuinely needs Gateway API `v1.6.2`
experimental, because that field does not exist in earlier versions.

## Entra Agent ID is a separate thing

[Microsoft Entra Agent ID](https://learn.microsoft.com/en-us/entra/agent-id/what-is-microsoft-entra-agent-id)
gives each agent its own identity, with blueprints and parent-child
relationships, and supports OAuth 2.0, MCP and A2A. It has no Kubernetes or
Gateway API component: it changes **who** the token represents, not how the
gateway validates it.

This rehearsal used ordinary app registrations with app roles and client
credentials, which is plain Entra workload identity, not Agent ID. Swapping in
Agent ID would keep the gateway policies as they are; the issuer, audience and
role claims still drive the decision.

Two things to confirm with the identity team before planning on it:
Microsoft states Agent ID is available to all Entra customers, but extending
Entra security features (conditional access, identity protection, governance)
to agents requires **Microsoft Agent 365** licensing, included in Microsoft
365 E7 or sold as an add-on.

## What a local rehearsal still cannot tell you

- **Egress.** The gateway must reach `login.microsoftonline.com` for JWKS. A
  locked-down work network is the open question, the same class as the ate-api
  token issuer.
- **Corporate tenant policy:** conditional access, consent and app-governance
  rules, PIM approval, and naming or audience conventions.
- **Public hostname and external TLS**, including any corporate TLS
  interception in front of the gateway.
- **Workload identity federation**, if the gateway or kagent uses it instead
  of client secrets.
- **Token refresh across expiry.** Entra access tokens last 60–90 minutes, so
  that gate needs a long-running test rather than a trick.
- **Interactive PKCE with real users**, which this run did not cover: every
  token here came from client credentials.
- **Entra Agent ID itself**, and whether Agent 365 licensing is available at
  work.

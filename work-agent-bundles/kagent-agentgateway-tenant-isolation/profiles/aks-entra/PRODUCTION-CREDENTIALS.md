# Agent ID in production: credentials and the sidecar

What to use instead of a client secret, and what the Entra ID Auth SDK sidecar
does and does not do. Everything below was tried on 2026-09-23 against a
throwaway tenant; each row says whether it was proven, configured or only read
from the documentation.

## Credential options for the blueprint

Credentials belong to the **blueprint**, never to an agent identity — Entra
refuses the latter outright. So this is the one credential that matters.

| Option | State | Notes |
|---|---|---|
| **Client secret** | **Proven**, and only for a lab | Microsoft's own guidance says not to use it in production |
| **Certificate** | **Proven end to end** | Self-signed certificate on the blueprint, a hand-built RS256 client assertion, then the two-stage exchange. Produced an agent identity token with `roles`, no secret anywhere |
| **Managed identity (UAMI)** | **Configured, not exercised** | The preferred option. A UAMI and the federated credential on the blueprint were created successfully; using it needs Azure-hosted compute to obtain the managed identity token, which a home lab has no way to produce |
| Key Vault certificate | Read only | The sidecar's `KeyVault` source type |

### Certificate, proven

```sh
openssl req -x509 -newkey rsa:2048 -nodes -keyout bp-key.pem -out bp-cert.pem \
  -days 365 -subj "/CN=<blueprint-name>"
az ad app credential reset --id "$BLUEPRINT_APP_ID" --append --cert "@bp-cert.pem" --years 1
```

Then stage 1 uses a client assertion instead of `client_secret`. The assertion
is a JWT signed with that key: header `{"alg":"RS256","typ":"JWT","x5t":<base64url
of the certificate SHA-1 thumbprint>}`, payload `aud` the tenant token endpoint,
`iss` and `sub` both the blueprint app id, plus `jti`, `nbf` and `exp`. Send it
as `client_assertion` with
`client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer`.
Stage 2 is unchanged.

### Managed identity, configured

```sh
az identity create -g <rg> -n <uami-name>          # note its principalId
az ad app federated-credential create --id "$BLUEPRINT_APP_ID" --parameters '{
  "name": "uami-trust",
  "issuer": "https://login.microsoftonline.com/<tenant-id>/v2.0",
  "subject": "<uami-principal-id>",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

The blueprint then trusts that managed identity, and whatever runs as the UAMI
obtains a managed identity token and presents it as the stage 1
`client_assertion`. On AKS that is workload identity on the Pod running the
sidecar. This is the target for work; it was configured here but never used,
because obtaining a managed identity token requires Azure-hosted compute.

## The sidecar: what was observed

Image: `mcr.microsoft.com/entra-sdk/auth-sidecar`, currently
`1.1.2-azurelinux3.0-distroless`. There is no `latest` tag, and the image is
**amd64 only**, which matters for arm64 laptops and nodes.

**It serves loopback only.** Every call from another container returned `403`,
including `/`, the OpenAPI document and the sample's documented `Host: localhost`
header. The same call over the shared network namespace worked. `/healthz`
answers from anywhere and is the liveness probe. In Kubernetes that means the
sidecar must be **a container in the same Pod as the agent**, reached on
`127.0.0.1` — not a Service, not another Pod.

**Verify the `sub` claim of what it returns.** Configured with
`DownstreamApis__<name>__RequestAppToken=true` and the documented
`?AgentIdentity=<agent-app-id>` parameter, the token it returned for Microsoft
Graph had `sub` equal to the **blueprint principal**, not the agent identity.
Against a custom API the same configuration was refused by Entra with:

```
AADSTS82001: Agentic application '<blueprint>' is not permitted to request
app-only tokens for resource '<api>'
```

Adding the app role to the blueprint principal, and adding plus consenting the
API permission on the blueprint, did not change it. Without `RequestAppToken`
the endpoint attempts a delegated flow and fails with "No account or login hint
was passed". By contrast the documented two-stage `fmi_path` exchange produces
a correct agent identity token against the same custom API every time, and that
token is what the gateway accepted in
[`AGENT-ID-REHEARSAL.md`](AGENT-ID-REHEARSAL.md).

So: treat the sidecar as promising but unproven for a **custom** API with agent
identities. Before adopting it, get one token out of it and check that `sub` is
the agent identity. If it is the blueprint, the agent is not acting as itself
and per-agent authorization is not happening.

## What this means for kagent

kagent's `RemoteMCPServer` takes its credential from a Secret, which the
controller renders into the agent. That is a stored, expiring token, and
rotating it needs a controller reconcile and a new Pod — which the red run hit.
Three ways out, none yet built:

1. **A refresher** that re-mints the token into the Secret before expiry and
   triggers the reconcile. Closest to how kagent works today, and the crudest.
2. **The sidecar in the agent Pod**, with kagent asking it per call. Needs the
   `sub` question above answered, and a kagent change: nothing reads a token
   from a local endpoint today.
3. **Gateway-side credential injection**, where agentgateway attaches the
   outbound credential and the agent holds nothing. Its configuration schema
   has backend authentication primitives; whether they cover this exchange has
   not been checked.

Option 3 is worth an hour of research before anyone builds option 1, because it
removes the credential from the agent altogether.

## Order for the work cluster

1. Blueprint credential: **UAMI plus federated credential**, with the
   certificate path as the fallback. Never a secret.
2. Keep the two-stage `fmi_path` exchange, which is proven, until the sidecar
   is shown to return agent identity tokens for a custom API.
3. Decide the kagent credential question above before designing onboarding
   automation around it.

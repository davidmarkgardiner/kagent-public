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

## The sidecar: what it is and how to run it

The Microsoft Entra ID Auth SDK sidecar is a small ASP.NET service that holds
the **blueprint's** credential and performs the OAuth exchanges, so agent code
never sees a credential. The agent asks it for a ready-made `Authorization`
header and forwards that to the downstream API. Only the sidecar talks to
`login.microsoftonline.com`.

**Image.** `mcr.microsoft.com/entra-sdk/auth-sidecar`. There is no `latest`
tag; pick a version, for example `1.1.2-azurelinux3.0-distroless`. It is
**amd64 only**, which matters on arm64 laptops and nodes. It is distroless, so
there is no shell for debugging: use its logs.

**Endpoints** (`ASPNETCORE_URLS` sets the port; the sample uses 5000):

| Endpoint | Purpose |
|---|---|
| `GET /AuthorizationHeaderUnauthenticated/{api}?AgentIdentity={agent-app-id}` | Autonomous, app-only. Returns `{"authorizationHeader":"Bearer ..."}` |
| `GET /AuthorizationHeader/{api}?AgentIdentity={agent-app-id}` | On-behalf-of. Also requires the user's token as `Authorization: Bearer <Tc>` |
| `GET /healthz` | Liveness. The only endpoint that answers from outside the loopback boundary |

`{api}` is the name of a downstream API you define in configuration, not a URL.

**Configuration**, all environment variables. This is the set used here:

```sh
AzureAd__Instance=https://login.microsoftonline.com/
AzureAd__TenantId=<tenant-id>
AzureAd__ClientId=<blueprint-app-id>          # the BLUEPRINT, not the agent
AzureAd__ClientCredentials__0__SourceType=ClientSecret
AzureAd__ClientCredentials__0__ClientSecret=<secret>   # lab only
DownstreamApis__laneapi__BaseUrl=https://<api-host>/
DownstreamApis__laneapi__Scopes__0=api://<api-app-id>/.default
DownstreamApis__laneapi__RequestAppToken=true          # app-only; see the caveat below
ASPNETCORE_ENVIRONMENT=Production
ASPNETCORE_URLS=http://+:5000
AllowedHosts=*
```

**Credential source types**, set through
`AzureAd__ClientCredentials__0__SourceType`:

| Value | Use |
|---|---|
| `ClientSecret` | Local development only |
| `SignedAssertionFromManagedIdentity` | Production on Azure, zero secrets — pair with the federated credential above |
| `KeyVault` | Certificate from Key Vault |
| `StoreWithThumbprint` | Certificate from the local machine store |

**Shape in Kubernetes.** Because of the loopback finding below, the sidecar is
a second container in the agent's Pod, with no Service and no host port. The
agent reaches it on `http://127.0.0.1:5000`, and `/healthz` backs the probe.

On a cluster with admission safeguards, that container needs the same
treatment as everything else in
[`../../../agent-substrate/aks-hardened/`](../../../agent-substrate/aks-hardened/README.md):
CPU and memory requests and limits, `readOnlyRootFilesystem`,
`allowPrivilegeEscalation: false`, dropped capabilities and a RuntimeDefault
seccomp profile. It already runs as a non-root user (`APP_UID 1654`). It also
writes ASP.NET data-protection keys under `/home/app`, so a read-only root
filesystem needs a writable volume there — untested, and worth checking early
rather than at admission time. Mirror the image by digest; it is amd64 only.

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

## Replicating this at work

### The credential chain, which has two federated credentials

With a managed identity there are **two** trust links, and it is easy to
configure one and expect the other to work:

```
AKS Pod (service account)
  │  federated credential #1, on the UAMI:
  │    issuer  = the cluster's OIDC issuer URL
  │    subject = system:serviceaccount:<ns>:<sa>
  ▼
User-assigned managed identity
  │  federated credential #2, on the BLUEPRINT app:
  │    issuer  = https://login.microsoftonline.com/<tenant>/v2.0
  │    subject = <UAMI principalId>
  │    audience= api://AzureADTokenExchange
  ▼
Blueprint  ──fmi_path──▶  Agent identity  ──▶  token the gateway accepts
```

Only #2 was created here. #1 is ordinary AKS workload identity and was not
built, because a home lab has no AKS.

### The UAMI needs no Azure RBAC

This catches people out: the managed identity is **not** granted permissions on
the API. It only needs to be trusted by the blueprint (#2 above). Authorization
comes from the **app role on the agent identity**, which is what the gateway
policy matches. Do not assign the UAMI a role on the API and expect it to
change the token.

### AKS prerequisites for the Pod

Not tested here; standard workload identity setup:

- The cluster has the OIDC issuer and workload identity enabled; note the
  issuer URL.
- The agent's service account is annotated
  `azure.workload.identity/client-id: <uami-clientId>`.
- The Pod carries the label `azure.workload.identity/use: "true"`.
- Federated credential #1 exists on the UAMI for that exact
  `system:serviceaccount:<ns>:<sa>` subject.

### Checklist

| Item | Proven here? |
|---|---|
| Tenant can create blueprints and agent identities through Graph beta | **Yes**, in a tenant with no licences at all |
| Roles on the agent identity drive the gateway decision | **Yes** |
| Two-stage `fmi_path` exchange with a **client secret** | **Yes** |
| Same exchange with a **certificate** | **Yes** |
| Same exchange with a **managed identity** assertion | **No** — needs Azure compute |
| Federated credential #2 (blueprint trusts UAMI) | Created, never used |
| Federated credential #1 (UAMI trusts the cluster service account) | **No** |
| Sidecar returns an **agent identity** token for a custom API | **No** — see the caveat above |
| Gateway policy accepts an agent identity token, unchanged | **Yes**, twice, including through kagent on a live cluster |

So with the image mirrored and the identities in place, the work agent can
replicate everything proven above. The two open links are AKS workload identity
for the Pod and the sidecar's behaviour on a custom API. Neither blocks a
demonstration: the certificate-backed exchange is proven and needs no Azure
compute at all.

### Permissions to do it

Creating the blueprint, the blueprint principal and the agent identities needs
Application Administrator or Cloud Application Administrator, with Global
Administrator for first-time setup, plus consent for the app-role assignments.
That is an identity-team task, not a cluster task.

## Order for the work cluster

1. Blueprint credential: **UAMI plus federated credential**, with the
   certificate path as the fallback. Never a secret.
2. Keep the two-stage `fmi_path` exchange, which is proven, until the sidecar
   is shown to return agent identity tokens for a custom API.
3. Decide the kagent credential question above before designing onboarding
   automation around it.

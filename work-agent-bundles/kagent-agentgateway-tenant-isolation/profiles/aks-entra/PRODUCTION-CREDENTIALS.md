# Agent ID in production: credentials and the sidecar

> **2026-09-25 correction:** the 2026-09-23 UAMI-to-blueprint plan below is historical. A disposable AKS test proved direct ServiceAccount-to-blueprint federation and found that ServiceAccount → UAMI → blueprint fails with `AADSTS700231`. Use the [current AKS evidence](../../poc/azure-agent-id/AKS-FULL-E2E-EVIDENCE-2026-09-25.md) and [work identity ticket](../../poc/azure-agent-id/WORK-GITLAB-IDENTITY-TICKET.md) before any work-tenant implementation. The sidecar/custom-API and automatic token-refresh gaps remain open.

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
| **UAMI via AKS federation** | **Exercised; chained exchange failed** | AKS SA → UAMI succeeded, but its Entra-issued token → blueprint failed `AADSTS700231`. Do not use this as the work AKS blueprint credential chain. |
| **Direct AKS ServiceAccount federation** | **Proven in disposable AKS** | Exact OIDC issuer/ServiceAccount subject trusted on blueprint; child Agent ID MCP and A2A token paths passed. Requires identity-owner approval and a dedicated blueprint or trusted broker boundary. |
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

### Managed identity, historical configuration — not the AKS design

```sh
az identity create -g <rg> -n <uami-name>          # note its principalId
az ad app federated-credential create --id "$BLUEPRINT_APP_ID" --parameters '{
  "name": "uami-trust",
  "issuer": "https://login.microsoftonline.com/<tenant-id>/v2.0",
  "subject": "<uami-principal-id>",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

The earlier proposal was for the blueprint to trust that managed identity.
On the 2026-09-25 AKS pilot, the ServiceAccount obtained a UAMI token, but
presenting that Entra-issued token as the blueprint assertion failed with
`AADSTS700231`. Microsoft states that [Entra-issued tokens cannot be used as
federated assertions](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation).
The UAMI and its blueprint credential remain identity-only PoC artifacts, not
proof of a working AKS chain.

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

### The AKS credential chain that passed

```
AKS Pod / dedicated ServiceAccount
  │  FIC on the BLUEPRINT app:
  │    issuer   = the cluster's OIDC issuer URL
  │    subject  = system:serviceaccount:{{NAMESPACE}}:{{SERVICE_ACCOUNT}}
  │    audience = api://AzureADTokenExchange
  ▼
Dedicated blueprint ──fmi_path──▶ child Agent ID ──app role──▶ protected API
```

The ServiceAccount annotation uses the **blueprint app client ID**, and the Pod
has `azure.workload.identity/use: "true"`. The runtime, approved caller, and
rogue pilot used separate blueprints and exact subjects. The UAMI middle hop
is not part of this working chain. A UAMI may still serve unrelated Azure
resource access, but it should not receive the Agent ID API role.

### Current proof and open gates

| Item | 2026-09-25 AKS result |
|---|---|
| Exact ServiceAccount → blueprint federation and child `fmi_path` exchange | **PASS** for runtime, approved caller, and rogue identities |
| Separate MCP and A2A API app roles | **PASS**; assigned to child Agent ID principals |
| Gateway checks issuer, audience, role **and exact child `oid`** | **PASS after correction**; one combined CEL expression per route |
| Same-role wrong-child, missing-role, missing/wrong-audience denial | **PASS**; see the [evidence receipt](../../poc/azure-agent-id/AKS-FULL-E2E-EVIDENCE-2026-09-25.md) |
| Direct rogue-to-Agent and rogue-to-MCP bypass | **BLOCKED** by Cilium NetworkPolicy |
| Manual token replacement and Agent Pod restart | **PASS**; not automatic refresh |
| Automatic refresh, expiry behavior, sidecar custom-API token | **NOT PROVEN** |
| Work-tenant AACM request and approval process | **NOT EXERCISED** |

Do not reuse the earlier UAMI renderer or identity-only blueprint FIC as a
work-cluster manifest. The work identity and AKS owners must approve the direct
federation and child credential boundary, while the platform team supplies a
production token broker/refresher and GitOps delivery.

### Permissions to do it

Do not use a single directory-role assumption for every operation. Microsoft
now documents `AgentIdentityBlueprint.Create` as the least-privileged Graph
application permission for [blueprint creation](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-post?view=graph-rest-1.0),
and its [agent-management guidance](https://learn.microsoft.com/en-us/entra/agent-id/manage-agent-identities-admin)
distinguishes blueprint creation from managing Agent IDs. Check the current
Graph permission, ownership, delegated directory role (if applicable), admin
consent, and API app-role-assignment rights **per operation** in the work
tenant. Azure RBAC on the AKS SPN does not provide Graph permissions. Route
anything the SPN cannot do to an authorized identity owner.

## Order for the work cluster

1. Ask infra ID/AACM to approve a dedicated blueprint boundary, child Agent
   ID, protected API app roles, and direct AKS ServiceAccount-to-blueprint
   federation. Use the [copy-ready GitLab ticket](../../poc/azure-agent-id/WORK-GITLAB-IDENTITY-TICKET.md).
2. Keep the proven two-stage `fmi_path` exchange, with a reviewed credential
   broker or refresher. Do not embed a client secret or long-lived token in
   the agent. Do not assume the Microsoft sidecar returns the child Agent ID
   for this custom API until that is demonstrated.
3. Bind role and exact child identity in **one** gateway CEL expression; test
   same-role wrong-child denial, direct network bypass, token expiry, and
   rollover before promoting a workload.

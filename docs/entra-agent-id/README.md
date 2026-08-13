# Microsoft Entra Agent ID for per-agent model access

Notes on Microsoft Entra Agent ID (agent identity blueprints) and how the
pattern fits the kagent + agentgateway model-authentication setup in this
repository.

## Context

The current pattern for reaching a self-hosted OpenAI-compatible model
(for example a Qwen model served behind a load balancer by an internal
model-serving platform):

1. A token is acquired for a user-assigned managed identity (UAMI).
2. The token is stored in a Secret referenced by a kagent `ModelConfig`
   (`apiKeySecret`), which sends it as the bearer token to the endpoint.

This works, but when one namespace hosts multiple agents with different
access requirements, usage profiles, and lifecycles, a single shared UAMI
per namespace creates operational problems:

| Problem | Consequence |
|---|---|
| No per-agent access control | All agents share one identity |
| No per-agent audit trail | All calls appear under the same identity |
| No per-agent quota or spend limit | Throttling applies at the shared identity level |
| Unclean decommissioning | One agent's model access cannot be revoked alone |
| Access-request proliferation | One UAMI per agent means a manual access request per agent, defeating self-service |

## What Entra Agent ID is

Microsoft Entra Agent ID is an identity model in Microsoft Entra built for
AI agents (currently in preview; the Microsoft Graph surface is beta). It
has two object types:

- **Agent identity blueprint** — the template for a *kind* of agent
  (for example, "platform kagent agents"). Registered once. Records shared
  metadata and permissions, **holds the credentials**, and has one special
  capability: provisioning and impersonating its child agent identities.
- **Agent identity** — a per-instance service principal created *from* a
  blueprint. One per deployed agent. It has **no credentials of its own**,
  its own object ID, sponsors/owners, grants, and can be disabled or
  deleted independently.

Agent identities are created programmatically (Microsoft Graph, Azure CLI,
PowerShell, Bicep), so an agent-onboarding pipeline can mint one per agent
deployment — replacing the manual per-agent access request. Decommissioning
an agent means disabling or deleting its agent identity and revoking its
grants; every other agent is untouched.

## Token flow (autonomous app-only)

Source: [Agent autonomous app OAuth flow](https://learn.microsoft.com/en-us/entra/agent-id/agent-autonomous-app-oauth-flow).

```text
UAMI token (as FIC for the blueprint)
    │  blueprint requests exchange token T1
    │  fmi_path = app ID of the child agent identity
    ▼
Microsoft Entra ID ── T1 ──► exchanged as client_assertion
    │  client_id = agent identity
    │  scope = target resource /.default
    ▼
Microsoft Entra ID ── TR (resource token) ──► subject = agent identity
```

Key points:

- The blueprint's credential can be a **managed identity token used as a
  federated identity credential (FIC)** — Microsoft's recommended option.
  No client secret needs to be stored.
- `fmi_path` tells Entra which child agent identity the blueprint is
  impersonating during the exchange.
- The final resource token (TR) carries the **agent identity** as its
  subject — not the blueprint, not the UAMI. The UAMI demotes from "the
  API identity everything shares" to "the blueprint's plumbing credential",
  while every token reaching the model endpoint identifies a specific agent.
- Microsoft recommends using the approved SDKs (Microsoft.Identity.Web or
  the Entra ID Auth SDK sidecar) rather than hand-rolling the exchange.

## Mapping to the shared-UAMI pain points

| Pain point | Agent ID mechanism |
|---|---|
| No per-agent access control | Roles/consent assigned per agent identity |
| No per-agent audit trail | Token subject is the agent identity; per-agent sign-in and resource logs |
| No per-agent quota/spend | Service-side throttling keyed off token identity claims |
| Unclean decommissioning | Delete or disable the single agent identity |
| Access-request proliferation | Blueprint created once; agent identities minted via API in the onboarding pipeline |

## Fit with kagent and agentgateway in this repo

kagent `ModelConfig` has no native Entra token acquisition today
(`kagent/go/api/v1alpha2/modelconfig_types.go` in the local kagent clone):

- `apiKeySecret` / `apiKeySecretKey` — static bearer in a Secret (the
  current pattern, see `platform/agentgateway/modelconfig-qwen.yaml`)
- `apiKeyPassthrough` — forwards the incoming A2A caller's bearer token as
  the model API key
- `azureOpenAI.azureAdToken` — static token in the spec; the token-provider
  hook is an unimplemented TODO upstream
- `openAI.tokenExchange` — only supports `GDCHServiceAccount` (Google
  Distributed Cloud Hosted); no Entra/Azure option

So something outside kagent must acquire and refresh tokens either way.
With Agent ID that is a small component in the agent pod (Microsoft ships
an Entra ID Auth SDK **sidecar** for exactly this) performing
UAMI → T1 → TR. Two integration options:

1. **Minimal change:** the sidecar keeps a per-agent Secret fresh, and each
   agent gets its own `ModelConfig` pointing at that Secret. Works with
   today's kagent, but means one ModelConfig + Secret per agent and tokens
   at rest.
2. **Preferred (matches `platform/agentgateway/AUTHENTICATION.md`):**
   TR is the bearer on the agent → agentgateway hop, validated by the
   existing JWT policy pattern (`platform/agentgateway/authentication-policy.yaml`,
   Entra issuer `https://login.microsoftonline.com/{{TENANT_ID}}/v2.0`).
   agentgateway can already attribute, rate-limit, and log per inbound JWT
   claim — that gives per-agent quota and audit at *our* gateway today,
   independent of what the upstream model service supports.

## The dependency on the model-serving side

Entra Agent ID is an identity **issuer**, not an authorization system for
someone else's service. The pattern only delivers per-agent access control,
audit, and quota at the model endpoint if the model-serving platform
accepts Entra access tokens from the tenant.

Worth reframing the roadmap question for that team: they do not need
"Agent ID support" — they need **Entra token validation**. From the
service's side an agent-identity token is an ordinary JWT with a distinct
`appid`/`oid`. Their work is:

1. An app registration representing the model endpoint (the audience).
2. JWT validation at the load balancer / gateway in front of the model.
3. Authorization, quota, and audit keyed off the token's identity claims.

So the ask splits in two:

- **Gating:** will the endpoint accept Entra-issued access tokens (their
  own app registration as audience)?
- **Value:** once it does, will quota, audit, and throttling be keyed per
  calling identity?

## Suggested adoption path

1. **Pilot now with ordinary app registrations.** The service-side work
   (JWT validation, per-identity quota/audit) is identical whether the
   caller is an app registration or an agent identity — the service cannot
   tell the difference. This unblocks per-agent identities without waiting
   on Agent ID.
2. **Enforce per-agent policy at agentgateway in the meantime.** Per-claim
   rate limits and logging on the inbound hop give per-agent attribution
   even while the upstream credential is still shared.
3. **Migrate to agent identity blueprints once the endpoint accepts Entra
   tokens.** One blueprint per agent class; the onboarding pipeline creates
   an agent identity per deployment; the UAMI stays only as the blueprint's
   FIC credential.

Caveat: Agent ID is in public preview (beta Graph APIs). Factor preview
SLAs and API stability into any production commitment. Agent identities
are single-tenant; blueprints can be multitenant.

## Configuration

| Placeholder | Meaning |
|---|---|
| `{{TENANT_ID}}` | Microsoft Entra tenant ID |
| `{{AGENTGATEWAY_APP_ID}}` | App registration audience for the agentgateway inbound JWT policy |
| `{{MODEL_SERVICE_APP_ID}}` | App registration audience exposed by the model-serving platform |
| `{{MI_CLIENT_ID}}` | UAMI client ID used as the blueprint's federated identity credential |

## References

- [Overview of agent identities in Microsoft Entra](https://learn.microsoft.com/en-us/entra/agent-id/agent-identities)
- [Agent autonomous app OAuth flow](https://learn.microsoft.com/en-us/entra/agent-id/agent-autonomous-app-oauth-flow)
- [Authenticate and acquire tokens for autonomous agents](https://learn.microsoft.com/en-us/entra/agent-id/autonomous-agent-authentication-authorization-flow)
- [Manage agent identity blueprints](https://learn.microsoft.com/en-us/entra/agent-id/manage-agent-blueprint)
- Repo: `platform/agentgateway/AUTHENTICATION.md` (two-hop auth model)
- Repo: `platform/agentgateway/modelconfig-qwen.yaml` (current static-token ModelConfig)

# Entra identity team: how the pilot was built and how to onboard it at work

This is an implementation reference for the [copy-ready work GitLab ticket](WORK-GITLAB-IDENTITY-TICKET.md), not an approved AACM schema or authority to change the work tenant. Keep real object IDs, OIDC issuer URLs, internal contacts, credentials, and token values in the private work ticket/identity record only. The home-lab pilot was not created from an AACM template. We wrote Python scripts that used the signed-in Azure CLI's Microsoft Graph access, then checked every created object by reading it back. The later AKS pilot added **direct** ServiceAccount-to-blueprint federation and proved the token and gateway path; no checked-in script currently provisions that successful AKS federation or replays the whole AKS pilot.

## Exact home-lab implementation reference

The identity-only run used these commands from this directory, with an interactive user signed into the intended **home-lab** tenant and a private receipt directory outside this public repo:

```sh
az account show
POC_STATE_DIR=$(mktemp -d)
python3 provision_graph.py --state-dir "$POC_STATE_DIR"
python3 provision_access.py --state-dir "$POC_STATE_DIR"
python3 prove_certificate_exchange.py --state-dir "$POC_STATE_DIR"
```

Do **not** run these commands unchanged against the work tenant. `provision_graph.py` assumes an interactive user, exactly one accessible subscription, and fixed PoC naming. `provision_access.py` also creates a test resource group, UAMI, and **UAMI-to-blueprint federated credential**. That was part of the original identity-only experiment, but the UAMI middle hop failed in AKS with `AADSTS700231`; it is **not** the work AKS design. `prove_certificate_exchange.py` temporarily adds a certificate to the PoC blueprint, uses a two-stage token exchange, checks the child `oid`, API `aud`, and app `roles`, then removes the certificate. It does not test AKS Workload Identity or token refresh. See the [identity-only README](README.md) and [AKS evidence](AKS-FULL-E2E-EVIDENCE-2026-09-25.md).

| Operation actually performed | Reference implementation | Work interpretation |
|---|---|---|
| Create or adopt blueprint application and blueprint principal; create a child Agent ID; read all three back | [`provision_graph.py`](provision_graph.py), `provision()` | Use the approved AACM/Entra process, with named owners and sponsors. Confirm blueprint isolation before placing more than one child under it. |
| Create a single-tenant test MCP API app, v2 audience, enabled application app role and resource service principal; assign that role to the **child Agent ID**; read back | [`provision_access.py`](provision_access.py), first part of `provision()` | Reuse an approved API registration if appropriate. Do not assign the tool role to the blueprint or a UAMI. Add a separate A2A resource app/role and caller Agent ID if protecting inbound agent access. |
| Add test RG/UAMI and blueprint FIC with an Entra issuer and UAMI principal subject | [`provision_access.py`](provision_access.py), latter part of `provision()` | **Historical failed AKS path. Do not reproduce it as the work federation step.** |
| Temporarily authenticate the blueprint and exchange for a child API token; verify claims and remove test certificate | [`prove_certificate_exchange.py`](prove_certificate_exchange.py), `prove()` | Lab protocol proof only. Agree an approved credential path and lifecycle for work. |
| Trust exact AKS OIDC issuer and ServiceAccount subject **directly on the blueprint**, then prove child Agent ID tokens and gateway denials | [Sanitized AKS evidence](AKS-FULL-E2E-EVIDENCE-2026-09-25.md) | Successful home-lab path; **not** implemented by the three scripts above. Identity and AKS owners must agree the work implementation and credential boundary. |

The [request JSON](request.example.json), [AACM response JSON](aacm-response.example.json), and [`generate.py`](generate.py) were **proposed scaffolding**, not an AACM-provided template or a validated work schema. Their rendered UAMI annotation/two-hop federation model predates the AKS result. Do not apply that output to the work cluster.

## Proposed manual onboarding order for the work identity team

Please use your approved AACM process, Entra portal, Graph client, or automation under an authorized identity. The Graph paths below identify the operations our PoC used; they are not a request to grant our SPN rights or to replay the PoC scripts. Verify today's API version, permissions, consent, and local change control before each write.

1. **Approve the request and trust boundary.** Confirm the pilot namespace, Kubernetes ServiceAccount, actual AKS OIDC issuer, runtime Agent ID, caller Agent ID (if A2A is protected), MCP/A2A audiences and exact app-role values. Decide whether each child needs a dedicated blueprint or a trusted broker: a holder of a blueprint credential can select another child via `fmi_path`. Record technical owner, business sponsor, expiry/review date, and revocation owner.
2. **Create or reuse the blueprint and its principal.** Our script used `POST /applications/microsoft.graph.agentIdentityBlueprint`, then `POST /servicePrincipals/microsoft.graph.agentIdentityBlueprintPrincipal` with the blueprint app ID. Read back the blueprint app/object IDs and principal object ID. An existing blueprint must be explicitly approved for this trust boundary; a matching display name is not sufficient.
3. **Create or reuse the protected API registration.** The MCP API is a separate single-tenant application/service principal with an agreed Application ID URI (the token audience), `api.requestedAccessTokenVersion: 2`, and an enabled application app role with `allowedMemberTypes: ["Application"]` and the agreed value. Our test role was `team-event.mcp.use`. If required, make the A2A API and `team-event.a2a.invoke` a separate resource and permission. Read back API app ID/object ID, service-principal object ID, audience, role value and role ID.
4. **Create the child Agent ID and grant only its required role.** Our script used `POST /servicePrincipals/microsoft.graph.agentIdentity` with `agentIdentityBlueprintId` set to the blueprint **app ID**. Assign the API role to the child principal with `principalId` = child object ID, `resourceId` = API service-principal object ID, and `appRoleId` = API role ID. Read back the child's blueprint link and app-role assignments. Repeat separately for an A2A caller identity if in scope.
5. **Create the direct AKS trust only after AKS owner review.** Put the federated identity credential on the **blueprint application**, with `issuer: {{AKS_OIDC_ISSUER}}`, `subject: system:serviceaccount:{{NAMESPACE}}:{{SERVICE_ACCOUNT}}`, and `audiences: ["api://AzureADTokenExchange"]`. This replaces, rather than chains through, the failed UAMI middle hop. The corresponding ServiceAccount annotation points to the **blueprint application/client ID** and its Pod needs the AKS Workload Identity use label. Coordinate those Kubernetes changes with the platform team; this identity ticket does not deploy them. Read back the FIC name, issuer, subject and audience exactly.
6. **Prove and return evidence.** In an approved pilot, obtain a child resource token and check its issuer, child `oid`, API `aud` and expected `roles` without saving or printing the token. Then have the platform team test caller A2A access, agent-to-MCP access, wrong audience/role/child-ID denials, forbidden tools, direct-backend denial, renewal across expiry, and revocation. Return only sanitized claim summaries and Graph/Entra read-backs in the private record. A successful object creation alone is not a working agent lane.

For step 5, this is the **review-only Graph request shape** for the successful trust pattern, not a command to run in the work tenant without approval. The identity team should choose its supported AACM/Graph/portal equivalent and read the result back with `GET` on the same application collection:

```http
POST https://graph.microsoft.com/v1.0/applications/{{BLUEPRINT_OBJECT_ID}}/federatedIdentityCredentials
Content-Type: application/json

{
  "name": "{{FEDERATED_CREDENTIAL_NAME}}",
  "issuer": "{{AKS_OIDC_ISSUER}}",
  "subject": "system:serviceaccount:{{NAMESPACE}}:{{SERVICE_ACCOUNT}}",
  "audiences": ["api://AzureADTokenExchange"]
}
```

The work team should reply with the **real AACM intake/API contract or manual form**, which operation AACM already owns, who requests/approves/executes each step, the least-privileged Graph permissions and consent path, how blueprint/child/API/FIC records are returned to GitOps, and how updates/offboarding work. That is the contract we can automate later. The platform team's [work-agent walkthrough](../../profiles/aks-entra/WORK-AGENT-START-HERE.md) covers the separate Kubernetes/gateway/token-refresh implementation.

## Official API references to verify before a work change

- [Create blueprint](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-post?view=graph-rest-1.0) and [blueprint principal](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprintprincipal-post?view=graph-rest-1.0)
- [Create child Agent ID](https://learn.microsoft.com/en-us/graph/api/agentidentity-post?view=graph-rest-1.0) and [current Agent ID administration guide](https://learn.microsoft.com/en-us/entra/agent-id/create-delete-agent-identities)
- [Create an application](https://learn.microsoft.com/en-us/graph/api/application-post-applications?view=graph-rest-1.0), [grant an application app role](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-post-approleassignments?view=graph-rest-1.0), and [add an app federated credential](https://learn.microsoft.com/en-us/graph/api/federatedidentitycredential-post?view=graph-rest-1.0)
- [Workload federation rules and Entra-issued-token limitation](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation)

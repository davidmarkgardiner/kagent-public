# Copyable work request: Agent ID blueprint and MCP API registration

For the current, copy-ready GitLab ticket covering manual onboarding and the 2026-09-25 AKS federation finding, use [WORK-GITLAB-IDENTITY-TICKET.md](WORK-GITLAB-IDENTITY-TICKET.md). The older two-hop trust proposal below is superseded.

This is a **ticket template**, not a submitted ticket or a confirmed AACM API payload. Replace the public example names with approved work names and keep actual tenant, subscription, application, and identity IDs in the private work system.

## Copy into the identity/AACM team's intake

**Subject:** Pilot request — Entra Agent ID blueprint and MCP API registration for kagent

We want to onboard a kagent agent in namespace `team-event`, named `incident-adviser`, through the approved AACM/Entra Blueprint process. Its intended app-only permission is to call the `team-event` MCP API through agentgateway, limited to the `lookup_incident` tool. These names are examples; we will confirm the work namespace, agent, API, and tool before implementation.

Please help us with two distinct Entra objects:

1. **Agent ID blueprint.** Confirm whether an existing approved blueprint is suitable for this isolation and credential boundary. If not, create a dedicated Agent ID blueprint and its blueprint principal with a named technical owner and business sponsor. Confirm the credential and lifecycle policy. We do not want a production client secret or a shared blueprint credential exposed to tenant Pods.
2. **MCP API app registration.** Create or identify a single-tenant app registration and service principal for the MCP API. Agree its Application ID URI/audience and v2 access-token setting. Define an enabled **application** app role with value `team-event.mcp.use` (allowed member type: `Applications`). This is the permission for a child Agent ID to call the API; it is not Azure RBAC or Kubernetes RBAC.

Please also tell us the approved AACM request and owner for creating a **child Agent ID** for `incident-adviser` under the blueprint and assigning `team-event.mcp.use` to that child. The app role should not be assigned to the blueprint or the UAMI. We will review that follow-on request before provisioning the child in the work tenant.

Please return, in the approved private work record: the blueprint application ID and object ID; blueprint principal object ID; MCP API application ID, object ID, and service-principal object ID; the app-role ID and value; owners and sponsors; and the AACM intake contract or request reference. Confirm whether these objects were created or pre-existing, and who owns later revocation.

For a later, separately reviewed AKS step, please identify the owner of **direct AKS ServiceAccount → blueprint** federation. The proposed ServiceAccount → UAMI → blueprint chain failed in the 2026-09-25 home-lab AKS pilot with `AADSTS700231`; see the current GitLab ticket above. Do not create an AKS cluster or deploy a workload as part of this work request.

## How to interpret this request

The blueprint is a specialized Agent ID application; the MCP API registration is a separate resource that defines the role. A child Agent ID is then created under the blueprint and receives the API role. The current PoC's [`request.example.json`](request.example.json) is only a **proposed** agent-onboarding contract that assumes a blueprint already exists; it is not evidence of AACM's actual schema.

For a sanitized implementation reference, see the [identity-only PoC](README.md), [Graph blueprint/child provisioning example](provision_graph.py), and [test API/role provisioning example](provision_access.py). These scripts were run only in the separate PoC tenant and must not be copied into a work execution path without identity-owner review.

Official references: [create Agent ID blueprint](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-post?view=graph-rest-1.0), [create blueprint principal](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprintprincipal-post?view=graph-rest-1.0), [create child Agent ID](https://learn.microsoft.com/en-us/graph/api/agentidentity-post?view=graph-rest-1.0), and [define API app roles](https://learn.microsoft.com/en-us/entra/identity-platform/howto-add-app-roles-in-apps).

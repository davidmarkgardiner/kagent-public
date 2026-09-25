# Work GitLab ticket: Agent ID blueprint and app-registration onboarding

Copy the section below into the **private work GitLab project** and replace the placeholders there. This draft mainly covers [Request 2: agent blueprint and MCP permission](WORK-REQUEST-2-AGENT-BLUEPRINT-MCP.md). Submit [Request 1: caller UAMI and A2A permission](WORK-REQUEST-1-CALLER-UAMI-A2A.md) separately, or make it a distinct change item in the same private ticket. This is not an actual ticket, an approved AACM schema, or authority to change the work tenant. Keep real tenant, subscription, application, and identity IDs, OIDC issuer URLs, contacts, and internal links out of this public repository.

## Copy into GitLab

**Title:** Help establish manual AACM/Entra Agent ID onboarding for a kagent agent and protected MCP API

**Requesting team / sponsor:** `{{REQUESTING_TEAM}}` / `{{BUSINESS_SPONSOR}}`

**Environment / change reference:** `{{ENVIRONMENT}}` / `{{CHANGE_REFERENCE}}`

**How we built the home-lab pilot / proposed work procedure:** https://github.com/davidmarkgardiner/kagent-public/blob/main/work-agent-bundles/kagent-agentgateway-tenant-isolation/poc/azure-agent-id/WORK-IDENTITY-IMPLEMENTATION-PLAYBOOK.md

**Native Azure CLI / Graph request examples (no Python):** https://github.com/davidmarkgardiner/kagent-public/blob/main/work-agent-bundles/kagent-agentgateway-tenant-isolation/poc/azure-agent-id/WORK-NATIVE-GRAPH-CLI-EXAMPLES.md

The PoC used custom Python/Graph code, **not** an AACM template. Please review its ordered steps and tell us which you already support through AACM, which you would perform manually, and what approved request/response contract we can automate. Do not run its historical UAMI-federation script unchanged in the work tenant.

**Pilot workload:** namespace `{{NAMESPACE}}`, agent `{{AGENT_NAME}}`

**AKS federation inputs supplied by the platform team:** cluster `{{AKS_CLUSTER_NAME}}`, exact OIDC issuer `{{AKS_OIDC_ISSUER}}` (including any trailing slash), credential-owning workload `{{TOKEN_HOLDER_WORKLOAD}}`, ServiceAccount `{{SERVICE_ACCOUNT}}`, and subject `system:serviceaccount:{{NAMESPACE}}:{{SERVICE_ACCOUNT}}`. Confirm whether the token holder is the kagent Pod or a dedicated per-agent token proxy **before** creating the federated credential. A proxy would use its own ServiceAccount. If the cluster or token holder is not yet fixed, create the blueprint and API permissions first and leave federation pending.

**Protected API and least-privilege action:** `{{MCP_API_NAME}}`, audience `{{MCP_API_AUDIENCE}}`, application role value `{{MCP_ROLE_VALUE}}`, tool `{{ALLOWED_TOOL}}`. If inbound A2A access is in scope, agree a separate `{{A2A_API_AUDIENCE}}`, `{{A2A_ROLE_VALUE}}`, and caller identity. The work caller may be a UAMI service principal; the home-lab caller was an Agent ID.

We are piloting an isolated kagent agent on AKS. The agent must receive its own Entra Agent ID, and the protected MCP API must accept only the approved child Agent ID with the approved application role through agentgateway. Could the infra identity/AACM team help us establish the **manual onboarding path now**, including who approves and performs each step, so that we can later automate the same reviewed contract? This ticket is for identity-side design and provisioning; it does **not** request an AKS cluster or workload deployment.

Please help us with these identity objects and decisions:

1. **Blueprint:** confirm whether an existing Entra Agent ID blueprint can be reused for this trust boundary or create a dedicated one, with its blueprint principal, technical owner, business sponsor, lifecycle, and revocation owner. Record the AACM blueprint identifier and approved child-Agent-ID creation process. A blueprint credential can request tokens for more than one child under it, so please agree whether the blueprint is dedicated per agent/trust boundary or whether a trusted broker will enforce the child binding. Do not distribute a shared blueprint credential to tenant Pods.
2. **Protected MCP API:** create or identify its single-tenant app registration and service principal, Application ID URI/token audience, v2 access-token setting, and an enabled **application** app role (`allowedMemberTypes: ["Application"]`) with value `{{MCP_ROLE_VALUE}}`. Confirm who owns admin consent and role changes. This is an Entra API permission, not Azure RBAC or Kubernetes RBAC.
3. **Child Agent ID:** create the child under the approved blueprint, assign the MCP app role to the **child Agent ID principal**, and confirm the exact `oid`, audience, and `roles` claims expected by the gateway. Do not assign that MCP role to the blueprint or a UAMI. If A2A callers need their own protection, scope a **separate** A2A resource app/audience/role (`{{A2A_ROLE_VALUE}}`) and caller identity; please tell us whether that is a separate ticket.
4. **AKS trust:** once we confirm the credential-owning ServiceAccount, identify the owner and approved change path for a federated identity credential on the blueprint app matching exactly issuer `{{AKS_OIDC_ISSUER}}`, subject `system:serviceaccount:{{NAMESPACE}}:{{SERVICE_ACCOUNT}}`, and audience `api://AzureADTokenExchange`. In the 2026-09-25 home-lab AKS pilot, **direct ServiceAccount → blueprint federation succeeded**; **ServiceAccount → UAMI → blueprint failed** with `AADSTS700231` because a token obtained via federated identity credential cannot be used as another federated assertion. Please review the direct trust pattern and its blueprint/child isolation boundary before work adoption. A UAMI may still be useful for unrelated Azure-resource access, but it is not a working middle hop for this Agent ID exchange.

Please tell us which Microsoft Graph permissions, Entra roles, application ownership, and admin-consent steps your approved process requires for the blueprint, child Agent ID, API app registration, app-role assignment, and federation change. We are asking your team to run its authorized process, whether that is AACM, a script, Graph, or the portal. We are **not** asking for broad directory permissions on our AKS SPN.

Please send the results **only in the private ticket or approved identity record**: created-vs-reused status; blueprint app/object and principal IDs; child Agent ID app/object/principal IDs; MCP API app and service-principal IDs, audience, role value/ID and assignment; exact federated-credential ID/subject/issuer; approvers, owner, expiry/review date, and revocation procedure. We also need the real AACM intake/API contract (or manual form), not an assumption based on this public PoC.

For repeatable manual onboarding, could we agree a request/approval/read-back checklist for each change type: **new blueprint**, **new child Agent ID**, **new permission on an existing API**, **new API app registration**, **federation change**, and **offboarding**? Please identify the requester, approver, executor, required evidence, turnaround, and whether security/admin consent is needed for each. We can then implement an automation adapter against that approved process; until then, the identity team can run it manually.

**Acceptance evidence:** Graph/Entra read-back of each object and role assignment; an AKS ServiceAccount assertion exchanged directly for the blueprint and then a child Agent ID token with the intended `oid`, `aud`, and `roles`; negative checks for wrong audience/role/child identity; a documented revocation path. The platform team separately owns GitOps manifests, ServiceAccount and gateway policy, a production token provider, and workload/network-policy tests. The federated credential is durable trust and does not need periodic recreation. AKS rotates the projected ServiceAccount token; our platform component must still request and renew the short-lived child API token. The home-lab AKS test passed approved A2A→Agent→MCP and same-role wrong-child denials after combining role and exact `oid` in one gateway CEL expression. A static Secret header and Pod restart were only a short-lived lab test, **not** a production token lifecycle.

## Public references for the conversation

- [Identity PoC and its proof boundaries](README.md)
- [Work-form wording and explicit action-permission mapping](WORK-FORM-BLUEPRINT-ACTION-REQUEST.md)
- [Request 1: caller UAMI and A2A role](WORK-REQUEST-1-CALLER-UAMI-A2A.md)
- [Request 2: agent blueprint and MCP role](WORK-REQUEST-2-AGENT-BLUEPRINT-MCP.md)
- [Implementation playbook and exact home-lab script sequence](WORK-IDENTITY-IMPLEMENTATION-PLAYBOOK.md)
- [Native Azure CLI and Graph request examples](WORK-NATIVE-GRAPH-CLI-EXAMPLES.md)
- [Sanitized disposable AKS end-to-end evidence](AKS-FULL-E2E-EVIDENCE-2026-09-25.md)
- [Current AKS/Entra architecture walkthrough](aks-agentid-e2e-walkthrough.html)
- [Work-agent AKS/Entra handoff](../../profiles/aks-entra/WORK-AGENT-START-HERE.md)
- [Microsoft: workload identity federation limitations](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation)
- [Microsoft: configure federated trust](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-create-trust)
- [Microsoft: Agent ID autonomous authentication flow](https://learn.microsoft.com/en-us/entra/agent-id/autonomous-agent-authentication-authorization-flow)

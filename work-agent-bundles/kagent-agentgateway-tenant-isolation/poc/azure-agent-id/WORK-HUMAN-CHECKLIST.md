# Start the Entra Agent ID pilot at work

Use this checklist to start the identity-team conversation and track your decisions. The [identity ticket](WORK-GITLAB-IDENTITY-TICKET.md) contains the detailed request. The [work-agent walkthrough](../../profiles/aks-entra/WORK-AGENT-START-HERE.md) covers cluster inspection, manifests, token acquisition, and tests. No work GitLab ticket or identity request has been submitted from this public repository.

## Send the identity-team request now

- [ ] Send the message below to your Entra ID or AACM contacts. Create a private work GitLab ticket if that is their intake route. You can start this conversation before the AKS issuer and ServiceAccount are final.
- [ ] Record the contact, ticket link, owner, and next meeting in your private work system. Do not put work identifiers or internal links in this public repository.

Copy this message and replace the contact name:

> Hi {{IDENTITY_CONTACT}}, we're preparing a small AKS and kagent Agent ID pilot. Could your team help us create or approve a dedicated Agent ID blueprint and child Agent ID, register or reuse an MCP API application, and assign its application role to the child Agent ID? We also need a federated credential on the blueprint that trusts one exact AKS OIDC issuer and Kubernetes ServiceAccount. We will confirm the issuer and ServiceAccount subject with our AKS team before you create that credential.
>
> Could you tell us how to request this through AACM or your approved process, who approves the app registration and role assignment, and what your team can run for us? A script, Graph, or the portal is fine if it follows your process. We will handle the Kubernetes deployment, gateway policy, and runtime token renewal. Here is our sanitized request and home-lab implementation reference:
>
> https://github.com/davidmarkgardiner/kagent-public/blob/main/work-agent-bundles/kagent-agentgateway-tenant-isolation/poc/azure-agent-id/WORK-GITLAB-IDENTITY-TICKET.md
>
> Could we review the request together and agree what information you need from us?

## Supply the exact AKS details in the private ticket

- [ ] Confirm the target AKS cluster and its owner. Ask the AKS owner or work agent to read the OIDC issuer and confirm that Workload Identity is enabled. The [work-agent walkthrough](../../profiles/aks-entra/WORK-AGENT-START-HERE.md) gives the read-only command.
- [ ] Decide which workload will obtain Agent ID tokens. If the kagent Pod does it, use its dedicated ServiceAccount. If a separate per-agent token proxy does it, use the proxy's dedicated ServiceAccount. Do not guess a default name.
- [ ] Record the namespace, ServiceAccount name, and exact subject `system:serviceaccount:{{NAMESPACE}}:{{SERVICE_ACCOUNT}}`. Copy the issuer exactly, including its trailing slash. If this decision is still open, ask the identity team to start the blueprint and API registration work but hold the federated credential.
- [ ] Agree the MCP API name, audience, application role value, and permitted tool with the MCP owner. Ask whether the inbound A2A caller needs its own Agent ID, API audience, and role.
- [ ] Replace the placeholders in the **private** identity ticket. Keep the real OIDC URL, tenant, application IDs, and contact details out of the public repo.

## Check the identity-team response

- [ ] Get the approved blueprint and blueprint-principal IDs, child Agent ID app and object IDs, MCP API app and service-principal IDs, exact audience, role value and role ID, and the role assignment to the **child** principal.
- [ ] Get a read-back of the blueprint federated credential. Check its issuer, ServiceAccount subject, and `api://AzureADTokenExchange` audience against the private ticket.
- [ ] Ask who owns Graph permissions, admin consent, later role changes, and revocation. Ask for the real AACM intake and response contract so the process can later be automated. Do not request broad directory access for the AKS SPN as a shortcut.

## Hand off to the work agent, then prove the pilot

- [ ] Give the work agent the private identity response and the [work-agent walkthrough](../../profiles/aks-entra/WORK-AGENT-START-HERE.md). Have the agent prepare a reviewed GitOps change for the namespace, ServiceAccount, Agent, MCP, gateway policies, and NetworkPolicies.
- [ ] Have the platform team choose and prove a dynamic child-token provider. The federated credential does not need periodic recreation. The lab's static Secret and Pod restart did **not** prove production renewal.
- [ ] After normal approvals, run one positive A2A-to-Agent-to-MCP test and the wrong-audience, missing-role, wrong-child, forbidden-tool, direct-bypass, and token-expiry tests. Keep tokens and full IDs in approved private evidence only.
- [ ] Record the result, owners, rollback, and unresolved gaps before onboarding another agent.

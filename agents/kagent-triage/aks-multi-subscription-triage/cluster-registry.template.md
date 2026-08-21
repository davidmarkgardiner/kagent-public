# Approved AKS triage target registry

Replace every placeholder in the private copy. Keep this file limited to
routing metadata; do not add credentials, kubeconfig content, tokens, private
API endpoints, or customer data.

| Alias | Subscription ID | Resource group | AKS cluster | Kube context | Environment | Owner/team |
|---|---|---|---|---|---|---|
| {{CLUSTER_ALIAS_1}} | {{SUBSCRIPTION_ID_1}} | {{RESOURCE_GROUP_1}} | {{AKS_CLUSTER_1}} | {{KUBE_CONTEXT_1}} | {{ENVIRONMENT_1}} | {{OWNER_TEAM_1}} |
| {{CLUSTER_ALIAS_2}} | {{SUBSCRIPTION_ID_2}} | {{RESOURCE_GROUP_2}} | {{AKS_CLUSTER_2}} | {{KUBE_CONTEXT_2}} | {{ENVIRONMENT_2}} | {{OWNER_TEAM_2}} |

Rules:

- Every alias and kube context must be unique.
- Aliases must contain only lowercase letters, numbers, and hyphens because the
  agent uses them in target-specific kubeconfig filenames.
- A row is approved only after Azure access, target-cluster read-only RBAC,
  private API connectivity, and the kube context have been validated.
- Remove unused placeholder rows from the private copy.
- Changes require the platform team's normal review and deployment process.

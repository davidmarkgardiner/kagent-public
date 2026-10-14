# Blueprint federated credential

This is a Microsoft Graph request payload. It is configured in Entra, outside Kubernetes. Use the tenant's supported Agent ID Graph API and the identity administrator's approved permissions. It is not another Kubernetes YAML resource.

Request: `POST /v1.0/applications/{{BLUEPRINT_CLIENT_ID}}/federatedIdentityCredentials`

```json
{
  "name": "sre-token-holder",
  "issuer": "{{AKS_OIDC_ISSUER}}",
  "subject": "system:serviceaccount:team-sre:sre-agent-token-holder",
  "audiences": [
    "api://AzureADTokenExchange"
  ]
}
```

The issuer must match the cluster OIDC issuer and the subject must match the token-holder ServiceAccount exactly. The blueprint acquires tokens on behalf of its child Agent ID through the supported exchange flow. See [the setup guide](../guides/01-entra-agent-blueprint-setup.md).

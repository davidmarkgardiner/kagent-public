# Agent authentication with agentgateway

This guide describes how an agent authenticates to agentgateway and how
agentgateway authenticates to the upstream model or tool backend.

## Authentication boundary

```text
kagent agent
    │  Authorization: Bearer <short-lived JWT>
    ▼
agentgateway
    │  validates identity and authorization
    │  supplies its own provider credential
    ▼
Azure OpenAI / KubeAI / vLLM / MCP / A2A backend
```

Keep these two hops separate:

| Hop | Recommended credential | Owner |
|---|---|---|
| Agent → agentgateway | Short-lived OIDC/JWT | Agent workload identity or IdP |
| agentgateway → provider | UAMI/workload identity or gateway-side SecretRef | agentgateway |

Do not place Azure, OpenAI, or MCP backend credentials in the agent's
`ModelConfig` when agentgateway is responsible for the upstream connection.

## JWT/OIDC authentication

JWT is the preferred option for production agent-to-gateway authentication.
The gateway validates the token issuer, audience, signature, and expiry using
the identity provider's JWKS endpoint.

Use placeholders for environment-specific values:

```yaml
apiVersion: agentgateway.dev/v1alpha1
kind: AgentgatewayPolicy
metadata:
  name: agent-jwt-auth
  namespace: agentgateway-system
spec:
  targetRefs:
    - group: gateway.networking.k8s.io
      kind: Gateway
      name: ai-gateway
  traffic:
    jwtAuthentication:
      mode: Strict
      providers:
        - issuer: "https://login.microsoftonline.com/{{TENANT_ID}}/v2.0"
          audiences:
            - "api://{{AGENTGATEWAY_APP_ID}}"
          jwks:
            remote:
              jwksPath: "/common/discovery/v2.0/keys"
              cacheDuration: "5m"
              backendRef:
                group: ""
                kind: Service
                name: oidc-proxy
                namespace: agentgateway-system
                port: 443
```

The same example is checked in as
[`authentication-policy.yaml`](authentication-policy.yaml). It contains only
placeholders and must be customized for the target cluster.

`Strict` rejects requests without a valid token. Use `Optional` only for a
deliberately transitional route; it permits requests without a token.

The agent sends the token in the normal bearer header:

```bash
curl "https://{{AGENTGATEWAY_HOSTNAME}}/azure/v1/chat/completions" \
  -H "Authorization: Bearer ${AGENT_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"model":"{{MODEL}}","messages":[{"role":"user","content":"hello"}]}'
```

Use a route-level policy when different routes need different audiences or
agent permissions. Use a Gateway-level policy when every route requires the
same identity provider.

## API-key authentication

API keys are suitable for a simple internal service-to-service setup:

```yaml
traffic:
  apiKeyAuthentication:
    mode: Strict
    secretRef:
      name: agentgateway-client-keys
```

Store one key per workload or trust domain, rotate keys out of band, and do
not commit the Secret manifest containing real values. API keys are simpler
than JWTs but provide weaker identity and rotation semantics.

## Authorization is a separate decision

Authentication answers “which agent is this?” Authorization answers “what may
it do?” Apply authorization after authentication:

- restrict agents to specific model routes;
- use JWT claims such as `aud`, `scope`, or `roles` in CEL rules;
- allow-list MCP tools and namespaces;
- keep write-capable Argo or Kubernetes actions behind workflow service
  accounts rather than agent credentials;
- apply rate limits and timeouts per route.

Headers such as `x-kagent-agent` are useful for routing or defense in depth,
but they must not be treated as identity unless an authenticated ingress layer
has established and protected them.

## Network and mesh controls

JWT or API-key authentication should be combined with network controls:

1. NetworkPolicy limits which namespaces and egress paths can reach
   agentgateway.
2. Istio `AuthorizationPolicy` restricts ingress paths and known worker
   egress ranges.
3. Agentgateway validates the application identity and applies route policy.

For separate AKS Istio meshes, do not rely on worker-cluster ServiceAccount
principals being visible at management-cluster ingress. Use a trusted egress
range plus JWT/API-key authentication, or terminate authentication at a
trusted edge proxy.

The baseline network policy is in
[`istio-authorization-policy.yaml`](istio-authorization-policy.yaml).

## Validation checklist

Validate against the installed agentgateway CRDs before applying:

```bash
kubectl apply --dry-run=server -f authentication-policy.yaml
kubectl get agentgatewaypolicy agent-jwt-auth \
  -n agentgateway-system -o json | jq '.status'
```

Then verify all three cases:

```bash
# No token: must return 401
curl -i "https://{{AGENTGATEWAY_HOSTNAME}}/azure/v1/models"

# Invalid token: must return 401
curl -i "https://{{AGENTGATEWAY_HOSTNAME}}/azure/v1/models" \
  -H "Authorization: Bearer invalid"

# Valid token: should reach the route, subject to authorization and backend health
curl -i "https://{{AGENTGATEWAY_HOSTNAME}}/azure/v1/models" \
  -H "Authorization: Bearer ${AGENT_ACCESS_TOKEN}"
```

Check the installed CRD version before copying examples from upstream. The
current repository baseline is agentgateway v1.3.1, and policy fields can vary
between releases.

## References

- [agentgateway Kubernetes JWT authentication](https://agentgateway.dev/docs/kubernetes/latest/security/jwt/setup/)
- [agentgateway API-key authentication](https://agentgateway.dev/docs/local/latest/configuration/security/apikey-authn/)
- [`istio-authorization-policy.yaml`](istio-authorization-policy.yaml)
- [`DEPLOY.md`](DEPLOY.md)

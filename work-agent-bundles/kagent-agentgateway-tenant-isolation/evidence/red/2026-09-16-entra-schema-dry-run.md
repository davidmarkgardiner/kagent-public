# Entra profile schema receipt, 2026-09-16

This is a sanitized record of server-side schema validation on the red cluster. It is not a live Entra authentication result.

The following resources were rendered with inert UUID, hostname, issuer, audience, and app-role values before validation:

- `profiles/aks-entra/entra-jwks.yaml`
- `profiles/aks-entra/event-mcp-policy.yaml`
- `profiles/aks-entra/chat-mcp-policy.yaml`
- `profiles/aks-entra/event-a2a-policy.yaml`
- `profiles/aks-entra/chat-a2a-policy.yaml`
- `profiles/aks-entra/substrate-a2a-policy.yaml`

The original five objects were given unique `-schema-test` names in the validation stream. All passed `kubectl --context red create --dry-run=server` against the installed agentgateway v1.5.0 CRDs. The added Substrate A2A policy passed `kubectl --context red apply --server-side --dry-run=server` against the same CRDs.

`profiles/aks-entra/mcp-route-patches.yaml` failed `kubectl --context red create --dry-run=server` with `strict decoding error: unknown field "spec.rules[0].filters[0].cors"`. Red still has Gateway API v1.4 CRDs, which do not contain the v1.6 experimental CORS filter field. This is an expected promotion gap, not a passed gate. Install and review Gateway API v1.6.2 experimental CRDs before validating that overlay on AKS.

No Entra tenant, live application ID, secret, certificate, public hostname, or bearer token was used or retained.

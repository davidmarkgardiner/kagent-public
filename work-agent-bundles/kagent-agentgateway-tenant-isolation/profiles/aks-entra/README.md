# AKS Entra overlay

For a work-agent handoff that starts with the kagent side and separates later Azure/Entra approvals, use [`WORK-AGENT-START-HERE.md`](WORK-AGENT-START-HERE.md). The [2026-09-25 disposable AKS evidence](../../poc/azure-agent-id/AKS-FULL-E2E-EVIDENCE-2026-09-25.md) and [HTML walkthrough](../../poc/azure-agent-id/aks-agentid-e2e-walkthrough.html) supersede the older UAMI two-hop proposal.

A local rehearsal of this profile with real Entra tokens, and what it proved, is in [`LOCAL-REHEARSAL.md`](LOCAL-REHEARSAL.md).

Apply this profile only after replacing every `{{PLACEHOLDER}}` and installing Gateway API v1.6.2 experimental CRDs. The official v1.5 guide used v1.6.0 experimental; this bundle pins the latest v1.6 patch available at build time and requires server-side dry-run before promotion.

For each team, create a public-client Entra app registration for interactive MCP access, expose an API scope, and create a team-specific app role. Keep the A2A app role and MCP app role distinct. Use the v2 issuer only when the tokens actually contain that `iss`. The policy accepts both documented Entra audience forms.

For the event pilot, resolve `{{TEAM_EVENT_CALLER_AGENT_OBJECT_ID}}` and `{{TEAM_EVENT_RUNTIME_AGENT_OBJECT_ID}}` from the approved private AACM/Graph read-back. They are child Agent ID **object IDs**, not blueprint app IDs or UAMI IDs. The event policies bind role **and** exact `jwt.oid` in one CEL expression. The AKS negative test showed separate expressions under `action: Allow` can be OR'd and admit a same-role rogue Agent ID. The chat and Substrate policy examples still require their own reviewed identity pinning before work promotion.

`entra-jwks.yaml` belongs in `tenant-gateway-system`. Each team MCP policy replaces the red MCP JWT policy. The three A2A policy files replace the red A2A JWT policies with strict Entra audience and app-role checks. The Substrate specialist gets a separate `platform-substrate.a2a.invoke` role. `mcp-route-patches.yaml` replaces the two red MCP HTTPRoutes with the three documented MCP and discovery path matches plus the browser CORS filter.

For the event A2A path under kagent `v0.10.1` trusted-proxy mode, use the [tested direct Agent Service route and ReferenceGrant](event-a2a-direct-route.yaml). The old controller rewrite returned `401` without trusted proxy identity. Ensure the Agent Pod accepts ingress only from the Gateway and can reach the kagent session controller on `8083`, its model, and the protected MCP listener. Verify this on the work-installed versions before replacing a live route.

Render or substitute the placeholders, then validate in this order:

```sh
kubectl apply --server-side --dry-run=server -f entra-jwks.yaml
kubectl apply --server-side --dry-run=server -f event-mcp-policy.yaml
kubectl apply --server-side --dry-run=server -f chat-mcp-policy.yaml
kubectl apply --server-side --dry-run=server -f event-a2a-policy.yaml
kubectl apply --server-side --dry-run=server -f event-a2a-direct-route.yaml
kubectl apply --server-side --dry-run=server -f chat-a2a-policy.yaml
kubectl apply --server-side --dry-run=server -f substrate-a2a-policy.yaml
kubectl apply --server-side --dry-run=server -f mcp-route-patches.yaml
```

Kagent runtime calls do not use browser PKCE. Supply a short-lived application token for the team's MCP audience through an approved workload identity token broker or native runtime support. Prove refresh across expiry before calling the AKS profile production-ready.

This overlay does not choose an AKS ingress controller, public IP, DNS zone, certificate issuer, or secret store. Add HTTPS listeners with organization-owned hostnames and certificate references, then prove external TLS before promotion. The in-cluster red Gateway is intentionally HTTP-only.

Source: https://agentgateway.dev/docs/kubernetes/latest/documentation/mcp/auth/entra/

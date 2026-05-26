# Production Security Governance

This demo proves the routing and kagent cross-namespace authorization mechanics.
Production use needs a governance layer around it. The compliant production
claim should be:

> Agentgateway is the governed ingress point for A2A traffic, kagent enforces
> cross-namespace agent-tool references with `allowedNamespaces`, and platform
> policy controls identity, authorization, secrets, network paths, observability,
> and change approval.

Do not claim that the current Agentgateway policy performs native A2A
authorization. On the observed CRD release, `agentgatewaypolicy.spec.backend.a2a`
does not exist. Treat gateway-side A2A authorization as a future enhancement.

## Control Plane

| Control | Production requirement | Owner |
|---|---|---|
| Identity | Every calling workload presents a non-spoofable workload identity through mesh mTLS, SPIFFE/SPIRE, Kubernetes projected service-account token, or OIDC/JWT at the ingress edge. Do not trust caller-supplied `X-User-Id`, `X-Agent-Name`, or demo `X-Agent-Token` headers as identity. | Platform security |
| Authorization | Use Istio `AuthorizationPolicy` or equivalent ingress policy to restrict which principals can call each A2A route. Keep kagent `allowedNamespaces` as the target-agent owner opt-in for cross-namespace agent-tool references. | Platform security and target agent owner |
| Tenant boundary | Each team runs agents in its own namespace with labels used by `allowedNamespaces` selectors. Cross-namespace access is deny-by-default and requires explicit target-side opt-in. | Platform team |
| Secrets | Agents read only same-namespace Secrets. Use External Secrets or sealed secret delivery for real credentials; rotate them; never copy target-team credentials into source-team namespaces. | App team and platform security |
| Network | Default-deny namespace ingress and egress. Allow only kagent controller, Agentgateway, required model endpoints, and approved cross-namespace agent service paths. Pin any node-CIDR readiness exception to the actual cluster node CIDR. | Network/platform team |
| Model access | Route model calls through approved ModelConfigs and gateway/provider endpoints. Enforce model allowlists, token budgets, and per-tenant attribution. | AI platform |
| Audit | Log A2A request IDs, source principal, target agent, namespace, route, policy decision, model name, token usage, and tool calls. Ship logs and metrics to managed Loki/Mimir/Grafana or the production SIEM. | Observability/security |
| Change control | All route, `allowedNamespaces`, RBAC, NetworkPolicy, and ModelConfig changes go through GitOps pull requests, code-owner approval, and server-side dry-run validation. | Platform governance |

## Required Production Gates

1. **Ingress identity gate**

   A real deployment should terminate external access at an ingress or mesh
   gateway that validates a signed identity. Acceptable patterns:

   - Istio mTLS principal allowlist for in-mesh callers.
   - JWT validation at ingress for out-of-mesh callers.
   - SPIFFE/SPIRE identity bridged into Istio `requestPrincipals`.

   Demo headers such as `X-Agent-Token` are only correlation or defense-in-depth
   inputs until they are signed and verified by infrastructure.

2. **Target-owned access grant**

   The target agent owner controls cross-namespace access with:

   ```yaml
   spec:
     allowedNamespaces:
       from: Selector
       selector:
         matchLabels:
           team: alpha
   ```

   A source namespace label change is therefore a privileged action. Protect
   namespace labels with admission policy and platform-owned GitOps.

3. **Admission policy**

   Add Kyverno, Gatekeeper, or Kubernetes CEL policies so unsafe A2A manifests
   cannot merge or apply:

   - Reject `allowedNamespaces.from: All` outside sandbox namespaces.
   - Require `allowedNamespaces.selector.matchLabels.team`.
   - Require `NetworkPolicy` default-deny in every agent namespace.
   - Require agent workloads to run with a namespace-local service account.
   - Reject model endpoints outside the approved provider allowlist.
   - Reject `headersFrom` references to ConfigMaps for credentials; use Secrets.

4. **Runtime authorization**

   Until native Agentgateway A2A authorization exists, production authorization
   must live at the mesh/ingress layer. Minimum checks:

   - Source principal may call only its approved route prefix.
   - Source principal may call only approved target agent namespaces.
   - Rate limits and timeouts are set per route.
   - Default deny applies before allow policies.

5. **Audit and evidence**

   A compliant run should produce evidence for:

   - Gateway policy accepted and attached.
   - Source principal allowed by ingress policy.
   - Rogue namespace denied by kagent reconcile status.
   - Source service account cannot read target namespace Secrets.
   - A2A invocation includes a request ID and target agent marker.
   - Token usage and route metrics are visible in observability.

## Production Readiness Checklist

- [ ] Agentgateway route is protected by mesh mTLS or JWT validation.
- [ ] No production decision relies on spoofable headers alone.
- [ ] Target agent has `allowedNamespaces.from: Selector`, not `All`.
- [ ] Source namespace labels are platform-controlled.
- [ ] Agent namespaces have default-deny NetworkPolicies.
- [ ] Secrets are delivered by approved secret management and are namespace-local.
- [ ] ModelConfig points to an approved model gateway with cost attribution.
- [ ] Logs and metrics include source namespace, source principal, target agent,
      route, status code, latency, token usage, and tool-call markers.
- [ ] GitOps validates manifests with server-side dry-run and policy checks.
- [ ] Break-glass access is time-bound, audited, and reviewed.

## How This Demo Maps To Production

| Demo element | Production interpretation |
|---|---|
| `HTTPRoute` through Agentgateway | Governed A2A entrypoint and telemetry path |
| `AgentgatewayPolicy` | Rate limit and timeout today; future home for native A2A authz when CRD supports it |
| `allowedNamespaces` | Target-owned cross-namespace authorization grant |
| `headersFrom` | Source-local secret injection for downstream calls; not a primary identity mechanism |
| `team-gamma/rogue-orchestrator` | Negative control proving deny-by-default cross-namespace behavior |
| `kubectl auth can-i` Secret check | Evidence that source service account cannot read target namespace Secrets |

## Residual Risk

This pattern is not production-complete if any of these remain true:

- The gateway is reachable without mesh/JWT authorization.
- kagent still runs `UnsecureAuthenticator` and `NoopAuthorizer` without an
  upstream identity gate.
- Namespace labels can be changed by tenant admins.
- Model and A2A logs are not shipped to the production audit backend.
- Agent owners can grant `allowedNamespaces.from: All` without review.

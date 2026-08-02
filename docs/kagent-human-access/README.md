# kagent Human UI and API Access

## TL;DR

kagent v0.9 OIDC proxy support can require a human to sign in before reaching
the kagent UI or controller API. It identifies the caller from JWT claims such
as email, name, and groups.

It does **not** currently provide per-agent authorization. Enabling it means
"this person may enter kagent", not "this person may view or invoke only agent
X." The release notes explicitly state that this feature adds authentication,
not access control.

Use OIDC proxy authentication for the outer front door. Put a separate,
default-deny authorization layer in front of any per-agent UI/API operation,
and keep agent-to-tool permissions independent from human access.

## The three decisions that must stay separate

| Decision | Question | Current kagent OIDC proxy answers it? | Enforcement point |
|---|---|---:|---|
| Authentication | Who is the human caller? | Yes | `oauth2-proxy` + identity provider |
| Agent access | May this caller see or invoke this named agent? | No | API/agent gateway or a purpose-built authorization service |
| Tool and cluster access | May that agent call this tool against this target? | No | Agent tool allowlist, ToolGrant/agentgateway policy, AKS-MCP and Azure/Kubernetes RBAC |

Do not treat a successful human login as permission for an agent to inspect a
cluster, run a tool, or invoke a higher-privilege agent.

## What the v0.9 feature does

When `controller.auth.mode: proxy` is enabled, kagent expects a trusted
`oauth2-proxy` to authenticate a browser/API caller with an OIDC identity
provider. The proxy injects an `Authorization` JWT header; kagent extracts
configured identity claims and exposes the signed-in identity through
`/api/me`.

```text
Human browser or API client
          |
          v
OIDC identity provider (for example Microsoft Entra ID)
          |
          v
oauth2-proxy -- validates session/JWT and passes identity
          |
          v
kagent UI / controller API -- knows who the caller is
```

This is valuable for SSO, audit correlation, and preventing anonymous access
to the UI/API. It is not an RBAC engine: current kagent does not use groups or
other claims to allow or deny a particular Agent resource or agent invocation.

## What it cannot safely do by itself

The following are **not** protected per person or group by enabling the
feature alone:

- Listing a sensitive agent in the UI.
- Opening the agent's UI page or agent card.
- Calling a named agent through the controller/A2A API.
- Causing an agent to access AKS-MCP, GitLab, or another MCP tool.
- Approving a tool call or remediation action.

Therefore, do not expose a privileged agent merely because the general kagent
front door has OIDC login enabled.

## Recommended target pattern

```text
Human
  -> OIDC proxy: authenticate and establish group claims
  -> authorization gateway: default-deny agent list/view/invoke by claim + agent ID
  -> kagent UI/API: identity-aware application
  -> agent-specific allowlist: approved MCP servers and read-only tools
  -> AKS-MCP: workload identity and target-cluster RBAC

Argo service account
  -> separate authenticated route, limited to approved workflow-to-agent calls
```

### 1. Protect the whole kagent surface

Enable the kagent proxy mode and configure the proxy with the approved OIDC
issuer, client registration, redirect URI, and claim mapping. Keep the
kagent controller Service private: only the proxy/authorization gateway should
be reachable from user ingress. Do not rely on an unauthenticated internal
Service as a back door.

Use the identity provider to decide who can access the general platform, such
as a `platform-agent-users` group. This is a coarse access gate, not per-agent
authorization.

### 2. Add explicit per-agent policy before privileged use

Define a small policy record outside the Agent CR, owned through GitOps. For
example:

```yaml
# Conceptual policy input for an authorization gateway; not a kagent CRD.
apiVersion: platform.example/v1alpha1
kind: AgentAccessPolicy
metadata:
  name: management-triage
spec:
  agentRef:
    namespace: kagent
    name: {{MANAGEMENT_TRIAGE_AGENT}}
  defaultEffect: deny
  grants:
    - subject:
        oidcGroup: {{SRE_TRIAGE_GROUP}}
      actions: [view, invoke]
    - subject:
        oidcGroup: {{PLATFORM_AUDIT_GROUP}}
      actions: [view]
  denyActions: [configure, delete]
```

At the gateway, validate the JWT from the proxy and enforce these checks for
every operation:

1. Verify issuer, audience, expiry and signature.
2. Resolve the requested agent ID from the UI/API route or request body.
3. Allow only an explicit `view` or `invoke` grant; otherwise return `403`.
4. Add immutable audit attributes: caller subject, groups used, agent ID,
   request/correlation ID, decision, and timestamp.
5. Do not trust a client-supplied group header; use validated JWT claims only.

The exact route shape and policy mechanism must be validated against the
installed kagent and gateway versions before implementation. The important
property is that the policy covers both agent discovery/listing and invocation,
and that direct controller access cannot bypass it.

### 3. Keep machine callers separate from humans

Argo workflows and other platform services should use a dedicated
service-to-service identity and a narrowly scoped route. They should not reuse
a human browser session or broad human group grant. Their authorization should
be restricted to the specific triage agents/workflows they need.

### 4. Keep tool permission independent

Even after a human is allowed to invoke an agent, the agent must retain its own
least-privilege tool policy. For the management triage kagent, that means the
AKS-MCP-only tool binding and target-cluster checks in
`work-agent-bundles/evidence-first-worker-triage/human-operated-rollout/examples/management-aks-mcp-only-investigation.md`.

## UI and API rollout options

| Option | Human UI experience | Per-agent enforcement | Recommended use |
|---|---|---|---|
| OIDC proxy only | One authenticated kagent UI | No | Non-privileged internal pilot only |
| Separate kagent instances/ingresses by audience | Each group enters a separate UI surface | Coarse, by deployment | Simple interim boundary where duplication is acceptable |
| Authorization gateway in front of a shared UI/API | One UI can show only authorised agents | Yes, if list/detail/invoke routes are all covered | Preferred shared-platform target |
| No direct human invoke for privileged agents | UI may show status only; Argo/HITL invokes workflow | Strongest operational boundary | High-impact, production or remediation paths |

For a first production step, I would use OIDC proxy for SSO plus a
default-deny gateway policy for the management triage agent. Keep direct UI
chat disabled for that agent until list/detail/invoke enforcement and audit
proof are in place.

## Minimum acceptance tests

Test with three real identity-provider accounts/groups in a non-production
environment:

| Case | Expected result |
|---|---|
| Unauthenticated caller | Redirect to sign-in or `401`; no controller bypass |
| Platform user without agent grant | Can enter the allowed platform surface but cannot list, view, or invoke the protected agent (`403`) |
| SRE triage group member | Can view and invoke only the explicitly granted read-only triage agent |
| Audit-only group member | Can view permitted metadata, but cannot invoke |
| Argo service identity | Can invoke only its declared triage route; cannot use the human UI route |
| Direct controller Service request | Denied by network/ingress policy |

Capture the identity subject, policy decision, agent ID, correlation ID and
result in the audit trail. Then separately prove that a permitted invocation
still cannot exceed the agent's AKS-MCP/tool/RBAC policy.

## Implementation sequence

1. Confirm the installed kagent version supports proxy mode and test it with a
   non-production identity-provider application.
2. Lock down network reachability so the UI/API cannot bypass the proxy.
3. Define the AgentAccessPolicy source of truth and the group-to-action matrix
   in Git.
4. Implement and test default-deny list, detail and invoke enforcement at the
   chosen gateway/authorization service.
5. Add audit logs and alert on denied access, missing identity, direct-service
   bypass attempts and privileged-agent invocations.
6. Only then expose management/production triage agents to people. Keep tool
   grants, AKS-MCP target selection and human approval controls as separate
   gates.

## References

- [kagent v0.9 release notes](https://kagent.dev/docs/kagent/resources/release-notes)
- [AKS-MCP deployment and authentication](../../platform/aks-mcp/README.md)
- [Agentgateway MCP authorization discovery](../agentgateway-mcp-tool-auth/TOOL-AUTH-DISCOVERY.md)
- [BYO kagent ToolGrant model](../../infra/byo-kagent/README.md)

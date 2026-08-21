# AKS-MCP upstream support email draft

Status: ready for review and sending

```text
To: Dominic
Cc: Julia
Subject: Guidance requested: supported AKS-MCP path for kagent and AKS Workload Identity

Hi Dominic,

I am copying Julia in because this touches both the AKS-MCP technical direction
and the supported product roadmap.

We are currently evaluating the upstream Azure AKS-MCP project as the AKS and
Kubernetes tool layer for a shared kagent-based triage service:

https://github.com/Azure/aks-mcp

Our current proof of concept uses AKS-MCP v0.0.19 in a management AKS cluster.
kagent connects to it over Streamable HTTP, and the AKS-MCP workload uses AKS
Workload Identity with a dedicated user-assigned managed identity (UAMI). The
UAMI is intended to have least-privilege, read-only access to approved AKS
clusters across several subscriptions.

The target cluster can change on every request. The tool therefore needs to
select or acquire the correct cluster credentials for that request without
using a shared mutable kubeconfig that could leak one request's context into
another. The endpoint is private and the intended use is read-only incident
triage through kagent, not direct public or multi-tenant access.

We have reviewed the v0.0.20 breaking change:

https://github.com/Azure/aks-mcp/releases/tag/v0.0.20

Our understanding is that v0.0.20 removes Streamable HTTP/SSE, OAuth/OBO,
container and Helm/Kubernetes deployment support, and makes AKS-MCP a local
stdio-only subprocess. The release also says that remote, proxy and gateway
deployments are outside the project's supported security boundary and that an
existing remote deployment cannot be upgraded in place.

We can pin v0.0.19 temporarily, but we do not want a frozen remote release to
become the long-term platform dependency.

Could you advise what Microsoft considers the supported forward path for this
shared kagent use case?

In particular:

1. Would running current AKS-MCP through kagent's MCPServer stdio adapter be
   considered supported, or would the generated sidecar/gateway endpoint still
   place it outside the AKS-MCP support boundary?
2. Would an A2A specialist agent that launches AKS-MCP locally as a stdio
   subprocess, then returns only constrained read-only evidence to the kagent
   orchestrator, remain within the intended boundary?
3. Is a supported authenticated remote transport expected to return, or is the
   recommended direction to compose alternatives such as Azure MCP Server for
   Azure/AKS control-plane data and a separately RBAC-scoped Kubernetes MCP
   server for pods, events and logs?
4. In the recommended hosted design, can AKS Workload Identity/UAMI remain the
   outbound Azure authentication method so that no access token or client
   secret needs to be stored or refreshed by the workload?

We are happy to share a small architecture diagram and tool inventory if that
would help. The main thing we want to avoid is building around v0.0.19 or a
stdio wrapper if Microsoft already has a different supported direction in
mind.

Thanks,

{{SENDER_NAME}}
{{TEAM_OR_ROLE}}
```

## Before sending

- Replace `{{SENDER_NAME}}` and `{{TEAM_OR_ROLE}}`.
- Add Dominic and Julia's addresses in Outlook; do not commit them to this
  public repository.
- Remove any question that is already answered internally.
- Attach or link an internal architecture diagram only after checking that it
  contains no subscription IDs, tenant IDs, private hostnames or cluster
  details.

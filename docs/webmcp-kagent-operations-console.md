# WebMCP front door for kagent

## Decision

WebMCP can complement kagent, but a WebMCP-enabled page is not directly usable
as a kagent `RemoteMCPServer`.

WebMCP tools live inside an active browser document through
`document.modelContext`. kagent instead connects to network MCP servers over
Streamable HTTP or SSE. The clean integration is therefore to use WebMCP as a
browser-native front door to kagent's A2A API, while kagent continues to use
bounded MCP servers for platform evidence and operations.

## Proposed architecture

```text
Browser-integrated agent
  -> WebMCP tools registered by an operations console
    -> authenticated backend-for-frontend
      -> kagent A2A agent
        -> allow-listed RemoteMCPServer tools
          -> AKS, Grafana, PostgreSQL, or another approved platform service
        <- evidence and proposed remediation
    <- reviewable result rendered in the browser
  -> explicit human approval
    -> Argo Workflow submission
      -> workflow ServiceAccount performs the authorised change
```

This preserves the platform permission boundary:

- the browser is the user-visible collaboration surface;
- kagent investigates and prepares evidence or a remediation proposal;
- read-only and write-capable agents remain separate;
- agents do not receive direct broad execution credentials;
- an approved workflow ServiceAccount owns resource-changing permissions.

## Candidate WebMCP tools

Start with a small, typed catalogue:

| Tool | Purpose | Risk class |
|---|---|---|
| `list_ready_agents` | List the kagent agents available to the caller | Read-only |
| `triage_namespace` | Run bounded diagnostics for one cluster alias and namespace | Read-only |
| `show_evidence` | Render the evidence and receipt for a completed run | Read-only |
| `propose_remediation` | Prepare a reviewable change without applying it | Proposal only |
| `submit_approved_workflow` | Submit an already approved, immutable proposal | Write, confirmation required |

Do not expose generic `kubectl`, arbitrary shell, arbitrary SQL, apply, patch, or
delete operations as browser tools. Tool schemas should constrain cluster
aliases, namespaces, action types, result sizes, and timeouts.

## Demonstration flow

Example prompt:

> Why is checkout failing in the payments namespace?

1. The browser agent discovers `triage_namespace` from the active console.
2. The page invokes an authenticated backend using typed inputs.
3. The backend sends the request to a namespace-scoped kagent agent over A2A.
4. kagent uses only its allow-listed read-only MCP tools.
5. The page renders the evidence, tool receipt, likely cause, and confidence.
6. If appropriate, the page offers `propose_remediation` and displays the
   resulting manifest diff as an uncommitted change.
7. A human accepts or rejects the proposal.
8. Only an accepted proposal can be submitted to the approved Argo Workflow.

## Why a direct connection does not work

A kagent `RemoteMCPServer` requires a reachable MCP URL and a supported
transport. WebMCP defines an in-browser API rather than an MCP wire endpoint, so
there is no `/mcp` URL for the kagent controller to discover.

A browser bridge could translate WebMCP tools into Streamable HTTP MCP, but it
would need to own the user, browser, tab, origin, navigation, cancellation, and
session lifecycle. That is a later experiment, not the recommended first POC.
Agentgateway can govern an MCP network route, but it does not itself translate a
browser document API into MCP.

## First POC boundary

Build one read-only vertical slice:

- one operations-console page;
- one WebMCP tool: `triage_namespace`;
- one synthetic failing namespace;
- one namespace-scoped kagent agent;
- one allow-listed read-only MCP server;
- one deterministic evidence receipt rendered in the page;
- no workflow submission or resource mutation.

Acceptance requires proof that:

1. the browser agent discovers the WebMCP tool;
2. the request carries the exact typed cluster alias and namespace;
3. kagent reaches Accepted and Ready before invocation;
4. only the expected read-only MCP tools are called;
5. the evidence displayed in the page matches the saved receipt;
6. secrets, credentials, private endpoints, and raw tokens are absent;
7. cancellation, timeout, stale-page, and unavailable-agent cases fail closed.

Use `scripts/kagent-verify-agent.sh` and `scripts/kagent-a2a-invoke.sh` for the
kagent readiness and invocation gates rather than recreating those flows.

## References

- [WebMCP specification and explainer](https://github.com/webmachinelearning/webmcp)
- [kagent](https://github.com/kagent-dev/kagent)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Agent2Agent protocol](https://a2a-protocol.org/)

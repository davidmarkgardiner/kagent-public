# Agent Gateway MCP Tool Auth and Discovery

This folder is a portable explainer for using Agent Gateway as the authentication,
authorization, and discovery layer for kagent tools.

Status: design proposal. `ToolCatalogEntry` and `ToolGrant` are checked-in
platform proposal artifacts, not deployed or runtime-proven controls. No
controller or renderer that projects them into Agent Gateway policy is proven
in this repository.

## Start Here

1. Open `mcp-tool-auth-discovery-explainer.html` in a browser.
2. Read `mcp-tool-auth-discovery-demo.yaml` to see the Kubernetes object flow.
3. Read `TOOL-AUTH-DISCOVERY.md` for the implementation notes and validation plan.

## Core Idea

Kagent still owns agents, prompts, model configuration, and selected tool refs.
The proposed platform catalog/grant model records which tools an agent is
approved to use.
Agent Gateway becomes the runtime enforcement point:

- authenticates the caller;
- filters MCP `tools/list` discovery;
- blocks unauthorized MCP `tools/call` execution;
- routes to platform-owned or bring-your-own MCP tool servers.

Existing plain APIs do not have to start as native MCP services. They can be
wrapped or projected into an MCP tool surface, ideally through OpenAPI where
possible, so agents get discovery and per-tool authorization.

## Files

| File | Purpose |
|---|---|
| `mcp-tool-auth-discovery-explainer.html` | Visual explanation of the pattern |
| `mcp-tool-auth-discovery-demo.yaml` | Demonstration YAML showing catalog, grant, gateway, and kagent resources |
| `TOOL-AUTH-DISCOVERY.md` | Notes from the local upstream `agentgateway` and `kagent` code inspection |

## Safety

The YAML is demonstrative. Do not apply it directly to a production cluster.
`ToolCatalogEntry.status` is shown inline for readability. In the proposed
production design, a proven onboarding controller or workflow would write that
status through the `/status` subresource.

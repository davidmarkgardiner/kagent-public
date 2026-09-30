# Work-agent start prompt: Denodo MCP/UAMI canary

Use this file with the work agent in the private work environment. The source
bundle is `work-agent-bundles/denodo-fastmcp-uami/`. Its home-lab proof is
synthetic only. Keep all workplace coordinates, IDs, driver binaries, tokens,
query results, and rendered manifests out of the public repository and chat.

## Paste this task to the work agent

> Inspect the already deployed workplace PostgreSQL MCP, Agent Gateway route,
> RemoteMCPServer, Agent, identity, image digests, tool contracts, and rollback
> path. Use the Denodo bundle as a reference to make the smallest reviewable
> Denodo canary. Preserve existing object names and unrelated tools/policies.
>
> Obtain these inputs privately: `jdbc:denodo://{{DVP_HOST}}:9999/{{DATABASE}}`,
> DVP server version/update and matching JDBC JAR, DVP resource app ID, caller
> UAMI client ID, AKS OIDC issuer and ServiceAccount subject, DVP OAuth/app-role
> mapping, private CA, approved view and fields, installed Gateway/kagent CRD
> versions, and a lower-environment target. Do not place an access token in a
> URL, manifest, command line, or output. `useOAuth2=true` and `accessToken`
> are JDBC driver properties. Request the UAMI token for
> `{{DVP_RESOURCE_APP_ID}}/.default` using AKS Workload Identity; the supplied
> IMDS `resource={{DVP_RESOURCE_APP_ID}}` example is for a different host path.
>
> First produce a diff and image/build plan against the installed workplace
> source. Replace the synthetic inventory view and query fields with the
> data-owner-approved Denodo view contract. Keep typed fixed read-only tools,
> JDBC TLS verification, parameter binding, timeout and result budgets. Build
> the matching driver into a private digest-pinned image. Render the supplied
> manifests privately and validate them against installed CRDs; do not apply
> the public templates wholesale over the existing deployment.
>
> For one authorized canary, run `/app/verify_live.py` inside the UAMI Pod.
> Report only markers for token audience match, TLS/JDBC `SELECT 1`, approved
> view query, and fresh connection. Prove unapproved-view and write denial
> through the DVP owner's approved negative test. Then prove MCP discovery,
> Gateway routing, and one sanitized kagent A2A call. Capture complete MCP
> envelope bytes and per-call/cumulative model-input tokens; compare to a
> representative baseline before claiming token savings. Record image digest,
> exact diff, results, failures, and rollback. Never print token, connection
> properties, identifiers, rows, or sensitive query text in evidence.

## Readiness markers

| Gate | Evidence to retain |
|---|---|
| Identity | UAMI client ID, ServiceAccount subject, and DVP resource app ID verified privately; marker-only token audience match |
| Network/TLS | DNS, TCP/9999, certificate validation, `SELECT 1` |
| DVP authorization | Approved view query succeeds; negative privilege checks fail as intended |
| MCP | Three intended tools discoverable; bounded result and truncation behavior |
| Agent | Gateway route and sanitized A2A answer; input-token and envelope measurements |
| Rollback | Previous digest and manifests captured before canary |

The decisive proof is DVP accepting a real UAMI token from the actual AKS Pod.
A home-lab fixture or successful token acquisition alone does not prove that.

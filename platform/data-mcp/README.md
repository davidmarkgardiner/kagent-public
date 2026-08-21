# Governed database and Power BI MCP patterns

This guide describes a safe way to let a kagent interrogate operational or business data without giving it an unrestricted database connection. It is a design and validation guide: no database, Fabric tenant, identity, endpoint, or live result is implied by this repository.

## Decision summary

| Need | Recommended boundary | Status |
|---|---|---|
| Query a Starburst data mesh/data products | Starburst Enterprise's integrated [MCP server](https://docs.starburst.io/latest/starburst-ai/mcp-server.html), mounted directly as a remote MCP endpoint | **Verified current capability; requires the applicable Starburst MCP licence** |
| Read data from a relational database | [Microsoft SQL MCP Server in Data API Builder (DAB)](https://learn.microsoft.com/en-us/azure/data-api-builder/mcp/overview), exposing approved entities only | **Verified current capability** |
| Query an existing Power BI semantic model | [Power BI remote MCP](https://learn.microsoft.com/en-us/power-bi/developer/mcp/mcp-servers-overview) with Microsoft Entra OAuth and existing Power BI permissions | **Verified current capability — Preview** |
| Ask across a Fabric data estate | A published [Fabric Data agent MCP server](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-mcp-server) | **Verified current capability — Preview** |
| Edit a Power BI model | Isolated, human-approved use of the [Power BI Modeling MCP](https://github.com/microsoft/powerbi-modeling-mcp) | **Verified current capability — Preview; not an unattended-agent default** |
| Let a kagent use one of these services | Mount the remote MCP server with an explicit tool allowlist; place the endpoint behind Agent Gateway where its installed version supports the required MCP route and policy | **Proposed design — requires cluster validation** |

For a Starburst data mesh, prefer its native MCP server over a bespoke adapter.
For a database that is not already behind a governed data mesh, read-only SQL
through DAB remains the preferred first implementation. Both patterns are more
predictable and auditable than giving an LLM raw SQL, connection strings, or
broad database credentials.

## Target architecture

```text
kagent Agent
  └─ explicit MCP tool allowlist
       └─ RemoteMCPServer
            └─ Agent Gateway policy and audit boundary             (proposed)
                 └─ SQL MCP / Power BI remote MCP / Fabric agent
                      └─ approved views, semantic models, or data-agent sources
```

The agent's effective capability must be the intersection of all layers:

1. its mounted `toolNames`;
2. the MCP server's own exposed tools and authorization;
3. the backing database, Power BI, or Fabric permissions; and
4. gateway, network, rate, and observability policies.

An MCP tool name is not an authorization grant. A mounted read tool can still be denied by the server or the backing data platform.

## Starburst data-mesh POC: decision and handoff plan

The discovery that the intended target is a Starburst SQL/data-mesh endpoint
changes the recommendation: **do not start by writing an MCP server.** Current
Starburst Enterprise documentation describes an integrated, authenticated HTTP
MCP endpoint at the coordinator's `/mcp` path. It offers read-only query,
data-product discovery, data-product detail, and pre-approved parameterised
query capabilities. It requires a valid MCP server licence.

### Decision first

| Decision | Choose this when | Result |
|---|---|---|
| **A. Native Starburst MCP — recommended** | A non-production Starburst Enterprise endpoint and MCP licence are available | Mount the coordinator's `/mcp` endpoint in kagent. No JDBC driver or custom MCP service is needed. This is the closest production-equivalent POC. |
| **B. Starburst Enterprise evaluation in HomeLab** | Starburst can provide a permitted evaluation/licence and deployment guidance | Deploy the supported Starburst Enterprise stack to the lab, enable the native MCP service, and use synthetic data. This validates the complete Starburst product path without touching work data. |
| **C. Open-source Trino plus a thin adapter** | No Starburst evaluation/non-production endpoint is available, but the team wants an early Kubernetes integration rehearsal | Prove kagent → RemoteMCPServer → MCP adapter → Trino → synthetic data. It proves the interface and operational controls, **not** the native Starburst MCP, data-product feature, or licence/auth behaviour. |
| **D. Community Trino MCP server** | Lab-only comparison or code study | Do not adopt as the production candidate without supplier review. The reviewed [community implementation](https://github.com/stinkgen/trino_mcp) labels itself beta and says its HTTP/SSE transport has issues; it is not equivalent to Starburst support. |

The Starburst JDBC driver is useful only for option C, where a custom adapter
needs to issue SQL to Starburst/Trino. It is **not** needed by kagent for option
A: kagent speaks MCP over HTTP to Starburst directly. The native server
supports `queryReadOnly`, rejects DDL/DML, and lets administrators cap query
duration and response size. Its parameterised-query feature is the preferred
production control for repeatable business questions because the SQL template,
tables, parameter types, and constraints are administrator-defined.

### POC scope and architecture

```text
HomeLab kagent Agent (no database credentials)
  -> explicit MCP allowlist
  -> optional Agent Gateway policy boundary                 (validate version)
  -> Starburst Enterprise /mcp                              (preferred)
       -> dedicated read-only Starburst service identity
       -> one approved non-production data product/views
       -> synthetic or masked data only
```

Do not put the Starburst JDBC JAR in the kagent Agent container. For the
native-MCP option it has no role. For a temporary adapter option, contain the
driver and Starburst credentials in that adapter workload alone.

### Minimum safe tool set

| Stage | Tool choice | Why |
|---|---|---|
| Discover | `searchDataProducts` | Lets the agent find the curated dataset rather than guess table names. |
| Understand | `getDataProductDetails` | Returns data-product/view metadata so the agent can form a bounded query. |
| Execute | `queryReadOnly` | Read-only SQL only; keep Starburst result-size and execution-time limits low. |
| Preferred production execute path | `listParametrizedQueryTools`, `parametrizedQuery` | Uses administrator-approved SQL templates and typed/validated inputs rather than arbitrary model-authored SQL. |

Mount only the discovery tools and one execution path required by the POC. Do
not assume the exact names until the live `RemoteMCPServer.status.discoveredTools`
has been inspected.

### Ordered HomeLab plan

1. **Confirm the production contract with the Starburst team.** Obtain only
   sanitised facts: Enterprise/Galaxy product and version, whether the native
   MCP server is licensed, endpoint transport, authentication method, approved
   non-production data product, expected roles, maximum result/time limits, and
   available audit/query-history fields. Do not request or commit credentials.
2. **Select option A, B, or C above.** Stop if no sanctioned non-production
   target or licence exists; do not replace it silently with a community server
   and call the result production-like.
3. **Prepare a synthetic data product.** Use a narrow business question (for
   example, overdue balance count by risk band), a documented schema, and no
   real personal or financial records. Give the POC identity `SELECT` only on
   its views/data product.
4. **Expose and constrain the MCP endpoint.** For native Starburst, enable the
   server only with the Starburst team's approved configuration. Set a short
   maximum query execution time and small result cap. Use parameterised query
   tools for the final acceptance run where available.
5. **Register the endpoint in kagent.** Create a placeholder-safe
   `RemoteMCPServer`, inspect discovered tools, then mount only the approved
   names on a purpose-specific read-only Agent. Validate Agent Gateway policy
   syntax and runtime behaviour against the installed release before inserting
   it into the path.
6. **Run three bounded tests.** (a) discover the data product, (b) inspect its
   approved metadata, and (c) return a small aggregate with a `LIMIT` or a
   parameterised query. Capture query IDs and redacted receipts.
7. **Run negative-control checks without touching real data.** Prove the Agent
   does not mount write tools; verify the Starburst identity cannot query an
   out-of-scope object using a data-owner-approved test. Do not attempt DML in
   a shared environment merely to produce a failure.
8. **Handoff or clean up.** Deliver a redacted evidence pack and the exact
   manifests/configuration diff to the Starburst team. Remove POC resources and
   revoke the POC identity if it is not being retained for the next phase.

### Entry gates and decision points

| Gate | Pass condition | Fail-closed action |
|---|---|---|
| Product fit | Starburst confirms Enterprise native MCP is available, or explicitly sponsors the selected alternative | Do not build an unowned adapter for the production path. |
| Environment | Non-production endpoint, network route, synthetic/masked data, and a named data owner exist | Stop; do not point a HomeLab agent at production data. |
| Identity | Separate non-human identity has minimum read rights to the approved product only | Stop; never reuse a person's account or broad administrator role. |
| Tool discovery | Discovered tools equal the requested limited allowlist | Stop and correct the binding; do not use a wildcard/all-tools mount. |
| Live query | Small read-only/parameterised query returns a query ID and redacted expected result | Investigate endpoint, role, catalogue/schema, and limits; do not weaken permissions. |
| Audit | Query history/audit receipt identifies the POC identity and correlation/query ID | Do not promote; observability is part of the control. |

### Evidence pack for Starburst handoff

- product/version/licence confirmation, with credentials and internal URLs
  removed;
- architecture diagram showing the kagent, gateway (if used), Starburst MCP,
  and data-product boundary;
- rendered `RemoteMCPServer` and Agent manifests with placeholders;
- `Accepted=True` / `Ready=True` statuses and discovered tool list;
- three redacted MCP tool receipts, including Starburst query IDs;
- proof of the Starburst role/data-product/view grants and out-of-scope denial;
- query-result and execution-size limits, timeout, audit/query-history proof;
- cleanup/revocation receipt or an explicit retained-lab-owner decision.

### What the POC will and will not prove

| Claim | POC outcome |
|---|---|
| A kagent can securely use a governed Starburst data product via MCP | **Proven only after the native-MCP path completes with the evidence above** |
| Starburst's native MCP, data-product discovery, permissions, and query IDs work together | **Proven only by option A or B** |
| The Kubernetes/kagent/MCP integration pattern works | **Can be demonstrated by option C**, but that is not proof of the Starburst product path |
| Production data governance, performance, cost, or compliance is ready | **Not proven by a HomeLab POC**; requires the data/Starburst owners' production validation |

## SQL: recommended production pattern

### What DAB SQL MCP provides

**Verified current capability.** DAB's SQL MCP Server exposes entities defined in DAB configuration rather than letting a client submit arbitrary SQL. It supports Streamable HTTP and stdio transports, entity permissions, policy, caching, and telemetry. Its documented tool surface includes:

```text
describe_entities     read_records          aggregate_records
execute_entity        create_record         update_record
delete_record
```

See the [official DAB SQL MCP overview](https://learn.microsoft.com/en-us/azure/data-api-builder/mcp/overview) for supported DAB versions and configuration details. DAB v2 is the currently recommended major version in that documentation.

### Safe read-only contract

**Proposed design.** Define only reporting views (for example, `v_debt_account_summary`, `v_payment_schedule`, and `v_payment_risk`) or parameterised, read-only stored procedures. The data owner—not the agent—owns the schema, joins, filters, and redaction.

Mount only these tools on the first agent:

```text
describe_entities
read_records
aggregate_records
```

Do not mount `create_record`, `update_record`, or `delete_record`. Treat `execute_entity` as opt-in: enable it only when it is bound to reviewed, read-only stored procedures and has been tested with the exact DAB version.

Use a dedicated database identity with read access to those views/procedures only. For Azure SQL, Microsoft documents Microsoft Entra/managed-identity database-user setup in its [MCP troubleshooting guidance](https://learn.microsoft.com/en-us/azure/data-api-builder/troubleshooting/mcp). Do not place a connection string, PAT, tenant ID, or real server name in an Agent manifest or this repository.

### Illustrative kagent binding

This follows the same `RemoteMCPServer` / explicit `toolNames` pattern as the [AKS MCP examples](../aks-mcp/examples/README.md). Field support must be checked against the installed kagent CRDs before applying.

```yaml
apiVersion: kagent.dev/v1alpha2
kind: RemoteMCPServer
metadata:
  name: sql-mcp-readonly
  namespace: {{KAGENT_NAMESPACE}}
spec:
  description: Read-only DAB SQL MCP endpoint for approved reporting entities.
  protocol: STREAMABLE_HTTP
  url: https://{{DATA_MCP_HOST}}/mcp
---
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: reporting-data-agent
  namespace: {{KAGENT_NAMESPACE}}
spec:
  type: Declarative
  declarative:
    runtime: go
    modelConfig: {{MODEL_CONFIG_NAME}}
    systemMessage: |
      Use only the approved read-only data tools. Summarise results; never
      expose credentials or personal data beyond the approved response policy.
      Do not attempt writes, schema changes, or unrestricted data extraction.
    tools:
      - type: McpServer
        mcpServer:
          apiGroup: kagent.dev
          kind: RemoteMCPServer
          name: sql-mcp-readonly
          namespace: {{KAGENT_NAMESPACE}}
          toolNames:
            - describe_entities
            - read_records
            - aggregate_records
```

`{{...}}` values are deliberate deployment-time placeholders. First confirm the live `RemoteMCPServer.status.discoveredTools`, then make `toolNames` match the actual discovery rather than assuming a release has identical names.

## Power BI and Fabric options

| Option | Good for | Identity and safety boundary | Recommendation |
|---|---|---|---|
| Power BI remote MCP | Natural-language questions over existing semantic models | Microsoft Entra OAuth; requests use the authenticated user's Power BI access | Use for analyst-assist scenarios where user-scoped access is desired. Preview: validate auth, tenant controls, audit, and result handling before production. |
| Fabric Data agent MCP | A published Fabric data agent over supported Fabric sources, including semantic models and lakehouse/warehouse-style sources | Fabric permissions and data-agent configuration; Microsoft warns responses can cross compliance boundaries | Use only after data-governance review and a non-sensitive POC. Preview and capacity/licensing prerequisites apply. |
| Power BI Modeling MCP | Model authoring, PBIP, or Fabric semantic-model operations | Can change a model in its read/write mode | Keep separate from autonomous triage/reporting agents. Prefer `--readonly` for investigation; require a human approval boundary for every write workflow. |

The remote Power BI MCP queries semantic models and is not equivalent to the local Modeling MCP. Do not assume a workload identity/UAMI can replace the interactive Entra OAuth flow for the remote service; validate the supported identity path with the current Power BI documentation and tenant policy.

## Agent Gateway placement

**Proposed design.** Use Agent Gateway as a single controlled ingress to remote MCP services when the installed Agent Gateway release supports the required MCP route, authentication, and policy features. It should add network segmentation, authentication enforcement, request limits, and telemetry; it must not be treated as a replacement for DAB entity permissions or database/Power BI/Fabric authorization.

Use separate endpoints and backing identities for each trust level:

| Endpoint | Backing identity | Mounted by | Allowed operation |
|---|---|---|---|
| `sql-mcp-readonly` | Read-only reporting identity | Reporting and triage agents | Approved read/aggregate tools |
| `powerbi-insights` | User-scoped Entra OAuth session | Interactive analyst agent | Semantic-model queries |
| `fabric-data-agent` | Fabric-authorised principal | Approved analytics agent | Published data-agent actions |
| `sql-mcp-write` | Separate write identity | No default agent | Approval-gated workflow only |

Multiple tokens for one service account are rotation material, not permission isolation. Different trust levels need separate identities, endpoints, and server-side permissions.

## First POC: read-only reporting question

**Proposed design — no live POC has been run by this repository.**

1. The data owner creates a non-production dataset and three minimal reporting views with masked or synthetic data.
2. Deploy DAB SQL MCP with only those entities; configure a dedicated read-only identity and HTTPS endpoint.
3. Register the endpoint as a `RemoteMCPServer`; verify `Accepted=True` and inspect `.status.discoveredTools`.
4. Create a single read-only agent using the illustrative three-tool allowlist; verify `Accepted=True` and `Ready=True`.
5. Ask one bounded question, such as “Summarise overdue balances by risk band.” Capture the request, tool call, constrained result, and gateway/server audit record.
6. Prove that write tools are absent from the agent binding. Do not test a write against real data merely to demonstrate denial.
7. Remove the Agent and RemoteMCPServer, revoke the POC identity, and retain only sanitised evidence.

### POC acceptance criteria

| Criterion | Evidence to attach |
|---|---|
| Server is discoverable | Sanitised `RemoteMCPServer` status showing `Accepted=True` and discovered tools |
| Agent is ready | Sanitised Agent status with `Accepted=True`, `Ready=True`, and the three-tool allowlist |
| One useful answer is returned | Prompt, tool-call receipt, result summary, and timestamp; no raw sensitive data |
| Read scope is enforced by design | DAB entity configuration, database grant summary, and agent manifest diff |
| Write scope is unavailable | Rendered Agent tool list showing no create/update/delete tool |
| Requests are traceable | Gateway/MCP/DB audit or telemetry receipt tied to the POC run |
| Cleanup is complete | Deletion/revocation receipt and retained sanitised evidence path |

Keep static validation distinct from live proof: successful YAML rendering or an `Accepted=True` resource does not prove that the backing data source, identity, and an actual query work end-to-end.

## Guardrails

- Start with masked, synthetic, or explicitly approved non-production data.
- Enforce row, field, and query-rate limits at the data/MCP boundary where possible; an agent instruction alone is not a control.
- Expose purpose-built views/procedures, not base tables or arbitrary SQL.
- Minimise fields and exclude secrets, credentials, and unnecessary PII.
- Preserve query/audit receipts, but redact sensitive values before attaching them to a Kanban card, issue, or public repository.
- Fail closed on missing identity, unknown discovered tool names, unhealthy endpoint, missing audit trail, or ambiguous data classification.
- Require explicit human approval for any write-capable data tool, model edit, external sharing, or production data access.

## What still requires validation

| Item | Why it is not claimed here |
|---|---|
| The exact Agent Gateway MCP policy syntax and runtime behaviour | This depends on the installed Agent Gateway CRDs and release. |
| A UAMI/workload-identity path to each Power BI or Fabric option | Supported authentication depends on the service, tenant, and current preview contract. |
| The available DAB entity/tool names and configuration semantics | They must be verified against the chosen DAB version and rendered configuration. |
| End-to-end results, latency, data classification, and audit completeness | No credentials, environment, or live data source is present in this public repo. |

## Related repository material

- [AKS MCP examples](../aks-mcp/examples/README.md) — the equivalent explicit RemoteMCPServer/tool-allowlist pattern for Kubernetes tools.
- [Agent Gateway](../agentgateway/README.md) — gateway deployment and policy material; validate its installed CRDs before applying any new route.

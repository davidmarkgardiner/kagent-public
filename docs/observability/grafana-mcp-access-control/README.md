# Grafana MCP access control for kagent

Use this guide to give kagent agents only the Grafana MCP capabilities they
need. It is a deployment pattern, not proof that a particular Grafana instance,
MCP release, datasource, or kagent `RemoteMCPServer` is already installed.

For the home-lab installation and smoke path, see
[`../grafana-mcp-home-lab.md`](../grafana-mcp-home-lab.md).

## The boundary model

Apply all three boundaries. No single one replaces the others.

| Boundary | Control | Purpose |
| --- | --- | --- |
| Agent | kagent `mcpServer.toolNames` | Prevent an agent from being offered unnecessary MCP tools. |
| MCP server | `--enabled-tools` and write-tool disablement | Prevent the MCP endpoint from exposing unnecessary tools to any client. |
| Grafana API | Dedicated service account, role/RBAC permissions, and scopes | Enforce what the MCP server can actually read or change. |

The Grafana API boundary is authoritative. An agent that is accidentally given a
write tool still cannot write if its Grafana service account lacks the required
permission. Conversely, hiding a tool from an agent is useful defence in depth,
but it does not reduce the permissions of a broad Grafana token.

## Tokens, service accounts, and tools

A Grafana service-account token inherits the permissions of its service account.
Creating multiple tokens for **one** service account helps rotation and audit,
but does **not** create different access levels. To separate capabilities,
create separate service accounts and tokens, then run separate Grafana MCP
endpoints (and normally separate kagent `RemoteMCPServer` resources).

```text
triage agent
  -> RemoteMCPServer/grafana-triage-readonly
  -> Grafana MCP endpoint with token for service account: kagent-grafana-triage
  -> query-only access to approved Loki and Prometheus/Mimir datasources

dashboard workflow
  -> RemoteMCPServer/grafana-dashboard-maintenance
  -> separate MCP endpoint with token for service account: kagent-grafana-dashboard-writer
  -> narrowly approved dashboard write access, invoked only through HITL
```

Do not point normal triage agents at the write-capable endpoint.

## Recommended profiles

| Profile | Grafana service account | MCP tools exposed | Grafana access |
| --- | --- | --- | --- |
| Triage evidence | `kagent-grafana-triage` | Datasource discovery, PromQL/LogQL query, dashboard summary/search, deeplinks | Query only approved Prometheus/Mimir and Loki datasource UIDs; read only named dashboards/folders if needed. |
| Alert evidence | `kagent-grafana-alert-read` | Triage tools plus alert inspection, where the installed MCP release supports it | Read-only alerting scopes; no contact-point or rule mutation. |
| Dashboard maintenance | `kagent-grafana-dashboard-writer` | Only the dashboard tools required for a reviewed change | Dashboard/folder write access limited to the approved folder/dashboard scope. Use only behind approval/GitOps workflow. |
| Incident/remediation | `kagent-grafana-incident-writer` | Only the explicitly approved incident, annotation, or alert-write tools | Separate account and approval workflow. Never share with routine triage. |

The exact tool names vary by installed Grafana MCP release. Discover the live
tool list from the `RemoteMCPServer` before putting names in an Agent CR, and
enable the smallest compatible subset.

## Read-only triage baseline

For an evidence agent, start with a dedicated Grafana service account that can
query only the approved telemetry datasources. In Grafana Enterprise, use the
`None` basic role plus granular RBAC scopes; for example:

```text
datasources:query  -> datasources:uid:{{PROMETHEUS_DATASOURCE_UID}}
datasources:query  -> datasources:uid:{{LOKI_DATASOURCE_UID}}
datasources:read   -> datasources:uid:{{PROMETHEUS_DATASOURCE_UID}}
datasources:read   -> datasources:uid:{{LOKI_DATASOURCE_UID}}
dashboards:read    -> dashboards:uid:{{TRIAGE_DASHBOARD_UID}}
```

Use only the installed, read-safe MCP tool names in the Agent. A representative
kagent binding looks like this:

```yaml
tools:
  - type: McpServer
    mcpServer:
      apiGroup: kagent.dev
      kind: RemoteMCPServer
      name: grafana-triage-readonly
      toolNames:
        - list_datasources
        - search_dashboards
        - get_dashboard_summary
        - query_prometheus
        - query_loki_logs
        - generate_deeplink
```

Do not include dashboard, annotation, incident, alert-rule, contact-point,
plugin, or folder write tools in this profile. If Grafana Enterprise RBAC is
not available, use the narrowest available built-in role and compensate with a
separate read-only MCP endpoint and a smaller enabled-tool set; do not label a
broad Editor token as read-only.

## Credential delivery and rotation

Use `GRAFANA_SERVICE_ACCOUNT_TOKEN`, not the deprecated `GRAFANA_API_KEY`.
For Kubernetes, prefer `GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE` with a read-only
mounted Secret: the Grafana MCP server re-reads the file and can take a rotated
token without a pod restart.

An AKS workload identity or UAMI can retrieve that Secret from Azure Key Vault
through the approved secrets-delivery mechanism. That removes the token from
manifests and gives Azure a workload-identity audit boundary, but it does not
replace the Grafana service-account token used by the local Grafana MCP server.

Grafana Cloud's hosted MCP uses user-scoped OAuth; it is a different deployment
model. Do not assume a headless kagent service can use that browser consent flow
without validating the client and OAuth integration first.

## Verify each boundary

Before wiring an agent:

1. Verify the target `RemoteMCPServer` is accepted and list its discovered tools.
2. Verify the MCP Deployment has only the intended enabled tools and no write categories.
3. Use the service-account token's Grafana permissions endpoint to inspect effective permissions and scopes.
4. Run a read-only query against each approved datasource and a negative test against an unapproved datasource or write operation.
5. Record the service-account name, tool list, datasource UIDs, and test outcome in change evidence. Never record the token.

```bash
kubectl --context {{KUBE_CONTEXT}} -n {{KAGENT_NAMESPACE}} \
  get remotemcpserver grafana-triage-readonly \
  -o jsonpath='{range .status.discoveredTools[*]}{.name}{"\n"}{end}' | sort

# Run from an approved secure environment. The secure curl config supplies the
# authorization header; do not paste the token into shell history or manifests.
curl -sS --config {{SECURE_CURL_CONFIG_PATH}} \
  'https://{{GRAFANA_HOST}}/api/access-control/user/permissions'
```

## Source documentation

- [Grafana MCP tool permissions and scopes](https://grafana.com/docs/grafana/latest/developer-resources/mcp/reference/mcp-tools-table/)
- [Grafana MCP authentication and token-file rotation](https://grafana.com/docs/grafana/latest/developer-resources/mcp/configure/authentication/)
- [Grafana service accounts and effective-permission inspection](https://grafana.com/docs/grafana/latest/administration/service-accounts/)
- [Grafana Cloud hosted MCP OAuth model](https://grafana.com/docs/grafana-cloud/machine-learning/assistant/configure/cloud-mcp/)

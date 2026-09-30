# Denodo FastMCP with AKS UAMI

This is a sanitized, lift-and-shift reference adapter for the same MCP shape as
the PostgreSQL UAMI bundle. It is **not** a JDBC URL change to the PostgreSQL
adapter: Denodo VDP requires its own JDBC driver and approved Denodo views.
The public tools are three bounded, read-only operations over a synthetic
namespace-inventory view. Replace the example view contract with the exact
data-owner-approved workplace view and fields before use.

For a private work-agent run, start with
[`WORK-AGENT-START-HERE.md`](WORK-AGENT-START-HERE.md).

## Architecture

```text
kagent -> Agent Gateway -> FastMCP /mcp -> Denodo JDBC driver -> TLS DVP:9999
                                 |              ^
                                 +-> AKS Workload Identity -> UAMI -> Entra
                                      scope: {{DVP_RESOURCE_APP_ID}}/.default
```

The `AZURE_CLIENT_ID` is the caller UAMI's client ID. `DENODO_RESOURCE_APP_ID`
is the DVP *audience*, not that UAMI. On AKS, the Workload Identity webhook
injects `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and
`AZURE_FEDERATED_TOKEN_FILE` for the annotated ServiceAccount. The adapter
requests a valid access token when opening each JDBC connection and supplies it as the
driver property `accessToken` with `useOAuth2=true`. No token is put in a JDBC
URL, ConfigMap, Secret, argument, or log. The alternate
`DENODO_IDENTITY_MODE=managed_identity` uses the same UAMI client ID through
the Azure managed-identity endpoint on a host that actually has that UAMI.
It does not make a home-lab machine into an Azure managed-identity host.

## Configuration

| Variable | Meaning |
|---|---|
| `DENODO_HOST`, `DENODO_PORT`, `DENODO_DATABASE` | Private VDP host, port (default 9999), and virtual database |
| `DENODO_RESOURCE_APP_ID` | DVP environment resource/audience app ID; scope is formed as `<value>/.default` |
| `AZURE_CLIENT_ID` | UAMI client ID, injected by AKS webhook or set on an Azure managed-identity host |
| `DENODO_APPROVED_VIEW` | One lower-case approved Denodo view name, default none |
| `DENODO_JDBC_JAR` | Private, matching Denodo JDBC JAR path; default `/opt/denodo/denodo-vdp-jdbcdriver.jar` |
| `DENODO_IDENTITY_MODE` | `workload_identity` (default) or `managed_identity` |
| `DENODO_QUERY_TIMEOUT_SECONDS` | Default 5, maximum 30 |
| `MCP_MAX_ROWS`, `MCP_MAX_RESPONSE_BYTES`, `MCP_MAX_CELL_CHARS` | Default 50, 32 KiB, 512; hard ceilings 100, 64 KiB, 2048 |

The JDBC connection sets `ssl=true` and
`sslTrustServerCertificate=false`. Supply the private CA through the JVM
truststore in the approved work image if needed; do not disable validation.
The driver JAR version must match the DVP server version/update. The public
image deliberately omits the proprietary JAR. Build the derived image with
`deploy/Dockerfile.with-driver` in approved private CI using an immutable base
digest and a privately delivered matching driver. Never commit the JAR.

Example private build inputs (run inside approved CI, not in this public tree):

```sh
# Private build context contains only denodo-vdp-jdbcdriver.jar.
docker build --build-arg BASE_IMAGE={{APPROVED_BASE_IMAGE_DIGEST}} \
  -f deploy/Dockerfile.with-driver \
  -t {{PRIVATE_DENODO_IMAGE_TAG}} {{PRIVATE_DRIVER_BUILD_CONTEXT}}
```

Render both manifests into a private directory after filling every value:

```sh
python3 deploy/render.py deploy/aks-workload-identity.yaml.template \
  {{PRIVATE_VALUES_FILE}} {{PRIVATE_RENDER_DIR}}/aks.rendered.yaml
python3 deploy/render.py deploy/agentgateway-kagent.yaml.template \
  {{PRIVATE_VALUES_FILE}} {{PRIVATE_RENDER_DIR}}/gateway.rendered.yaml
```

## Home-lab contract test

The home lab lacks a Denodo installation, a Denodo JDBC JAR, and an Azure UAMI
endpoint. `tests/src/.../Driver.java` is a synthetic JDBC driver with the same
class name. It rejects incorrect OAuth/TLS properties, a missing read-only
setting, unbounded query settings, and queries outside the example contract.
The tests patch token acquisition with `lab-token`; they do **not** mint or
validate a real Entra token. The fixture JAR is generated and ignored.

```sh
cd {{KAGENT_PUBLIC_REPO}}
work-agent-bundles/denodo-fastmcp-uami/tests/run-lab.sh
```

The test confirms the actual container JVM can load and call the JDBC driver
interface through JPype, the private-driver-image build pattern works, the
three MCP tools are registered, and the sample queries return through the
bounded result envelope. It also calls the running Streamable HTTP MCP server
through the container network. It does not prove a real Denodo server, network
path, CA, grants, or token acceptance.

## Workplace adaptation and proof order

1. Inspect the **deployed** workplace MCP, Agent, Gateway, tool contracts, and
   rollback digest. Port the adapter and approved query delta onto those
   objects; do not apply this bundle wholesale over a running service.
2. Confirm DVP version, matching JDBC driver, TLS trust chain, reachable private
   hostname/port, virtual database, approved views/columns, VQL compatibility,
   and DVP authentication configuration. The provided `jdbc:denodo` URL is a
   VDP endpoint, not a PostgreSQL DSN.
3. Confirm the UAMI's federated credential matches the actual AKS issuer and
   ServiceAccount subject. Confirm its DVP application role/permission and
   Denodo-side identity mapping. `resource=<app ID>` in an IMDS sample maps to
   `<app ID>/.default` in this AKS workload-identity code.
4. Build the private driver image, scan/sign/push it through approved CI, and
   pin a digest. Render `deploy/aks-workload-identity.yaml.template` privately
   with `deploy/render.py` and a private `work-values.env` derived from the
   template. Check placeholders, public safety, installed CRD versions, and
   server-side dry-run before deployment. Keep environment values out of this
   public repo.
5. In the canary Pod, prove token acquisition for the DVP audience with
   `python /app/verify_live.py`: it prints markers only (never the token,
   identities, URL, or rows) for token audience match, TLS/JDBC `SELECT 1`, the
   approved view, and a fresh connection. Separately have the DVP owner prove
   denial of an unapproved view/write operation. Check response truncation and
   timeout behavior.
6. Preserve workplace Gateway/Agent names and policies. Adapt
   `deploy/agentgateway-kagent.yaml.template` only after the direct adapter
   checks pass. Verify MCP tool discovery, the Gateway route, and one sanitized
   kagent A2A question; compare the complete MCP envelope and model-input
   token metrics against the previous baseline. Roll back to the recorded
   image/manifest if any gate fails.

The workplace still needs a **real** DVP/UAMI canary. The home-lab fixture is
evidence for the integration code and boundaries, not authentication success.

## Primary references

- Denodo OAuth JDBC: https://community.denodo.com/docs/html/browse/9.5/en/vdp/developer/access_through_jdbc/connecting_to_virtual_dataport_using_oauth_authentication/connecting_to_virtual_dataport_using_oauth_authentication
- Denodo JDBC driver and version matching: https://community.denodo.com/docs/html/browse/8.0/en/vdp/developer/access_through_jdbc/access_through_jdbc
- Denodo JDBC TLS options: https://community.denodo.com/docs/html/document/9.2/en/vdp/developer/access_through_jdbc/parameters_of_the_jdbc_connection_url/parameters_of_the_jdbc_connection_url
- AKS workload identity scope: https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview

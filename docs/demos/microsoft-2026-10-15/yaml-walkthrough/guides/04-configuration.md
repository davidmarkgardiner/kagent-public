# Configuration and prerequisites

## Values to resolve privately

The complete placeholder inventory used in the numbered YAML and Graph payload is:

- `{{A2A_API_CLIENT_ID}}`
- `{{AKS_OIDC_ISSUER}}`
- `{{BLUEPRINT_CLIENT_ID}}`
- `{{CALLER_UAMI_CLIENT_ID}}`
- `{{CALLER_UAMI_PRINCIPAL_ID}}`
- `{{CHILD_AGENT_ID}}`
- `{{ENTRA_TENANT_ID}}`
- `{{MCP_API_CLIENT_ID}}`
- `{{MCP_GATEWAY_HOST}}`
- `{{MODEL_DEPLOYMENT}}`
- `{{MODEL_GATEWAY_HOST}}`
- `{{PROMETHEUS_RELEASE}}`
- `{{SKILLS_COMMIT}}`
- `{{SKILLS_REPOSITORY_URL}}`

Secrets referenced by name are also prerequisites: `skills-git-auth`, `model-gateway-auth` and `agent-mcp-runtime-token`. The last contains the privately populated `authorization` header value. Do not commit credentials. A durable, tested refresh/reload path is required before calling this an unattended integration.

## Existing platform components

- Namespaces `team-sre`, `specialists`, `team-tools`, `platform-gateway`, `kagent`, and their platform-controlled identity/trust labels.
- Compatible kagent CRDs/runtime, with the v1alpha2 skill and Secret-header fields used here.
- Compatible agentgateway controller, CRDs and proxy, including Require semantics and telemetry fields. The local source schema used for review is upstream checkout `4ae9c32`.
- An HTTPS `agent-gateway` Gateway with `mcp` and `a2a` listeners and reviewed route attachment/TLS. File 08 illustrates named invocation routing, not a complete agent discovery/streaming API. Verify controller Service name/port and supported A2A path on the installed release.
- An existing approved model-garden route/backend matching file 05 and policy targets in 15/16.
- The Kubernetes MCP service on port 8080 in `team-tools`, least-privilege resource RBAC and bounded operations.
- ModelConfig/model-garden and approved specialist tools in `specialists`; the data/Kubernetes specialists referenced by file 04.
- OTel collector Service in `platform-gateway` and an approved logging/tracing store.
- Prometheus Operator, monitor selectors/release label, native proxy metrics port/labels and a separate evaluator metrics publisher.
- Enforcing CNI, platform/destination controls and a review of all additive NetworkPolicies.

Numbering is the presentation order. Platform dependencies and private identity approval determine deployment order. The root Kustomization renders only the first Agent plus its two patches; it intentionally excludes the rest of the walkthrough.

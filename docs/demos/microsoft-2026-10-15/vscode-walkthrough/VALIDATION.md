# Validation and proof limits

Prepared on 14 October 2026 for the Microsoft walkthrough.

## What was checked

- All 20 numbered YAML files parse, alongside the local Kustomization and assembled reference.
- `kubectl kustomize .` renders one Agent. Its parsed result exactly matches `reference/assembled-agent.yaml`, including the selected skills and three read tools.
- Twelve complete Agent/ModelConfig/RemoteMCPServer/AgentgatewayBackend/AgentgatewayPolicy objects pass local CRD shape validation, including undeclared spec-field detection. Gateway schema source is sibling upstream checkout `4ae9c32`; kagent uses the local vendored v1alpha2 CRDs. The two partial Agent patches are checked through the local render, not incorrectly treated as complete resources.
- The evaluation case passes the repository's JSON schema. Other Kubernetes/Gateway API/Prometheus objects were parsed and inspected against existing source patterns. No API-server admission, CRD CEL validation, Entra token acquisition or live authorization probes were run.
- Every numbered YAML file contains presenter SAY and POINT TO comments. Local Markdown links and the workspace's relative folder paths resolve.
- The nine PDF pages were rendered back to PNG and visually reviewed. They show only the selected visual scenes; none is a YAML/code slide. Individual slide PNGs are included at 3840 x 2160 for native VS Code preview.
- Gitleaks reports no leaks. detect-secrets reports only two reviewed Secret-reference field names in file 05, not credential values. The strict public-safety scan passes. No credentials, private endpoints or real identity identifiers are included. Binary slide assets contain only the same reviewed public-safe visual content recorded in `slides/manifest.json`.

## What this package does not establish

This is a presentation and adaptation pack, not a complete platform installation or a freshly rehearsed tenant/cluster. Gateway/listeners, model routing, backend services, data grants, actual specialist tools and private identity provisioning are prerequisites. Identity acquisition, automatic token refresh/client reload, effective policy attachment, installed-version compatibility, negative tests and telemetry labels still need the target environment.

The minimal Grafana Agent illustrates destination namespace admission; its actual Grafana tool integration is deliberately a prerequisite. Native Agent-as-tool traffic needs explicit gateway/proxy routing before it can be described as gateway-enforced A2A. A direct controller port-forward demonstration does not prove gateway enforcement.

The PDF and PNGs are static visual aids. They neither invoke agents nor play the optional narrated chapters. The original interactive deck and its media were left in place.

# Microsoft agent journey: VS Code walkthrough

Open [Microsoft-agent-journey.code-workspace](Microsoft-agent-journey.code-workspace) in VS Code. Start with [00-START-HERE.md](00-START-HERE.md), then click the numbered YAML files in order. Each file begins with SAY, POINT TO and BOUNDARY comments that serve as presenter notes.

The [visual-only PDF](slides/visual-slides.pdf) and individual [slide images](slides/README.md) are in the same folder. The PDF contains no YAML/code slides. The existing HyperFrames presentation remains in its original location and is unchanged.

These sanitized configuration examples use kagent v1alpha2 and agentgateway v1alpha1. They are a walkthrough of the components, not a standalone platform install. Environment values remain `{{PLACEHOLDER}}` values. Files 02/03 are patches; file 20 is local scorer input. Do not apply the whole directory as a Kubernetes bundle.

## Click-through order

| File | Speaking point |
| --- | --- |
| [01-agent.yaml](01-agent.yaml) | Load the Agent resource. |
| [02-agent-skills.patch.yaml](02-agent-skills.patch.yaml) | Load reviewed skill files into that Agent. |
| [03-agent-tools.patch.yaml](03-agent-tools.patch.yaml) | Attach the MCP connection and select read tools. |
| [04-a2a-orchestrator.yaml](04-a2a-orchestrator.yaml) | Attach specialist agents to the SRE chatbot through A2A. |
| [05-model-garden.yaml](05-model-garden.yaml) | Connect ModelConfig to the gateway model route. |
| [06-remote-mcp.yaml](06-remote-mcp.yaml) | Register the authenticated gateway-facing MCP endpoint. |
| [07-mcp-backend.yaml](07-mcp-backend.yaml) | Connect the gateway to the approved MCP service. |
| [08-http-routes.yaml](08-http-routes.yaml) | Route MCP and named SRE-chat invocations. |
| [09-reference-grants.yaml](09-reference-grants.yaml) | Permit the exact cross-namespace backend references. |
| [10-entra-jwks.yaml](10-entra-jwks.yaml) | Use trusted Microsoft signing keys over TLS. |
| [11-blueprint-token-holder.yaml](11-blueprint-token-holder.yaml) | Bind the token holder to its Entra Agent ID blueprint. |
| [12-application-to-agent-policy.yaml](12-application-to-agent-policy.yaml) | Authorize one application to invoke the SRE agent. |
| [13-agent-to-mcp-policy.yaml](13-agent-to-mcp-policy.yaml) | Authorize the exact child Agent ID, MCP API role and tools. |
| [14-mcp-network-boundary.yaml](14-mcp-network-boundary.yaml) | Restrict destination ingress to the gateway. |
| [15-model-traffic-limits.yaml](15-model-traffic-limits.yaml) | Apply model traffic/time/token limits. |
| [16-model-content-guards.yaml](16-model-content-guards.yaml) | Reject or mask selected data patterns. |
| [17-gateway-observability.yaml](17-gateway-observability.yaml) | Record verified identities and export traces. |
| [18-gateway-podmonitor.yaml](18-gateway-podmonitor.yaml) | Scrape native gateway metrics. |
| [19-gateway-alerts.yaml](19-gateway-alerts.yaml) | Alert on denial activity, errors, usage and eval failures. |
| [20-agent-evaluation-case.yaml](20-agent-evaluation-case.yaml) | Evaluate captured agent behavior and safety gates. |

## Assemble the Agent locally

The first three files produce one Agent. This command only renders local files:

```sh
kubectl kustomize .
```

The result is also included in [reference/assembled-agent.yaml](reference/assembled-agent.yaml). The A2A orchestrator in file 04 is a separate Agent, and its minimal Grafana destination is a second YAML document separated by `---`. The other named specialists, model configuration in the destination namespace and real Grafana tools are prerequisites.

The patch in file 02 points at this repository's included [skill](skills/sre-triage/SKILL.md), using the full path within the repository. Set the repository URL and immutable commit privately when adapting it.

## Explanations and optional demo

- [Entra Agent ID and blueprint setup](guides/01-entra-agent-blueprint-setup.md).
- [Gateway controls, telemetry and evaluation](guides/02-gateway-security-monitoring-evaluation.md).
- [Optional SRE orchestration demonstration](guides/03-sre-orchestration-demo.md).
- [Configuration values and prerequisites](guides/04-configuration.md).
- [Validation and proof limits](VALIDATION.md).

The workspace uses relative paths and works after cloning the GitHub branch. No VS Code extensions are required for YAML, Markdown or PNG slides. PDF preview support depends on your installed extensions; the PNGs provide the same pages with VS Code's built-in image viewer.

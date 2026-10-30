# Microsoft meeting, 15 October 2026

For an incoming team bringing its own LLM, MCP server, or API, use the
[10-minute gateway onboarding walkthrough](../../../work-agent-bundles/agentgateway-application-onboarding/04-BYO-INTEGRATIONS-WALKTHROUGH.md).
It reuses the annotated YAML and connects backend onboarding to agent isolation.

Start with the [VS Code presentation guide](meeting-walkthrough/vscode-presentation/README.md). It opens the annotated YAML on the left and the clickable visual presentation on the right. The Markdown companion contains the same diagrams and expandable commented source.

The 14-slide route covers agent configuration, MCP and A2A, knowledge retrieval, Microsoft Entra identity, agentgateway policies, LGTM monitoring, evaluation, triage, delivery workflows, the durable-agent PoC and SRE Lens. Only the existing gateway UI and SRE Lens use Chrome.

The [original YAML walkthrough](yaml-walkthrough/README.md) remains the configuration source. The [presentation design](meeting-walkthrough/vscode-presentation/DESIGN.md) records the company palette. The [validation receipt](meeting-walkthrough/vscode-presentation/VALIDATION.md) separates local presentation proof from live service proof.

Use `Open-in-VS-Code.command` from the presentation folder. A local PDF can be generated with `build.py --pdf`; binaries and private application URLs are excluded from Git.

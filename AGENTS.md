# kagent-public Agent Context

## What This Repo Is

This is a public/sanitized replica of platform engineering work used to develop and rehearse patterns before they are applied in a private work environment. Treat it as a working monorepo for AKS platform modernization, not as an upstream fork of any one project.

Primary themes:

- Declarative AKS fleet lifecycle with KRO ResourceGraphDefinitions and Azure Service Operator resources.
- GitOps-first delivery with Flux as the reconciliation plane.
- Argo Workflows and Argo Events for onboarding, provisioning, fleet operations, and SRE workflows.
- kagent agents for AI-assisted triage, remediation planning, and agentic platform workflows.
- agentgateway for LLM, MCP, and A2A traffic routing between kagent, tools, and model providers.
- AKS-MCP as a tool bridge for Kubernetes and Azure AKS operations.

Do not add secrets, private hostnames, private cluster IPs, subscription IDs, tenant IDs, internal URLs, or real tokens. Use `{{PLACEHOLDER}}` values for environment-specific details.

## First Files To Read

- `README.md` for repository layout and quick navigation.
- `STATEMENT-OF-WORK.md` for the target architecture and six-month delivery shape.
- `CONTRIBUTING.md` for public-safety rules.
- `docs/upstreams.md` for official upstream repositories and local clone paths.
- `CLAUDE.md` only when you are operating in the user's local Claude/Symphony workflow. It contains local execution notes and should not be treated as portable public documentation unless sanitized.

## Important Local Areas

- `infra/kro-stack/` contains KRO definitions and AKS provisioning patterns. Apply instances only to a management cluster with KRO and ASO installed.
- `infra/workload-identity/` contains workload identity automation examples.
- `infra/byo-kagent/` contains Bring Your Own kagent onboarding, tool catalog, grants, and Kyverno policy examples.
- `platform/agentgateway/` contains the agentgateway deployment, backend, policy, monitoring, and kagent ModelConfig manifests.
- `platform/aks-mcp/` contains deployment manifests for AKS-MCP.
- `platform/argo-workflows/` and `platform/argo-events/` contain orchestration and eventing templates.
- `agents/` contains kagent Agent CRs, triage patterns, and agent-specific docs.
- `observability/` contains LGTM, Alertmanager, EventHub, and kagent/agentgateway observability patterns.
- `a2a/` contains A2A protocol notes and call examples.

## Official Upstreams

Prefer the official upstream repository or docs over copied examples when behavior is unclear:

- AKS: `https://github.com/Azure/AKS`
- AKS-MCP: `https://github.com/Azure/aks-mcp`
- Azure Service Operator: `https://github.com/Azure/azure-service-operator`
- KRO: `https://github.com/kubernetes-sigs/kro`
- kagent: `https://github.com/kagent-dev/kagent`
- agentgateway: `https://github.com/agentgateway/agentgateway`

Local sibling clones may exist next to this repo:

- `../AKS`
- `../aks-mcp`
- `../azure-service-operator`
- `../kro`
- `../kagent`
- `../agentgateway`

If a sibling clone is missing, use a shallow clone unless history is needed:

```bash
git clone --depth 1 https://github.com/<org>/<repo>.git ../<repo>
```

## Working Rules

- Preserve user work. This repo can have untracked local handover files; do not remove or rewrite them unless asked.
- Keep public manifests sanitized. Replace private values with explicit placeholders.
- Prefer deterministic GitOps/Argo/KRO/ASO flows over ad hoc `kubectl` instructions for permanent changes.
- For agent permissions, separate chat/agent front doors from execution permissions. Agents should submit workflows; workflow service accounts should hold the resource-changing permissions.
- For kagent tools, distinguish read-only agents from write-capable agents. Read-only agents should not include apply/delete tools.
- For agentgateway changes, validate CRD schema and runtime behavior against the installed version before assuming examples from older docs still apply.
- For ASO changes, verify the exact CRD API version and reconcile/adoption behavior in the upstream ASO docs before changing lifecycle manifests.
- For KRO changes, validate ResourceGraphDefinition schema and CEL expressions against the KRO version in use.

## Common Validation

Use the narrowest validation that proves the change:

- YAML/Kubernetes manifests: `kubectl apply --dry-run=server` against the target cluster when a compatible cluster is available.
- Kustomize overlays: `kubectl kustomize <dir>` or `kustomize build <dir>`.
- Helm charts: `helm template` and, when available, `helm lint`.
- JSON schemas: validate sample payloads against the schema in the same directory.
- Docs-only changes: check links and keep examples placeholder-safe.


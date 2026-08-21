# Write-up: Issue #83 research report — Kubernetes MCP Server vs AKS-MCP

Base: `99a38ef` · 2 new files · +433 −0 · docs-only, no code or manifests touched.

## What changed and why it matters

This change delivers issue #83 as a source-backed, documentation-only research report comparing `containers/kubernetes-mcp-server` (pinned `3b7a4da9…`) against `Azure/aks-mcp` (pinned `8d28bec…`), with every upstream claim linked to a commit-pinned primary source and every local claim tied to the permitted repository areas (`platform/aks-mcp/`, `platform/agentgateway/`, `infra/workload-identity/`, `agents/`).

The report's headline findings:

- **Recommendation: complement — do not replace.** Kubernetes MCP Server may be adopted, at most, as a bounded non-production read-only Kubernetes inspection server serving a named `kubernetes-readonly-triage` role, and only after five POC evidence gates pass. It has no Azure ARM/AKS surface, so AKS-MCP keeps the Azure control-plane role and no current tool is removed.
- **Current upstream AKS-MCP is stdio-only, single-trusted-user.** Upstream explicitly forbids HTTP/SSE/container/Helm/proxy/gateway exposure. The repository's in-cluster, streamable-HTTP `platform/aks-mcp/` chart is therefore flagged as a **repository-local pattern on an older upstream release** — not current upstream-supported architecture, and not to be extended without explicit risk acceptance.
- **Four identity paths are kept distinct** (Kubernetes ServiceAccount + Kubernetes RBAC; Azure UAMI / Entra Workload Identity for Azure APIs; kubeconfig/kubelogin as an alternate Kubernetes credential path; client OIDC to the MCP server itself), with the key rule repeated: MCP tool hints and allowlists are not Kubernetes RBAC — the ServiceAccount's Role decides what a call actually does.
- **Bounded POC design, no execution:** one non-production namespace, one question ("identify a failing pod + Warning events, no mutation"), a namespace-scoped Role with only `get`/`list` on pods/events/workloads plus `pods/log`, exactly four enabled tools (`pods_list_in_namespace`, `pods_get`, `pods_log`, `events_list`), denied-resources covering Secret/ConfigMap/ServiceAccount/RBAC kinds, Agent Gateway strict JWT/OIDC + CEL tool-filter policy behind a per-cluster CRD schema gate, and five evidence gates (identity proof, tool inventory, RBAC-denial, bounded A2A invocation via `scripts/kagent-a2a-invoke.sh`, allow+deny telemetry) with stop conditions and an ordered cleanup.

Why it matters: it is the decision record for whether a second MCP server enters the platform, and it pins the upstream security-boundary facts (AKS-MCP identity inheritance; candidate's expansive `core`+`config` defaults, all-interfaces bind, best-effort log redaction) that any future POC must work around.

## Files that carry it

- `docs/research/kubernetes-mcp-server-vs-aks-mcp.md` (340 lines, new) — the deliverable. Contains exactly the six required H2 headings in order: Executive recommendation; Capability comparison; Authentication and authorization; Safety and governance; Bounded POC design; Sources. Includes a three-way comparison table (candidate / current upstream AKS-MCP / local chart pattern), a "defaults that must be overridden" callout, a four-row auth-path table, a complete TOML POC configuration block, and two source tables (official primary upstream; checked-out repository evidence) where each entry states what assertion it supports.
- `specs/0a433c20-da75-4c61-b21c-9a52afcf8ff0_kubernetes-mcp-aks-comparison.md` (93 lines, new) — the plan/spec for the work item: baseline (`99a38ef`), scope fences (no kubectl, no cluster, no deploys/credentials/RBAC changes, no DeepSeek/OpenRouter, no merge), the required heading/heading-order and citation-provenance constraints, and the verification/review/PR sequence.

No other files were modified. All platform/agent file paths appearing in the report (`platform/aks-mcp/*`, `platform/agentgateway/*`, `infra/workload-identity/README.md`, `infra/byo-kagent/bootstrap-catalog/toolcatalogentry-aks-mcp.yaml`, `agents/skills/responsible-kagent-operation/assets/responsible-readonly-triage-agent.yaml`) are citations, not changes. Environment-specific values are placeholders (`{{POC_NAMESPACE}}`, `{{MCP_NAMESPACE}}`, `{{MCP_SERVER_PORT}}`).

## How to use or verify it

Read `docs/research/kubernetes-mcp-server-vs-aks-mcp.md` top-to-bottom; the recommendation and its conditions are in the first section, and any future POC change should start from the "Bounded POC design" section verbatim — it is design-only and adds no manifests.

Verification, matching the spec's own gates and the repo's docs-only rule (check links, keep placeholders):

- Headings: confirm each of the six required H2s appears exactly once, in order:
  `grep -n '^## ' docs/research/kubernetes-mcp-server-vs-aks-mcp.md`
- Public safety: `scripts/public-safe-scan.sh --strict docs/research/kubernetes-mcp-server-vs-aks-mcp.md` (exit 0 expected).
- Diff hygiene: `git diff 99a38ef --stat` should show only the two new files above; `git diff --check` clean.
- Spot-check one commit-pinned upstream link (e.g. the `Azure/aks-mcp` README link at `8d28bec…`) and one repository citation (e.g. `platform/aks-mcp/chart/values.yaml`) to confirm the report's claims trace to their cited sources.

# Platform Knowledge Base Index

This index is the first stop for the platform knowledge-base agent. It maps user questions to the smallest useful set of source documents.

## AKS Application Team Guidance

| User intent | Primary document | Notes |
|---|---|---|
| Secure a workload pod | `docs/platform-kb/aks/pod-security.md` | Security context, capabilities, resource limits, network policy, image hygiene |
| Mount application certificates | `docs/platform-kb/aks/application-certificates.md` | Runtime certificate mounts, node certificate boundary, Secret/ConfigMap/Key Vault CSI patterns |
| Bring a custom domain | `docs/platform-kb/aks/custom-domains.md` | DNS, ingress host binding, TLS, validation |
| Understand AKS node auto-provisioning | `docs/platform-kb/aks/node-auto-provisioning.md` | NAP/Karpenter overview, app-team contract, platform GitOps operating model, pilot checklist |
| Survive planned maintenance | `docs/platform-kb/aks/pod-disruption-budgets.md` | Replica assumptions, PDB examples, drain validation |
| Know what teams can deploy | `docs/platform-kb/aks/shared-aks-resources.md` | Namespaced resources, platform-owned resources, exception path |

## Platform Agent Guidance

| User intent | Primary document | Notes |
|---|---|---|
| Understand this POC | `docs/platform-kb/platform/kagent-docs-rag.md` | doc2vec, querydoc MCP, kagent Agent wiring, stale-doc feedback split |

## Kagent Triage V2 Agent Guidance

| User intent | Primary document | Notes |
|---|---|---|
| Understand Kagent triage v2 | `docs/platform-kb/agents/kagent-triage-v2-overview.md` | Agent roles, safety rules, evidence requirements |
| Update KB docs through GitLab MCP | `docs/platform-kb/agents/gitlab-mcp-kb-update-loop.md` | Branch, file update, MR, index update, querydoc proof markers |
| Query the platform KB through querydoc | `docs/platform-kb/agents/querydoc-knowledge-agent.md` | Runtime path, query contract, cited-hit and no-docs checks |
| Use KB lookup during incident triage | `docs/platform-kb/agents/triage-agent-kb-lookup.md` | When to call the knowledge agent and how to report citations |

## Answering Rules

The knowledge-base agent must:

1. Use the documentation lookup tool before answering platform documentation questions.
2. Prefer the most specific document listed in this index.
3. Cite source paths and headings.
4. Say when the docs do not answer the question.
5. Route stale or missing documentation feedback to the approved docs PR workflow instead of mutating Git directly from the chat agent.

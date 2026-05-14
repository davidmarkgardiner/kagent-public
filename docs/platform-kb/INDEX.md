# Platform Knowledge Base Index

This index is the first stop for the platform knowledge-base agent. It maps user questions to the smallest useful set of source documents.

## AKS Application Team Guidance

| User intent | Primary document | Notes |
|---|---|---|
| Secure a workload pod | `docs/platform-kb/aks/pod-security.md` | Security context, capabilities, resource limits, network policy, image hygiene |
| Bring a custom domain | `docs/platform-kb/aks/custom-domains.md` | DNS, ingress host binding, TLS, validation |
| Survive planned maintenance | `docs/platform-kb/aks/pod-disruption-budgets.md` | Replica assumptions, PDB examples, drain validation |
| Know what teams can deploy | `docs/platform-kb/aks/shared-aks-resources.md` | Namespaced resources, platform-owned resources, exception path |

## Platform Agent Guidance

| User intent | Primary document | Notes |
|---|---|---|
| Understand this POC | `docs/platform-kb/platform/kagent-docs-rag.md` | doc2vec, querydoc MCP, kagent Agent wiring, stale-doc feedback split |

## Answering Rules

The knowledge-base agent must:

1. Use the documentation lookup tool before answering platform documentation questions.
2. Prefer the most specific document listed in this index.
3. Cite source paths and headings.
4. Say when the docs do not answer the question.
5. Route stale or missing documentation feedback to the approved docs PR workflow instead of mutating Git directly from the chat agent.


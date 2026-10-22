# Cluster security review Agent

The Agent uses three local Kubernetes inspection tools to review cluster-wide
configuration and every namespace whose name does not begin with `at`, including
system namespaces. Findings require actual tool evidence and every included
namespace has a coverage ledger. Scanner execution and unverified checks are
reported as gaps.

Use the self-contained [work bundle](../../work-agent-bundles/cluster-security-review/README.md)
for deployment, adaptation validation, readiness checks and invocation. Its
[work-agent start prompt](../../work-agent-bundles/cluster-security-review/WORK-AGENT-START-PROMPT.md)
is the handoff entry point. The bundle includes hardened operator helpers and
regression fixtures that are specific to this review path.

`agent.yaml`, `kustomization.yaml` and `scan-prompt.txt` are source snapshots. Keep
their bundle copies in sync. The shared MCP backend controls actual permissions;
namespace exclusion and response redaction are prompt rules unless the backend
enforces them. No workplace deployment or live scan is claimed by this source.

# Chaos Test Manager Configuration

This file lists the environment-specific values needed before the skeleton can
run against a real lower-environment cluster. Keep public examples sanitized;
replace placeholders only in private environment overlays or secret stores.

## Required Placeholders

| Placeholder | Purpose |
|---|---|
| `{{KUBE_CONTEXT}}` | Target non-production Kubernetes context |
| `{{KAGENT_NAMESPACE}}` | kagent namespace, usually `kagent` |
| `{{ARGO_NAMESPACE}}` | Argo Workflows namespace, usually `argo` |
| `{{ARGO_EVENTS_NAMESPACE}}` | Argo Events namespace |
| `{{CHAOS_ALLOWED_NAMESPACES}}` | Namespace allowlist for chaos targets |
| `{{CHAT_MODEL_CONFIG}}` | kagent ModelConfig for chat/triage agents |
| `{{EMBEDDING_MODEL_CONFIG}}` | ModelConfig for KB/doc retrieval |
| `{{GRAFANA_MCP_REMOTE_SERVER_NAME}}` | Read-only Grafana MCP RemoteMCPServer |
| `{{GITOPS_MCP_REMOTE_SERVER_NAME}}` | GitLab/GitOps MCP RemoteMCPServer |
| `{{GITLAB_HOST}}` | GitLab host |
| `{{GITLAB_SANDBOX_PROJECT}}` | Sandbox project for branches, reports, issues, and draft MRs |
| `{{GITLAB_TOKEN_SECRET}}` | Kubernetes Secret name containing the GitLab token |
| `{{GITLAB_SOURCE_BRANCH_PREFIX}}` | Feature branch prefix for chaos artefacts |
| `{{HITL_FRONT_DOOR}}` | Teams/Slack/mock-bot approval front door |
| `{{KB_REPO_URL}}` | Git-backed runbook repository |
| `{{KB_SOURCE_PATH}}` | Runbook source path inside the KB repo |
| `{{MEMORY_MCP_NAME}}` | Shared memory MCP server name |
| `{{STORAGE_CLASS}}` | Storage class for supporting platform components |
| `{{INTERNAL_REGISTRY}}` | Private registry mirror for required images |
| `{{ENV}}` | Lower-environment tier |
| `{{MAX_CONCURRENT}}` | Max concurrent chaos tests per cluster |
| `{{QUIET_PERIOD}}` | Minimum quiet period per service |
| `{{CLUSTER_SELECTION_LABELS}}` | Opt-in cluster selector labels |
| `{{MAX_SELECTED_CLUSTERS}}` | Upper bound for fleet selection |
| `{{FLEET_INVENTORY_SOURCE}}` | Source of cluster inventory |

## Images

Core chaos images:

- `litmuschaos/chaos-operator:3.28.0`
- `litmuschaos/chaos-runner:3.28.0`
- `litmuschaos/go-runner:3.28.0`

Workflow/helper images:

- `bitnamilegacy/kubectl:1.30.7`
- `alpine:3.19`
- `python:3.11-slim`
- Argo controller and executor images pinned by the environment's Argo install

Optional supporting images:

- ChaosCenter and MongoDB images if the UI is required
- `ghcr.io/kagent-dev/doc2vec/mcp:2.11.0` for querydoc/KB retrieval
- kagent and agentgateway runtime images from the approved platform bundle

## Required Controllers and CRDs

- `agents.kagent.dev`
- `modelconfigs.kagent.dev`
- `remotemcpservers.kagent.dev`
- `workflows.argoproj.io`
- `cronworkflows.argoproj.io`
- Argo Events `EventSource` and `Sensor`
- Litmus `ChaosEngine`, `ChaosExperiment`, and `ChaosResult`
- Flux or Argo CD for GitOps sync
- Kyverno for the optional admission policy at
  `infra/byo-kagent/kyverno-policies/validate-chaos-test-safety.yaml`

`ChaosTest` and `ReliabilitySuite` are config objects in v1. Do not install CRDs
for them unless a later controller spike proves the need.

## Permission Model

- Designer and suite agents are read-only.
- Scheduler and reporting agents write only to GitLab sandbox branches/MRs.
- Test manager agent submits or inspects Argo Workflows only.
- Litmus runner service accounts own namespace-scoped chaos permissions.
- Workflow service accounts own execution permissions.
- General agents never receive direct apply/delete privileges for chaos targets.

## Local Policy Gate

Run before opening a GitOps MR:

```bash
python3 chaos/reliability/scripts/validate-reliability-configs.py \
  chaos/reliability/examples/pod-delete.chaostest.yaml \
  chaos/reliability/examples/sample-platform.reliabilitysuite.yaml \
  chaos/reliability/gitops/litmus-pod-delete-chaosengine.yaml
```

The validator rejects production targets, missing HITL, missing opt-in labels,
missing rollback/abort conditions, and suite routing that does not send
below-benchmark tests to `review-manager-agent`.

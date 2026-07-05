# Fable Critical Review Execution

Date: 2026-07-05

This records the repo-side execution pass for
`FABLE-KAGENT-AKS-CRITICAL-REVIEW-REPORT.md`.

## Closed In This Pass

| Report gap | Repo action | Evidence |
|---|---|---|
| P0 sanitization leak | Replaced the specific secret manager project/secret path in the live work-agent audit with placeholders. | `work-agent-bundles/LIVE-WORK-AGENT-AUDIT-2026-06-07.md` |
| P0 shared memory server reachable too broadly | Added a NetworkPolicy limiting ingress to approved kagent runtime pods in the `kagent` namespace. | `platform/mcp-memory-server/networkpolicy.yaml` |
| P0 memory write/delete exposed through general k8s agent | Removed memory write tools from the memory-wired `k8s-agent`; it now keeps search/open/read only. | `agents/memory-wired/k8s-agent.yaml` |
| P0 front-door agents with write/delete/exec tools | Removed create/patch/apply/delete/exec/label/annotation tools from `cert-manager-agent`, `test-ns-agent`, and `memory-wired/k8s-agent`. | `agents/kagent-triage/cert-manager-agent.yaml`, `agents/kagent-triage/test-ns-agent.yaml`, `agents/memory-wired/k8s-agent.yaml` |
| P0 HITL tier self-classification | Changed the workflow tier classifier so the agent's proposed tier is logged only; unknown actions now default to `T4`. | `platform/teams-hitl/workflow-approval-template.yaml` |
| P0 HITL callback too weak | Added stricter Sensor filters for `workflow_namespace=argo` and `approval_id`, and enabled the Istio signature-header requirement policy. | `platform/teams-hitl/sensor.yaml`, `platform/teams-hitl/istio-authorization-policy.yaml` |
| P0 AKS-MCP Secret read in read-only mode | Added `rbac.includeSecrets=false` default and removed Secret reads from the default read-only ClusterRole. | `platform/aks-mcp/chart/values.yaml`, `platform/aks-mcp/chart/templates/rbac.yaml` |
| P0 ToolGrant bypass by annotation | Removed the author-set annotation escape and made ToolGrant existence come from the Kyverno API lookup. | `infra/byo-kagent/kyverno-policies/validate-agent-tool-grants.yaml` |
| P0 onboarding payload can grant broad RBAC | Removed `admin` from the payload schema and added script-side `view`/`edit` allowlisting plus AD group naming validation. | `platform/argo-workflows/templates/app-onboarding/schemas/golden-path-payload.schema.json`, `platform/argo-workflows/templates/app-onboarding/app-onboarding-template.yaml` |
| P0 onboarding Azure RoleAssignments are payload controlled | Added workflow parameters for approved Azure roleDefinitionIds and scope prefixes; RoleAssignments now fail closed unless both are allowlisted. | `platform/argo-workflows/templates/app-onboarding/app-onboarding-template.yaml` |

## Still Open

These need live-cluster validation or broader design decisions and were not
closed by static repo edits:

- Prove HITL callback HMAC value verification end to end. The repo now requires
  a signature header at Istio, but header presence is not cryptographic
  verification.
- Run a negative HITL test: forged callback rejected, stale approval rejected,
  and unknown action tiered to `T4`.
- Prove the canonical ingestion path and retire/deprecate duplicates.
- Update production Argo Sensor/Workflow wiring to consume Vector
  `target_agent`, `route_key`, and quarantine markers.
- Replace at least one synthetic specialist path with a real flagship run:
  alert -> real Grafana/Kubernetes evidence -> HITL block -> GitOps MR -> eval.
- Prove agentgateway/model failover under a forced 429/5xx or backend outage.
- Feed lifecycle eval from real traces/evidence rather than hand-written
  samples.

## Validation Expected Before Work Use

Static validation run locally:

```text
YAML_PARSE: passed for changed plain YAML files
JSON_SCHEMA_PARSE: passed for golden-path-payload.schema.json
AKS_MCP_HELM_RENDER: passed
AKS_MCP_RENDERED_READONLY_SECRET_READ: absent
DANGEROUS_TOOL_SEARCH_ON_PATCHED_AGENTS: clean
PUBLIC_SECRET_LOCATION_SEARCH: clean
GIT_DIFF_CHECK: passed
ARGO_SENSOR_SERVER_DRY_RUN_ON_KIND_ARGO_WORKFLOW: passed
```

Dry-run limitations:

- `kind-argo-workflow` does not have the `kagent` namespace, so kagent-scoped
  server dry-runs must be repeated on the target cluster.
- The `kind-argo-workflow` context does not have Istio or Kyverno CRDs, so
  those server dry-runs must be repeated where those CRDs are installed.

Run these before applying the changed manifests in a work cluster:

```bash
helm template aks-mcp platform/aks-mcp/chart --namespace aks-mcp
kubectl apply --dry-run=server -f platform/teams-hitl/sensor.yaml
kubectl apply --dry-run=server -f platform/teams-hitl/istio-authorization-policy.yaml
kubectl apply --dry-run=server -f platform/mcp-memory-server/networkpolicy.yaml
kubectl apply --dry-run=server -f infra/byo-kagent/kyverno-policies/validate-agent-tool-grants.yaml
kubectl apply --dry-run=server -f agents/kagent-triage/cert-manager-agent.yaml
kubectl apply --dry-run=server -f agents/kagent-triage/test-ns-agent.yaml
kubectl apply --dry-run=server -f agents/memory-wired/k8s-agent.yaml
```

Use the target work cluster CRD versions for server dry-runs. Do not infer
compatibility from static YAML alone.

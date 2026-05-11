# Design Decisions

## Why Plan A-lite over Plan A or Plan B

Three options were evaluated:

**Plan A** — new Argo WorkflowTemplate with 4 ConfigMaps (template + platform defaults + size tiers + manifests), sed-based substitution, agent extracts 3 fields.  
**Plan B** — agent renders a full ~4 KB UK8SClusterPublic YAML inline from the system prompt, no WorkflowTemplate.  
**Plan A-lite (chosen)** — single WorkflowTemplate with KRO YAML rendered inside it using bash `printf` + env vars from a Secret. Agent extracts 5 typed fields only. No ConfigMaps.

Codex review verdict: **A-lite wins.**

| Dimension | A | B | A-lite |
|---|---|---|---|
| ConfigMaps | 4 | 0 | 0 |
| Hallucination risk | Low | High — 4 KB YAML verbatim | Low — 5 typed fields |
| Debuggability | Good (Argo UI) | Poor (what did the model emit?) | Good (Argo UI) |
| Platform defaults | Literals in CM | In system prompt | In a Secret |

## Why the platform defaults are in a Secret (not a ConfigMap)

Codex flagged that the example cluster values include subscription IDs, identity resource IDs, SSH public keys, and Defender workspace IDs. Even though these are already committed in `example-cluster-public.yaml`, concentrating them in a separate Secret:

1. Keeps them out of the agent's system prompt (no LLM ever sees them).
2. Makes it easy to swap home → work values without touching the WorkflowTemplate.
3. Follows least-surprise: operators know to treat Secrets differently from ConfigMaps.

The `.yaml.template` is committed (with example values); the rendered `.yaml` file is gitignored.

## Why the agent SA cannot create KRO instances directly

Per `CLAUDE.md`: ASO can silently create Azure resources. If the agent SA had `create` on `uk8sclusterspublic`, a mis-prompted Qwen 14B could apply a KRO instance directly, bypassing the workflow's validation step and the explicit confirmation gate.

The RBAC design ensures: agent SA → only creates `argoproj.io/workflows`. The `argo-workflow-executor` SA → creates KRO instances, but only after the workflow's `validate-inputs` step has passed.

## Why `printf` over heredoc for YAML rendering

In Argo WorkflowTemplate `source:` fields (YAML literal block scalars), heredoc closing delimiters must match exactly after YAML indentation stripping. `printf '%s\n' "line" "line" ...` avoids this ambiguity entirely — each YAML line is a separate quoted string. It's verbose but reliable across all YAML parsers and Argo versions.

## Why dry-run simulates phases instead of just exiting

The wait-for-ready step in dry-run mode emits 6 phase transitions over 30 seconds (`validating-config` → `creating-resource-group` → `provisioning-control-plane` → `bootstrapping-node-pool` → `installing-addons` → `ready`). This gives the demo audience something to watch in the Argo UI and lets the agent's status tool return realistic-looking replies, making the dry-run visually indistinguishable from a real provision for a stakeholder who isn't watching timestamps.

## Codex review notes (condensed)

Top risks identified:

1. **Dry-run realism is overstated** — admission validation doesn't rehearse ASO identity, Azure quota, or the cert auto-trigger Job. Mitigated by: mandatory `smoke-test-cert-trigger.sh` at work before demo day, pre-staged fallback cluster.

2. **Authorization was too prompt-dependent in Plan B** — Plan B's kagent SA needed cluster-wide `create` on KRO resources. Mitigated by: structural RBAC split (agent SA ≠ workflow SA).

3. **Platform defaults are not innocent literals** — sub ID, identity IDs, SSH key, allow-all IP ranges. Mitigated by: Secret mount, gitignored rendered file.

Alternative considered but rejected: **GitOps PR-based POC** (agent opens a PR, CI dry-runs, Flux applies). Better auditability; weaker demo narrative. Worth revisiting for the production rollout path.

---

## Home-cluster deployment lessons (2026-05-09)

Discovered and fixed during first end-to-end deployment to `red` cluster. All captured in `deploy-home-dryrun.sh`.

### KRO aggregate RBAC — use wildcard from the start

KRO v0.7.x uses ClusterRole aggregation (label `rbac.kro.run/aggregate-to-controller: "true"`). Each new CRD that a managed RGD creates needs explicit list/watch permission for the KRO controller — **or use `resources: ["*"]` on the `kro.run` apiGroup**. Adding resources one by one as errors appear is slow. The `kro-aggregate-rbac.yaml` now sets wildcard from the start.

### KRO CEL vs bash `${VAR:-default}`

KRO v0.7.1 scans **all** YAML field values for `${...}` and tries to parse them as CEL expressions. This includes bash `source:` blocks. Two patterns cause failures:

- `${VAR}` where `VAR` looks like a resource name → replace with `$VAR`
- `${VAR:-default}` (bash default-value syntax) → replace with `if [ -z "$VAR" ]; then VAR=default; fi`

File fixed: `uk8s-certification-v2.yaml` line 990 (`${SEVERITY:-PARSE_ERROR}`).

### `uk8sclusterpublic` depends on two other RGDs

`uk8scluster-public.yaml` references both `UK8SCertification` (v1) and `UK8SFluxGitOps` as nested KRO resources. Both must be Active before `uk8sclusterpublic` can activate. Deploy order:

1. `uk8sfluxgitops-home-stub.yaml` (stub — the real RGD needs `kubernetesconfiguration.azure.com` CRDs not present on home cluster)
2. `uk8s-certification.yaml` (v1 — referenced by cluster-public)
3. `uk8s-certification-v2.yaml` (for cert trigger after provisioning)
4. `uk8scluster-public.yaml` (delete + re-apply to force reconcile after deps are Active)

### Home-cluster `uk8sfluxgitops` stub

The real `uk8sfluxgitops.yaml` RGD needs `kubernetesconfiguration.azure.com/v1api20241101` (Azure Kubernetes Configuration) which is not installed on the home cluster. The stub at `workflow/uk8sfluxgitops-home-stub.yaml` has the same schema but replaces Azure resources with a single ConfigMap placeholder. **Never apply the stub to the work cluster — use the full `uk8sfluxgitops.yaml` there.**

### KRO RGD backoff — force reconcile with delete + re-apply

When a KRO RGD fails reconciliation, it enters exponential backoff and does not automatically retry when its dependencies become available. `kubectl annotate` does not reliably trigger a re-reconcile. The only reliable method is `kubectl delete` + `kubectl apply`. The deploy script does this for `uk8sclusterpublic` to ensure a clean reconcile after deps are Active.

### KRO-generated CRD pluralization

KRO pluralises Kind names by appending `s` — `UK8SClusterPublic` → `uk8sclusterpublics` (not `uk8sclusterspublic`). The RBAC resource name must match exactly. Verified via `kubectl auth can-i` and `kubectl get crd`.

### Agent schema (kagent v1alpha2)

Correct schema for tools in `kagent.dev/v1alpha2`:
```yaml
tools:
  - type: McpServer
    mcpServer:
      apiGroup: kagent.dev
      kind: RemoteMCPServer
      name: kagent-tool-server
      toolNames: [k8s_apply_manifest, k8s_get_resources, k8s_describe_resource]
```
`modelConfig` is a plain string (`"default-model-config"`), not an object with `modelConfigRef`.

### `workflowtaskresults` RBAC required

`argo-workflow-executor` SA needs `create` on `workflowtaskresults.argoproj.io` in the `argo` namespace for Argo's task result reporting to work. Without it, every step exits with code 64. Added to `workflow-executor-status-writer` Role in `rbac.yaml`.

### ownerRef placement in status ConfigMap

The `ownerReferences` block must be a sibling of `labels` inside `metadata`, not a child of `labels`. The original template appended `$OWNER_REF` after `kro.run/demo: "true"` (inside the labels block), causing `cannot unmarshal array into Go struct field ObjectMeta.metadata.labels`. Fixed by appending `$OWNER_REF` after `namespace: argo` at the `metadata` level.

### macOS `grep -oP` not available

macOS `grep` does not support `-P` (Perl-compatible regex). Replace `grep -oP '(?<=workflow\.argoproj\.io/)[^ ]+'` with `sed 's|.*workflow\.argoproj\.io/\([^ ]*\).*|\1|'`. Fixed in `smoke-test-dryrun.sh` and `smoke-test-bad-inputs.sh`.

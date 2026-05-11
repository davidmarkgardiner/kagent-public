# App Certification v1

Application-scoped certification workflow. Structural clone of `uk8s-certification-v2.yaml`, re-scoped from cluster to a single Deployment in a single namespace.

This is **Phase 5** of the golden-path onboarding pipeline. It produces a structured verdict that downstream consumers (the master golden-path DAG, a Teams sign-off bot, or a `Certification` CR controller) act on.

## What it does

1. Creates an Argo `WorkflowTemplate` named `certify-app-<appName>` in the `argo` namespace.
2. Creates a `CronWorkflow` for monthly re-certification (suspended by default).
3. Optionally creates a one-shot `Job` that submits the first run when `certification.autoTrigger=true`. **Off by default** — apps cert on demand from Phase 5, not on creation.

## What it validates

Each task records a one-line summary (`passed=N failed=N warnings=N …`) into a per-workflow `ConfigMap` (`app-cert-results-<workflow-name>`, owner-ref'd to the Workflow so it's GC'd automatically).

| Task | Checks |
|---|---|
| `validate-namespace-foundations` | Namespace exists, has `managed-by=argo-workflows` label, has a ResourceQuota. |
| `validate-rbac-bindings` | At least one non-default ServiceAccount, at least one RoleBinding. |
| `validate-deployment-health` | Deployment exists; ready replicas == desired; no pods in CrashLoopBackOff. |
| `validate-probes-set` | Every container has both `livenessProbe` and `readinessProbe`. |
| `validate-resources-requests-limits` | Every container has both `requests` and `limits` for CPU and memory. |
| `validate-image-tag-policy` | No `:latest`, no untagged images. In PROD with `requireDigestPinInProd=true`, every image must contain `@sha256:`. |
| `validate-network-policy-coverage` | Default-deny ingress NetworkPolicy present; ideally at least one explicit allow rule too. |
| `validate-istio-mtls` | Skipped unless `hasIstio=true`. STRICT `PeerAuthentication` present in the namespace. |
| `validate-azure-resources` | Skipped unless `hasAzure=true`. ASO `UserAssignedIdentity` / `FederatedIdentityCredential` / `RoleAssignment` (filtered by `managed-by=argo-workflows` and name match) all show `Ready=True`. |

After `aggregate-certification` flattens the per-task summaries into a single JSON report, `agent-triage` posts the report to kagent via A2A and parses a strict-schema verdict back. The verdict shape is identical to cert v2:

```json
{
  "severity":          "CRITICAL | WARNING | INFO | AGENT_UNAVAILABLE | PARSE_ERROR",
  "blast_radius":      "<one subsystem name>",
  "failed_checks":     ["<check-name>"],
  "first_remediation": "<one short sentence>"
}
```

`severity` is exposed as the workflow output parameter `severity`. Use the optional `gate-on-critical` task (off by default) if you want the workflow to fail the run when severity is `CRITICAL`.

## Instance shape

```yaml
apiVersion: kro.run/v1alpha1
kind: AppCertificationV1
metadata:
  name: my-api-prod-cert
  namespace: argo
spec:
  appName:    my-api
  namespace:  my-api-prod
  ownerTeam:  payments
  swc:        CC11111
  environment: PROD
  hasIstio:    true
  hasAzure:    true
  requireDigestPinInProd: true
  certification:
    timeout:     900
    schedule:    "0 4 1 * *"     # 04:00 UTC, 1st of each month
    suspended:   true
    autoTrigger: false
  agentAnalysis:
    enabled:        true
    kagentService:  kagent.kagent.svc.cluster.local
    kagentPort:     80
    agentName:      sre-triage-agent
    timeoutSeconds: 120
    failOnCritical: false
```

## How to use

> **Pre-requisite:** apply `certification-rbac-app-v1.yaml` before the RGD. It grants `argo-workflow-executor` the cross-namespace reads (namespaces, quotas, deployments, pods, netpol, rolebindings, HPAs, PeerAuthentications, ASO identity resources) and ConfigMap write access in `argo`.

1. Apply RBAC, then the RGD:
   ```bash
   kubectl apply -f infra-stack/kro-stack/definitions/certification-rbac-app-v1.yaml
   kubectl apply -f infra-stack/kro-stack/definitions/app-certification-v1.yaml
   ```
2. For each app you want to certify, create an `AppCertificationV1` instance.
3. Submit a one-off run (or wait for the monthly CronWorkflow):
   ```bash
   argo submit -n argo --from workflowtemplate/certify-app-my-api
   ```
4. Read the verdict:
   ```bash
   argo get -n argo @latest -o json \
     | jq '.status.nodes | to_entries[]
           | select(.value.displayName == "agent-triage")
           | .value.outputs.parameters'
   ```

## Differences vs `uk8s-certification-v2.yaml`

| Concern | Cert v2 (cluster) | App cert v1 |
|---|---|---|
| Scope | A whole AKS cluster | A single Deployment + namespace |
| AKS credential dance | `az login` + `aks get-credentials` | None — runs against the same cluster |
| Cluster-wide reads | nodes, kube-system, flux-system | None |
| Per-task ConfigMap pattern | ✓ same | ✓ same |
| `aggregate-certification` shape | ✓ same | ✓ same — adds `app`, `owner_team`, `swc` |
| `agent-triage` A2A pattern | ✓ same | ✓ same — prompt anchors app + namespace |
| `gate-on-critical` | ✓ same | ✓ same |
| Auto-trigger Job default | `true` (cert on cluster create) | **`false`** (cert on demand) |
| Re-cert schedule default | weekly | monthly |

## Where this slots into the golden path

```
Phase 1: app-intake-agent           → writes _phase1_intake into payload
Phase 2: app-onboarding-template    → writes _phase2_infrastructure
Phase 3: app-hardening-agent (PR)   → writes _phase3_hardening
Phase 4: app-release-template       → writes _phase4_deployment
Phase 5: certify-app-<name>         ← THIS RGD — writes _phase5_certification
                  ↓
            kagent A2A verdict
                  ↓
            sign-off (auto if INFO,
                      Teams approval if WARNING,
                      ticket if CRITICAL)
```

The payload contract is defined at `application-stack/core/app-onboarding/schemas/golden-path-payload.schema.json`.

## What's intentionally not here yet

These are gaps Codex flagged in the design review. Each is a separate, smaller PR:

1. **Phase 5 → payload bridge.** A small post-step that takes the agent verdict and patches the corresponding `_phase5_certification` block onto a target ConfigMap or `Certification` CR. Today the verdict only lives in the per-workflow `ConfigMap` and Argo output parameters.
2. **HITL sign-off.** When severity is `WARNING`, the master DAG should suspend and route through `triage-with-approval`. Out of scope for this RGD.
3. **`Certification` CR controller.** A simple custom resource (`status.certified=true`, `status.expiresAt`) the rest of the platform can RBAC-gate against. Currently just a verdict + ConfigMap.
4. **Compensating actions on partial cert failure.** If `validate-azure-resources` fails because ASO is mid-reconcile, today the verdict is `WARNING` / `CRITICAL`. A retry-with-backoff on those tasks specifically would reduce noise.
5. ~~**Extended RBAC.**~~ ✅ **Shipped** — `certification-rbac-app-v1.yaml` contains the ClusterRole + ClusterRoleBinding for cross-namespace reads (namespaces, quotas, deployments, pods, netpol, rolebindings, HPAs, PeerAuthentications, ASO identity resources) plus a namespace-scoped Role + RoleBinding for ConfigMap writes in `argo`. Apply it before applying this RGD on any cluster.

## Files

| Path | Purpose |
|---|---|
| `app-certification-v1.yaml` | The RGD (this file's subject) |
| `certification-rbac-app-v1.yaml` | ClusterRole + Role for workflow executor — apply first |
| `README-app-certification.md` | This document |
| `../../../application-stack/core/app-onboarding/schemas/golden-path-payload.schema.json` | Cross-phase payload contract |
| `uk8s-certification-v2.yaml` | Cluster cert reference — read this if you're modifying the agent-triage pattern; we want both to stay aligned |

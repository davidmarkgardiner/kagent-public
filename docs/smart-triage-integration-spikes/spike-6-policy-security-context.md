# Spike 6 — Policy & Security Context

**Implementation order: 4 of 5.**

**Status:** implemented and live-proven as a public-safe contract proof on
2026-06-01.

Evidence:

- Workflow: `smart-triage-alert-b8gkz`, `Succeeded`, `14/14`.
- Marker: `SPECIALIST_POLICY: completed`.
- Safety marker: `REMEDIATION_SAFETY: blocked`.
- Guardrail proposal:
  `infra/byo-kagent/kyverno-policies/block-remediation-on-blocking-policy.yaml`
  renders through `kubectl kustomize`; the demo cluster does not currently have
  the Kyverno `ClusterPolicy` CRD installed, so server-side policy dry-run is
  not claimed.
- Proof helper:
  `a2a/smart-triage-fanout-demo/scripts/prove-policy-summary.sh`.

## Objective

Add policy and security constraints to the commander packet so remediation never
proposes an action that admission control (Kyverno/Gatekeeper), image policy, or
a known vulnerability finding would block. Read-only retrieval + an admission
guardrail proposal for write-capable MCP tools.

## Existing Repo Reuse (do not rebuild)

Kyverno is the authoritative engine in this repo; reuse its posture.

| Concern | Location |
|---|---|
| Kyverno policy set (BYO kagent / MCP governance) | `infra/byo-kagent/kyverno-policies/` |
| Dangerous-verb admission control (the guardrail template to extend) | `infra/byo-kagent/kyverno-policies/mcp-dangerous-verb.yaml` |
| Agent tool-grant validation | `infra/byo-kagent/kyverno-policies/validate-agent-tool-grants.yaml` |
| Agent cluster-target validation | `infra/byo-kagent/kyverno-policies/validate-agent-cluster-target.yaml` |
| Tenant defaults | `infra/byo-kagent/kyverno-policies/agent-tenant-defaults.yaml` |
| ToolGrant CRD | `infra/byo-kagent/crds/toolgrant-crd.yaml` |
| Phase 3 policy intent for smart-triage | `SMART-TRIAGE-FANOUT-WORK-PLAN.md` § Phase 3 |

No policy/security specialist exists yet — greenfield read-only agent + a
proposed (not enforced-by-default) admission guardrail.

## Proposed Architecture

```text
normalize-incident (namespace/workload)
  -> fanout-policy (NEW, read-only):
       read PolicyReports / ClusterPolicyReports for ns/workload
       read image scan / vulnerability findings
       classify: blocking vs warning
  -> emits BLOCKERS[] and WARNINGS[]
  -> commander: any remediation proposal is checked against BLOCKERS
  -> (proposal) admission guardrail rejects write-capable MCP/agent actions
     that would violate a blocking policy
```

Two questions the next agent resolves in Phase 0:

- Is `{{POLICY_ENGINE}}` Kyverno or Gatekeeper in the target cluster? (Repo
  standard is Kyverno; only use Gatekeeper if the work cluster standardized on
  it.)
- Where do image-scan / vulnerability findings live (`{{VULN_SOURCE}}`)?

## First Safe Proof

Read policy reports and image/security findings for **one** namespace or workload
and return a concise risk/blocker summary. Read-only.

```bash
# Kyverno PolicyReports (read-only):
kubectl get policyreport,clusterpolicyreport -n {{TARGET_NAMESPACE}} -o wide
kubectl get policyreport -n {{TARGET_NAMESPACE}} -o jsonpath='{.items[*].results[*].policy}'
# Gatekeeper alt (read-only): kubectl get constraints -A
```

Proof = a summary listing each failing policy for the workload, classified
blocking vs warning, with at least one concrete blocker or an explicit
`NO_BLOCKERS`.

## Required MCP / Tool / Server Shape

Read-only:

- Kubernetes read MCP for `PolicyReport`, `ClusterPolicyReport` (Kyverno) or
  `constraints` (Gatekeeper) — `get`/`list` only.
- A vulnerability/image-findings read source (`{{VULN_SOURCE}}`): scanner API,
  in-cluster report CRDs, or registry policy endpoint — read-only.
- No mutation verbs (must pass `mcp-dangerous-verb.yaml`).

## kagent Agent Contract

`kagent.dev/v1alpha2` Declarative read-only Agent. Required markers:

```text
SPECIALIST_POLICY: completed
EVIDENCE_SOURCE: {{POLICY_ENGINE}}
POLICY_REPORTS_READ: yes
BLOCKERS: <policy[, policy] | none>
WARNINGS: <policy[, policy] | none>
VULN_FINDINGS: <count by severity | none | source-unavailable>
REMEDIATION_SAFETY: blocked|allowed_with_warnings|clear
CURRENT_STATE_VERIFIED: yes
RECOMMENDATION: <hold remediation | proceed to HITL with warnings>
```

`systemMessage` must forbid proposing any policy mutation and must mark a
proposal `blocked` if any blocking policy or critical vuln applies.

## Admission-Control Guardrail Proposal (the write-side half)

Extend the existing `mcp-dangerous-verb.yaml` pattern with a policy that the
work cluster can enforce later:

- Deny a write-capable MCP/agent remediation action whose target namespace/
  workload has an open **blocking** PolicyReport result.
- Require `platform.kagent.dev/policy-reviewed=true` (mirroring the existing
  `danger-reviewed` override) before a flagged remediation can proceed.
- Ship it `validationFailureAction: Audit` first (proposal/observe), promote to
  `Enforce` only after review — do not flip the demo cluster to Enforce blindly.

## Argo Workflow Integration Point

Add `fanout-policy` to the DAG (depends on `normalize-incident`) via
`call-specialist`. **Also** gate the commander: policy context should be checked
**before** any GitLab MR creation **and** surfaced in the HITL packet (the brief
asks "before MR, before HITL, or both" — answer: both). If `REMEDIATION_SAFETY:
blocked`, the commander presents the blocker and the MR/remediation path stays
closed even on approve.

## HITL Requirement

Mandatory. Policy context strengthens HITL: a blocked proposal is shown to the
operator with the exact violating policy; the operator cannot approve a
remediation that the guardrail would reject (or must add a reviewed override,
audited).

## Required Manifests / Scripts To Create

| Artifact | Purpose |
|---|---|
| `policy-security-specialist-agent.yaml` | New read-only Agent |
| `policy-read-remotemcpserver.yaml` (if needed) | Read-only policy/vuln MCP |
| `infra/byo-kagent/kyverno-policies/block-remediation-on-blocking-policy.yaml` | Proposed Audit-mode guardrail |
| Edit `workflow.yaml` | Add `fanout-policy` + pre-MR safety check |
| `scripts/prove-policy-summary.sh` | One A2A call asserting blocker classification |

## Validation Commands

```bash
kubectl apply --dry-run=server -f .../policy-security-specialist-agent.yaml
kubectl apply --dry-run=server -f infra/byo-kagent/kyverno-policies/block-remediation-on-blocking-policy.yaml
# Confirm read-only tool wiring. Do not grep the whole manifest because the
# systemMessage may mention forbidden verbs as policy guidance.
yq -r '.. | .toolNames? // empty | .[]' .../policy-security-specialist-agent.yaml \
  | grep -Eiq '(apply|delete|exec|patch|admin|drop)' \
  && echo "FAIL: mutating tool present" || echo "OK: read-only tools"
bash -n scripts/prove-policy-summary.sh
```

## Public-Safe Placeholders

| Placeholder | Use |
|---|---|
| `{{POLICY_ENGINE}}` | kyverno \| gatekeeper |
| `{{VULN_SOURCE}}` | scanner / report CRD / registry policy endpoint |
| `{{TARGET_NAMESPACE}}` | Non-prod incident namespace |
| `{{POLICY_READ_MCP}}` | Read-only policy MCP server name |
| `{{SEVERITY_BLOCK_THRESHOLD}}` | e.g. critical-and-above blocks |

## Evidence To Capture

- PolicyReport read output for one workload (sanitized).
- Blocker-vs-warning classification with the exact policy names.
- A `blocked` case and a `clear` case.
- Dry-run of the Audit-mode guardrail denying a flagged write action.

## Failure Classes

| Class | Meaning | Evidence |
|---|---|---|
| `POLICY_API_UNAVAILABLE` | Kyverno/Gatekeeper reports unreadable | MCP/agent logs |
| `NO_REPORT_FOUND` | No PolicyReport for the workload (treat as clear-but-unverified) | query output |
| `BLOCKING_POLICY` | A blocking policy applies (signal, not failure) | report result |
| `VULN_SOURCE_UNAVAILABLE` | Vulnerability source unreachable | scanner logs |
| `UNSAFE_REMEDIATION_PROPOSAL` | A proposed action violates a blocker | guardrail denial |

## Rollback / Disable Path

```bash
kubectl delete -f .../policy-security-specialist-agent.yaml --ignore-not-found
kubectl delete -f infra/byo-kagent/kyverno-policies/block-remediation-on-blocking-policy.yaml --ignore-not-found
# Guardrail ships in Audit mode; deleting it cannot unblock real traffic.
```

## Known Risks

- Flipping the guardrail to `Enforce` on a shared cluster can block unrelated
  workloads — keep it Audit until reviewed, document the override annotation.
- `NO_REPORT_FOUND` must not be read as "safe"; mark it clear-but-unverified.
- Vuln-source coupling: scanner APIs vary; keep the marker schema source-agnostic.
- Over-blocking erodes trust; tune `{{SEVERITY_BLOCK_THRESHOLD}}` with owners.

## Exit Criteria

- Specialist returns blocker/warning classification for one workload.
- `blocked` and `clear` cases both correct.
- Audit-mode guardrail dry-run denies a flagged write action and allows a clean
  one.
- Read agent passes the dangerous-verb policy; failure classes emitted.

# Review: `eval-plan.md` (Kagent Agent Evaluation Plan)

**Reviewer:** automated repo-grounded review
**Scope:** correctness of `eval-plan.md` against the actual repo, soundness of the score model, and Phase 1 build-readiness.

---

## Verdict

**Sound direction, ready to build Phase 1 — after fixing one blocker.**

The layered model is right: score deterministic facts directly, use an LLM judge only where deterministic checks are weak, and keep safety as hard gates separate from the weighted score. That matches current agent-eval practice and the repo's own read-only-first posture (`observability/AGENT-ROSTER.md`, `observability/PRODUCTION-READINESS.md`). The phasing is correct — deterministic MVP before Phoenix/judge.

The one blocker is mechanical but fatal to the safety story: the golden cases match on tool names that **do not exist** in this repo, so the forbidden-tool hard gate would never fire.

---

## Verification against the repo

Every factual claim in the plan's baseline section was checked. All accurate.

| Claim in eval-plan | Verdict | Evidence |
|---|---|---|
| `chaos/litmus/scripts/chaos-eval-poc.py` emits a health score and assumes `1.0` for reasoning/tool/cost | ✅ Accurate | `compute_health_score` L96-103: `0.25*1.0` reasoning_quality, `0.20*1.0` tool_efficiency, `0.10*1.0` cost_efficiency; only `workflow_stability` measured |
| chaos-eval evidence lists Phoenix LLM-as-judge as a next step | ✅ Accurate | `chaos/litmus/evidence/chaos-eval-2026-05-18.md:32` |
| `PRODUCTION-READINESS.md` describes namespace-by-namespace fault injection + triage accuracy validation | ✅ Accurate | §11 "Engineering Rollout — Namespace-by-Namespace Fault Injection", L222-243 |
| `AGENT-ROSTER.md` says agents start read-only, promote after proving accuracy over weeks | ✅ Accurate | L519, L691 |
| `observability/grafana/dashboards/agentgateway-traffic-quality.json` exists | ✅ Exists | file present |
| Coverage agents exist (`kube-system`, `flux-system`, `cert-manager`, `kyverno`, `istio-ingress`, `grafana-evidence`, `chaos-triage`) | ✅ All exist | `agents/kagent-triage/**`, `agents/grafana-evidence-agent/`, `chaos/litmus/manifests/agent-chaos-triage.yaml` |
| `observability/agent-evals/` (proposed home) | ⬜ Not yet present | Expected — it is the proposal |

---

## 🔴 Blocker — tool names in the golden cases do not exist

The example case (`requiredTools`/`forbiddenTools`) and the Phase 1 deterministic checks match on `kubectl_get`, `kubectl_describe`, `kubectl_logs`, `kubectl_apply`, `kubectl_delete`, `kubectl_exec`. **None of these are real kagent tool names.** The deployed agent CRs under `agents/kagent-triage/**` use the `k8s_*` family:

| eval-plan (wrong) | actual kagent tool |
|---|---|
| `kubectl_get` | `k8s_get_resources` |
| `kubectl_describe` | `k8s_describe_resource` |
| `kubectl_logs` | `k8s_get_pod_logs` |
| `kubectl_apply` | `k8s_apply_manifest` |
| `kubectl_delete` | `k8s_delete_resource` |
| `kubectl_exec` | `k8s_execute_command` |

Also present in real CRs: `k8s_get_events`, `k8s_get_resource_yaml`, `k8s_patch_resource`, `k8s_create_resource`, `k8s_check_service_connectivity`, `k8s_get_cluster_configuration`, `k8s_get_available_api_resources`, `k8s_label_resource`, `k8s_annotate_resource`.

**Impact:** `requiredTools`/`forbiddenTools` matching against trace/audit evidence would never match a real tool call. The forbidden-tool hard gate — the safety centerpiece of the whole plan — silently passes everything. Fix every case and the schema examples to use `k8s_*` names, and source the canonical list from an existing CR rather than hand-writing it.

---

## 🟡 Should fix before / while building

1. **`AgentEvalCase` is not a real CRD.** `apiVersion: eval.kagent.dev/v1alpha1` has no controller in this repo. It is fine as a plain YAML document format, but say so explicitly: it is a file schema validated by `score-agent-run.py`, not a `kubectl apply`-able resource. (Real agent CRs use `kagent.dev/v1alpha2`.) Otherwise someone will try to wire a controller that was never intended.

2. **The chaos-eval-poc refactor is a schema migration, not a drop-in.** `chaos-eval-poc.py` scores `reasoning_quality` / `tool_efficiency` / `workflow_stability` / `cost_efficiency`. The new model has seven different sub-scores (`task_success, diagnosis_correctness, tool_trajectory, evidence_quality, safety_and_permissions, latency, cost_efficiency` — weights sum to 1.0 ✓). Chaos infra runs have no diagnosis/evidence/safety dimension to score. The plan's own Phase 4 acceptance criterion ("chaos recovery score and agent quality score are not blended without visibility") **contradicts** the Phase 1 task "refactor `chaos-eval-poc.py` so it uses the shared scorer." Resolution: keep an **infra-recovery scorer** and an **agent-quality scorer** as two separate things that share only the report emitter / JSON shape. Do not force chaos runs through the agent rubric.

3. **`AGENT-ROSTER.md` is divergent — do not trust its agent names.** The roster proposes `sre-triage-agent`, `network-agent`, `storage-agent`, `security-agent`, etc. Those are **not** the deployed agents and **not** the eval-plan coverage list. The eval-plan's coverage correctly tracks the real `agents/kagent-triage/**` set. Worth a follow-up to reconcile the roster doc so it stops misleading reviewers.

4. **Tool-call argument shape is unspecified / invented.** The JSON result example shows `arguments: {namespace, resource: "pod/..."}`. The real `k8s_get_resources` tool has its own argument schema. Phase 2 tool-trajectory scoring must match the actual argument keys emitted in OTel/audit spans. Capture one real trace before finalizing the matcher.

5. **`task_success` (weight 0.30) has no deterministic definition.** For read-only triage there is no apply to confirm "success." As written it either collapses into `diagnosis_correctness` (double-counting 0.30 + 0.25) or it quietly needs the judge in Phase 1 — which contradicts "deliver a useful scorecard without a judge." Define `task_success` deterministically for triage (e.g. "emitted a diagnosis block conforming to the required output schema"), or fold its weight into `diagnosis_correctness` for the deterministic MVP.

---

## 🟢 Minor

- **Latency/cost weights (0.05 each) need a source.** With a local Qwen model behind agentgateway, where do token counts come from? Phase 2 already hedges ("token counts when available"), so latency/cost may be unscorable at MVP. State the fallback explicitly — drop the weight and renormalize, rather than scoring a missing value as `1.0` (the exact mistake the plan criticizes in `chaos-eval-poc.py`).
- **Define the sanitization gate for `results/`.** "Result files should usually stay untracked unless they are sanitized" needs a concrete rule: no private IPs, hostnames, tenant/subscription IDs (the repo's public-safety rule in `AGENTS.md`). `chaos-eval-poc.py` already redacts the cluster address (L111: "private address redacted") — reuse that pattern in the shared emitter.
- **Hard gates should apply to read-only too.** The promotion table allows `>= 0.90` read-only production, but zero-hard-gate is only required for write-capable agents. A `0.91` run that leaked a secret or fabricated a resource should not promote. Make "zero hard-gate failures" a precondition for **any** promotion, not just write paths.

---

## Answers to the plan's own Review Questions

- **Where should it live?** Everything under `observability/agent-evals/`. Chaos keeps its own manifests but calls the shared **report emitter** only — not the agent rubric.
- **Default judge model?** Local Qwen via agentgateway: matches the existing chaos POC, needs no external tokens, public-safe. Keep `{{JUDGE_PROVIDER}}` / `{{JUDGE_MODEL}}` swappable for work-environment validation.
- **First scorecard agents?** `kube-system-agent`, `flux-system-agent`, `cert-manager-agent` — they already carry rich runbooks and failure-mode tables in their system prompts, so deterministic expected-diagnosis keywords are easy to author.
- **Min score before dev enablement?** `0.80` **and** zero hard-gate failures (the staging-ready bar).
- **Score write-capable agents now?** No. Stabilize read-only triage scoring first; the repo already mandates read-only-first promotion.

---

## Recommended First PR (amended)

Keep the plan's 6-step deterministic MVP, but add **step 0**: fix all tool names to the `k8s_*` family across every case and schema example, sourcing the canonical tool list from a real CR. Without that, the deterministic safety gate is non-functional and the MVP proves nothing about safety.

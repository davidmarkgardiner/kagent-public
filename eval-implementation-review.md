# Review: Agent-Evals Implementation

**Reviewer:** automated repo-grounded review
**Scope:** the built-out eval system under `observability/agent-evals/`, its wiring into `a2a/smart-triage-fanout-demo/workflow.yaml`, and the two handoff docs. Companion to `eval-plan-review.md`.

---

## Verdict

**Strong implementation — every prior blocker is fixed. Ship the deterministic agent-run scorer; treat the lifecycle scorecard as a wiring shell, not a quality signal yet.**

The deterministic scoring engine is genuinely good and matches the plan's intent. The one thing to be loud about: in the wired demo the lifecycle evaluator scores **hardcoded markers**, so it is green by construction (sample result = `1.0`, passed, zero hard failures). That is fine for a visual demo and the handoff doc discloses it — but no one should read the lifecycle score as evidence the agents work until the collector is fed real Argo node outputs / audit traces.

---

## Fixed since `eval-plan-review.md` (credit)

| Prior finding | Status |
|---|---|
| 🔴 Tool names `kubectl_*` don't exist | ✅ Fixed — cases use `k8s_get_resources` / `k8s_describe_resource` / `k8s_apply_manifest` etc.; `tools/k8s-tool-catalog.yaml` sources the canonical list from real CRs |
| 🟡 `AgentEvalCase` masqueraded as a CRD | ✅ Fixed — now `schemaVersion: agent-evals.kagent-public/v1alpha1`, no `apiVersion`/controller implication |
| 🟡 chaos refactor would blend rubrics | ✅ Fixed — two separate scorers (`score-agent-run.py`, `score-lifecycle-run.py`), chaos untouched |
| 🟡 `task_success` undefined for read-only | ✅ Fixed — deterministic = required `outputSections` present (`score-agent-run.py:147,167`) |
| 🟢 latency/cost unscorable at MVP | ✅ Fixed — `not_scored` excluded from the weighted denominator (`weighted_score` L97-107); no false `1.0` |
| 🟢 hard gates only for write paths | ✅ Fixed — `passed = score>=min AND not hard_failures` for every run; leak gate + namespace gate apply unconditionally |

Also good: no custom image (alpine:3.19 + `apk add python3 py3-yaml`, scripts mounted from a Kustomize ConfigMap); leak scanner covers GUIDs, RFC1918 IPs, internal URLs, secret-like text in both scorers; the collector's docstring is honest ("does not claim a real remediation unless evidence says so").

---

## 🔴 The wired lifecycle eval scores hardcoded markers, not agents

In `workflow.yaml`, the `prove-result` step writes a **fixed** marker heredoc (L406-427) that always contains:

```
REMEDIATION_EXECUTED: yes
VERIFICATION_PASSED: yes
HITL_STATUS: resumed
TICKET_UPDATED: yes
pod status changed from CrashLoopBackOff to Ready
```

These strings are literals — not derived from the specialist/commander A2A responses. `collect-lifecycle-evidence.py` turns those literals into the lifecycle booleans (`marker_lifecycle`, L186-208), so `score-lifecycle-run.py` necessarily passes. The sample proves it: **score `1.0`, passed, `hard_failures: []`, every sub-score `1.0`.**

Consequences:
- The lifecycle scorecard reports a perfect score regardless of what the agents actually did. It grades the harness, not the system under test.
- `sre-remediation-agent` is in `requiredAgents` and shows "completed", but **no step in the workflow ever calls it** — `finalize-approved` is a shell `echo` (L359-367). The agent is conjured by the `REMEDIATION_EXECUTED: yes` marker. Same for `evaluation-agent` (synthesized from the `printf 'EVALUATION_AGENT: completed'` at template L105).

This is acceptable as a *demo of the eval plumbing*, but the docs must state plainly that **the lifecycle score is non-evidential until real telemetry replaces the markers.** Risk: a reader treats "0.9 lifecycle" as proof of agent quality.

Mitigation already present: `KAGENT-EVAL-LIFT-AND-SHIFT-HANDOFF.md:139-146` lists the synthetic→real marker swap. Good — make that caveat just as prominent in the demo README and the scorecard HTML, not only the lift-and-shift doc.

---

## 🟡 Should address

1. **The real-evidence code path is built but never exercised.** The collector can parse `status.nodes` from `argo get -o json` (`node_phase_succeeded`, `workflow_duration_seconds`), but `prove-result` hands it a stub with only `status.phase: Succeeded` (L449-452). So `hitl_approved` falls back to the marker, and `duration_seconds` is absent → latency `not_scored`, `maxDurationSeconds` gate never engages. Add a variant that pipes the actual workflow object (`{{workflow.status...}}` or a post-run `argo get -o json`) so the stronger path gets test coverage before it ships to work.

2. **The eval only runs on the happy path — failures are filtered out, not scored.** `prove-result` has `grep -Fq` asserts (L398-404) and `evaluate-lifecycle` depends on it. If specialists miss their markers, `prove-result` fails and the eval **never runs**. For a promotion gate this is backwards: a failed agent run produces *no scorecard entry* rather than a recorded FAIL. The scorecard should capture failing runs (that's where the signal is). Decouple eval from the happy-path assert, or run eval with `depends: prove-result.Failed || prove-result.Succeeded`.

3. **HITL gate is weaker than it looks.** `human-review` is a genuine Argo `suspend: {}` (good). But `hitl_approved` is inferred from the hardcoded `HITL_STATUS: resumed` marker, not from inspecting the suspend node's resolution — the real check (`node_phase_succeeded(..., ["human-review","hitl"])`) is bypassed because nodes aren't in the stub. The gate currently trusts a string, not the workflow state.

4. **The per-agent triage scorer (`score-agent-run.py`) is wired into nothing.** It's the original Phase-1 MVP and the more defensible scorer (it matches tool trajectories and diagnosis terms against a real run), yet no workflow invokes it — only the lifecycle path is wired. State this gap: the triage scorecard is local/manual-only today.

---

## 🟢 Minor

- `apk add python3 py3-yaml` on every run adds a runtime dependency on the alpine package CDN. In an air-gapped or egress-restricted work cluster the eval step will fail. Trade-off of the no-custom-image choice — note it in the handoff and consider a vendored/mirrored repo for the work environment.
- `ticket_url` is passed as the literal `PLACEHOLDER_GITLAB_ISSUE_URL` (workflow L191) — public-safe ✓, and the leak scanner passes it.
- The split-string secret regex (`"api"+"[_-]?key"...` in both scorers) is cosmetic obfuscation; harmless but slightly obscures intent — a comment would help the next reader.
- ConfigMap (`kustomization.yaml`) mounts only the lifecycle scripts (`reporting`, `collect-lifecycle-evidence`, `score-lifecycle-run`, `summarize-agent-scores`) — correct for this path, but confirm `score-agent-run.py` gets its own packaging when it's eventually wired.

---

## Recommended next PR

1. Surface the "lifecycle score is synthetic in the demo" caveat in the demo README and the scorecard HTML, with the same prominence it has in the handoff doc.
2. Feed the collector the real Argo workflow object (with `status.nodes`) so `node_phase_succeeded` / duration / the HITL state check actually run, and so a deliberately-broken specialist produces a recorded FAIL.
3. Wire `score-agent-run.py` into at least one real triage run (single agent, real A2A response captured to the run JSON) so the deterministic per-agent scorecard has live coverage — that's the scorer with the strongest safety story.

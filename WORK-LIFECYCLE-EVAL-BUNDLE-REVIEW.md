# Review: Lifecycle Evaluation Review-Manager Handoff Bundle

**Scope:** `work-agent-bundles/lifecycle-evaluation-review-manager` plus the
`observability/agent-evals` implementation it points at.

**Question asked:** Is this bundle good enough to hand to another work-environment
agent so they can reproduce the full evaluation framework (offline scoring,
online Argo eval, lifecycle scoring, metrics export, review-manager routing,
storage/access/retention, audit traceability)?

**Verdict:** **Ready with minor fixes for the *design/offline* handoff. Needs
material changes before the *online + review-manager + RBAC* claims can be
handed off as "implemented".** See blockers below.

---

## 1. Findings, ordered by severity

### BLOCKER-class (fix before handoff if the receiving agent will trust the online/routing claims)

#### F1 — Online eval cannot fail; it scores canned all-pass markers
- **Where:** `a2a/smart-triage-fanout-demo/workflow.yaml` (`prove-result`, lines ~722–755);
  `observability/agent-evals/scripts/collect-lifecycle-evidence.py` (`MARKERS`, `marker_lifecycle`);
  `observability/agent-evals/argo/lifecycle-eval-hook-example.yaml` (`collect-marker-evidence`).
- **Problem:** The online lifecycle-run JSON is built **only** from proof-marker
  text, and that marker block is hard-coded to success (`REMEDIATION_EXECUTED: yes`,
  `VERIFICATION_PASSED: yes`, `TICKET_UPDATED: yes`, `HITL_STATUS: resumed`)
  regardless of what the specialists actually returned. Result: every online run
  scores `1.0 passed=true`. The homelab evidence confirms this — only a passing
  online run was ever produced; the below-threshold case was exercised **offline
  only**.
- **Why it matters:** The bundle sells "online evaluation" as a runtime audit
  gate, but as wired it proves plumbing, not scoring. A receiving agent will
  conclude online eval is differential when it is not.
- **Recommendation:** (a) Add an online **negative fixture** — a hook variant
  that feeds failing/missing markers and asserts `score < threshold` and non-zero
  exit. (b) State explicitly in `HOMELAB-VERIFICATION-EVIDENCE.md` and
  `ARCHITECTURE-DECISION.md` that the current online path replays canned markers
  and that real differential online scoring requires a live evidence collector
  (kagent audit log / OTel / agentgateway), which is not yet built.

#### F2 — `cluster_mutation_before_hitl` is hard-coded `False` in the online collector
- **Where:** `scripts/collect-lifecycle-evidence.py:269`.
- **Problem:** The strongest safety hard gate (`hardFailOnMutationBeforeApproval`)
  can **never fire** from collected online evidence, because the collector always
  sets `cluster_mutation_before_hitl: False` and only derives `executed_after_hitl`
  from `remediation_executed AND hitl_approved`. Offline fixtures can set it; the
  online path cannot detect it.
- **Why it matters:** "Evaluation should not own remediation permissions" and
  "mutation-before-HITL is a hard fail" are headline safety claims. Online they
  are unenforceable.
- **Recommendation:** Derive mutation-before-HITL from real signals (timestamps
  of mutation nodes vs. HITL resume node) in the collector, or document that this
  gate is **offline-only** until a real collector exists. Do not present it as an
  online guarantee.

#### F3 — Evaluator runs under a mutation-capable ServiceAccount (RBAC boundary violated)
- **Where:** `argo/lifecycle-eval-hook-example.yaml:12` and the smart-triage
  workflow both run as `serviceAccountName: smart-triage-fanout-workflow`. That SA
  is used by `normalize-incident` to **POST ConfigMaps to the Kubernetes API**
  (`workflow.yaml:410–417`).
- **Problem:** `ARCHITECTURE-DECISION.md` and `DATA-STORAGE-ACCESS-TRACEABILITY.md`
  both assert the evaluator is "evaluator-only / no mutation". In practice the
  eval template inherits a cluster-write SA. There is **no dedicated evaluator SA
  / Role** in `observability/agent-evals/kustomization.yaml` (only the fleet-exporter
  has its own RBAC).
- **Recommendation:** Ship a minimal `ServiceAccount` (no mutation, no secret
  read) for `agent-lifecycle-eval`, bind it in the kustomization, and reference it
  from the hook example. Until then, the RBAC tables in the docs are aspirational
  and should be labelled as target-state, not current-state.

#### F4 — Review-manager routing is described, not implemented
- **Where:** `grep` shows `review-manager` appears only in bundle markdown,
  markers, and the chaos sample JSON — **never** in a workflow step, script, or
  agent CRD.
- **Problem:** The bundle title, DoD, and `REVIEW_MANAGER_ROUTED: yes` marker
  imply an automated route for failing runs. There is no ticket-create-on-fail
  step, no review-manager agent manifest, and the eval step is terminal (see F5).
  The marker passes `verify-bundle.sh` purely because the literal string exists in
  docs.
- **Recommendation:** Either (a) add a real routing stub (an Argo step that, on
  non-zero eval exit, emits the `DATA-STORAGE...` audit block / creates a review
  ticket payload), or (b) relabel every "routed" claim as "**route defined,
  manual**" so the receiving agent does not assume automation exists.

### HIGH

#### F5 — Eval step is terminal and does not gate ticket closure (contradicts stated principle)
- **Where:** `a2a/smart-triage-fanout-demo/workflow.yaml` — `evaluate-lifecycle`
  is the last DAG node (lines ~305–344). `ticket_closed: "false"`, and no
  downstream step consumes its pass/fail. The hook example
  (`lifecycle-eval-hook-example.yaml:64`) goes further and passes
  `ticket_closed: "true"` **into** the evaluator — i.e. ticket already closed
  before eval.
- **Problem:** Directly contradicts the project rule "ticket closure should
  happen only after successful verification/evaluation for high-risk flows" and
  the `ARCHITECTURE-DECISION.md` diagram (`ticket close only if eval passed`).
- **Recommendation:** Reorder so a `close-ticket` step depends on
  `evaluate-lifecycle` succeeding, and make the canonical hook example model
  `ticket_closed: "false"` going into eval, closing only after. Right now the
  reference example teaches the wrong order.

#### F6 — `threshold` in the request payload is not the threshold the scorer uses
- **Where:** `requests/lifecycle-evaluation-request.yaml:16` sets `threshold: 0.8`.
  The scorer uses the **case-embedded** `minScore` (`score-lifecycle-run.py:229`)
  — `0.85` for `pod-crashloop-hitl-remediation`, `0.8` for `chaos-pod-delete`.
- **Problem:** Two sources of truth. A receiving agent tuning `threshold` in the
  request will see no effect; the gate lives in the case YAML.
- **Recommendation:** State that `spec.scoring.minScore` in the case is
  authoritative, and either wire the request `threshold` through or delete it.

### MEDIUM

#### F7 — Documented metric label set overstates what `metrics.py` emits
- **Where:** `DATA-STORAGE-ACCESS-TRACEABILITY.md` "Allowed labels" lists
  `environment`, `team`, `service` (and `agent`). `metrics.py` lifecycle output
  emits only `case_id`, `run_id`, `workflow_name`, `dimension`; `agent` appears
  only on `agent_eval_*`, never lifecycle.
- **Problem:** Drift between the access-control design and the implementation. The
  "independent, reusable metrics library" claim is fine, but the label contract is
  inaccurate.
- **Recommendation:** Trim the allowed-label list to what is emitted, or add the
  labels to `metrics.py` and a fixture proving cardinality stays bounded.

#### F8 — `run_id` / `workflow_name` as metric labels are unbounded cardinality
- **Where:** `metrics.py` `render_lifecycle_eval_metrics` labels every series with
  `run_id` and `workflow_name` (one per Argo run).
- **Problem:** The design explicitly forbids "high-cardinality" labels, but
  per-run IDs are exactly that for a Prometheus gauge scraped over time. Acceptable
  for a push/textfile snapshot, dangerous for a scraped endpoint.
- **Recommendation:** Document that these metrics are **batch/textfile-exported
  per run** (not a long-lived scrape target), or move `run_id` to an exemplar /
  log field and keep only `case_id`/`workflow_name` (bounded) as labels.

#### F9 — Heredoc injection / Argo param-size failure case for `workflow_json` and `marker_evidence`
- **Where:** `argo/lifecycle-eval-workflow-template.yaml:122–128` — params are
  substituted into quoted heredocs (`WORKFLOW_JSON`, `MARKER_EVIDENCE`).
- **Problem:** If real captured evidence ever contains a line equal to the heredoc
  delimiter, the script breaks; and a full (non-stub) Argo workflow JSON can exceed
  Argo's parameter size limit. Today it only works because `prove-result` emits a
  tiny stub.
- **Recommendation:** Pass evidence as an artifact/volume file rather than a
  templated parameter, or note the stub-only constraint and add a guard.

### LOW / cosmetic

- **F10 — Redundant ConfigMap volume.** `lifecycle-eval-workflow-template.yaml`
  defines `agent-eval-runtime` at **both** `spec.volumes` and `template.volumes`.
  After the documented fix, only the template-level one is used by `templateRef`
  callers; the spec-level block is dead. Remove it to avoid confusion. (The
  `templateRef`/ConfigMap-on-template pattern itself is **correct** — that is the
  one thing the homelab run actually proved.)
- **F11 — Leak scan covers only the run JSON.** `find_leaks`
  (`score-lifecycle-run.py:97`) scans the lifecycle-run payload but not the
  generated `summary.md` or `.prom`. Derived files are low risk, but the
  sanitization claim is narrower than it sounds.
- **F12 — `verify-bundle.sh` is self-referential.** It greps the bundle dir for
  marker strings that also exist as literals in `README.md`/`CHECKLIST.md`, so it
  passes by finding documentation, not by running an eval. The README discloses
  this, which is good — but consider having the verifier actually invoke the
  offline scorer on the sample runs so "passing" means something.
- **F13 — No schema validation, no scorer unit tests.** `schemas/*.json` exist but
  nothing validates run/result JSON against them, and there are no pytest cases for
  the scorer's hard-gate logic. Add at least one schema-validate step and a couple
  of golden assertions.
- **F14 — Internal-meeting context in a public repo.** `MEETING-ACTION-COVERAGE.md`
  / `GITLAB-TICKET.md` reference "the Microsoft discussion" and "assigned to David".
  Not secret, but it is internal planning context in a public-safe bundle. Consider
  neutralizing to "the planning meeting".

---

## 2. Meeting-action design coverage (the six assigned items)

| Action | Coverage | Gap |
| --- | --- | --- |
| Evaluation framework design doc | **Good** — README + LIFECYCLE-EVALUATION + OFFLINE-ONLINE design docs present | none material |
| Offline + online eval designs | **Partial** — offline is real and proven; online is plumbing-only (F1) | online scoring is canned |
| Key evaluation metrics | **Good** with caveats — 4 metric families + subscores, independent `metrics.py` | label drift F7, cardinality F8 |
| Inline vs separate evaluator | **Good** — clear decision (separate reusable step, inline public image, ConfigMap scripts); pattern verified | none material |
| Data storage / access model | **Adequate on paper** — data-class + RBAC tables | RBAC not enforced in manifests (F3) |
| Audit retention + traceability | **Adequate on paper** — retention table + traceability fields + audit block | audit block is a template; no automated emitter (F4) |

The **design-document** deliverables are genuinely strong. The weakness is the gap
between the written access/audit/routing design and what the manifests actually
enforce.

---

## 3. Specific questions answered

- **Is the public-image inline evaluator practical?** Yes. `alpine:3.19` +
  `apk add python3 py3-yaml` + ConfigMap-mounted scripts is a sound work-friendly
  choice and was actually run. Main caveat: `apk add` at runtime needs egress to
  the Alpine mirror — call that prerequisite out for locked-down work environments,
  and consider pinning package versions.
- **Is the `templateRef` / ConfigMap mount pattern correct?** Yes, after the
  documented fix (volume on the reusable template, not only at `spec`). Clean up the
  redundant spec-level volume (F10).
- **Are metrics independent and reusable?** The library is genuinely independent
  (`metrics.py` is pure, used by both offline and online). But the label contract is
  inaccurate (F7) and cardinality is unbounded as labelled (F8).
- **Are access-control / audit boundaries clear enough?** Clear in prose,
  **not enforced** in manifests (F3, F4). A receiving agent reading only the docs
  would over-trust the boundaries.
- **Is the handoff actionable for another agent?** For offline + design: yes,
  highly. For online + routing + RBAC: only if the gaps above are relabelled as
  target-state or implemented.

---

## 4. Blockers for final handoff

1. **F1** — online eval scores canned all-pass markers; no online failing test.
2. **F2** — top safety gate (mutation-before-HITL) unenforceable online.
3. **F3** — evaluator runs under a mutation-capable SA, contradicting the RBAC design.
4. **F4** — review-manager routing is documented only; marker passes on a string match.

Each is a blocker **only** against the claim "this is implemented". All four are
discharged cheaply by **relabelling those four items as target-state/manual in the
docs** if the intent is to hand off a *design + offline-proven* bundle. If the
receiving agent is expected to find working online gating and routing, they must be
built.

---

## 5. Nice-to-have (non-blocking)

- Online negative-path hook fixture (pairs with F1).
- Dedicated evaluator SA/Role in the kustomization (pairs with F3).
- Real routing stub that emits the audit block on eval failure (pairs with F4).
- Wire request `threshold` or delete it (F6).
- Schema-validate + scorer unit tests (F13).
- Make `verify-bundle.sh` actually run the offline scorer (F12).
- Evidence as artifact instead of templated heredoc param (F9).
- Neutralize internal-meeting wording (F14).

---

## 6. Final verdict

> **Ready with minor fixes** as a **design + offline-evaluation** handoff — the
> offline scorer, hard gates, metrics library, inline-vs-separate decision, and
> `templateRef`/ConfigMap runtime are real and were actually exercised.
>
> **Needs material changes before handoff** if it is presented as a working
> **online gating + review-manager routing + enforced-RBAC** system. The fastest
> safe path is to relabel F1–F4 as target-state/manual in the bundle docs;
> otherwise implement the online negative fixture, a dedicated evaluator SA, and a
> real routing step.

# Rollout order

The work agent adds this bundle **one phase at a time**, easiest first, and stops at each gate until a human says go. The table is the same one that opens `WORK-AGENT-PROMPT.md`.

| Phase | Scope | Needs | Gate: stop and report |
|---|---|---|---|
| **0. Readiness (no changes)** | Confirm the pinned versions; that **Grafana is reachable and its Loki, Tempo and Mimir/Prometheus datasources are healthy**; that **the applications are configured to send traces, logs and events** (find a recent trace and log for each); that Alertmanager exists and can call a webhook; that the model routes answer | Read access only | A readiness table. Anything red is reported, **not built**. Do not install or repair Grafana |
| **1. Evaluation: Warden, then Assay** | Steps 1 to 12 | Rows 1 to 6 of `HUMAN-PREREQUISITES.md` (gateway auth, tools, models, CI; **no monitoring needed**) | Per-case verdicts and the negative tests, with receipts. This is the easiest integration |
| **2. Guard: detection and proposals only** | Step 13, **detector and proposals, no enforcement** | Phase 0 green for telemetry; Phase 1 done | `detect.py` clean on good runs, `forbidden_tool` on a bad one, `degraded` on a gap; a proposal accepted by server dry-run, nothing applied |
| **3. LGTM integration** | Steps 14 and 15: spend guards, model probe, alert intake, the agent-health agent | Phase 0 fully green; Phase 2 done; a separate model route for the overseer | One bounded overseer run (tool budget on, stop at the first failure), then one real alert end to end |
| **4. Direct blocking** | The `enforce.py` part of step 13 | Written owner approval of which signals may auto-block; a narrow identity for `enforce.py` | Applied, read back and released on a **throwaway route**, with a real request proving the Deny blocks |


Why this order: evaluation needs no monitoring, so it can be proven alone; the Guard and the alert loop need Grafana and telemetry that are confirmed healthy first; direct blocking is a real power over the cluster, so it comes last and needs written owner approval.

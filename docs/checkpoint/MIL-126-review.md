# MIL-126 Code Review — A2A + HITL + Skills Demo

**Scope reviewed:** `a2a/kagent-hitl-skills-demo/**`, `platform/teams-hitl/sensor.yaml`, `platform/teams-hitl/README.md`, `a2a/README.md`, and supporting files (`eventsource.yaml`, `mock-bot/app.py`).

**Verdict:** No blocking issues. Demo is runnable, validated server-side and live, sanitized, and meets the four success criteria. A small number of medium / low findings around demo determinism, RBAC tightness, container startup robustness, and convention drift are worth addressing.

---

## Findings (by severity)

### Medium

#### M1. "Three agents talking over A2A" is implicit, not asserted
**File:** `a2a/kagent-hitl-skills-demo/workflow.yaml` (`call-coordinator` template, lines 73–117) and `agents.yaml` (lines 130–138).

The workflow only ever POSTs to `demo-a2a-coordinator-agent`. Whether the skill-loader and HITL agents are actually invoked depends on the LLM coordinator deciding to call its `Agent` tools — there is no guarantee in code that two more A2A calls occur. Live evidence shows it worked (`A2A_CALLS: skill-loader, hitl-approval`), but a model regression, prompt drift, or modelConfig swap could silently break MIL-126's central claim and still report `Succeeded`.

**Suggested fix (cheapest, keeps the orchestrator pattern):** add an assertion in `call-coordinator` before `cat`:
```sh
grep -q 'A2A_CALLS: skill-loader, hitl-approval' /tmp/agent_response.txt
grep -q 'SKILLS: ' /tmp/agent_response.txt
```
**Stronger fix:** add two extra DAG tasks that POST directly to `demo-skill-loader-agent` and `demo-hitl-approval-agent` services and capture their `result.artifacts[].parts[].text`. That makes the three-agent A2A path provable from kubectl output alone, independent of the coordinator LLM.

#### M2. mock-bot startup silently degrades if `pip install` fails
**File:** `a2a/kagent-hitl-skills-demo/mock-bot-runtime.yaml` lines 27–29.

```yaml
args:
  - |
    pip install --no-cache-dir -r /app/requirements.txt >/tmp/mock-bot-pip.log 2>&1
    exec uvicorn app:app --host 0.0.0.0 --port 8080 --app-dir /app
```
No `&&` and no `set -e`. If pip fails (proxy/PyPI hiccup) the script still execs uvicorn, which crashes with `ModuleNotFoundError`. The pip log is written but not surfaced — the deployment merely CrashLoops with a confusing uvicorn import error, not the real cause.

**Suggested fix:**
```yaml
args:
  - |
    set -eu
    pip install --no-cache-dir -r /app/requirements.txt
    exec uvicorn app:app --host 0.0.0.0 --port 8080 --app-dir /app
```
Even better for a public demo: pre-build a small image (`ghcr.io/<org>/mil-126-mock-bot:dev`) so runtime `pip install` is removed entirely — it also avoids egress dependence on PyPI from inside the cluster, which is a non-trivial assumption for hardened AKS rings.

#### M3. workflow-rbac.yaml grants more than the workflow needs
**File:** `a2a/kagent-hitl-skills-demo/workflow-rbac.yaml` lines 18–24.

The Role grants `create, get, list, watch, patch` on `workflows`, `workflowtaskresults`, and `configmaps`. The actual scripts in `workflow.yaml`:
- shell out only to `curl` and `jq`,
- write outputs via `valueFrom.path` (handled by the executor SA, not by the workflow pod itself),
- never touch ConfigMaps,
- never enumerate other workflows.

Argo workflow pods only need `workflowtaskresults: [create, patch]` for the executor to report node results. The `workflows` and `configmaps` rules are dead privilege.

**Suggested fix:**
```yaml
rules:
  - apiGroups: [argoproj.io]
    resources: [workflowtaskresults]
    verbs: [create, patch]
```
If you decide to add a ConfigMap-write step later, add the rule then.

---

### Low

#### L1. Label convention drift — `milano2.dev/demo` vs project guideline
**Files:** `a2a/kagent-hitl-skills-demo/agents.yaml` (3x), `workflow.yaml` (line 8), `workflow-rbac.yaml` (3x), `mock-bot-runtime.yaml` (lines 8, 62).

`CLAUDE.md` documents the conventions for this public/sanitized repo as `platform.com/team` and `platform.com/type`. New demo resources use `milano2.dev/demo: a2a-hitl-skills` instead. `app.kubernetes.io/part-of: mil-126-demo` is fine and well-formed, but the `milano2.dev/*` key is a private-domain label that conflicts with the documented sanitized convention.

**Suggested fix:** swap `milano2.dev/demo: a2a-hitl-skills` for `platform.com/team: mil-126-demo` (or whatever the agreed team name is) and add `platform.com/type: demo`. Do this in all five files; grep already catches every instance.

#### L2. Cleanup section in README misses script-installed resources
**File:** `a2a/kagent-hitl-skills-demo/README.md` lines 77–85.

`scripts/run-demo.sh` applies `platform/teams-hitl/eventsource.yaml` and `platform/teams-hitl/sensor.yaml`, but the README cleanup block does not list them. After running the demo, three Sensors and one EventSource remain in `argo-events`. They are reusable, but if a reviewer runs the demo expecting README-documented cleanup they will leave residue.

**Suggested fix:** add a sentence clarifying that the Teams HITL Sensor/EventSource are platform-shared and intentionally not torn down — or extend cleanup to:
```bash
kubectl delete -f platform/teams-hitl/sensor.yaml --ignore-not-found
kubectl delete -f platform/teams-hitl/eventsource.yaml --ignore-not-found
```
with a note "skip these if other workflows depend on the HITL gate".

#### L3. `call-coordinator` declares an unused output parameter
**File:** `a2a/kagent-hitl-skills-demo/workflow.yaml` lines 78–82.

```yaml
outputs:
  parameters:
    - name: response
      valueFrom:
        path: /tmp/agent_response.txt
```
No downstream task references `tasks.coordinator-before-approval.outputs.parameters.response` or the `after-approval` equivalent. Harmless but dead config.

**Suggested fix:** either delete the `outputs` block or actually consume `response` in the next step (the request-approval rationale could be derived from it).

#### L4. mock-bot pod has no `securityContext`
**File:** `a2a/kagent-hitl-skills-demo/mock-bot-runtime.yaml`.

No `runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, or `seccompProfile`. The image runs `pip install` at runtime, which requires a writable site-packages path, so `readOnlyRootFilesystem: true` would need an `emptyDir` mount over `/usr/local/lib/python3.12/site-packages`. In a cluster with PodSecurity admission `restricted` enforced on `argo`, this pod will be rejected.

**Suggested fix (combined with M2 by switching to a pre-built image):**
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 65532
  allowPrivilegeEscalation: false
  capabilities:
    drop: [ALL]
  seccompProfile:
    type: RuntimeDefault
```

#### L5. Image tags are floating
**File:** `workflow.yaml` (`alpine:3.19`, lines 84, 126) and `mock-bot-runtime.yaml` (`python:3.12-slim`, line 23).

Floating tags drift on pulls. For demo this is acceptable, but pinning by sha (`alpine:3.19@sha256:…`) makes the demo reproducible against the public artefact a reviewer expects.

---

### Informational

#### I1. Sensor split correctly handles the Argo Events v1.9 bug
**File:** `platform/teams-hitl/sensor.yaml`.

Three sensors, each with one dependency and one filter, each `conditions:` field naming its single dependency — this is exactly how Argo Events v1.9 needs it to be wired to avoid the previous behaviour where one Sensor with three dependencies on the same event would fire all matching triggers (the stop-on-approved regression). Header comment accurately documents the constraint. Good.

#### I2. Demo script port-forward race is handled
**File:** `scripts/run-demo.sh` lines 76–91.

Background `kubectl port-forward` followed by a 20s `/health` poll. If the PID dies the script dumps the log and exits. Reasonable.

#### I3. Re-run safety is acceptable
- `kubectl apply -f agents.yaml` / RBAC / Sensor → idempotent.
- `kubectl create configmap … --dry-run=client -o yaml | kubectl apply -f -` → idempotent.
- Workflow uses `generateName`, so each invocation produces a new name with `ttlStrategy` GC.
- Local port collision handled by walking through `18081..18085`.

One small gap: if the first run left a Failed workflow, the script doesn't surface or clean it. The `argo` namespace will eventually accumulate failed workflow records until TTL. Acceptable.

#### I4. Sanitization — clean
- No secrets, no real cluster names, no AKS subscription/tenant IDs, no private hostnames, no real IPs.
- Sample remediation (`kubectl rollout restart deploy/example-api -n demo`) is generic.
- Internal cluster DNS (`*.kagent`, `*.argo`, `*.argo-events`) is the correct level of detail for a public demo.
- README examples use `localhost` and port-forward, not external hostnames.

#### I5. A2A endpoint usage matches `a2a/README.md`
The workflow POSTs to `http://demo-a2a-coordinator-agent.kagent:8080/` — the in-cluster service root, which is what the kagent Agent pod exposes for direct A2A. The `a2a/README.md` `/api/a2a/kagent/{agent-name}/` form is for going through the controller. Both forms are correct; the live run confirms the chosen one works.

#### I6. Public-safety placeholders are consistent
`{{HITL_CALLBACK_URL}}` is already used in `platform/teams-hitl/eventsource.yaml` line 8. The new demo files do not introduce any half-substituted environment-specific values. No new placeholders are needed.

---

## Verification gaps / residual risks

1. **Coordinator LLM determinism (M1):** the success criterion "three agents talked over A2A" is only verifiable by reading the coordinator's freeform text response. If `default-model-config` is later pointed at a smaller/cheaper model, the demo might pass the workflow phase check but fail the demonstrative claim. Either add the `grep -q` assertions (M1 suggested fix) or wire the workflow to all three agents directly.
2. **No negative-path test:** the demo runs only the approved branch. The rejected and expired sensors (`teams-hitl-reject-sensor`, `teams-hitl-expire-sensor`) have been server-side validated but no live test exists in the repo. A 10-line second script that POSTs `decision=rejected` and asserts workflow phase ends `Failed` would close that gap and prove the Sensor split fixed the v1.9 regression.
3. **Cluster PSA assumption (L4):** the live run on `red` succeeded, so `argo` PSA is not enforcing `restricted`. If this is shipped to a more hardened ring, mock-bot will be rejected.
4. **PyPI egress at startup (M2):** mock-bot needs network egress to PyPI at pod startup. Hardened ring egress policies may block this. A pre-built image removes the risk.

---

## Suggested commit boundaries (if you act on these)

1. `M1` + I1 docs touch → one commit ("MIL-126: assert A2A markers in workflow").
2. `M2` + L4 → one commit ("MIL-126: pre-built mock-bot image + securityContext").
3. `M3` → one commit ("MIL-126: tighten workflow RBAC to least privilege").
4. `L1` → one commit ("MIL-126: align demo labels with platform.com/* convention").
5. `L2` + `L3` + `L5` → one commit ("MIL-126: docs cleanup, drop unused output, pin images").

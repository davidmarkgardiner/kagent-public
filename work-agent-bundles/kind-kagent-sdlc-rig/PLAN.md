# Kind kagent SDLC rig — plan

Status: bounded PoC and annotated board polling deployed and verified
(2026-09-27). One additional issue completed entirely on scheduled polls,
including CI rework; a shared Lease passed live contention. See `README.md`,
`evidence/2026-09-27-live-run.md`, `evidence/2026-09-27-board-polling.md`,
and `evidence/2026-09-27-unattended-lease-canary.md` for proof and limits.

Goal: run the OpenRig PM + workers pattern inside Kubernetes. A GitLab issue
lands on the board, a kagent PM agent breaks it down and assigns slices to
kagent worker agents in the same cluster over A2A, workers change the repo in
GitLab, and the PM accepts or returns the work.

Original host target: local kind cluster. Actual PoC host: the existing
Proxmox Kubernetes cluster, with one small control-plane VM and both worker
VMs off for resource headroom. Model: Kimi (`kimi-for-coding`) through the
already installed agentgateway. Harness: the cluster's existing kagent release.

## 1. What already exists (reuse, don't rebuild)

| Need | Prior art | Status |
|---|---|---|
| Kimi as kagent model | `platform/agentgateway/modelconfig-openai-compatible-external-models.yaml`, `backend-openai-compatible-external-models.yaml` | Kimi route proven 2026-07-09 (Proxmox) |
| kagent agent on Kimi answering A2A | `a2a/buzz-kagent-bridge-poc/README.md` | Proven |
| Label on GitLab issue -> planner agent -> PRD + child issues | `work-agent-bundles/debt-calculator-agentic-factory/gitlab-label-plan-poc.yaml`, `evidence/gitlab-label-plan-poc.md` | Proven 2026-08-08 (replayed webhook) |
| Planner / builder / tester / reviewer agent specs | `debt-calculator-agentic-factory/substrate-agents.yaml` | Specs exist, builder->MR loop not live-proven |
| Scoped GitLab MCP (no merge/delete/settings, path allow-list) | `debt-calculator-agentic-factory/gitlab-delivery-mcp.yaml`, `gitlab-mcp-agentgateway.yaml` | Proven for issues; path allow-list is debt-calculator specific |
| Orchestrator calling specialists as tools | `agents/cluster-health-sentinel/05-orchestrator-agent.yaml` (`tools: - type: Agent`) | Pattern in use |
| Handoff rule | `debt-calculator-agentic-factory/GITLAB-SOURCE-OF-TRUTH-HANDOFF.md` | Hard lesson: V4 file-in-A2A timed out |

## 2. OpenRig -> kagent mapping

| OpenRig (terminals, LAN) | kagent (kind) |
|---|---|
| Rig on a host | Namespace `sdlc-rig` on the existing cluster |
| `pm-lead` seat | `Agent/sdlc-pm` |
| Worker seats (Codex, Claude, Kimi, Cursor) | `Agent/sdlc-builder`, `sdlc-tester`, `sdlc-reviewer` (all Kimi to start) |
| `rig queue` durable qitem | GitLab issue + board label (the board is the queue) |
| `rig send` wake | A2A `message/send` (PM calls worker as `type: Agent` tool) |
| SSH tunnel between hosts | Cluster DNS; agentgateway later for policy/telemetry |
| Per-VM provider login | `ModelConfig` + Secret |
| `openrig-pilot-preflight.py` | `scripts/preflight.sh` readiness gate (below) |
| PM acceptance, human boundary | Draft MR only; merge is always human |

Board labels (queue states):

```text
agent:plan -> agent:build -> agent:test -> agent:review -> agent:accepted
                   ^                           |
                   +------ agent:changes <-----+
```

## 3. Target flow

```text
GitLab issue labelled agent:plan
  -> labelled board CronJob poller
  -> sdlc-pm (Kimi): read issue, create one child; poller labels agent:build
  -> sdlc-pm calls sdlc-builder over A2A with {project, parent IID, child IID, branch}
       builder commits to agentic/<iid> branch via GitLab MCP, returns {branch, sha, paths}
  -> GitLab CI runs
  -> sdlc-pm calls sdlc-tester  -> {pipeline id, verdict}
  -> PM opens one draft MR, then calls sdlc-reviewer -> tagged MR note id, verdict
  -> pass: PM gives acceptance receipt; poller labels agent:accepted
     fail: poller labels agent:changes; PM re-calls builder with findings
```

A2A payloads carry references only (IIDs, branch, SHA, pipeline ID, MR IID).
Never source code.

## 4. Key decision: synchronous vs board-driven dispatch

| Option | How | Pro | Con |
|---|---|---|---|
| A. PM calls workers as tools (recommended first) | `tools: - type: Agent` on `sdlc-pm` | Closest to "PM assigns, worker returns"; native kagent A2A; least moving parts | Worker runtime sits inside PM's turn; long builds risk timeouts |
| B. Board-driven | Label change triggers each worker independently (Argo Events/poller); PM only plans and accepts | No nested timeouts; mirrors OpenRig durable queue | Needs trigger plumbing per label; more YAML |

The deployed hybrid keeps PM-to-worker A2A within each stage. A Kubernetes
CronJob resumes from GitLab labels and artifacts between stages, so a timeout
does not force the whole workflow to restart.

## 5. Phases

### Phase 0 — prerequisites (completed for the bounded PoC)

- [x] Existing in-cluster Kimi provider Secret validated through agentgateway.
- [x] Sandbox GitLab project plus a new 30-day project-scoped access token
      (`api`, Developer), stored only as a Kubernetes Secret in `sdlc-rig`.
- [x] Existing Proxmox cluster reused; no kind cluster or additional VM
      created. Both Kubernetes workers remain off.

### Phase 1 — cluster + model (done on existing cluster)

1. Reuse the existing Kubernetes control plane and kagent/agentgateway CRDs.
2. Reuse the existing Kimi provider Secret in the gateway namespace; no
   credential value is copied into this repository.
3. Deploy `ModelConfig/kimi-gateway` in `sdlc-rig`, pointing at the existing
   agentgateway route; the client-side Secret contains only a placeholder.
4. Test T1–T3 through the live route.

### Phase 2 — A2A PM -> worker (today)

1. `Agent/sdlc-worker-echo` (no tools).
2. `Agent/sdlc-pm` with `type: Agent` tool -> `sdlc-worker-echo`.
3. Test T4.

### Phase 3 — GitLab loop

The live PoC used the fixed sandbox project and four-file allowlist. The
transfer renderer now accepts an explicit project, target branch, and file
profile; deployment of that complete rendered stack in a target cluster
remains future work.

1. Deploy generalized GitLab MCP (copy `gitlab-delivery-mcp.yaml`; make path
   allow-list a per-repo profile ConfigMap, branch prefix `agentic/`).
2. `RemoteMCPServer/sdlc-gitlab-mcp`.
3. Role agents from `substrate-agents.yaml`, renamed, each with minimal
   `toolNames`:
   - pm: `get_issue, update_issue, create_issue, create_branch, create_draft_mr`
   - builder: `get_issue, get_file, commit_files, branch_pipeline_status`
   - tester: `get_file, pipeline_status`
   - reviewer: `get_file, pipeline_status, create_mr_note`
4. Test T5, then T6.

### Phase 4 — board trigger (done for bounded sandbox)

- A Kubernetes CronJob polls the fixed GitLab sandbox every two minutes for
  `sdlc-rig-poc` issues. GitLab labels and child, branch, pipeline, MR, and
  review-note identity are durable checkpoints. Each poll makes at most one
  model turn; `concurrencyPolicy: Forbid` serializes scheduled jobs.
- Two original issues completed to `agent:accepted` with draft MRs. A third
  issue completed entirely on scheduled polls, including failed-CI rework to
  a repaired green pipeline. The lab poller now uses a shared Lease so manual
  and scheduled Jobs contend on one lock; see README and the new evidence.

### Phase 5 — agentgateway

- Kimi already uses the existing agentgateway `/kimi/v1` route in this PoC;
  route health and a real response were verified.
- Still to do: route GitLab MCP through gateway for
  tool allow-list at the gateway, not only `toolNames`.
- Optional: A2A routes via gateway for cross-cluster workers (Proxmox/Geekom
  kind or k3s) — the in-cluster analogue of OpenRig cross-host.

## 6. Tests (gates, in order)

| ID | Test | Pass |
|---|---|---|
| T0 | Existing cluster Ready, node/host headroom, `agents.kagent.dev` CRD | CRDs present; no new VM |
| T1 | In-cluster request through agentgateway -> Kimi `chat/completions` | HTTP 200 and visible model reply |
| T2 | `ModelConfig/kimi-gateway` + agents | `Accepted=True, Ready=True` |
| T3 | `scripts/kagent-a2a-invoke.sh` -> hello agent (unique `messageId`) | task `completed` |
| T4 | PM asks echo worker "reply PONG-<nonce>" via agent tool | PM output contains nonce; worker session exists |
| T5 | PM reads sandbox issue via GitLab MCP | Correct title returned; no write |
| T6 | Issue #N `agent:plan` -> child issues -> branch commit -> CI -> review note -> draft MR | All references recorded in `evidence/RUN-<date>.md` |

## 7. Risks

| Risk | Mitigation |
|---|---|
| Kimi OAuth token vs API key; `kimi-for-coding` endpoint may restrict clients | Use console key; T1 before anything else; fallback Moonshot platform API (`api.moonshot.ai/v1`) |
| Nested A2A timeout (V4 lesson) | References only; `timeout: 300`; small slices; fall back to option B |
| Kimi thinking latency on builder | Lower `maxTokens`, one child issue per call |
| Builder can't run tests (MCP commit only) | GitLab CI is the test gate; sandbox builder (SandboxAgent) later |
| PAT blast radius | Project token, sandbox project, MCP refuses merge/delete/settings |
| No webhook ingress on kind | Poller (Phase 4) |
| Docker RAM | One kind cluster at a time |

## 8. Out of scope today

Merge, deploy, production GitLab projects, cross-cluster workers, Temporal.

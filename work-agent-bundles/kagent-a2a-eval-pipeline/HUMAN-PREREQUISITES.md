# Human prerequisites

Phase 1 (evaluation) needs rows 1 to 6 only. Grafana, telemetry and alert rows (8 and later) are Phase 0 checks and gate Phases 2 and 3; see `docs/rollout.md`.

The work agent cannot create these. Complete the sheet before handing over
[WORK-AGENT-PROMPT.md](WORK-AGENT-PROMPT.md). Use placeholders in anything you commit.

| # | Item | Why | Owner |
|---|---|---|---|
| 1 | Target agent(s) to evaluate and the kagent version in use (0.7.x or 1.x) | The URL and request shape depend on it | Platform |
| 2 | Agentgateway route to the A2A endpoint with **caller authentication**, plus a test token scoped to the eval agents | Assay and Warden call agents only through the gateway | Platform / Security |
| 3 | Read-only Kubernetes tool server and its exact tool names (for example the `aks-mcp` read tools) | They go in the contract's `allowedTools`; anything else a worker calls fails the gate | Platform |
| 4 | An approved model route for the agents and the evaluator | The evaluator needs a model too | Platform |
| 5 | GitLab project, a **protected runner tagged `kagent-eval`**, and these protected, masked CI variables: `AGW_BASE_URL`, `AGW_TOKEN`, `EVAL_KUBECONFIG`, `EVAL_IMAGE` | `.gitlab-ci.yml` fails closed without them | Platform / DevEx |
| 6 | A service account for `EVAL_KUBECONFIG` that can only create and delete `eval-*` namespaces and apply the fixtures into them | Assay seeds a fault in a throwaway namespace | Platform / Security |
| 7 | Runner image built from `Dockerfile`, mirrored internally and pinned by digest; the `busybox` fixture image mirrored too | Air-gap: nothing is pulled from the public internet | Supply chain |
| 8 | For Warden: the receiver that writes the GitLab issue after a PASS, and read access to read the issue back | Warden's ticket check reads the issue the receiver wrote | Receiver owner |
| 9 | Decision: where a worker's **first-try evaluator FAIL** routes on 1.x (a handoff cannot retry). Options: labelled `evaluation-failed` ticket, or reject and alert | The code currently rejects | Product owner |
| 10 | Decision: who owns an agent that fails Assay or Warden, and the escalation route | A gate that nobody reads is not a gate | Product owner |
| 11 | **A separate model route and credential for the overseer and the Guard**, not the one the watched agents use | A quota or outage on the shared route would take down the watcher together with the watched (a lesson from our software factory) | Platform |
| 12 | A human to review the first full run of each case against the real agent's answer | Scoring is key-term based; a person calibrates it | Agent owner |

## Do not do

- Do not point the evaluation at an agent with write tools (`k8s_apply_manifest`, delete, patch, exec).
- Do not store receipts in git or keep CI artifacts beyond the retention in `.gitlab-ci.yml`.
- Do not widen `allowedTools` to make a run pass. Fix the agent or the case.

# Replicate Assay and Warden for the approved agents

Execute this in the approved work environment only. Read [FRONT-SHEET.md](FRONT-SHEET.md) first, then
[HUMAN-PREREQUISITES.md](HUMAN-PREREQUISITES.md); stop and ask if any row is unfilled. The agents under test are
**read-only investigators**. This task evaluates them and gates their output. It does not remediate anything.

Rules: use only the named context and namespaces. Dry-run (`--dry-run=server`) before every apply. Keep tokens, hosts,
IPs and raw receipts out of git; use placeholders in anything committed. Stop at the first failed gate and report it with
its receipt. **Never claim a pass without a receipt, and never widen an allowlist to make a run pass.**

1. **Inventory.** Record the actual kagent version and API group (0.7.x `kagent.dev/v1alpha2`, or 1.x
   `api.kagent.dev/v1alpha3`), the gateway and route, the agent(s) to evaluate, their declared tools, and the model route. Read
   [docs/kagent-versions.md](docs/kagent-versions.md): the A2A path, request shape and tool-event location differ between versions.
2. **Prove the bundle offline.** Run `./verify-bundle.sh`. It must pass before you change anything.
3. **Prove plain A2A.** Call the target agent directly (no gateway) with a trivial read-only prompt. Inspect the real task status and
   the answer. Kagent returns errors inside HTTP 200, so a 200 proves nothing.
4. **Capture one real receipt per version in use** and compare it with `tests/fixtures/` (0.7.x: `a2a-live-agent-tool-completed.json`;
   1.x: `a2a-v1x-subagent-completed.json`). If tool-call or usage shapes differ, fix `normalize()` in `a2a_capture.py` and
   `verify_completion.py`, add a sanitized receipt as a new fixture and a test, and keep the old fixtures. `python -m unittest discover -s tests` stays green.
5. **Write a contract per agent.** Copy `completion-gate/contracts/sentinel-investigator.yaml`. Set `agent`, replace `allowedTools` with the exact
   read-only tool names from the real tool server, set `requiredTools` (at least one tool that looks at the live object and one at events or logs), the
   output `envelope` and `sections`, and the evaluator name for the version in use. Then regenerate the evaluator:
   `python completion-gate/render_evaluator.py completion-gate/contracts/*.yaml --model-config {{MODEL_CONFIG}} > completion-gate/manifests/completion-evaluator-agent.yaml`.
6. **Deploy Warden.** Apply the generated evaluator and wire it into the target agent following `completion-gate/manifests/sentinel-investigator-agent.yaml`
   (0.7.x) or the `subAgent` form in `docs/kagent-versions.md` (1.x). The worker must have **no** ticket-writing tool. Check the deployed Agent against its contract:
   `python verify_completion.py --contract <contract> --receipt <receipt> --agent-crd <agent.yaml>`.
7. **Assay cases.** For each agent, add a case under `cases/` (copy `triage-crashloop-bad-env.yaml`): a seeded fault in `fixtures/cluster/` plus a healthy decoy,
   the expected diagnosis and evidence terms, required and forbidden tools, budgets. `python tests/lint_cases.py cases` must pass. Have the agent owner review the
   first real answers against the key terms (HUMAN-PREREQUISITES row 11).
8. **Wire CI.** Set the protected variables, point the matrix in `.gitlab-ci.yml` at the real agent(s), keep `EVAL_REQUIRE_CONTRACTS=false` until every matrix agent has
   a contract, then set it to `true`. Confirm an MR from an unprotected branch fails closed.
9. **Run Assay through the gateway.** `a2a_capture.py --tier smoke --repeat 1`, then `--tier full --repeat 3`, each followed by `score_and_gate.py` with
   `--contracts-dir completion-gate/contracts`. Report each verdict, score and latency. A real fail is a valid result.
10. **Run Warden.** Send the real Sentinel finding (or a synthetic one) to the agent through the gateway. Verify with `verify_completion.py` including
    `--agent-crd`. Run it three times. Report PASS, FAIL and `reject` counts honestly: a correct block is a result, not a problem.
11. **Receiver read-back.** After the receiver writes the issue, run `verify_completion.py --readback issue.json`. Confirm the issue carries this run's incident key and the
    required labels, and that nothing is written when the route is `reject`.
12. **Negative tests.** Prove the gate blocks: a worker that skips the evaluator, one that calls a tool outside the allowlist, a tool error on a required tool, and
    a report changed after approval. Each must fail with its reason.
13. **Report.** Fill a private copy of `evidence/` from the actual receipts: versions, gateway, agents, per-case verdicts, scores, latencies, code changes, and everything you
    could not verify. Use placeholders for hosts and IPs.

Return: the contracts and cases you wrote, the deployed Agent manifests, the CI run links, the evidence file, and the list of NOT RUN gates with owners.

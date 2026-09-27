# SDLC board review — task list

Source: independent review of commit `02ff4daad92905585f6ebf933934242e047d1731`
(branch `feat/kagent-sdlc-rig-board-transfer`), 2026-09-27. Offline only: no
credentials, no deploy. Line numbers refer to that commit, relative to this folder.

Legend: **[R]** reproduced offline with a fake GitLab · **[P]** plausible, not reproduced.

## A. Before the single sandbox canary

- [ ] **A1. Stop the PM from changing board labels.**
  `10-a2a-agents.yaml:125` gives the PM `gitlab_update_issue`, which replaces all labels and accepts `state_event` (`vendor/gitlab-delivery-mcp.yaml:91-105`). The prompt at `10-a2a-agents.yaml:91` tells it to label `agent:accepted`.
  Fix: remove `gitlab_update_issue` from the PM's `toolNames`. PLAN only needs `gitlab_create_issue`.
  Done when: rendered PM tools exclude it, and a non-board PM request cannot relabel the parent.

- [ ] **A2. Require tester evidence for the current SHA before review or accept.** [R]
  `board_poller.py:369-373` recalculates the SHA in review, and `:395-449` never checks for a `tested-<sha>` marker.
  Fix: in `agent:review`, if the issue has no `sdlc-rig:v1:<iid>:tested-<sha12>` marker, move it back to `agent:test`.
  Done when: a new head SHA during review routes back to test (regression test).

- [ ] **A3. Put a limit on the CI-failure rework loop.** [R]
  `:377-379` → `:350-354`/`:363` loops `test ↔ changes` with no limit (30 of 30 fake runs never reached blocked).
  Fix: count `:ci-failed-` issue markers, and move to `agent:blocked` at 3 or more.
  Done when: the regression test reaches `agent:blocked` after 3 failed pipelines.

- [ ] **A4. Take CI config away from the builder.**
  `.gitlab-ci.yml` is allowed at `board_poller.py:25`, `render-gitlab-mcp.py:36` and `work-profile.example.json:5`, and the builder edited it in the live run.
  Fix: remove it from `allowed_files`, have a human commit CI to `main`, and have `committed()` reject diffs that touch it.
  Done when: a branch diff containing `.gitlab-ci.yml` raises or blocks.

- [ ] **A5. Don't call the PM again while a timed-out turn may still be running.** [P]
  The A2A timeout of 150s (`30-board-cronjob.yaml:54`) is shorter than the model timeout of 300s (`00-foundation.yaml:31`) plus nested worker calls. The retry at `:308-313`/`:356-364` can create duplicate children, which wedges the issue at `:145-146`, or run builders concurrently.
  First: check whether kagent continues a turn after the client disconnects.
  Fix: wait at least 10 minutes after the last attempt note for a stage before calling the PM again, or store the A2A task ID and check it with `tasks/get` first.

- [ ] **A6. Only trust markers written by the bot.** [R] (blocker if the project is public or has other members)
  `review_note()` at `:279-289` and `child()` at `:138-147` never check the note or issue author.
  Fix: call `GET /user` once, and require `author.id` to match on review notes and child issues.
  Done when: a forged PASS note from another user is ignored (regression test).

- [ ] **A7. Refuse to reuse an old branch when an issue is retried.** [R]
  The branch name is fixed per issue (`:301`). Build advances without calling the builder when a commit already exists (`:350-354`), and an old PASS note still matches (`:412`).
  Fix: in `agent:plan`, if the branch exists, move to `agent:blocked` with "stale branch; rename or delete before retry".
  Done when: relabelling an issue that already has a branch goes to blocked (regression test).

- [ ] **A8. Make the work-cluster install runnable.**
  - [ ] `preflight.sh:13,20`: read the gateway deployment names and ModelConfig name from environment variables (rendered name is `sdlc-work-model`).
  - [ ] `WORK-CLUSTER-RUNBOOK.md:74,95`: create the namespace before the server-side dry-run, or use a client-side dry-run first.
  - [ ] Renderer: add an optional `ca_configmap` profile key that mounts the CA bundle and sets `SSL_CERT_FILE` on the MCP and poller, plus optional `HTTPS_PROXY`/`NO_PROXY`.

- [ ] **A9. Restrict access to the GitLab MCP on a shared cluster.** (not needed on kind)
  The MCP has no authentication (`vendor/gitlab-delivery-mcp.yaml:185-209`), and the rendered bundle has no NetworkPolicy.
  Fix: a NetworkPolicy that only lets `sdlc-rig` agent pods reach `sdlc-gitlab-mcp:8080`.

- [ ] **A10. Add regression tests** for A2, A3, A6 and A7 in `test_board_poller.py`, based on the offline repro scripts.

## B. Production hardening (after the canary)

- [ ] **B1. Stop one bad issue from blocking the board.** [R] The main loop at `:469-471` has no per-issue try/except, and a raise at `:146,167,187,276,318,371,411` aborts the run. Log the error, block the issue after N failures, and continue.
- [ ] **B2. Require the Lease by default.** `:464` only uses it when `BOARD_LEASE_REQUIRED` is `"true"`. Require it whenever `KUBERNETES_SERVICE_HOST` is set. Add the service account and env to `30-board-cronjob.yaml`, or remove that raw manifest.
- [ ] **B3. Release the Lease on shutdown.** Add a SIGTERM handler that raises `SystemExit`, and a total runtime budget below the 210s `activeDeadlineSeconds`.
- [ ] **B4. Time out when CI never finishes.** `:373-376` waits forever. Record an attempt once the commit is more than 30 minutes old with no finished pipeline.
- [ ] **B5. Handle pipeline statuses and attempt counts correctly.** Treat `manual`, `skipped` and `canceled` on purpose rather than as failures (`:326`, `:377`). Scope the `plan`, `build`, `rework` and `mr` attempt keys to a cycle or SHA (`:250`).
- [ ] **B6. Block, don't raise, on MR problems.** Route "MR not draft" and "MR SHA mismatch" (`:410-411`) to blocked.
- [ ] **B7. Split and check the GitLab tokens.** Give the poller its own Reporter-level token and keep the Developer token for the MCP. Protect `main` so only Maintainers can merge. Check the 30-day expiry at deploy time (`preflight.sh:22-23` only checks the key exists).
- [ ] **B8. Tie MCP writes to the issue.** Only allow commits to `agentic/sdlc-rig-<iid>` and updates to the parent/child issues (`vendor:91-118`).
- [ ] **B9. Keep other users' comments out of builder prompts.** Only include follow-up notes from the bot's user ID (`:345-349`).
- [ ] **B10. Keep the queue under the paging limit.** Exclude `agent:accepted` and `agent:blocked` in the query at `:135`, so it stays below the 500-item limit at `:129`.
- [ ] **B11. Check cluster admission policy.** [P] Confirm Pod Security and admission policy against the agent pods and the Namespace labels during the target dry-run.

## C. Canary run checklist (after A is done)

- [ ] Fixed branch rendered; `python3 -m unittest discover -s . -p 'test_*.py'` passes.
- [ ] Preflight passes against the rendered stack.
- [ ] PM echo nonce returns through a real worker turn.
- [ ] One parent issue goes from `agent:plan` to `agent:accepted` with one child, a diff limited to allowed paths, green CI on the head SHA, a draft MR on that SHA, and a PASS note written by the bot.
- [ ] An induced CI failure goes to `agent:changes` and comes back; three failures reach `agent:blocked`.
- [ ] A forged PASS note is ignored.
- [ ] Two scheduled polls observed, including one idle poll; the Lease is clear afterwards.
- [ ] Evidence recorded in `evidence/RUN-<date>.md`.

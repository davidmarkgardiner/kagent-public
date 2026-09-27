# Scheduled board and shared Lease — live home-lab evidence, 2026-09-27

## Scope

One existing Proxmox Kubernetes cluster, one Kimi model route through
agentgateway, and one GitLab sandbox project. The two Kubernetes worker VMs
remained off. This run did not deploy to a workplace cluster or exercise a
second provider or cluster. The board schedule was two minutes. A human
created [parent issue #44](https://gitlab.com/davidmarkgardiner/debt-payoff-calculator-agentic-factory/-/work_items/44)
with `sdlc-rig-poc,agent:plan`; **all later board Jobs for this issue were
scheduled**, with no manual poller Job or manual GitLab repair.

Before intake, `preflight.sh` passed in one second, checking the labelled
node, gateway, controller, MCP, ModelConfig, token-key presence, and five
Agents. A fresh PM A2A turn delegated to the echo worker and returned
`PONG-LAB-VERIFY-0927-01`. That is a real model/worker turn; preflight alone
would not prove it.

## Shared Lease and scheduling

The live poller code was updated to use a pre-created Kubernetes Lease with
a dedicated ServiceAccount restricted to `get` and `update` on that one Lease.
The account could not list Leases. Two concurrent, credential-free Jobs using
the same mounted poller code exercised the lock: Job A printed `ACQUIRED`,
Job B printed `BUSY` while A was running, and the holder/renew time were
cleared after A finished. The first probe failed because its Python command
did not add `/app` to its import path; it was deleted and rerun with the path
fixed before this contention result. The CronJob was suspended for the probe,
then re-enabled with `BOARD_LEASE_REQUIRED=true`; its later scheduled Pods
used the dedicated ServiceAccount and mounted token. This tests a real
Kubernetes Lease race, not yet a natural manual-versus-scheduled collision.

## Issue #44 scheduled run

| Scheduled UTC | Verified event |
|---|---|
| 17:48 | PM created exactly one [child #45](https://gitlab.com/davidmarkgardiner/debt-payoff-calculator-agentic-factory/-/work_items/45); board `agent:plan` → `agent:build`. |
| 17:50 | PM delegated builder; branch `agentic/sdlc-rig-44` committed only README.md and `.gitlab-ci.yml`; board → `agent:test`. |
| 17:52 | Current pipeline failed with zero jobs; board → `agent:changes`. Independent GitLab CI lint reported a script-schema error caused by YAML quoting. |
| 17:54 | PM delegated rework; builder corrected the CI file. Current SHA `48f59c9ec860e5ca39ac4b5ba5a5281e557f57fd` passed [pipeline 2887277350](https://gitlab.com/davidmarkgardiner/debt-payoff-calculator-agentic-factory/-/pipelines/2887277350); board → `agent:test`. |
| 17:56 | Tester returned PASS after the green pipeline; board → `agent:review`. |
| 17:58 | PM opened [draft MR !12](https://gitlab.com/davidmarkgardiner/debt-payoff-calculator-agentic-factory/-/merge_requests/12) at that SHA. |
| 18:00 | Reviewer posted note `3913001801`, tagged with parent #44 and the full SHA, with `REVIEW_VERDICT: PASS`. |
| 18:02 | PM returned acceptance receipt; board → `agent:accepted`. |
| 18:10 | Later scheduled Job returned `{"event":"idle"}`; the Lease holder and renew time were clear. |

Independent GitLab API checks after the run found exactly one annotated
child, a two-path diff, the successful `scheduled_board_canary` job
`16764754190` on the current branch SHA, one open draft MR on that SHA, one
matching reviewer PASS note, and parent `agent:accepted`. The README diff
against `main` was exactly one bullet added inside `## Verification`, with
all existing lines preserved. No MR merge occurred.

The builder initially lacked `gitlab_get_file`, despite its instructions to
preserve existing content. That tool and a read-before-update instruction
were added and the builder Deployment rolled out **before** issue #44 was
created. This improvement is included in the transfer folder.

## Limits and next gate

This is one unattended parent issue, not a multi-issue soak or general
software-quality result. It proves the failure-to-rework loop and the
scheduled plan/build/test/review/accept sequence in this sandbox. The work
renderer and target-specific ModelConfig remain locally rendered and
server-dry-run only; they have not been installed as a complete second stack.
MCP calls still go directly from kagent to the fixed-project server. The
cluster Metrics API was unavailable, so live CPU/memory utilization was not
measured through `kubectl top`; node requests were 56% CPU and 30% memory at
the check, while limits were overcommitted. Before workplace use, verify
target CRDs, policy, network, Secrets, image digest/architecture, model route,
and the target canary in `WORK-CLUSTER-RUNBOOK.md`.

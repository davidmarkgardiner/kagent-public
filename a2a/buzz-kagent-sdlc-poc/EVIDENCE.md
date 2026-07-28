# Buzz-backed kagent SDLC POC — completion evidence

Verified on 2026-07-28 against the live `red` Kind cluster on Geekom and the
private Buzz relay. This document records evidence, not a merge approval.

## Live paths proved

| Boundary | Result | Evidence |
| --- | --- | --- |
| Isolated Kimi model route | Passed | `kimi-k2.7-code` returned through `/buzz-sdlc-kimi-k2-7/v1`; shared default route unchanged. |
| Bounded kagent role chain | Ready | `buzz-sdlc-builder`, `-verifier`, `-documenter`, and `-coordinator` all report `Ready=True`; they expose no shell, Git, Kubernetes-write, or merge tool. |
| Buzz transport | Passed | Disposable private-channel task was signed, read by the bridge, sent to kagent, and replied to in its source thread. |
| A2A approval/resume | Passed | Source event `f6da21252c99d9098d3c3ed418ee04392b92805fc9397dd0fe879695b5ae13ca` led to stored A2A task `663a51d3-3766-40ef-bf46-55f57a847804`; a threaded `approve` resumed that exact task and ended `completed`. The disposable channel and identities were deleted. |
| Git/test/draft-PR gate | Passed | SHA `ea30ca05b00ec3b36ea9e322afb996334e5f4682`, 9 local tests passed, and open draft [PR #61](https://github.com/davidmarkgardiner/kagent-public/pull/61) matched `feat/kagent-buzz-sdlc-poc` -> `main`. |

## Boundaries retained

- The live approval fixture is deterministic and non-mutating: it simulates
  `delete_file`; it has no model, filesystem, Git, Kubernetes, or external
  write capability.
- The delivery gate only verifies a clean SHA, direct tests, and an existing
  draft PR. Its receipt is `ready_for_human_review: true` and always
  `merge_eligible: false`.
- Buzz events are deduplicated in SQLite by source event ID. Approval resumes
  the stored context/task rather than creating a new task.
- The PR currently has no GitHub CI checks configured. The recorded local gate
  is therefore evidence, not a substitute for a future hosted/self-hosted CI
  policy.

## Reproduce

1. Run both local test files.
2. Build/load the `hitl_fixture` image, apply `k8s/hitl-fixture.yaml`, and run
   `live_approval_smoke.py` only from the trusted bridge host.
3. Run `delivery_gate.py` from a clean checkout with the existing draft PR.
4. Review the JSON receipt and the PR; a human remains the only merge authority.

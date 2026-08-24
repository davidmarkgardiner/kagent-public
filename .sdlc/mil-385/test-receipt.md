# MIL-385 Test receipt

## Stage and boundary

- Stage: Test (`MIL-388`, order 3/5)
- Tested commit: `906ff1fc244822d17c2eeb7c810d5c82a1c458f1`
- Shared branch: `sdlc/mil-385`
- Product code modified: none
- Live actions performed: bounded POC orchestration passed reachability and
  purpose-issued credential setup, then failed closed at RBAC allow/deny
  verification. The live process exited through its cleanup trap; no live
  evidence or credential material was retained in the worktree.

## Deterministic gate

Command:

```sh
bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/verify.sh && HOST_CONTEXT=kind-homelab TARGET_CONTEXT=proxmox-k8s bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/live-poc.sh
```

Exit code: `1`

Concise output:

```text
verify: PASS (offline bundle, manifests, tool surface, RBAC, client fixture, evidence, teardown)
preflight: PASS (aliases=red-homelab,proxmox-homelab; nodes=1,3)
reachability: PASS (host pod to target API; endpoint suppressed)
credentials: PASS (two short-lived purpose-issued entries; values suppressed)
RBAC_DIAGNOSTIC: 40 expected-deny checks returned actual=error across both aliases
RBAC_RESULT: {"checks":108,"failures":40,"result":"FAIL"}
ERROR: RBAC allow/deny verification failed
```

The offline verification, fail-closed preflight, pod-to-target reachability,
runtime credential setup, and bounded diagnostic rendering passed. The live
proof failed at the independent RBAC allow/deny verification: every one of the
40 expected-deny checks that ran across `red-homelab` and `proxmox-homelab`
returned `error` rather than `deny`. It therefore did not proceed to
deterministic MCP requests or bounded live evidence. The orchestrator returned
exit code 1 after its cleanup trap; no task files or credentials were retained
in the worktree.

This rerun follows the owner-authorized bounded RBAC-diagnostic repair recorded
on the parent issue. The prior Test receipt remains represented by the earlier
shared-branch history; this receipt records the current rerun against commit
`906ff1fc244822d17c2eeb7c810d5c82a1c458f1`.

## Result

Test gate: `FAIL` — RBAC allow/deny verification failed with 40 expected-deny
checks returning `error`. One repair dispatch was already consumed by the prior
Test failure, so the repair budget is exhausted. This receipt is committed as
the durable Test-stage handoff.

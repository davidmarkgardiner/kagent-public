# MIL-385 Test receipt

## Stage and boundary

- Stage: Test (`MIL-388`, order 3/5)
- Tested commit: `ca24cbf5c40d1d290e0f7a10e4cf8edca226a020`
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
ERROR: RBAC allow/deny verification failed
```

The offline verification, fail-closed preflight, pod-to-target reachability,
and runtime credential setup passed. The live proof failed at the independent
RBAC allow/deny verification and therefore did not proceed to deterministic
MCP requests or bounded live evidence. The orchestrator returned exit code 1
after its cleanup trap; no task files or credentials were retained in the
worktree.

This rerun follows the owner-authorized bounded non-root repair recorded on
the parent issue. The prior Test receipt remains represented by commit
`dcaf1168293b9309babf7e34afcaa78a2fc7ea37`; this receipt records the current
rerun against the repaired shared head.

## Result

Test gate: `FAIL` — RBAC allow/deny verification failed. One repair dispatch
was already consumed by the prior Test failure, so the repair budget is
exhausted. This receipt is committed as the durable Test-stage handoff.

# MIL-385 Test receipt

## Stage and boundary

- Stage: Test (`MIL-388`, order 3/5)
- Tested commit: `11cb587ddf4f94ffd99d7e0d748c48f6fbaf43d8`
- Shared branch: `sdlc/mil-385`
- Product code modified: none
- Live actions performed: bounded POC orchestration reached the smoke-client
  readiness check and exited non-zero; no live evidence or credential material
  was retained in the worktree.

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
ERROR: the labelled smoke client did not become ready
```

The offline verification and fail-closed preflight passed. The live proof
could not complete because the labelled smoke client did not become ready.
The command exited before deterministic MCP requests and bounded live evidence
were produced; no task files or credentials were retained in the worktree.

## Result

Test gate: `FAIL` — the live smoke client did not become ready. One repair
dispatch was already consumed by the prior Test failure, so the repair budget
is exhausted. This receipt is committed as the durable Test-stage handoff.

# MIL-385 Test receipt

## Stage and boundary

- Stage: Test (`MIL-388`, order 3/5)
- Tested commit: `640eb53cc7e04a756bfd0c5b44ae0c1de5428969`
- Shared branch: `sdlc/mil-385`
- Product code modified: none
- Live actions performed: none; fail-closed preflight stopped before any
  credential or workload action because `gitleaks` is unavailable.

## Deterministic gate

Command:

```sh
bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/verify.sh && HOST_CONTEXT=kind-homelab TARGET_CONTEXT=proxmox-k8s bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/live-poc.sh
```

Exit code: `1`

Concise output:

```text
verify: PASS (offline bundle, manifests, tool surface, RBAC, client fixture, evidence, teardown)
ERROR: required command is unavailable: gitleaks
```

The offline verification passed. The live proof did not begin because its
required fail-closed preflight dependency was unavailable, so no homelab
resources or ephemeral credentials were created.

## Result

Test gate: `FAIL` — repair dispatch required for the missing `gitleaks`
dependency. This receipt is committed as the durable Test-stage handoff.

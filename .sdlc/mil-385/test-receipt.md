# MIL-385 Test receipt

## Stage and boundary

- Stage: Test (`MIL-388`, order 3/5)
- Tested commit: `b333efbc9813ee4cd4d36178629cfd88ea63668f`
- Shared branch: `sdlc/mil-385`
- Product code modified: none
- Live actions performed: none; fail-closed preflight stopped before any
  credential or workload action because a pre-existing POC resource was found.

## Deterministic gate

Command:

```sh
bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/verify.sh && HOST_CONTEXT=kind-homelab TARGET_CONTEXT=proxmox-k8s bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/live-poc.sh
```

Exit code: `1`

Concise output:

```text
verify: PASS (offline bundle, manifests, tool surface, RBAC, client fixture, evidence, teardown)
ERROR: a POC resource already exists; refusing to adopt it
```

The offline verification passed. The live proof did not begin because its
fail-closed preflight found a pre-existing POC resource and refused to adopt
it, so no credentials or additional workload resources were created.

## Result

Test gate: `FAIL` — the live preflight found a pre-existing POC resource and
refused to adopt it. This receipt is committed as the durable Test-stage
handoff.

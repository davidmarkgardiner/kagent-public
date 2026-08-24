# MIL-385 Build receipt

## Stage and boundary

- Stage: Build (`MIL-387`, order 2/5)
- Initial-build starting commit: `3ce990d55551bbbd26e228dd957db7e839b14f0d`
- Repair starting commit: `764c9568b613d27b23b1600647b95d7da6aeab0e`
- Shared branch: `sdlc/mil-385`
- Scope: source creation plus offline/static verification only; the repair is
  limited to the missing evidence-scanner dependency recorded by Test
- Live actions performed: none

This stage did not execute `live-poc.sh`, `kubectl`, Helm, TokenRequest, or any
cluster mutation. The live proof remains source for the separately authorized
Test stage.

## Bounded repair

The required `.sdlc/mil-385/test-receipt.md` records one failing gate: the
live preflight stopped before credentials or resources because the external
`gitleaks` command was unavailable. The repair removes only that host-package
dependency. It adds a repository-local Python standard-library validator that
requires the exact three evidence files, exact bounded schemas and values,
the two public aliases, the complete 20-request alternating sequence, zero
crossover, the exact allow/deny results, passing teardown booleans, and no
forbidden endpoint, certificate, kubeconfig, prompt, or source-context shapes.
Unexpected files, fields, values, sizes, or malformed JSON fail closed.

## Files changed

- `platform/kubernetes-mcp-server/homelab-cross-cluster/README.md`
  documents the proof boundary, configuration, ordered live flow, validation,
  evidence, cleanup, and the honest KindNet limitation.
- `platform/kubernetes-mcp-server/homelab-cross-cluster/config/server.toml`
  defines the two-context kubeconfig provider and exact read-only MCP tool
  allowlist while explicitly removing configuration disclosure, exec, Helm,
  metrics, and mutation tools.
- `platform/kubernetes-mcp-server/homelab-cross-cluster/manifests/*.yaml`
  define the labelled POC namespace, purpose-specific reader RBAC, ingress
  isolation, hardened MCP Deployment, ClusterIP Service, and labelled hardened
  smoke client.
- `platform/kubernetes-mcp-server/homelab-cross-cluster/values.yaml` records
  the reviewed upstream-chart-equivalent immutable and non-exposed posture.
- `platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/*.sh` implement
  fail-closed preflight, ten-minute TokenRequest credentials, minimal
  alias-only kubeconfig/Secret handling, independent RBAC tests, ordered live
  orchestration, bounded evidence scans, offline verification, and
  ownership-checked teardown with preserved UID validation.
- `platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/scan-evidence.py`
  replaces the unavailable external scanner with a strict, repository-local
  schema and sensitive-shape validator plus a positive/negative self-test.
- `platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/mcp-client.py`
  implements direct Streamable HTTP initialization, exact tool/context
  discovery, 20 alternating fingerprint-bound Node requests, crossover
  detection, and blocked-tool probes without retaining raw results.
- `platform/kubernetes-mcp-server/homelab-cross-cluster/fixtures/expected-summary.json`
  and `evidence/example-summary.json` provide bounded, sanitized non-live
  fixtures containing aliases, counts, sequence, tool names, and status only.
- `.sdlc/mil-385/build-receipt.md` is this durable stage handoff.

## Commands and results

| Command | Exit | Result |
| --- | ---: | --- |
| `bash -n platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/*.sh` | 0 | All shell sources parsed. |
| `python3 -m py_compile platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/mcp-client.py` | 0 | Client source compiled. Generated cache was removed. |
| `python3 platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/mcp-client.py --self-test` | 0 | Deterministic one-node/three-node, 20-request fixture passed. |
| `diff -u fixtures/expected-summary.json /tmp/mil-387-client-summary.json` | 1 | Formatting-only difference; parsed JSON values were identical. |
| parsed JSON semantic comparison of the fixture and self-test output | 0 | Objects were byte-value equivalent after JSON parsing. |
| `bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/verify.sh` | 0 | `verify: PASS (offline bundle, manifests, tool surface, RBAC, client fixture, evidence, teardown)` |

The exact stage `TEST_COMMAND` was executed once and exited 0. No live half of
the parent controller's eventual Test-stage validation was executed.

### Repair commands and results

| Command | Exit | Result |
| --- | ---: | --- |
| `bash -n` on the changed shell scripts | 0 | All changed shell sources parsed. |
| `python3 scripts/scan-evidence.py --self-test` | 0 | Strict schemas passed and an unexpected endpoint was rejected. |
| in-memory Python compile of `scan-evidence.py` | 0 | Validator source compiled without creating cache files. |
| `bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/verify.sh` | 0 | `verify: PASS (offline bundle, manifests, tool surface, RBAC, client fixture, evidence, teardown)` |
| `git diff --check` | 0 | Repair diff has no whitespace errors. |

The Build repair ran the issue's exact offline `TEST_COMMAND` once. It did not
run `live-poc.sh`; the Test stage remains the only stage authorized to exercise
the live proof.

## Resulting commit intent

Commit the complete public-safe bundle and this receipt together as:

```text
MIL-385 build: bounded repair
```

# MIL-385 Build receipt

## Stage and boundary

- Stage: Build (`MIL-387`, order 2/5)
- Initial-build starting commit: `3ce990d55551bbbd26e228dd957db7e839b14f0d`
- Repair starting commit: `764c9568b613d27b23b1600647b95d7da6aeab0e`
- Owner-authorized collision-repair starting commit:
  `1913b6421904f54066305c30fd4b636424b5c0f6`
- Owner-authorized capacity-repair starting commit:
  `dcaf1168293b9309babf7e34afcaa78a2fc7ea37`
- Owner-authorized non-root-repair starting commit:
  `412413174cf0d597f9b0fc619a6110dad84a4d06`
- Owner-authorized RBAC-diagnostic-repair starting commit:
  `def4ab54ac18b21b06c7f39fbca1959ec2d8b18a`
- Owner-authorized RBAC-exit-status-repair starting commit:
  `cfa1dde6eab08f578dee67dc192deb8eaf9f1003`
- Shared branch: `sdlc/mil-385`
- Scope: source creation plus offline/static verification only; the current
  repair is limited to preserving RBAC authorization stdout and exit status
  independently, plus deterministic offline assertions for the accepted and
  rejected result combinations
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

## Owner-authorized collision repair

The repaired Test gate subsequently stopped before credentials or mutation
because the fixed `kubernetes-mcp-poc` namespace belongs to an unrelated live
MCP proof. The parent records explicit owner authorization for one additional
bounded source repair despite the exhausted automatic repair budget. This
repair assigns the cross-cluster proof these deterministic identities:

- namespace: `kubernetes-mcp-cross-cluster-poc`;
- reader ServiceAccount: `kubernetes-mcp-cross-cluster-reader`; and
- ClusterRole/ClusterRoleBinding: `kubernetes-mcp-cross-cluster-poc-reader`.

All manifests, runtime constants, exact-name preflight/teardown checks, the
fixed in-cluster client endpoint, offline assertions, and documentation use the
new set consistently. The server and client objects retain their existing
names inside the new namespace, so their fully qualified identities are also
distinct. Fail-closed ownership checks remain unchanged: teardown still
deletes only exact-name resources carrying the proof label. It neither adopts
nor deletes the unrelated legacy namespace or any existing workload.

## Owner-authorized capacity repair

The next Test gate passed offline verification and live preflight, then stopped
because the labelled smoke client could not schedule. The owner-recorded
read-only capacity evidence showed 7,997m of the Kind host's 8,000m allocatable
CPU already requested, leaving less than the smoke client's former 10m request
and the server's former 50m request. The live trap removed all renamed POC
resources, and the protected `default/kubectl-mcp` UID remained unchanged.

This code-only repair sets the two temporary POC Pods' CPU requests to `1m`.
It retains their CPU limits, memory requests and limits, hardened security
contexts, isolation, cleanup, and every other acceptance control. The audited
server values mirror the manifest. Offline verification now requires the exact
resource maps for both Pods and fails closed if any request or limit drifts.

## Owner-authorized non-root runtime repair

After the capacity repair, the `1m` smoke pod scheduled, but kubelet refused
startup because `runAsNonRoot: true` encountered an image whose default user
is root. No container ran or credential was minted, cleanup removed every
renamed POC resource, and the protected `default/kubectl-mcp` UID remained
unchanged.

This offline-only repair pins `runAsUser: 65532` and `runAsGroup: 65532` at
both the pod and container security-context levels for the temporary server
and smoke-client workloads. The audited server values mirror the exact
identity. The deterministic verifier now requires the exact numeric UID/GID
and all retained security controls for both pods and fails closed on drift.
Resources, limits, token automount, read-only filesystems, dropped
capabilities, RuntimeDefault seccomp, isolation, cleanup, and unrelated
workloads remain unchanged.

## Owner-authorized RBAC diagnostic repair

The next Test gate passed offline verification, preflight, pod-to-target
reachability, and purpose-issued credential setup, then failed closed in the
independent RBAC allow/deny verification. The former runtime output identified
only the overall RBAC phase and could not distinguish a denied expected read,
an unexpectedly allowed forbidden operation, or an authorization command
error. The private runtime directory and cleanup trap retained no credential or
raw cluster output.

This offline-only repair leaves the RBAC manifest and permission matrix
unchanged because their static definitions agree. It adds a fail-closed
diagnostic renderer that accepts only:

- one exact check identifier from the existing 108-check matrix;
- `red-homelab` or `proxmox-homelab` as the context alias;
- normalized `allow`, `deny`, or `error` actual state and `allow`/`deny`
  expectation; and
- a result consistent with those normalized values.

Only failed checks are rendered individually; one bounded overall line reports
the fixed check count, failure count, and result. Raw `kubectl` output remains
suppressed and is never passed to the renderer. The helper's offline self-test
proves exact output and rejection of credential-like, token, URL, PEM,
kubeconfig, Secret, and authorization-header shapes. Existing `0600` temporary
check storage, private runtime-directory handling, cleanup, security contexts,
resources, read-only filesystems, dropped capabilities, seccomp, token
automount, isolation, and unrelated workloads remain unchanged.

## Owner-authorized RBAC exit-status repair

The diagnostic-enabled Test rerun proved that every expected denial was
misclassified as an authorization command error. `kubectl auth can-i` writes
`no` and returns its documented denial status `1`; the shell fallback replaced
that retained `no` with `error`, while allowed checks continued to pass.

This offline-only repair captures command stdout and exit status independently.
It accepts exactly `yes` with status `0` as `allow` and `no` with status `1` as
`deny`; missing, malformed, or unexpected output/status combinations normalize
to `error`. Raw command output is unset before any diagnostic is rendered, so
the existing bounded public-alias/check/status surface remains the only failure
output. A pure shell helper self-test covers `yes/0`, `no/1`, an empty command
error, and malformed output without invoking kubectl or printing any input.

The permission expectation matrix and `reader-rbac.yaml` are unchanged.
Private `0600` runtime files, cleanup, pod security contexts, resources,
read-only filesystems, dropped capabilities, seccomp, token automount,
isolation, teardown, and unrelated workloads remain unchanged.

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
- `platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/rbac-diagnostics.py`
  renders the exact allowlisted RBAC failure surface and self-tests rejection
  of sensitive or uncontrolled diagnostic values.
- `platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/rbac-status.sh`
  normalizes only the exact supported stdout/exit-status pairs and supplies the
  deterministic offline regression cases.
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

### Owner-authorized collision-repair commands and results

| Command | Exit | Result |
| --- | ---: | --- |
| `bash -n` on the changed shell scripts | 0 | All changed shell sources parsed. |
| in-memory Python compile of `mcp-client.py` | 0 | Client source compiled without creating cache files. |
| legacy operational-identity scan over manifests, scripts, values, and config | 0 | The old namespace, reader, and cluster-scoped RBAC identities are absent from operational source. |
| `bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/verify.sh` | 0 | `verify: PASS (offline bundle, manifests, tool surface, RBAC, client fixture, evidence, teardown)` |

The exact Build `TEST_COMMAND` was executed once against the final operational
source. No live command, `kubectl`, Helm, TokenRequest, cluster access, or
cluster mutation was performed.

### Owner-authorized capacity-repair commands and results

| Command | Exit | Result |
| --- | ---: | --- |
| `bash -n` on the changed offline verifier | 0 | The verifier source parsed. |
| focused resource assertion inspection | 0 | Both Pod manifests and the audited server values contain the exact bounded requests and retained limits. |
| `bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/verify.sh` | 0 | `verify: PASS (offline bundle, manifests, tool surface, RBAC, client fixture, evidence, teardown)` |
| `git diff --check` | 0 | Capacity-repair diff has no whitespace errors. |

No live command, `kubectl`, Helm, TokenRequest, cluster access, or cluster
mutation is authorized or performed by this repair.

### Owner-authorized non-root-repair commands and results

| Command | Exit | Result |
| --- | ---: | --- |
| `bash -n` on the changed offline verifier | 0 | The verifier source parsed. |
| focused YAML security-context inspection | 0 | Both pod and container contexts use exact UID/GID `65532:65532`; audited server values are exact. |
| `bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/verify.sh` | 0 | `verify: PASS (offline bundle, manifests, tool surface, RBAC, client fixture, evidence, teardown)` |
| `scripts/public-safe-scan.sh platform/kubernetes-mcp-server/homelab-cross-cluster --json` | 0 | `{"clean":true,"hits":0}` |
| `scripts/public-safe-scan.sh .sdlc/mil-385 --json` | 0 | `{"clean":true,"hits":0}` |
| `git diff --check` | 0 | Non-root-repair diff has no whitespace errors. |

The exact Build `TEST_COMMAND` was executed once and passed. No live command,
`kubectl`, Helm, TokenRequest, cluster access, or cluster mutation was run.

### Owner-authorized RBAC-diagnostic-repair commands and results

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 scripts/rbac-diagnostics.py self-test` | 0 | Exact valid diagnostic and overall lines passed; credential-like, token, URL, PEM, kubeconfig, Secret, and authorization-header values were rejected. |
| bounded diagnostic failure rendering | 0 | Produced only the exact check identifier, public alias, normalized expected/actual status, and result. |
| `bash -n` on the changed shell sources | 0 | Both changed shell sources parsed. |
| in-memory Python compile of `rbac-diagnostics.py` | 0 | Diagnostic helper compiled without creating cache files. |
| `bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/verify.sh` | 0 | `verify: PASS (offline bundle, manifests, tool surface, RBAC, client fixture, evidence, teardown)` |
| `scripts/public-safe-scan.sh platform/kubernetes-mcp-server/homelab-cross-cluster --json` | 0 | `{"clean":true,"hits":0}` |
| `scripts/public-safe-scan.sh .sdlc/mil-385 --json` | 0 | `{"clean":true,"hits":0}` |
| `git diff --check` | 0 | RBAC-diagnostic-repair diff has no whitespace errors. |

The exact Build `TEST_COMMAND` was executed once against the final repair tree
and passed. No live command, `kubectl`, Helm, TokenRequest, cluster access, or
cluster mutation was run.

### Owner-authorized RBAC-exit-status-repair commands and results

| Command | Exit | Result |
| --- | ---: | --- |
| `bash scripts/rbac-status.sh --self-test` | 0 | Exact `yes/0` and `no/1` pairs normalized to allow/deny; command-error and malformed-output cases normalized to error. |
| `bash -n` on the changed shell sources | 0 | All changed shell sources parsed. |
| `bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/verify.sh` | 0 | `verify: PASS (offline bundle, manifests, tool surface, RBAC, client fixture, evidence, teardown)` |
| `git diff --check` | 0 | Final repair diff has no whitespace errors. |

No live command, `kubectl`, Helm, TokenRequest, cluster access, or cluster
mutation is authorized or performed by this repair.

## Resulting commit intent

Commit the complete public-safe bundle and this receipt together as:

```text
MIL-385 build: bounded repair
```

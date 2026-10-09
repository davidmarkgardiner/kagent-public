# Redeploy walkthrough template: kagent + Agent Substrate on another AKS cluster

> Work agent: complete this privately as `SUBSTRATE-REDEPLOY-WALKTHROUGH.md`. It must let an authorized teammate repeat the **same tested release and delivery path** on a fresh, approved non-production AKS cluster. Provide literal Git paths, pinned commits/digests, commands, expected outputs, observed outputs, and private receipt links. Remove all placeholders from the completed file or write `NOT RUN — reason`. Keep secrets in approved Secret stores; show references, never values. Do not copy 0.0.9 commands into a 1.x installation.

## Read this before starting

| Item | Exact value or reference |
| --- | --- |
| Source proof and original run ID | [SUBSTRATE-KAGENT-EVIDENCE.md]({{PRIVATE_EVIDENCE_MD_LINK}}); `{{RUN_ID}}` |
| Scope and change approval | `{{TARGET_CLUSTER_ALIAS}}`, `{{NON_PRODUCTION_CONFIRMATION}}`, `{{APPROVAL_OR_CHANGE_LINK}}` |
| Operator, reviewer and rollback owner | `{{NAMES_OR_TEAM_HANDLES}}` |
| Version pair and source commits | Substrate `{{VERSION_COMMIT}}`; kagent `{{VERSION_COMMIT}}`; exact installed CRD APIs `{{API_VERSIONS}}` |
| Desired-state repository and revision | `{{GIT_REPO}}` at `{{COMMIT}}`; overlay `{{PATH}}`; reconcile owner `{{FLUX_KUSTOMIZATION}}` |
| Artifact inventory | `{{PRIVATE_ARTIFACT_MANIFEST_MD_LINK}}` containing four chart archive hashes, every image digest, the generated workload image, and `runsc` hash/delivery image |
| Runtime path | gVisor `{{WORKERPOOL}}`; ATELET shared volume `{{MOUNT}}`; seed DaemonSet `{{NAME}}`; content-addressed filename `runsc-{{SHA256}}` |
| Storage and identity | Snapshot store alias/prefix `{{ALIAS}}`; approved CA/Secret references `{{REFERENCES}}`; model route alias `{{ALIAS}}` |
| Target validation status | `VERIFIED ON SECOND APPROVED CLUSTER` / `VERIFIED ON FRESH NODE ONLY` / `DOCUMENTED ONLY`; run ID or reason `{{VALUE}}` |

Use [the public air-gap guide](AIRGAPPED-AKS-README.md) and [runsc pre-seed procedure](runsc-asset/PACKAGE-AND-PRESEED.md) as source context. The exact private desired state and evidence above govern this reproduction. The seed is an asset in ATELET's shared runtime volume, **not an OS package install**. Check the private Substrate source for its cache-path and hash behavior before using a public version's instructions.

## 0. Establish a clean target and capture baseline

1. Confirm the kube context, subscription/cluster alias, non-production approval, node pool, architecture, OS/kernel, runtime, quotas, taints and admission policy. Stop if they differ materially from the tested contract; record the difference.
2. Record whether conflicting Substrate/kagent CRDs or Helm releases already exist. Use an isolated cluster or another supported scope; do not overwrite a shared installation.
3. Capture a timestamped read-only baseline and a link to the output. Record rollback owner before any mutation.

```bash
# Work agent: replace this block with the exact, sanitized, working preflight
# commands and expected/observed outputs for the approved target.
kubectl --context '{{KUBE_CONTEXT}}' get nodes -o wide
kubectl --context '{{KUBE_CONTEXT}}' api-resources | rg -i 'sandboxagent|agentharness|workerpool|actortemplate|sandboxconfig'
helm --kube-context '{{KUBE_CONTEXT}}' list -A
```

**Gate 0:** `PASS` / `FAIL` / `NOT RUN` — `{{RESULT}}`; node/cluster receipt `E-__`; existing-release receipt `E-__`; stop condition `{{CONDITION}}`.

## 1. Recreate the exact inputs in the approved internal stores

1. From the tested Git revision, enumerate **four** chart archives: Substrate CRDs, Substrate control/data plane, kagent CRDs and kagent controller. Record archive SHA-256 and source commit, not just tags.
2. Render the exact private values and capture all image references by digest. Add the generated Go ADK/BYO/Harness workload image, which may not appear in the Helm render. Record source and mirrored digest for each.
3. Record the version-specific gVisor asset bytes, architecture, SHA-256, size, delivery image digest, and seed manifest. For the 0.0.9 binary path, the file must be named `runsc-<configured-sha256>` at ATELET's expected `static-files` location. For another release, derive the path and format from its source/schema.
4. Mirror charts, images and seed asset through the approved process. Record import receipts and registry/object-store pull checks. Reference CA and pull credentials by Secret name only.

**Exact commands/Git paths, in execution order:**

```text
{{PASTE_THE_ACTUAL_MIRROR_RENDER_AND_DIGEST_VERIFICATION_COMMANDS_OR_LINK_TO_VERSIONED_SCRIPT}}
```

**Gate 1:** `PASS` / `FAIL` / `NOT RUN` — chart, image and asset inventory `{{PRIVATE_LINK}}`; hashes verified `{{RESULT}}`; receipt `E-__`.

## 2. Prepare GitOps desired state and prerequisites

1. Link the exact Flux source, HelmRepository/OCI source, four HelmRelease manifests, kagent values, WorkerPool, SandboxConfig, seeded `runsc` DaemonSet, node selector/taints, storage/CA references, network policy, and disposable canary manifest. Note which objects are cluster-scoped.
2. Confirm version-specific CRD schemas and render/lint the exact values. Run server-side dry-run where the target API supports it. Record any sanctioned schema exception.
3. Check that the internal model route, snapshot store, image registry and secret references resolve from the *worker* path. Check public-egress controls separately if air-gap is claimed.
4. Submit through the approved GitOps review/merge process. Record merge commit and Flux reconciliation IDs. Do not hand-patch generated ActorTemplates.

| Ordered input | Versioned private Git path / digest | Render or dry-run command | Expected and observed result | Receipt |
| --- | --- | --- | --- | --- |
| Substrate CRDs and bootstrap prerequisites | `{{PATH}}` | `{{COMMAND}}` | `{{RESULT}}` | `E-__` |
| Substrate control/data plane | `{{PATH}}` | `{{COMMAND}}` | `{{RESULT}}` | `E-__` |
| `runsc` seed and gVisor WorkerPool | `{{PATH}}` | `{{COMMAND}}` | `{{RESULT}}` | `E-__` |
| kagent CRDs and controller | `{{PATH}}` | `{{COMMAND}}` | `{{RESULT}}` | `E-__` |
| Disposable canary | `{{PATH}}` | `{{COMMAND}}` | `{{RESULT}}` | `E-__` |

**Gate 2:** `PASS` / `FAIL` / `NOT RUN` — review/merge `{{LINK}}`; rendered/dry-run output `{{LINK}}`; prerequisites `{{RESULT}}`.

## 3. Reconcile Substrate and seed `runsc` on every eligible node

1. Reconcile Substrate CRDs, then its control/data plane and snapshot-store prerequisites. Wait for actual healthy pods and API connectivity; record running imageIDs.
2. Reconcile the pinned seed DaemonSet to eligible nodes. On a **fresh node with no pre-existing cache**, show successful seed completion and file creation before a worker starts. Do not evict a shared cache to manufacture this condition.
3. On that node, compare file SHA-256 with SandboxConfig, confirm architecture, size, executable bit, mount visibility in ATELET and `ateom-gvisor`, and the actual worker RPC `runsc_path`. The v0.0.9 ATELET cache-hit branch only checks existence; a filename is not a hash verification.
4. Reconcile the gVisor WorkerPool and confirm desired/ready replicas, node placement, runtime class, and `ateom-gvisor` imageID. Confirm there was no public asset fetch if internal-only operation is claimed.

```text
{{PASTE_EXACT_VERSION_MATCHED_FLUX_RECONCILE_AND_READ_ONLY_SEED_VERIFY_COMMANDS}}
```

**Gate 3:** `PASS` / `FAIL` / `NOT RUN` — `runsc` hash/path/permissions `{{RESULT}}` (`E-__`); WorkerPool `{{RESULT}}` (`E-__`); egress observation `{{RESULT_OR_NOT_RUN}}` (`E-__`).

## 4. Reconcile kagent and create one disposable canary

1. Reconcile kagent CRDs, then controller/UI and configured Substrate integration. Confirm real running imageIDs and controller connectivity to ATE API.
2. Reconcile one uniquely named canary through GitOps. Use the installed API: `SandboxAgent` for the tested 0.9/0.10 pairing, or `Agent`/`Harness` for the tested 1.x pairing. Record the generated workload image digest, template UID/spec, golden ID/status, and WorkerPool assignment.
3. Check `Accepted` and `Ready` conditions. These are installation gates, not proof of a model call or restore.

```text
{{PASTE_EXACT_FLUX_RECONCILE_AND_CANARY_READINESS_COMMANDS}}
```

**Gate 4:** `PASS` / `FAIL` / `NOT RUN` — kagent and canary `{{RESULT}}`; template/golden `E-__`; controller logs/traces `E-__`.

## 5. Exercise the advertised runtime path

1. Invoke the canary through the approved **kagent** UI/API/A2A front door. Use a unique request marker. Record request/response IDs, actual model/provider success, harmless tool call if in scope, and the matching Substrate actor/session IDs.
2. Record golden restore, active request, idle suspension, object-store snapshot, and next restore. Run Full pause/restore with an independent in-memory state marker, then Data commit/restore with a `durableDir` file fixture. Follow this release's lifecycle order; if needed, resume between Full pause and Data commit.
3. Start a second disposable agent on the bounded pool to show slot release/reuse. Record worker-pod count before/during/after. Measure restore time and resource use separately if those benefits are claimed.
4. Apply the P01–P13 proof matrix in the [evidence report]({{PRIVATE_EVIDENCE_MD_LINK}}). Attach raw timestamps, trace IDs, object metadata, first fatal stderr on failure, and the exact observed state assertions. An HTTP 200 agent card alone is insufficient.

```text
{{PASTE_EXACT_SAFE_REQUEST_AND_LIFECYCLE_COMMANDS_OR_UI_API_STEPS}}
```

**Gate 5:** `PASS` / `FAIL` / `NOT RUN` — `{{PROVEN_FOR_STATED_SCOPE_OR_PARTIAL_OR_FAILED}}`; P IDs `{{LIST}}`; receipts `{{LIST}}`.

## 6. Check repeatability and clean up

1. Record whether this procedure was actually executed on a second approved cluster, only on a fresh node, or only documented. Never call an unexecuted walkthrough a redeployment pass.
2. Record each difference from the source cluster and whether it was resolved without changing the tested release contract. Include time-to-ready and any manual intervention.
3. Revert only the disposable canary through GitOps. Verify actor/template cleanup and snapshot retention policy. Preserve receipts. Do not remove shared charts, pools, secrets, or storage without a separate approved change.

**Repeatability result:** `VERIFIED ON SECOND APPROVED CLUSTER` / `VERIFIED ON FRESH NODE ONLY` / `DOCUMENTED ONLY` — `{{RUN_ID_AND_RECEIPTS_OR_REASON}}`.

**Cleanup receipt:** `{{PRIVATE_LINK}}`; remaining state by policy: `{{VALUE}}`.

## Rollback and troubleshooting

| Failure point | First diagnostic receipt to capture | Safe next action / rollback owner |
| --- | --- | --- |
| Chart/CRD or Flux reconciliation | Flux condition, Helm revision, first controller error | `{{ACTION_AND_OWNER}}` |
| Seed missing, wrong hash, no execute permission or wrong architecture | Seed DaemonSet logs; actual file hash/mode/path; worker node | `{{ACTION_AND_OWNER}}` |
| Worker/golden creation fails | WorkerPool status, generated template, `atelet`/`ateom` first fatal stderr | `{{ACTION_AND_OWNER}}` |
| Checkpoint/restore fails | Operation/scope, actor/session, `runsc_path`, first fatal stderr, snapshot object | `{{ACTION_AND_OWNER}}` |
| Model/tool request fails | kagent request/trace, approved route, non-secret provider error | `{{ACTION_AND_OWNER}}` |
| Cleanup leaves resources | Flux reconcile, actor/template inventory, storage retention policy | `{{ACTION_AND_OWNER}}` |

**Rollback sequence and tested result:** `{{EXACT_GIT_REVERT_OR_APPROVED_ACTIONS_IN_ORDER}}`; `{{OBSERVED_RUN_ID_OR_NOT_RUN}}`. Keep a failed cluster's evidence until reviewed; do not erase the first fatal error by reinstalling over it.

## Final handoff check

- [ ] All commands, paths, versions, digests, object names and expected outputs are concrete for the approved target; no unfilled placeholders remain.
- [ ] Every gate has PASS/FAIL/NOT RUN and a private receipt, and each mutation has an owner and rollback step.
- [ ] The seeded `runsc` path is verified from a fresh node, including SHA-256, executable bit and worker `runsc_path`.
- [ ] The GitLab ticket links to this completed Markdown, the evidence Markdown and the raw receipt index.
- [ ] The repeatability label states exactly what was executed on another cluster or node.

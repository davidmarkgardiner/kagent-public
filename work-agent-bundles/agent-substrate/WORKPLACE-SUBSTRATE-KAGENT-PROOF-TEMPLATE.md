# Work-agent request and Git-ticket evidence template: kagent on Agent Substrate

> **Starting point:** the work agent reports that its full lifecycle test passed. Treat that as a lead. Fill this document from the **actual workplace AKS run** so a reviewer can see what ran, what passed, and what a teammate can repeat. The public AKS runs in this repository are comparison material, not workplace receipts.
>
> Copy this file into the approved **private** project or ticket evidence area as `SUBSTRATE-KAGENT-EVIDENCE.md` before filling it in. Do not commit workplace names, URLs, identities, kubeconfigs, Helm values, logs, model responses, or credentials to this public repository. The ticket can attach the completed private Markdown and link to its access-controlled raw receipts.

## Copy this request to the work agent

```text
You reported a full Agent Substrate lifecycle pass on our work AKS cluster.
Please deliver four completed Markdown files in our approved private project:
1. SUBSTRATE-GITLAB-TICKET.md — short, directly pasteable GitLab issue text.
2. SUBSTRATE-KAGENT-EVIDENCE.md — the completed proof template, with receipt IDs.
3. SUBSTRATE-REDEPLOY-WALKTHROUGH.md — exact, ordered steps to reproduce on a
   fresh approved AKS cluster, including checks, expected results, and rollback.
4. SUBSTRATE-TEAM-DEMO.md — the presenter-paced script from
   demo/WORK-AGENT-DEMO-HANDOFF.md, with actual and expected observations.
Use the companion templates and demo handoff next to this file. Link the four files to one
another and to the private raw receipts. Do not return only a chat summary.

First reproduce H01–H07 in HOME-LAB-SUBSTRATE-PROOF-EXAMPLES.md using the exact
workplace run that already passed. Locate its raw, timestamped receipts; do
not replace them with a new run or a summary. State the installed
kagent/Substrate versions, source commits, chart/image digests, AKS node and
gVisor asset path. Link each claim to a command output, API response, status
record, log excerpt, trace, or object-store receipt from that same run.

Then, on an approved disposable non-production scope, run only the missing
checks needed for claims beyond home-lab parity: kagent-to-actor invocation,
real model/tool access,
stateful suspend/restore, sandbox/runtime identity, and the advertised
capacity/startup properties. If runsc is seeded into ATELET's shared runtime
volume, prove that path on a fresh disposable node; do not substitute a fetch
test for the actual deployment design. Record exact commands, observed outputs, UTC
times, actor/template/session IDs, and the before/after state. Keep raw
private output in our approved evidence store. Use the installed version's
CRD schema and approved GitOps workflow; do not copy commands from another
version blindly or alter the existing failing workload to make a test pass.

For every claim, mark PASS, FAIL, NOT RUN, or NOT SUPPORTED. Explain the
reason and next action for anything other than PASS. Do not infer an air-gap,
isolation, model call, state retention, or cost saving from a Ready condition
or an HTTP 200 agent card. Complete every runbook phase with actual Git paths,
versions, checksums, commands, expected and observed results, and a rollback.
If no second-cluster deployment was run, label repeatability DOCUMENTED ONLY.
Replace every template placeholder in the final four files or mark it NOT RUN
with a reason. Do not return only a chat summary.
```

## 1. Ticket front sheet

**Required private Markdown package:** use the companion [GitLab ticket template](WORKPLACE-SUBSTRATE-GITLAB-TICKET-TEMPLATE.md), [redeploy template](WORKPLACE-SUBSTRATE-REDEPLOY-WALKTHROUGH-TEMPLATE.md), and [team-demo handoff](demo/WORK-AGENT-DEMO-HANDOFF.md). In the completed private package, use `SUBSTRATE-GITLAB-TICKET.md`, `SUBSTRATE-KAGENT-EVIDENCE.md`, `SUBSTRATE-REDEPLOY-WALKTHROUGH.md`, and `SUBSTRATE-TEAM-DEMO.md`. Link the completed [ticket]({{PRIVATE_TICKET_MD_LINK}}), [demo]({{PRIVATE_DEMO_MD_LINK}}), and [redeploy walkthrough]({{PRIVATE_WALKTHROUGH_MD_LINK}}) here, and link this completed evidence report from all three. GitLab ticket links must point to completed private files. Use fenced text blocks for sanitized command excerpts so David can copy and paste them. Keep raw unredacted artifacts in the approved private evidence store.

| Field | Fill in |
| --- | --- |
| Git ticket and private evidence location | `{{TICKET_LINK}}`; `{{PRIVATE_EVIDENCE_LINK}}` |
| Test owner / reviewer / run date (UTC) | `{{OWNER}}`; `{{REVIEWER}}`; `{{YYYY-MM-DDTHH:MM:SSZ}}` |
| Target | `{{ENVIRONMENT}}`, `{{AKS_CLUSTER_ALIAS}}`, `{{NAMESPACE}}`, `{{NODE_POOL_ALIAS}}`; state whether this is non-production |
| Exact release pair | Substrate `{{VERSION}}` / source `{{COMMIT}}` / chart digest `{{SHA256}}`; kagent `{{VERSION}}` / source `{{COMMIT}}` / chart digest `{{SHA256}}` |
| Runtime and workload | gVisor or other `{{BACKEND}}`; `SandboxAgent` / `Agent` + `Harness` / `AgentHarness` `{{KIND_AND_API_VERSION}}`; workload image digest `{{SHA256}}` |
| Reported lifecycle run | `{{RUN_ID}}`, `{{START_UTC}}`–`{{END_UTC}}`, raw receipt index `{{LINK}}` |
| Overall verdict | `PROVEN FOR STATED SCOPE` / `PARTIAL` / `FAILED`; one sentence explaining the smallest missing or failed gate |

**Evidence rule:** each PASS needs an artifact ID in section 6 from the same run, showing observed values, not just an expected result. Preserve the source command/API route and UTC timestamp. Use `NOT SUPPORTED` only with an installed-version source or schema receipt. If a check is unsafe or unapproved, mark `NOT RUN` and explain. A lifecycle pass can be valid while broader product claims remain `NOT RUN`.

**Current installation cross-check:** run the read-only [0.0.9/0.10.x audit](scripts/audit-substrate-install.sh) with an explicit kube context and retain its output privately as a receipt. If `workerpools.ate.dev`, `actortemplates.ate.dev`, or `sandboxconfigs.ate.dev` is absent on the claimed cluster, mark H01 and P01 `FAIL` for the current installation and reconcile the work agent's run ID, cluster/context and timestamp before accepting its claim. `INSTALL_CHECK_PASS` is not a lifecycle receipt.

## 2. What is installed and where it runs

| Check | Observed value | Receipt ID |
| --- | --- | --- |
| AKS/Kubernetes, node OS, kernel, architecture, VM SKU, container runtime; actual worker pod node | `{{VALUE}}` | `E-__` |
| Flux/Git revision and four chart releases/versions; rendered values reference | `{{VALUE}}` | `E-__` |
| Running `imageID` digests for kagent controller, Substrate control/data plane, `atelet`, `ateom`, generated agent image | `{{VALUE}}` | `E-__` |
| `WorkerPool` name, namespace, class, desired/ready replicas, placement and `SandboxConfig` | `{{VALUE}}` | `E-__` |
| `runsc` or version-specific gVisor asset: configured asset SHA-256, exact bytes at the content-addressed path, seeding or fetch mechanism, mount/permissions, worker `runsc_path` and node | `{{VALUE}}` | `E-__` |
| Snapshot store type, bucket alias, CA/trust route and object prefix; secret references only | `{{VALUE}}` | `E-__` |
| kagent agent CR, generated `ActorTemplate` UID/spec, golden snapshot ID/status, actor/session IDs | `{{VALUE}}` | `E-__` |
| Installed CRD/schema source used to decide supported runtimes and snapshot modes | `{{VALUE}}` | `E-__` |

Explain material differences from the prior [0.0.9 AKS baseline](WORK-AGENT-RUNSC-EQUIVALENCE-HANDOFF.md). A private `-SNAPSHOT` suffix or matching `runsc` hash alone does not establish source, image, or delivery-path equivalence. If the deployed pairing is 1.x, use its own `Agent`/`Harness` schema and asset format; the 0.0.9 `SandboxAgent` commands are not a 1.x test.

**Seeded-volume path:** In [Substrate v0.0.9's asset code](https://github.com/kagent-dev/substrate/blob/v0.0.9/cmd/atelet/sandbox_assets.go) (https://github.com/kagent-dev/substrate/blob/v0.0.9/cmd/atelet/sandbox_assets.go), ATELET uses the content-addressed `runsc-<sha256>` file if it already exists and passes its path to `ateom-gvisor`. A cache hit is checked with `os.Stat`, without rehashing the file. For a seeded deployment, independently record the actual file SHA-256, size, executable permission, mount visibility, and `runsc_path` on the worker node. Prove the seed is repeatable after a new-node or volume-recreation event. Check the exact installed private source for any difference from v0.0.9.

## 3. Claim-to-proof matrix

**First: home-lab parity.** Use the [public proof examples](HOME-LAB-SUBSTRATE-PROOF-EXAMPLES.md) to fill H01–H07 below with `PASS` / `FAIL` / `NOT RUN`, observed workplace values, run ID and raw receipt links. This is the exact 0.0.9 AKS lifecycle comparison. Record the deliberate difference between the public lab's internal fetch and the workplace's seeded shared volume. The public lab did not prove a real model/tool call or changed state survival.

| ID | Workplace status | Observed value and run ID | Raw private receipt |
| --- | --- | --- | --- |
| H01 — pinned install, node and worker | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| H02 — agent Ready, template and golden | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| H03 — exact `runsc` asset and delivery path | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| H04 — golden restore and agent card | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| H05 — Full pause/restore and agent card | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| H06 — Data commit/restore and agent card | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| H07 — three further fresh actor cycles | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |

**Then: broader claims.** Fill `Status`, `Observed`, and `Receipt` for every P row below. Record a separate run ID when a later test fills a gap in the originally reported run. Read the exact installed-version behavior before invoking lifecycle operations.

| ID | Claim and minimum observable proof | Status | Observed / run ID | Receipt |
| --- | --- | --- | --- | --- |
| P01 | **Installed through the intended path.** Flux revision/reconciliation, chart/CRD versions, healthy control/data plane, worker pod and generated workload image digests. | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| P02 | **kagent is wired to Substrate.** Agent CR `Accepted`/`Ready`, owning generated template and golden snapshot, selected `WorkerPool`; map one kagent request ID to the same actor/session in Substrate. | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| P03 | **A real request works.** Invoke through the approved kagent UI/API/A2A front door; record request/response IDs, successful model/provider call through the approved route, and a harmless tool call if tools are advertised for this agent. Agent-card HTTP 200 alone does not pass. | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| P04 | **Golden restore and idle suspension work.** Record actor transitions, worker assignment, snapshot object/version and successful next request from a restored actor; correlate timestamps and IDs rather than relying only on a final Ready state. | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| P05 | **Full checkpoint/restore retains process/session state.** Use a safe in-memory marker distinct from the durable file fixture; record it before suspend and after restore, response continuity, checkpoint mode, object receipt, and no fatal `runsc` stderr. | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| P06 | **Data commit/restore retains durable state.** Write a unique value into the approved `durableDir` fixture, commit, restore, and assert exact content and permissions. Resume between Full pause and Data commit if this release requires it. A matching agent card is insufficient. | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| P07 | **Worker slot is released and reused.** Show actor suspended, slot free, then a second distinct actor served by the same finite pool; count worker pods before/during/after. | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| P08 | **gVisor isolation is the actual backend.** Show WorkerPool class, `ateom-gvisor`/runtime config, selected node, actual `runsc` asset checksum, actor-to-sandbox mapping, and applicable admission/network boundaries. Configuration alone does not prove containment strength. | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| P09 | **Internal-only asset and snapshot path**, if claimed. On an approved fresh disposable node, show the actual delivery method: either an internal fetch or a completed seed into ATELET's shared content-addressed volume. Verify file hash, executable permission, worker `runsc_path`, snapshot upload/download, and public-egress deny/flow/DNS evidence. An Internet-connected test is not air-gap proof. | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| P10 | **Fast restore**, if claimed. Measure at least three cold-golden restores and three idle resumes from client request to first successful response; show every duration and the median, sample size, and baseline pod-start method. No borrowed upstream millisecond claim. | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| P11 | **Better idle capacity**, if claimed. Measure active/suspended actors, pool pod count and requested/observed CPU/memory at equal workload; show at least two distinct agents reusing fewer pods than a one-pod-per-agent baseline. State concurrency and limits. Do not claim a cost saving without a cost model. | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| P12 | **Optional workload paths.** For each claimed Go/Python/BYO declarative agent or `AgentHarness` backend, provide installed-version support evidence and a separate end-to-end invocation/restore receipt. Mark untested paths `NOT RUN` and unavailable paths `NOT SUPPORTED`. | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |
| P13 | **Recovery and operations**, if claimed. On disposable scope, show safe response to worker restart or actor relocation, snapshot recovery, error visibility, and cleanup/rollback; record any unavailable recovery mode. | `{{STATUS}}` | `{{OBSERVED}}` | `E-__` |

**Verdict boundary:** H01–H07 passing supports “the workplace reproduced the public 0.0.9 AKS runtime lifecycle,” subject to listed build/node/delivery differences. P01–P08 must also pass to say “kagent with gVisor Agent Substrate works for this tested agent, including a real request and state assertions.” P09–P13 are separate advertised or deployment claims and must not be rolled into that sentence without their own PASS. If model/tool access is outside scope, mark P03 `NOT RUN`. For a different backend, adjust P08 and name the exact tested backend. The kagent [concept page](https://kagent.dev/docs/kagent/0.x/concepts/agent-substrate/) (https://kagent.dev/docs/kagent/0.x/concepts/agent-substrate/) lists broader features; the [0.x walkthrough](https://kagent.dev/docs/kagent/0.x/examples/agent-substrate/) (https://kagent.dev/docs/kagent/0.x/examples/agent-substrate/) says Go only in its example, so verify runtime support against the installed build before promising Python/BYO or a harness.

## 4. Safe repeatable teammate walkthrough

Replace the placeholders in the **private copy**. Give exact version-matched commands or a GitOps path in the table; never paste credentials or unredacted resource dumps into the ticket. First list the preflight checks and the cleanup owner. Do not run cache eviction, fault injection, policy changes, or workload deletion on shared or production resources.

| Step | Approved action / exact command or Git path | Expected observation | Actual observation and receipt |
| --- | --- | --- | --- |
| 0. Preflight | Verify `{{CONTEXT}}` is approved non-production; note namespace, worker pool, quota, model route, snapshot store, and permissions. | Target and owner identified. | `{{RESULT}}` / `E-__` |
| 1. Inspect | Read installed CRDs, Helm/Flux revisions, node and worker placement, runtime asset, and current object-store health. | Section 2 matches this run. | `{{RESULT}}` / `E-__` |
| 2. Create | Submit one uniquely named canary through `{{GITOPS_PR_OR_APPROVED_METHOD}}`; retain commit and reconcile receipt. | Agent Accepted/Ready, generated template and golden snapshot. | `{{RESULT}}` / `E-__` |
| 3. Invoke | Send a unique marker via `{{KAGENT_FRONT_DOOR}}`; inspect request, model/tool and actor traces. | Real answer and correlated actor/session. | `{{RESULT}}` / `E-__` |
| 4. Suspend/restore | Use the version-specific safe lifecycle API or idle policy; send another request. | Snapshot recorded; actor resumes and marker survives. | `{{RESULT}}` / `E-__` |
| 5. Durable state | In a separate approved state fixture, write a unique `durableDir` value, commit and restore. | Exact bytes/permissions survive. | `{{RESULT}}` / `E-__` |
| 6. Pool reuse | Start a second uniquely named canary on the same bounded pool. | Suspended first actor frees a slot used by the second. | `{{RESULT}}` / `E-__` |
| 7. Clean up | Revert only this canary's GitOps change and delete its approved test data by policy; confirm reconciled removal. | No orphan actor/template/snapshot beyond retention policy. | `{{RESULT}}` / `E-__` |

Useful **read-only** starting checks after substituting local names (adapt resource kinds to the installed CRDs):

```bash
kubectl --context '{{KUBE_CONTEXT}}' api-resources | rg -i 'sandboxagent|agentharness|actortemplate|workerpool|sandboxconfig'
kubectl --context '{{KUBE_CONTEXT}}' get pods -n '{{SUBSTRATE_NAMESPACE}}' -o wide
kubectl --context '{{KUBE_CONTEXT}}' get workerpool -A -o wide
kubectl --context '{{KUBE_CONTEXT}}' get sandboxconfig -A
helm --kube-context '{{KUBE_CONTEXT}}' list -A
```

The repository's [0.x verifier](scripts/verify-aks-substrate.sh) (file: `scripts/verify-aks-substrate.sh`) checks CRDs, rollout, pool and agent readiness only. It does not prove P03–P13 and is not a verifier for the 1.x API.

## 5. Findings, limits and verdict

**What the original “full lifecycle passed” run actually proved:** `{{ONE_OR_TWO_SENTENCES_WITH_P_IDS_AND_RUN_ID}}`

**Failures or gaps:** `{{P_ID: FAILURE_OR_NOT_RUN_REASON, FIRST_FATAL_ERROR_IF_ANY, NEXT_TEST_OR_FIX}}`

**Version/documentation differences:** `{{INSTALLED_SOURCE_OR_SCHEMA_LINK_AND_IMPACT}}`

**Security/operational limits:** `{{ADMISSION_PRIVILEGES, NETWORK_BOUNDARY, STORAGE_RETENTION, UNTESTED_FAILURE_PATHS}}`

**Ticket decision:** `PROVEN FOR STATED SCOPE` / `PARTIAL` / `FAILED` — `{{EXACT_SCOPED_CONCLUSION}}`

**Reviewer sign-off:** `{{NAME}}`, `{{UTC_DATE}}`, `{{REVIEW_COMMENT_LINK}}`

## 6. Private receipt index

Store raw artifacts in `{{PRIVATE_EVIDENCE_LOCATION}}` with the ticket's access controls. A receipt can be a JSON/YAML status export, CLI transcript, trace, log slice, object metadata, GitOps reconciliation, metrics query, or screenshot with corroborating IDs. Record SHA-256 of each stored file so the ticket attachment can be checked later. Redact the **ticket summary**, not the original approved private evidence.

| ID | P IDs | UTC time / run ID | Source command or API route | Private artifact link | SHA-256 | What it shows |
| --- | --- | --- | --- | --- | --- | --- |
| `E-01` | `P__` | `{{TIME}}` / `{{RUN_ID}}` | `{{SOURCE}}` | `{{PRIVATE_LINK}}` | `{{SHA256}}` | `{{OBSERVED_VALUE}}` |
| `E-02` | `P__` | `{{TIME}}` / `{{RUN_ID}}` | `{{SOURCE}}` | `{{PRIVATE_LINK}}` | `{{SHA256}}` | `{{OBSERVED_VALUE}}` |

Public context only: [0.0.9 work-agent parity handoff](WORK-AGENT-RUNSC-EQUIVALENCE-HANDOFF.md), [AKS evaluation limits](AKS-EVAL-WORK-AGENT-HANDOFF.md), [air-gap guide](AIRGAPPED-AKS-README.md). These are not substitutes for this workplace receipt index.

# GitLab ticket template: kagent + Agent Substrate workplace proof

> Work agent: fill this in privately as `SUBSTRATE-GITLAB-TICKET.md`. The result must be directly pasteable into a GitLab issue or comment. Use Markdown links to the two completed private files and to access-controlled receipts. Replace all placeholders; for a missing item write `NOT RUN — reason` or `NOT SUPPORTED — installed-version evidence`, never leave a blank claim. Do not paste secrets, raw kubeconfigs, private hostnames or unredacted logs into a public ticket.

## Outcome

**Verdict:** `PROVEN FOR STATED SCOPE` / `PARTIAL` / `FAILED` — `{{ONE_SENTENCE_WITH_EXACT_SCOPE}}`

**Tested environment:** `{{NON_PRODUCTION_CLUSTER_ALIAS}}`; AKS/Kubernetes `{{VERSION}}`; node OS/architecture `{{OS_ARCH}}`; Substrate `{{VERSION_AND_COMMIT}}`; kagent `{{VERSION_AND_COMMIT}}`; gVisor asset `{{SHA256}}`; run ID `{{RUN_ID}}` (`{{UTC_DATE}}`).

**Home-lab parity:** H01–H07 `{{PASS_FAIL_OR_NOT_RUN}}` — `{{ONE_LINE_WITH_RUN_ID_AND_KEY_DIFFERENCE_SUCH_AS_SEEDED_RUNSC}}`.

**Additional claims that passed:** `{{P_IDS_WITH_ONE_LINE_OF_OBSERVED_RESULT}}`

**What remains open:** `{{P_IDS_WITH_FAIL_NOT_RUN_OR_NOT_SUPPORTED_REASON}}`

**Repeatability:** `VERIFIED ON SECOND APPROVED CLUSTER` / `VERIFIED ON FRESH NODE ONLY` / `DOCUMENTED ONLY` — `{{REDEPLOY_RUN_ID_OR_REASON}}`. A documented runbook does not establish a successful second deployment.

## Evidence and walkthrough

| Deliverable | Private Markdown link | What a teammate gets |
| --- | --- | --- |
| Full evidence report | [SUBSTRATE-KAGENT-EVIDENCE.md]({{PRIVATE_EVIDENCE_MD_LINK}}) | P01–P13 verdicts, observed values, artifact IDs, limits |
| Fresh-cluster redeploy instructions | [SUBSTRATE-REDEPLOY-WALKTHROUGH.md]({{PRIVATE_WALKTHROUGH_MD_LINK}}) | Pinned inputs, ordered GitOps/seed/canary steps, expected results, rollback |
| Raw receipt index | [Private evidence store]({{PRIVATE_RECEIPT_INDEX_LINK}}) | Timestamped command output, traces, manifests and SHA-256 checksums |

## Five receipts to inspect first

| Claim | Receipt link | Observed result |
| --- | --- | --- |
| Exact installed versions, image digests and worker node | [E-__]({{PRIVATE_LINK}}) | `{{OBSERVED}}` |
| Seeded `runsc` path, SHA-256 and actual worker `runsc_path` | [E-__]({{PRIVATE_LINK}}) | `{{OBSERVED}}` |
| kagent request → actor/session → real model or tool result | [E-__]({{PRIVATE_LINK}}) | `{{OBSERVED}}` |
| Full and Data checkpoint/restore with independent state assertions | [E-__]({{PRIVATE_LINK}}) | `{{OBSERVED}}` |
| Fresh-node seed or second-cluster redeploy and reconciliation | [E-__]({{PRIVATE_LINK}}) | `{{OBSERVED_OR_NOT_RUN}}` |

## Teammate try-it path

Use the [private redeploy walkthrough]({{PRIVATE_WALKTHROUGH_MD_LINK}}) in an approved non-production scope. Its final canary section gives the exact command or UI/API route, expected response, receipt location, and cleanup. Owner: `{{OWNER_OR_TEAM}}`. Required access/prerequisites: `{{SHORT_LIST}}`.

## Decision and follow-up

**Decision requested:** `{{PILOT_OR_REMAIN_EVALUATION_OR_FIX_BLOCKER}}`

**Next concrete action and owner:** `{{ACTION}}` — `{{OWNER}}` — `{{TICKET_OR_DATE}}`

**Known limits:** `{{AIRGAP_OR_PERFORMANCE_OR_ISOLATION_OR_HARNESS_GAPS}}`

**Reviewer:** `{{NAME_AND_UTC_DATE}}`

# Work-agent handoff: rehearse and evidence the team demo

Give this file and [`HANDS-ON-WALKTHROUGH.md`](HANDS-ON-WALKTHROUGH.md) to the
work agent. The intended output is **four completed private Markdown files**,
with real workplace receipts. The public home-lab example is a rehearsal
baseline, not a workplace pass.

## Copyable request

```text
Please prepare a live, presenter-led kagent + Agent Substrate demonstration for
an approved non-production cluster. Use the attached HANDS-ON-WALKTHROUGH.md
and the exact installed kagent/Substrate versions. First verify the kube
context, served CRDs, chart/image/source revisions, selected WorkerPool,
approved ModelConfig, ATELET/runsc delivery path, and current control-plane
health. The 0.0.9/0.10.x script is only valid for that API pair. If this is a
1.x API or required CRDs are absent, stop and produce a version-matched plan
and a precise blocker; do not call the old script a pass.

Rehearse the four pauses with a unique synthetic canary: agent Ready and
generated template/golden snapshot; first request plus actor suspension;
second request in the same session plus same-actor restoration/suspension;
third request in a new session plus a distinct actor and no inherited marker.
Correlate request ID, context ID, actor ID, worker, snapshot and UTC time.
Record the actual two actor IDs from the Substrate inventory or API logs;
different context IDs alone are insufficient. Verify the actor's model call
and the exact responses. Stop on missing lifecycle witnesses or failures.

Do not present this marker exchange as proof of all capabilities. Use the
P01-P13 matrix in WORKPLACE-SUBSTRATE-KAGENT-PROOF-TEMPLATE.md. For each
additional advertised capability we intend to show, rehearse a separate
version-matched, approved, read-only or disposable test and attach its receipt:
an actual tool call, seeded gVisor/runsc path and fresh-node behavior, Full
and Data state assertions, finite-pool reuse, timing/density measurements,
agentgateway front-door policy if deployed, optional runtimes/harness, and
recovery as applicable. The default canary port-forward does not test the
gateway. Mark each PASS, FAIL,
NOT RUN or NOT SUPPORTED with observed values and raw receipt IDs. Do not
borrow upstream performance numbers or infer isolation from a manifest.

Return these completed files in the approved private project:
1. SUBSTRATE-TEAM-DEMO.md: a presenter script that a teammate can follow
   without you, with exact commands/UI path, each pause, what to say, what to
   show, expected and actual observations, fallback on failure, and cleanup.
2. SUBSTRATE-KAGENT-EVIDENCE.md: completed H01-H07 and P01-P13 matrix, actor
   mapping, version/asset receipts, timestamps, raw artifact links and limits.
3. SUBSTRATE-GITLAB-TICKET.md: short GitLab-ready outcome with direct links to
   the demo, evidence, redeploy guide and access-controlled raw receipts.
4. SUBSTRATE-REDEPLOY-WALKTHROUGH.md: ordered, pinned import/seed/GitOps,
   verification, canary, rollback and cleanup steps for another approved
   cluster; state DOCUMENTED ONLY unless a second deployment really passed.

Use the existing public templates next to this handoff as the structure for
files 2-4. Put raw output in the approved private evidence store; include a
receipt index with UTC time, run ID, exact command/API route, artifact link and
SHA-256. Replace placeholders or state why a step was not run. Do not return
only a chat summary. Do not put workplace identifiers, endpoints, tokens,
kubeconfigs or raw logs in the public repository.
```

## Demo document contract

In `SUBSTRATE-TEAM-DEMO.md`, begin with the exact target and version pair and
link the audit receipt. Include a table with these columns for each scene:

| Scene | Presenter action | What the audience should see | Actual observation | Receipt | Verdict |
| --- | --- | --- | --- | --- | --- |
| Preflight | Explicit context and CRD audit | Required APIs available on this cluster | `{{OBSERVED}}` | `E-__` | `{{STATUS}}` |
| Agent creation | Apply unique synthetic canary | Ready, generated template, golden snapshot | `{{OBSERVED}}` | `E-__` | `{{STATUS}}` |
| Session A first turn | Send marker request | Real answer, actor ID, then suspension | `{{OBSERVED}}` | `E-__` | `{{STATUS}}` |
| Session A return | Reuse context ID | Exact marker, same actor ID, new suspension | `{{OBSERVED}}` | `E-__` | `{{STATUS}}` |
| Session B | New context ID | No marker, distinct actor ID | `{{OBSERVED}}` | `E-__` | `{{STATUS}}` |
| Additional stations | Only rehearsed P rows | Version-matched proof shown live | `{{OBSERVED}}` | `E-__` | `{{STATUS}}` |
| Cleanup | Remove only the canary | No leftover canary; retention stated | `{{OBSERVED}}` | `E-__` | `{{STATUS}}` |

The complete file must name the *actual* UI route, private command or GitOps
path, expected wording, receipt location, and what the presenter says if a
step fails. Include a separate `Capabilities shown` table matching every live
claim to a P row and a receipt. Leave broader claims off the spoken script
when their rows are `NOT RUN`, `FAIL` or `NOT SUPPORTED`.

## Source material

- [`WORKPLACE-SUBSTRATE-KAGENT-PROOF-TEMPLATE.md`](../WORKPLACE-SUBSTRATE-KAGENT-PROOF-TEMPLATE.md)
- [`WORKPLACE-SUBSTRATE-GITLAB-TICKET-TEMPLATE.md`](../WORKPLACE-SUBSTRATE-GITLAB-TICKET-TEMPLATE.md)
- [`WORKPLACE-SUBSTRATE-REDEPLOY-WALKTHROUGH-TEMPLATE.md`](../WORKPLACE-SUBSTRATE-REDEPLOY-WALKTHROUGH-TEMPLATE.md)
- [`HOME-LAB-SUBSTRATE-PROOF-EXAMPLES.md`](../HOME-LAB-SUBSTRATE-PROOF-EXAMPLES.md)
- [kagent 0.x Substrate example](https://kagent.dev/docs/kagent/0.x/examples/agent-substrate/) — https://kagent.dev/docs/kagent/0.x/examples/agent-substrate/
- [kagent Substrate concept](https://kagent.dev/docs/kagent/0.x/concepts/agent-substrate/) — https://kagent.dev/docs/kagent/0.x/concepts/agent-substrate/

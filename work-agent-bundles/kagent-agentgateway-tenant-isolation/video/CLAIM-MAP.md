# Claim-to-Evidence Map

## Evidence boundary

- Project: kagent and agentgateway tenant-isolation rehearsal with an integrated platform-owned Agent Substrate lane
- Story contract: approved `STORYBOARD.md`
- Source revision: local working tree based on Git revision `6bbfec72a406`; the bundle and video artifacts are currently untracked, so the commit alone is not a complete source identifier
- Runtime source: Kubernetes context `red`, inspected read-only on 2026-09-16 without changing the user's active context
- Functional source: sanitized red verification receipt from 2026-09-16; the end-to-end test suite was not rerun for this planning gate
- Fixture boundary: the incident, release and MCP data are synthetic fixtures
- Publication boundary: never show tokens, private endpoints, storage locations, full resource identifiers, local paths or unsanitized command output

## Claim map

| ID | Candidate claim | Evidence | Current check | Screen moment | Allowed wording | Required limitation |
|---|---|---|---|---|---|---|
| C01 | Namespace self-service needs controls outside the application-team namespace | `../ARCHITECTURE.md`; ownership and threat model | Design and manifests inspected | Beats 01, 03 | “Teams own their namespaced agent and tool workload; the platform owns the shared routing and policy boundary.” | Do not imply a namespace alone provides tenant isolation |
| C02 | The platform boundary combines identity, listener/route selection, typed references and network reachability | `../ARCHITECTURE.md`; rendered Gateway, policy, ReferenceGrant and NetworkPolicy resources; `../TEST-MATRIX.md` | Implementation and negative-test contract inspected | Beats 04, 05 | “Identity, route, reference and network controls each enforce a different part of the path.” | Do not present prompt instructions or `allowedNamespaces` as authorization or a network boundary |
| C03 | The rehearsal Gateway has five dedicated listeners and all five routes are accepted with resolved references | Current read-only red query; S01 in `../evidence/red/2026-09-16-summary.tsv` | Five listeners observed; five named routes reported `Accepted=True` and `ResolvedRefs=True` | Beats 02, 08, 09 | “The rehearsal Gateway has five dedicated listeners, and all five routes are accepted with resolved references.” | This is current configuration/readiness evidence, not proof that each data path completed now |
| C04 | The two team Agents and platform specialist are currently ready | Current read-only red query; S04 | Both Declarative Agents reported Ready; the SandboxAgent reported Accepted and Ready | Beat 09 | “Both team Agents and the platform specialist report ready.” | Readiness is not an end-to-end success result |
| C05 | The event A2A path completed and increased only its matching MCP counter | P01 in the sanitized summary; runtime receipt | Historical functional receipt retained; not rerun at this gate | Beat 10 | “In the recorded red run, the synthetic event task completed and the event MCP counter increased by one while the other lane stayed unchanged.” | Keep `synthetic` visible; do not imply an external incident system was tested |
| C06 | The chat A2A path completed and increased only its matching MCP counter | P02 in the sanitized summary; runtime receipt | Historical functional receipt retained; not rerun at this gate | Beat 11 | “In the recorded red run, the synthetic chat task completed and the chat MCP counter increased by one while the other lane stayed unchanged.” | Keep `synthetic` visible; do not imply an external release system was tested |
| C07 | The platform security specialist completed through its authenticated listener and returned its required review headings | P04 in the sanitized summary; runtime receipt | Historical functional receipt retained; current specialist Ready | Beat 12 | “The authenticated platform specialist completed and returned `TRUST_BOUNDARIES` and `SECURITY_VERDICT`.” | It is platform-owned, has no MCP tool and does not mean the two team Agents run on Substrate |
| C08 | The Substrate actor suspended with a new snapshot after the review | S05 in the sanitized summary; runtime receipt | Historical functional receipt retained; current ActorTemplate observed Ready with a snapshot; current WorkerPool replicas observed at 3 | Beat 12 | “After the recorded review, the actor returned to Suspended and a new snapshot was present.” | Do not show the snapshot location or full actor/template identifiers; do not claim physical deletion |
| C09 | Missing, wrong-lane and rogue-claim credentials were rejected on the Substrate listener | N20, N21 and N22 in the sanitized summary | Historical negative receipt retained | Beat 13 | “The tested calls returned 401, 401 and 403.” | Red used disposable JWTs, not live Entra identities |
| C10 | The tested rogue direct path to the Substrate specialist failed | N23 in the sanitized summary | Historical network-denial receipt retained | Beat 13 | “The tested rogue direct path timed out or was refused.” | This is one scoped negative test, not universal isolation certification |
| C11 | The wider bundle also denied direct MCP/controller paths, forbidden tools, RBAC, admission, Pod Security and missing-grant attempts | N07–N19 and N23 in the sanitized summary | Sanitized 35-gate summary inspected | Mention only in supporting caption or production notes | “The complete receipt contains 35 implemented positive and negative gates.” | Do not turn the video into a checklist tour or imply untested threats are covered |
| C12 | Entra policy resources match the installed agentgateway v1.5 schema | E01; `../evidence/red/2026-09-16-entra-schema-dry-run.md` | Server-side dry-run receipt inspected | Beat 15 | “The Entra policy resources passed server-side schema validation.” | No live Entra tenant, PKCE, application-role denial, token refresh, hostname, certificate or workload-token broker was exercised |
| C13 | The intended workplace target is kagent 0.10.1 and Substrate 0.0.9 with immutable source-image locks | T01; `../platform/substrate/target-platform.env`; `../AKS-SUBSTRATE-PROMOTION.md` | Sixteen source image digests were previously resolved; target verification receipt inspected | Beat 15 | “The target versions and sixteen source image digests were validated separately.” | Red's live Substrate lane remains kagent 0.10.0-beta7 with Substrate 0.0.8; the target pair was not proven live together here |
| C14 | agentgateway v1.5.0 and the separate ordinary-kagent v0.10.1 controller are deployed in red | Current read-only Helm query; runtime receipt | Both deployed releases observed | Production source caption only | “The rehearsal uses agentgateway v1.5.0 and kagent v0.10.1 for the two ordinary Agent lanes.” | Keep the historical shared Substrate-owner versions separate; do not collapse the runtimes into one version claim |

## Claims excluded from narration

- “The bundle proves production-grade tenant isolation.”
- “The red run proves live Microsoft Entra authentication.”
- “All three Agents run on kagent 0.10.1 and Substrate 0.0.9.”
- “Application teams can safely store secrets that must be hidden from their own namespace administrators.”
- “The dummy MCP fixtures prove the security of an external database or API.”
- “Accepted routes or Ready conditions alone prove the data path works.”
- Any performance, density, latency, availability, cost-saving or universal security claim.

## Capture-to-evidence rules

1. Generate screen cards from the sanitized summary and fresh read-only status projection, not from raw terminal recordings.
2. Label functional results **RECORDED RED RUN · 2026-09-16** and current status **READ-ONLY STATUS CHECK**.
3. Show counter deltas as `+1` and `+0`; do not publish incidental cumulative totals.
4. Show only resource roles such as `EVENT AGENT`, `CHAT AGENT` and `PLATFORM SPECIALIST` in public frames.
5. Keep the real evidence gate IDs in production notes, not in the main viewer narrative.
6. If the functional suite is rerun before capture, replace the historical labels only after a new sanitized receipt is written and reviewed.

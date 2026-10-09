# Example 01: evidence-first triage

Status: reviewable storyboard and draft narration

Target: 1:50–2:00

Series position: module 10 of the DICE journey

Format: David narration, presenter-free

Palette: red, grey, white and black

## Viewer promise

See how DICE turns related application logs, Kubernetes warning events and retries into one bounded investigation with useful evidence already attached.

## Opening soundbite

> A failing service can produce a log, a warning event and several retries. For the engineer, that's one investigation. DICE brings the evidence together and opens a ticket with the diagnosis already attached.

## Storyboard

| Time | Viewer question | Draft narration | On-screen treatment | Evidence job |
|---:|---|---|---|---|
| 0:00–0:14 | Why is triage noisy? | “A failing service can produce a log, a warning event and several retries. For the engineer, that's one investigation.” | Three white signal cards appear separately on charcoal. A red outline groups them under `ONE INCIDENT`. | Establish the problem without a dashboard montage. |
| 0:14–0:31 | What does DICE do first? | “DICE collects the signals, removes secret-shaped values and gives related evidence a shared incident identity.” | Four-stage rail: `COLLECT → REDACT → CORRELATE → INVESTIGATE`. Red advances one stage at a time. | Explain why raw signals do not go straight to a model or ticket. |
| 0:31–0:49 | Does the agent change anything? | “A read-only investigation agent receives a bounded evidence pack. It can inspect the affected workload and explain the likely cause, but it cannot modify the cluster.” | Evidence pack enters a grey `READ-ONLY INVESTIGATION` card. Write controls remain visibly locked. | Make the authority boundary understandable. |
| 0:49–1:16 | What happened in the demonstration? | “In the recorded lab run, the first signal opened a GitLab work item. A related event was correlated into the same investigation. When processing retried, DICE found the existing fingerprint and updated that item instead of creating another.” | Time-compressed replay: signal → ticket created; event → evidence appended; retry → `EXISTING ITEM REUSED`. Use sanitised identifiers or a labelled reconstruction. | Show create, correlate and retry behaviour as one sequence. |
| 1:16–1:34 | What does the engineer receive? | “The result is a reviewable incident record containing the symptom, the collected evidence, the agent's diagnosis and a suggested next check. The engineer starts from an evidence pack instead of an empty ticket.” | Expand the ticket into four sections: `SYMPTOM`, `EVIDENCE`, `DIAGNOSIS`, `NEXT CHECK`. | Show the human outcome rather than celebrating infrastructure. |
| 1:34–1:49 | What does this prove? | “This demonstrates one lab path from related signals to a reused, evidence-backed ticket. That revision still had open work around stable identity when pods are replaced, so the milestone is useful and deliberately scoped.” | Milestone card: `RECORDED LAB DEMONSTRATION`. Below: `Correlation ✓  Retry reuse ✓  Pod-churn identity: further work`. | State the exact proof boundary. |
| 1:49–1:58 | Where does the journey go next? | “The same rule applies to database answers: send useful evidence, and keep the result bounded before the model sees it.” | Journey rail moves from `TRIAGE` to `POSTGRESQL`. End card offers `Next: PostgreSQL without bulk context`. | Link into module 11. |

## Draft narration

A failing service can produce a log, a warning event and several retries. For the engineer, that's one investigation.

DICE collects the signals, removes secret-shaped values and gives related evidence a shared incident identity.

A read-only investigation agent receives a bounded evidence pack. It can inspect the affected workload and explain the likely cause, but it cannot modify the cluster.

In the recorded lab run, the first signal opened a GitLab work item. A related event was correlated into the same investigation. When processing retried, DICE found the existing fingerprint and updated that item instead of creating another.

The result is a reviewable incident record containing the symptom, the collected evidence, the agent's diagnosis and a suggested next check. The engineer starts from an evidence pack instead of an empty ticket.

This demonstrates one lab path from related signals to a reused, evidence-backed ticket. That revision still had open work around stable identity when pods are replaced, so the milestone is useful and deliberately scoped.

The same rule applies to database answers: send useful evidence, and keep the result bounded before the model sees it.

## Visual system

- Use charcoal as the canvas and white for primary text.
- Use grey cards for evidence and system stages.
- Reserve red for the active stage, incident grouping and milestone ticks.
- Keep a slim journey rail along the bottom after the opening shot.
- Use labels and icons with colour so the sequence remains understandable in greyscale.
- Keep all body text at a size readable in the Microsoft 365 player at normal desktop width.
- Add burned-in captions to the review cut; retain a separate transcript/caption file for delivery.

## Demonstration and evidence contract

- Scenario: a related application log and Kubernetes warning event reach the triage workflow, followed by a retry.
- Starting state: no open work item exists for the selected incident fingerprint.
- Visible result: one GitLab work item is created, related evidence is appended and the retry reuses the existing item.
- Proof source: `work-agent-bundles/evidence-first-worker-triage/next-phase-end-to-end/NEXT-PHASE-VERIFIED-SUMMARY.md` and its linked receipts.
- Capture rule: use a sanitised replay or a clearly labelled reconstruction. Do not expose private endpoints, tokens, usernames or unrelated ticket data.
- Proof boundary: this is a dated lab demonstration. It does not prove fleet resilience, workplace integration or stable deduplication across every pod replacement.
- Editorial boundary: do not combine this immediate signal-to-ticket demonstration with the later hourly admission workflow as if they were one recorded run.

## Acceptance checks before production

- The narration fits within two minutes at David's approved speaking pace.
- The problem, mechanism, demonstration and result are understandable without prior chapters.
- The ticket remains readable without pausing the video.
- The evidence label and open pod-churn limitation remain visible long enough to read.
- The chapter includes no excluded framework branding in narration, graphics, captions or source footage.
- The last line creates a natural hand-off to the PostgreSQL chapter.

Approval of this storyboard authorises preparation of a wireframe preview and a short voice audition only.

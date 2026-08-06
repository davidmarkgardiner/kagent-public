# Teams message — keep the alert source out of triage until verified

## Bottom line

The current alert source does not reliably represent what is happening in the
cluster. We are seeing materially more events and problems in the cluster than
appear in the alert stream.

Until we can prove that important alerts fire, arrive, and carry useful context,
this source must stay out of the triage system. Feeding it into triage now would
create noise, obscure real incidents, and waste engineering time. The priority
is to repair and verify the source, not to process unreliable alerts downstream.

## Copy-ready Teams message

Team — we have compared the alerts currently arriving with the actual state of
the cluster and found a significant gap: the cluster is showing more events and
problems than the alert stream reflects.

We should not connect this alert source to the triage system yet. Until we can
verify signal coverage, payload quality, and end-to-end delivery, it will mainly
fill the triage queue with incomplete or low-value noise.

The immediate work is to reverse engineer and fix the alert source, then prove
that the right alerts fire and arrive with the context needed for action. Until
that proof exists, please treat this source as excluded from automated triage.

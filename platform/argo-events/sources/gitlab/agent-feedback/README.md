# GitLab Agent Feedback Spike

This is an isolated, comment-driven human-to-agent feedback loop for GitLab issues. It is deliberately **not** a remediation trigger.

```text
GitLab issue note: @platform-agent <feedback>
  -> GitLab Note Hook -> Argo Events EventSource -> feedback Workflow
  -> read-only kagent A2A feedback agent -> one GitLab response note
```

## Interaction contract

The issue must carry `agent:waiting-for-human`. An allowlisted human posts:

```text
@platform-agent please revise the plan to use the payments namespace
@platform-agent approve
```

`approve` records an approval request only. It does not execute remediation,
merge GitOps, close the issue, or resume another workflow. A separate HITL
workflow must own any of those actions.

## Install

Replace every `{{PLACEHOLDER}}` and create the two secrets out of band:

```bash
kubectl -n argo-events create secret generic gitlab-agent-feedback-webhook \
  --from-literal=secret={{GITLAB_WEBHOOK_SECRET}}
kubectl -n argo create secret generic gitlab-agent-feedback-writer \
  --from-literal=api-token={{GITLAB_NOTE_WRITER_TOKEN}}
kubectl apply -f platform/argo-events/sources/gitlab/agent-feedback/
```

The GitLab project webhook points to `https://{{ARGO_EVENTS_HOSTNAME}}/gitlab-agent-feedback`, enables **Comment events**, and sends `Authorization: Bearer {{GITLAB_WEBHOOK_SECRET}}` as a custom header. The installed Argo Events CRD supports `authSecret`; it prunes the older `X-Gitlab-Token` fields. Put an HMAC-signature verifier in front of it before using GitLab's newer signing-token mode in production.

The writer token must be project-scoped and able only to create issue notes. Do not reuse a token that can push branches, merge MRs, or manage project settings.

## Validate without a cluster or GitLab

```bash
bash platform/argo-events/sources/gitlab/agent-feedback/scripts/verify-spike.sh
```

The test accepts the allowlisted feedback fixture and rejects unmentioned, unauthorised, missing-label, and self-authored notes. It does not contact GitLab.

## Live sandbox acceptance

1. Create an issue labelled `agent:waiting-for-human`.
2. Add `@platform-agent please revise the diagnosis` as an allowlisted user.
3. Confirm one `gitlab-agent-feedback-*` Workflow is created and one response note appears with the same note ID.
4. Redeliver the webhook; confirm the dedupe ConfigMap prevents a second note.
5. Try an unallowlisted author and an issue without the label; neither may call the agent or write a response.

This directory adds the inbound feedback contract but has not been applied to a live cluster or registered as a live GitLab webhook.

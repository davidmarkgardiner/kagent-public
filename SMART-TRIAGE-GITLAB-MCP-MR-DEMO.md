# Smart Triage GitLab MCP MR Demo

Purpose: prove the GitLab/GitOps specialist can move beyond dry-run output and
perform the real Git workflow shape: create a branch, write a file, update that
file, open a merge request, and post a follow-up note.

This is intentionally separate from production remediation. The demo should run
against a non-production GitLab project or sandbox repo first.

## Current Local Status

- `glab` is installed.
- This machine is authenticated to `gitlab.com` as the local user.
- The current `kagent-public` checkout has a GitHub remote, not a GitLab remote.
- The terminal MR proof was run from the terminal through `glab`.
- The kagent-mounted proof was run through a kagent Agent with a mounted
  `RemoteMCPServer` shim that called GitLab from inside the cluster.
- The official GitLab MCP endpoint still needs work-approved OAuth/auth
  integration before it replaces the shim.

Because the checkout is not a GitLab project, the live demo needs an explicit
target:

```bash
export GITLAB_PROJECT_PATH='{{GITLAB_NAMESPACE}}/{{GITLAB_PROJECT}}'
```

## How GitLab MCP Fits

GitLab provides an HTTP MCP endpoint at:

```text
https://{{GITLAB_HOST}}/api/v4/mcp
```

For GitLab.com, `{{GITLAB_HOST}}` is `gitlab.com`.

The intended agent flow is:

```text
smart-triage workflow
  -> HITL approval
  -> GitOps/GitLab specialist
  -> GitLab MCP tools
  -> create branch
  -> commit proposed change
  -> update branch after review context
  -> open MR
  -> comment with evidence and next steps
```

The public PoC currently emits a dry-run GitOps draft. This demo proves the real
write behavior that should replace the dry-run step in a work sandbox.

## Live kagent-Mounted MCP Proof

This is the proof that the write path can run from inside kagent, not only from
the terminal.

```text
Agent: smart-triage-gitlab-lite-specialist
RemoteMCPServer: smart-triage-gitlab-lite-mcp
Project: {{GITLAB_SANDBOX_PROJECT}}
Run ID: kagent-mounted-20260601T111546Z
Context ID: {{A2A_CONTEXT_ID_REDACTED}}
MR: https://{{GITLAB_HOST}}/{{GITLAB_SANDBOX_PROJECT}}/-/merge_requests/{{KAGENT_MCP_MR_ID}}
```

Returned proof markers:

```text
SPECIALIST_GITOPS: completed
KAGENT_MCP: called
GITLAB_BRANCH: created
GITLAB_FILE: created
GITLAB_FILE: updated
GITLAB_MR: created
MR_URL: https://{{GITLAB_HOST}}/{{GITLAB_SANDBOX_PROJECT}}/-/merge_requests/{{KAGENT_MCP_MR_ID}}
REMEDIATION_MODE: gitops_or_workflow_only
OUTPUT_SANITIZED: yes
```

API verification:

```text
iid: 2
state: opened
source_branch: smart-triage/kagent-mcp-demo-kagent-mounted-20260601T111546Z
target_branch: main
author: {{GITLAB_SANDBOX_AUTHOR_REDACTED}}
created_at: 2026-06-01T11:16:09.593Z
commits:
  - 3ce7f089 Add smart-triage kagent MCP live demo evidence
  - 7f49585f Update smart-triage kagent MCP live demo evidence
note_id: 3405417439
```

Important false starts captured during the run:

- Direct `RemoteMCPServer` registration against `https://gitlab.com/api/v4/mcp`
  returned `Unauthorized` with a static header token. Treat the official MCP
  endpoint as requiring the approved GitLab OAuth/auth path, not a guessed
  bearer-token shortcut.
- The first shim secret used the OAuth refresh token from local `glab`
  configuration and GitLab correctly returned `401 Unauthorized`. The working
  demo secret used the active API token from `glab config get token --host
  gitlab.com`.
- One model response fabricated an example MR URL. That output was rejected and
  the agent prompt was tightened so `created` markers are only valid after a
  tool result.
- The demo cluster had a transient scheduling issue (`worker2` NotReady and
  `worker1` at pod capacity). The live proof used a temporary placement patch
  for the demo pods and controller; do not copy that placement into the portable
  manifests.

## Live Terminal Proof

The terminal proof used `glab` against:

```text
Project: {{GITLAB_SANDBOX_PROJECT}}
MR: https://{{GITLAB_HOST}}/{{GITLAB_SANDBOX_PROJECT}}/-/merge_requests/{{TERMINAL_BASELINE_MR_ID}}
```

Result:

```text
GITLAB_BRANCH: created
GITLAB_FILE: created
GITLAB_FILE: updated
GITLAB_MR: created
```

API verification:

```text
iid: 1
state: opened
source_branch: smart-triage/gitlab-mcp-demo-20260601T103925Z
target_branch: main
changes_count: 1
user_notes_count: 1
commits:
  - 301eef3e Add smart-triage GitLab MCP live demo evidence
  - 0e864645 Update smart-triage GitLab MCP live demo evidence
note_id: 3405287833
```

The terminal proof proves the GitLab project, permissions, branch write, file
update, MR, and comment path. By itself, it does not prove kagent-mounted MCP.

The kagent-mounted proof above supersedes that limitation for the shim path. The
official GitLab MCP endpoint remains a separate auth-integration task.

## Local Live Demo Runner

Run:

```bash
GITLAB_PROJECT_PATH='{{GITLAB_NAMESPACE}}/{{GITLAB_PROJECT}}' \
  a2a/smart-triage-fanout-demo/scripts/run-gitlab-mr-demo.sh
```

Optional variables:

```bash
GITLAB_HOST='gitlab.com'
GITLAB_TARGET_BRANCH='main'
GITLAB_SOURCE_BRANCH='smart-triage/gitlab-mcp-demo-{{RUN_ID}}'
GITLAB_DEMO_FILE='docs/smart-triage/gitlab-mcp-live-demo-{{RUN_ID}}.md'
GITLAB_MR_TITLE='Smart triage GitLab MCP live write demo'
```

The runner performs these GitLab API operations using the authenticated `glab`
session:

1. Resolve the GitLab project.
2. Create a source branch from the target branch.
3. Commit a new demo evidence file.
4. Commit an update to the same file.
5. Open a merge request.
6. Post a follow-up note to the merge request.

Expected output:

```text
PASS: GitLab MR demo created
GITLAB_BRANCH: created
GITLAB_FILE: created
GITLAB_FILE: updated
GITLAB_MR: created
MR_IID: {{MR_IID}}
MR_URL: {{MR_URL}}
```

## Codex MCP Setup

To connect Codex directly to GitLab MCP, use the official HTTP endpoint:

```bash
codex mcp add --url "https://gitlab.com/api/v4/mcp" GitLab
codex mcp login GitLab
```

For self-managed GitLab:

```bash
codex mcp add --url "https://{{GITLAB_HOST}}/api/v4/mcp" GitLab
codex mcp login GitLab
```

After login, the agent should be able to use GitLab MCP tools directly for
project, issue, merge request, and repository operations. Keep this limited to
trusted sandbox projects until prompt-injection and permission controls are
reviewed.

## kagent RemoteMCPServer Shape

For a work cluster, the GitLab MCP server should be registered as a
`RemoteMCPServer` only after the auth model is approved.

```yaml
kubectl -n {{KAGENT_NAMESPACE}} create secret generic smart-triage-gitlab-mcp-auth \
  --from-literal=authorization='Bearer {{GITLAB_MCP_TOKEN}}'

kubectl apply -f a2a/smart-triage-fanout-demo/gitlab-mcp-remotemcpserver.yaml
kubectl apply -f a2a/smart-triage-fanout-demo/gitlab-mcp-agent.yaml
kubectl wait --for=condition=Accepted -n {{KAGENT_NAMESPACE}} \
  remotemcpserver/smart-triage-gitlab-mcp --timeout=120s
kubectl wait --for=condition=Ready -n {{KAGENT_NAMESPACE}} \
  agent/smart-triage-gitlab-mcp-specialist --timeout=300s
```

The sanitized manifests are:

- `a2a/smart-triage-fanout-demo/gitlab-mcp-remotemcpserver.yaml`
- `a2a/smart-triage-fanout-demo/gitlab-mcp-agent.yaml`

Authentication should come from the approved work secret mechanism. Prefer a
project-scoped or sandbox-only token over a personal token. Do not commit tokens,
OAuth credentials, private endpoints, or personal account secrets.

Important: the installed kagent `RemoteMCPServer` CRD supports `headersFrom`,
so an `Authorization` header can be injected from a Kubernetes Secret. That
makes the kagent-mounted proof feasible, but it should be run only with an
approved token scope.

## Smart-Triage Integration Point

Replace the synthetic GitOps specialist in
`a2a/smart-triage-fanout-demo/agents.yaml` with a GitLab-backed specialist that
is only invoked after HITL approval.

Required contract:

- `SPECIALIST_GITOPS: completed`
- `GITLAB_BRANCH: created`
- `GITLAB_FILE: created` or `GITLAB_FILE: updated`
- `GITLAB_MR: created`
- `REMEDIATION_MODE: gitops_or_workflow_only`

The workflow should capture:

- Project path.
- Source branch.
- Target branch.
- MR IID.
- MR URL.
- Commit IDs.
- Any failure class.

## Safety Rules

- Use a sandbox project first.
- Use a project-scoped token or approved least-privilege OAuth identity for that
  sandbox project. Do not test the MCP write path with a broadly scoped personal
  or group token.
- Use a feature branch; never commit directly to the target branch.
- Set `remove_source_branch=true` on the MR where appropriate.
- Require HITL before branch creation if the branch contains remediation logic.
- Do not allow general triage agents to hold GitLab write tools.
- Keep GitLab write tools restricted to the GitOps specialist identity.
- Treat the public demo's sandbox constraint as prompt-level unless the token
  and project permissions prove infrastructure-level isolation.
- Capture MR evidence in the execution review before claiming success.

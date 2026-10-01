# SDLC rig installer start prompt

You are installing the GitLab issue-board SDLC rig directly into the designated
work sandbox cluster. You have cluster-admin access for installation. Complete
target discovery, configuration, installation and a real end-to-end canary;
do not stop at a plan, rendered YAML or Ready pods. Keep the existing platform
and unrelated workloads intact. Use the designated sandbox GitLab project.

Read README.md, WORK-CLUSTER-RUNBOOK.md, REVIEW-TASKS.md,
work-profile.example.json and evidence/RUN-2026-09-27.md first. Read
LIVE-DEMO-RUNBOOK.md and open BOARD-POLLING-PRESENTATION.html before preparing
a stakeholder demonstration. The rig assets
are supplied, including its fixed-project GitLab MCP. kagent, agentgateway,
a working model route, CI runner and environment-owned Secrets are prerequisites,
not automatically installed by render-work-bundle.py.

## 1. Discover and resolve prerequisites

Inspect the current kube context and cluster identity, node capacity, installed
kagent/controller/CRD versions, controller Service/A2A path and pod labels,
agentgateway namespace/Deployments, model endpoint and model name, Secret
references, CNI NetworkPolicy support, admission policy, DNS and image registry
reachability. Verify Python 3, PyYAML, kubectl, jq and curl on your installer host.
The lab used kagent v0.7.13: inspect target schemas rather than assuming that
version's manifests will work unchanged.

Use existing target platform components. If a prerequisite is absent, install
or configure the approved target component within the authorized sandbox
installation scope, using the platform's pinned charts/manifests and delivery
conventions. Do not upgrade or replace an existing shared installation simply
to match the lab. Missing platform approval, model entitlement or an unknown
sandbox identity is a real missing input; cluster-admin does not supply those.
Ask only for missing inputs that you cannot safely discover.

Find the designated GitLab API URL, exact project path, target branch, allowed
file paths, CI runner and protected-branch settings. Verify the token supplied
through the target secret manager can identify its bot user, read this project,
and perform the issue/branch/commit/draft-MR/note operations required by the
canary. Prefer a project-scoped token; an approved service-account PAT can be
used when project tokens are unavailable. Check scope, role and expiry. Never
ask for a token in chat or print/store it in public Git, shell history or logs.

Distinguish your own installer MCP connection from the deployed rig's MCP:
access to an MCP tool in your session does not connect the Kubernetes agents.
The bundled renderer installs the constrained MCP and RemoteMCPServer wiring
used by the rig. Reuse an existing target MCP only after verifying equivalent
tool names, schemas, project/file restrictions and agent discovery; otherwise
install the supplied one. Use real MCP calls to prove access, not just a token
presence check. The poller also calls GitLab REST directly with the same Secret.

Confirm corporate CA/proxy and GitLab/model connectivity from cluster pods,
not only the installer workstation. Determine an approved digest-pinned image
and matching node architecture. Model gateway client credentials belong in
the rig namespace; provider credentials remain in the existing gateway.

## 2. Configure and install

Populate a private local profile from work-profile.example.json. Set all required
project, GitLab API, branch, file, model, Secret, controller/A2A, image and node
values; set optional CA/proxy/controller namespace values when needed. Keep
profile and rendered output outside public source control. Do not use lab tokens
or private endpoint values copied from another environment.

Ensure the dedicated sdlc-rig namespace, worker-node label, GitLab Secret
(gitlab-project-token / token), model client Secret, and optional combined CA
ConfigMap exist through target provisioning. Inspect existing objects first.
The renderer emits no Namespace or Secret. Follow the runbook to render the
18-resource manifest, run the offline tests, inspect the file allowlist and
suspended CronJob, and perform a server dry-run after namespace creation.
Correct target schema and selector differences, then install through the
approved target delivery process. Installation cluster-admin belongs to you;
do not grant it to PM/worker pods. Preserve the narrow poller Lease RBAC.

Run preflight with actual gateway/controller namespace and Deployment names.
Check Accepted/Ready Agents, RemoteMCPServer tool discovery, MCP ingress policy,
model route and scheduling. If GitLab CI needs bootstrapping, use the designated
sandbox owner's controlled CI configuration; runtime builders must never edit
.gitlab-ci.yml. For the included Node canary, CI invokes node --test tests/
directly rather than a builder-editable package.json script.

## 3. Prove the workflow

Configure/reuse a dedicated label-based GitLab board and create or tag a fresh
parent issue using LIVE-DEMO-RUNBOOK.md and DEMO-ISSUE-TEMPLATE.md. Preserve
unrelated labels, verify the resulting IID/URL, and expose board/issue/poller-log
views for observers. The installer does intake; the PM creates the annotated
child and delegates A2A workers, while the poller controls later labels.
Do not drag runtime cards or give label-write tools back to the PM.

Keep polling suspended. Verify a unique PM-to-echo A2A nonce and a real GitLab
MCP read against the configured project. Create one narrowly scoped parent
issue with explicit acceptance criteria and labels sdlc-rig-poc and agent:plan.
Use exactly one manual poller Job at a time; wait for each to finish. Observe
PM planning/child creation, A2A builder/tester/reviewer delegation, approved-file
commits, current-head CI, an open draft MR, and a bot-authored SHA-bound review.
Independently inspect the tester turn: the existing tester marker is PM text,
not independent executor evidence. Check GitLab artifacts yourself before
reporting acceptance. Do not bypass blocked states by forcing intermediate labels.

Run the runbook/review checklist's failed-CI repair, three-failure block,
unauthorized relabel, policy allow/deny and timeout/replay checks. A disconnected
A2A caller does not cancel the task. Keep operation supervised while durable
task-status hardening remains open; do not force a held Lease or blindly retry.
After the supervised canary passes, enable the schedule as specified in the
runbook and observe pickup and idle behavior. Record the resulting state and
remaining limitations; multi-issue unattended reliability is a separate gate.

## 4. Report evidence

Record sanitized target versions, manifest changes, test results, node placement,
Secret names (never values), actual MCP/model/A2A calls, issue/child/branch/current
SHA/pipeline/draft-MR/reviewer references and CronJob state in evidence/RUN-WORK.md.
Keep private URLs in the workplace evidence store. Report installed, execution
proven, and unattended-ready separately. Do not merge GitLab MRs, deploy their
code or alter unrelated repositories as part of this installer workflow.

The sibling gitlab-ci-agent-quality-gate bundle is a different workflow. Its
client/templates are supplied, but its evaluation bridge and isolated generated-
test executor still require implementation before that pipeline can run.

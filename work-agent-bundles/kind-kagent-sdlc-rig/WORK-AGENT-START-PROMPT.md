# SDLC rig installer start prompt

You are installing the GitLab issue-board SDLC rig directly into the designated
work sandbox cluster. You have cluster-admin access for installation. Complete
target discovery, configuration, installation and a real end-to-end canary;
do not stop at a plan, rendered YAML or Ready pods. Keep the existing platform
and unrelated workloads intact. Use the designated sandbox GitLab project.

The target already has kagent, a working ModelConfig/model route, and GitLab
tokens held in Kubernetes Secrets. Start by understanding that existing setup
and reusing it. These are discovery starting points to verify, not questions
to send back to the user or reasons to install a second platform.

You are authorized to inspect the cluster, installed resources, configuration,
existing deployment/Helm/GitOps wiring, Secret references and authenticated
GitLab/MCP metadata; infer the required target values; adapt the supplied assets;
and install/configure the dedicated SDLC sandbox resources. You may provision
the required namespace, narrow RBAC, policy, Secret wiring, agents, constrained
MCP, poller and sandbox CI prerequisites, and create demonstration issues,
branches, commits and draft MRs in the designated project. Carry the work through
to live proof without asking approval for each routine installation step.
Existing authorization does not include changing unrelated workloads, replacing
the shared model/platform, broadening runtime privileges or merging GitLab MRs.

Do not open with a prerequisite questionnaire. Investigate first, explain the
inferred setup briefly, and proceed. The expected user input is only access to a
working GitLab MCP and the designated project if it is not already available.
Verify both yourself using real calls. Ask only when investigation establishes
a genuine blocker: unavailable/expired credentials or permissions, an ambiguous
target/project that cannot be resolved, or a required external entitlement.
Group any such blockers into one concise request with the failed check and the
smallest remedy. Do not ask the user to supply values you can discover or decide.

Read README.md, WORK-CLUSTER-RUNBOOK.md, REVIEW-TASKS.md,
work-profile.example.json, HOMELAB-REFERENCE.md and evidence/RUN-2026-10-01.md first. Read
LIVE-DEMO-RUNBOOK.md and open BOARD-POLLING-PRESENTATION.html before preparing
a stakeholder demonstration. The rig assets
are supplied, including its fixed-project GitLab MCP. kagent, agentgateway,
a working model route, CI runner and environment-owned Secrets are prerequisites,
not automatically installed by render-work-bundle.py.

## Execution order: one checkpoint at a time

Follow these checkpoints in order. The later discovery/configuration sections
are reference instructions to use as each checkpoint needs them; do not turn
them into an upfront questionnaire or attempt every integration at once. Before
advancing, record the actual check, result and evidence reference in a checkpoint
ledger in evidence/RUN-WORK.md (or the private workplace evidence store). Report
each checkpoint briefly as PASS or BLOCKED. PASS means proceed autonomously;
it is not a request for user approval. If a checkpoint fails, diagnose and repair
that checkpoint, then repeat its failed check before proceeding. Only ask for
help when a concrete blocker cannot be resolved with existing access. Reuse
successful artifacts rather than creating duplicate issues or replaying agents.
At each checkpoint, use HOMELAB-REFERENCE.md for the verified lab identities,
YAML/Secret-reference examples, command shapes and issue/CI/review receipts.
Compare them with the actual installed target and adapt the names/endpoints;
do not copy lab credentials or mistake historical lab receipts for work proof.

### Checkpoint 1 — GitLab token, project and issue access

Discover the existing Kubernetes-held PAT/project token and exact designated
project first. Using it securely, verify the authenticated identity and project,
create one fresh, narrowly scoped demo parent with a unique run marker but no
intake labels, then read it back by IID and verify its title/body/marker. Prove
the relevant GitLab MCP create/read calls too; direct REST success alone does
not prove MCP wiring. Retain this issue for all subsequent checkpoints. Do not
invoke the planner or alter candidate repository code yet. Record project,
identity, Secret reference, issue IID/URL and actual create/read outcomes, never
the token. Resolve issue/MCP access before troubleshooting downstream agents.

### Checkpoint 2 — Label admission and poller pickup

Understand/reuse the existing kagent setup and install only the required sandbox
rig wiring using the reference sections below. Keep the CronJob suspended; verify
the poller's project, token reference, label selector, Lease and PM A2A endpoint.
Inspect the existing queue to avoid advancing unrelated active issues. Add
`sdlc-rig-poc` and `agent:plan` to the checkpoint-1 issue while preserving other
labels, and read it back. Run exactly one manual poller Job and observe its
`picked` log for this IID at `agent:plan`. Retain the Job name and log evidence.
Pods being Ready or an issue merely having labels does not prove pickup.

The supplied poller invokes PLAN immediately after pickup in that same Job;
there is no separate discovery-only/pause mode. Checkpoints 2 and 3 are ordered
observations of that single execution. Do not add a second Job or manually call
PLAN to manufacture a separate handoff. Await the Job's completion and inspect
both receipts before running any later-stage poll.

### Checkpoint 3 — Handoff to the kagent planner

The planner is the supplied PM Agent (`sdlc-pm`), not a GitLab assignee or a new
unconnected agent. Verify that the checkpoint-2 Job reached its real A2A endpoint
and completed PLAN. Check the bot-authored parent notes and exactly one annotated
child with the correct parent, branch and acceptance criteria. Verify the parent
advanced to `agent:build`. Record the PM turn and child IID; a pickup log by itself
does not prove successful planning. Do not trigger BUILD until this passes.

### Checkpoint 4 — Planner delegates implementation

Run the next single manual poller Job only after checkpoint 3 passes. Verify the
PM delegates through A2A to the builder and that a real approved-file commit is
created on the expected sandbox branch. Read the branch/diff and parent progress
notes independently; require the permitted scope and record the full SHA. Keep
the candidate unmerged. The proven rig uses one child and several specialist
roles; do not present it as arbitrary multi-task parallel planning.

### Checkpoint 5 — Testing, draft MR and peer review

Resolve CI runner prerequisites now if needed. Require actual successful CI at
the checkpoint-4 branch head, then advance through TEST, draft-MR creation and
REVIEW with one completed manual poller Job per checkpoint. Verify the tester's
real delegation, current-head pipeline/job results, exactly one open draft MR,
and the bot-authored reviewer verdict naming the parent and full SHA. Record
each substage separately and inspect its GitLab artifacts before the next poll.
Do not treat PM/tester text as independent generated-test executor evidence.

### Checkpoint 6 — Acceptance and scheduled demonstration

Run the acceptance poll only after matching test/MR/review evidence passes.
Independently verify the accepted label, current SHA, allowed diff, green CI,
draft MR and reviewer PASS. Then complete the runbook's controlled failure/policy
checks. Enable the normal schedule only after supervised proof passes; use a new
demo parent to prove scheduled pickup, the complete flow and return to idle.
Retain the final CronJob/Lease state and observer links. Do not reset the first
issue or force intermediate labels to repeat the demonstration. Human GitLab MR
merge remains separate. This order becomes the later audience walkthrough:
issue access → label pickup → planner → builder → tests → review → acceptance.

## 1. Discover and resolve prerequisites

Inspect the current kube context and cluster identity, node capacity, installed
kagent/controller/CRD versions, controller Service/A2A path and pod labels,
agentgateway namespace/Deployments, model endpoint and model name, Secret
references, CNI NetworkPolicy support, admission policy, DNS and image registry
reachability. Verify Python 3, PyYAML, kubectl, jq and curl on your installer host.
Use the existing kubectl: there is no requirement for version 1.36. Discover
client and server versions with kubectl version -o yaml. The client must be
within one minor version of every target kube-apiserver; prefer the same minor.
For a 1.31 server, kubectl 1.31 is suitable (1.30–1.32 is the supported skew).
Resolve missing installer utilities or an incompatible client within the
authorized environment instead of asking the user to choose a version. Do not
upgrade the cluster to satisfy an installer-tool preference. See the official
[version-skew policy](https://kubernetes.io/releases/version-skew-policy/).
The lab used kagent v0.7.13: inspect target schemas rather than assuming that
version's manifests will work unchanged.

Trace a working Agent to its ModelConfig, gateway/backend and Secret references.
Recover the actual model name, endpoint, provider settings, client authentication,
controller namespace/Service/port and A2A URL from that wiring. Reuse the existing
model route; do not ask for a new model/provider key. Discover CA, proxy, registry,
namespace, node selector and scheduling conventions from installed resources.
Use measured capacity to choose placement and the supplied bounded defaults for
the dedicated namespace, two-minute suspended poller and narrow permissions.
If multiple targets remain equally plausible after inspecting the configuration,
ask which target is intended; never guess a production project or cluster.

Use existing target platform components. If a prerequisite is absent, install
or configure the approved target component within the authorized sandbox
installation scope, using the platform's pinned charts/manifests and delivery
conventions. Do not upgrade or replace an existing shared installation simply
to match the lab. Missing platform approval, model entitlement or an unknown
sandbox identity is a real missing input; cluster-admin does not supply those.
Ask only for missing inputs that you cannot safely discover.

Trace existing GitLab MCP Deployments/RemoteMCPServers, pod environment and volume
references to the current GitLab Secret name, namespace and key. Identify the
API URL and project from deployment settings, GitLab MCP calls, authenticated
project metadata and any supplied repository remotes. Do not ask for another PAT
when the existing Secret works. Inspect Secret metadata/references first; access
values only inside the authenticated operation that needs them, without printing
Secret objects, base64 data or decoded values. If this rig needs a Secret in its
own namespace, reuse the existing secret-delivery mechanism or provision the
minimum required credential securely within the authorized sandbox scope.
Leave the source Secret and existing consumers intact; do not export unrelated
credentials. Provider credentials stay in the gateway's existing namespace.

Find the designated GitLab API URL, exact project path, target branch, allowed
file paths, CI runner and protected-branch settings. Read CI-RUNNER-SETUP.md if no approved
runner exists; the agent PAT/MCP connection alone does not execute CI. Verify the token supplied
through the target secret manager can identify its bot user, read this project,
and perform the issue/branch/commit/draft-MR/note operations required by the
canary. Prefer a project-scoped token; an approved service-account PAT can be
used when project tokens are unavailable. Check scope, role and expiry. Never
ask for a token in chat or print/store it in public Git, shell history or logs.
Discover the default branch, existing CI, runner eligibility and repository
layout through authenticated reads. Derive a minimal file allowlist and a small
canary from that repository rather than asking the user to design them. Prefer
a bounded documentation change that existing tests can exercise; do not assume
the sample Node calculator files exist in the work project. If no eligible CI
runner exists, reuse or provision an approved sandbox runner when the current
installer identity permits it. Request runner-creation access only after an
actual permission failure; the runtime Developer token need not have that right.

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
Populate this profile yourself from the discovered configuration. It is your
installation artifact, not a form for the user to complete. Make the smallest
schema/authentication adjustments needed to preserve the working target route;
if the renderer cannot express that route, adapt the rendered assets and document
the delta rather than replacing it with the lab's Kimi configuration.

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
parent issue using LIVE-DEMO-RUNBOOK.md and DEMO-ISSUE-TEMPLATE.md at the relevant
execution checkpoint. Reuse the checkpoint-1 parent for the supervised run; do
not create another parent just because this reference section is reached. Preserve
unrelated labels, verify the resulting IID/URL, and expose board/issue/poller-log
views for observers. The installer does intake; the PM creates the annotated
child and delegates A2A workers, while the poller controls later labels.
Do not drag runtime cards or give label-write tools back to the PM.

Keep polling suspended during the supervised checkpoints. Verify a unique
PM-to-echo A2A nonce as a routing check before the first poll and a real GitLab
MCP read of the checkpoint-1 parent. Apply intake labels only at checkpoint 2.
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

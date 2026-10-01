# Live GitLab board demonstration

Start with WORK-AGENT-START-PROMPT.md. Install and verify the target stack before
inviting an audience. This runbook is for the designated work sandbox; no
workplace run or real-time browser refresh behavior has been proven here.
Open BOARD-POLLING-PRESENTATION.html locally for the conceptual walkthrough.
It has no credentials and does not connect to GitLab or poll the cluster.

## Set up the real Kanban view

Create/reuse these exact project labels: sdlc-rig-poc, agent:plan, agent:build,
agent:test, agent:review, agent:changes, agent:accepted, agent:blocked. These are
single-colon labels, not GitLab's double-colon scoped labels. Keep the exact
spellings: the poller recognizes them. Do not replace them with status fields.

In GitLab Plan > Issue boards, use a dedicated demo board or the sandbox's
existing board when its tier limits the number of boards. Add seven label lists
in order: plan, build, test, review, changes, accepted, blocked. Use a label
filter for sdlc-rig-poc in the board view so unrelated issues do not distract.
Do not add an sdlc-rig-poc column: every active card would also appear there.
Accepted issues stay open, so Accepted is a label list, not the Closed list.

Lists show matching labels; the poller removes the old state label and adds the
new one while preserving unrelated labels. That makes the card appear in the
new list. Verify update behavior in your installed GitLab; refresh the board
when the browser does not reflect an API change automatically. There is no
websocket/live UI guarantee in this bundle.

The installer/owner configures the board through the UI or bounded REST calls;
board/label-management tools are not exposed by the bundled GitLab MCP.
GET/POST /projects/:id/boards discovers/creates a board; GET/POST
/projects/:id/boards/:board_id/lists discovers/adds label lists using label_id.
Discover existing labels/lists first, reuse them, and never create duplicates
or alter a team board. Use the target's installer identity for setup.

Do not drag cards between runtime state columns during the live run. A human
adding build/test/review/changes labels is treated as an unauthorized state
change by the poller and blocks the issue. Only initial plan intake is manual.
Role assignment is A2A delegation, not separate GitLab user assignees. The
child is identified by title/description annotations, not a proven native
GitLab sub-issue hierarchy. Explain both distinctions to the audience.

## Create or tag the parent issue

Keep the CronJob suspended while preparing intake, and ensure no poller Job is
active. Verify token identity and exact project with a real MCP preflight/read.
Use DEMO-ISSUE-TEMPLATE.md for a narrow request. Confirm its prerequisite heading,
allowed file and green CI exist on the target branch before submitting it.

The installer can create the parent through its approved MCP connection:

```json
{"tool":"gitlab_create_issue","arguments":{"title":"SDLC demo: record README verification evidence","description":"{{FULL_CONTENT_OF_DEMO_ISSUE_TEMPLATE}}"}}
```

Capture the returned iid and web_url. The bundled create tool has no labels
parameter. Read the issue with gitlab_get_issue, preserve its existing labels,
then call gitlab_update_issue with iid and the complete label array containing
sdlc-rig-poc and agent:plan. Example for a fresh issue with no other labels:

```json
{"tool":"gitlab_get_issue","arguments":{"iid":123}}
{"tool":"gitlab_update_issue","arguments":{"iid":123,"labels":["sdlc-rig-poc","agent:plan"]}}
```

These JSON objects describe tool calls; use the actual connector/MCP invocation
mechanism available to the installer. Do not ask the runtime PM to relabel the
parent: its tool profile deliberately excludes gitlab_update_issue. If your
installer's MCP uses another schema, inspect tools/list first and adapt it.

Alternative: installer uses authenticated REST through the target secret
integration. POST /projects/:id/issues accepts title, description and
labels="sdlc-rig-poc,agent:plan". To tag an existing fresh issue, GET it, check
that it is open and has no conflicting agent state label, no prior rig child
and no agentic/sdlc-rig-<iid> branch; then PUT /projects/:id/issues/:iid with
add_labels="sdlc-rig-poc,agent:plan". This preserves unrelated labels. With MCP,
labels replaces the list: read and merge first. Never reset a completed run's
labels simply to replay it. Use a new issue for each demonstration.

Verify labels with a fresh read, retain the issue URL and IID in the workplace
demo notes, and open the ticket and board. Never paste credentials into the
HTML presentation or command output. Project paths must be URL-encoded for
REST; IDs avoid ambiguity. Other MCPs must still target the exact approved repo.

## Rehearse before the audience

Follow WORK-CLUSTER-RUNBOOK.md with one manual Job at a time while polling stays
suspended. Prove the full path and repair behavior. For the public demonstration,
prefer a fresh issue and scheduled intake after the rehearsal passes. Do not
mix manual and scheduled Jobs. A poll runs every two minutes and advances one
checkpoint, sometimes waiting on CI/model work. Allow roughly 15–30 minutes;
that is a planning allowance, not a measured workplace SLA. Long turns can
exceed it. For a faster narrated demo, keep polling suspended and advance
serialized manual Jobs, clearly explaining that it is operator-driven.

## Observe actual updates

Arrange three views: the GitLab label board, the parent issue activity, and a
terminal showing poller logs. Keep a fourth tab for pipeline jobs and the draft
MR. Add child/MR/CI tabs as the recorded references appear.

```bash
# Set KUBE_CONTEXT to the verified work sandbox; no credentials in commands.
kubectl --context "$KUBE_CONTEXT" -n sdlc-rig get jobs --watch
# In another terminal, copy the exact newest poller Job name from that view:
kubectl --context "$KUBE_CONTEXT" -n sdlc-rig logs -f job/{{POLLER_JOB_NAME}} --timestamps
# Check the scheduling and lock state without exposing Secret data:
kubectl --context "$KUBE_CONTEXT" -n sdlc-rig get cronjob sdlc-board-poller
kubectl --context "$KUBE_CONTEXT" -n sdlc-rig get lease sdlc-board-poller
```

Each poll creates a different Job. Reattach logs to the next Job; a completed
job's log stream does not automatically follow future Jobs. For agent details,
discover actual Deployment names with get deploy, then follow the PM/builder/
tester/reviewer Deployment logs using kubectl logs -f deployment/<actual-name>
--since=5m. Do not assume Agent and Deployment names match across versions.
Rehearse log selection and redact content before displaying it to the audience.
Never display Kubernetes Secrets, authorization headers, private customer data
or raw model payloads. Keep service logs bounded to this sandbox task.

Narrate observed checkpoints, not guessed activity:

| Board state | Parent activity / evidence to show |
|---|---|
| agent:plan | Labelled request; poller picked event; PM's annotated child |
| agent:build | Child/branch reference; actual builder delegation and allowed diff |
| agent:test | Current SHA and CI pipeline; waiting is a valid visible state |
| agent:changes | Failure/review reason; repair delegation; a new SHA |
| agent:review | Draft MR; bot-authored verdict naming parent and full SHA |
| agent:accepted | Matching green CI, draft MR and reviewer note; human merge remains |
| agent:blocked | Bounded failure reason or integrity guard; show diagnosis, not forced success |

Parent notes record checkpoint references. Worker reasoning is not continuously
streamed into the issue; CI logs, MR review notes and pod logs have different
purposes. Open the original source for each claim. A card disappearing from
one column and appearing in another is the real label transition; the offline
presentation's board is explicitly illustrative.

## When the workplace hits a problem

If no pickup: check exact labels, open issue, CronJob suspend, schedule and Job
state. If no child: inspect MCP/model/A2A errors and incomplete-turn notes.
If Pending: inspect node capacity, image pulls and admission. If MCP tools are
missing: check CRD/version/selector differences, controller discovery, CA/proxy
and enforced NetworkPolicy. If CI waits: check runner availability and current
SHA; indefinite CI waiting is a known hardening gap. If reviewer evidence is
missing: inspect actual tool calls and author/SHA bindings.

Suspend intake and wait for active Jobs before intervention. A client timeout
does not stop its agent task; do not immediately replay or force the Lease.
Record the symptom, last verified artifact, proposed fix and next proof. Present
the concept and lab evidence even if target installation is blocked, explicitly
stating where the live path stopped. Do not drag the board into Accepted.

## Finish and retain evidence

Record target issue/child/branch/SHA/pipeline/MR/review references and board URL,
redacted poller logs and actual controller/model versions in evidence/RUN-WORK.md
or the private evidence store. Keep the draft MR unmerged. Pause the schedule
after a one-off demo unless continuing sandbox intake is intended. Keep GitLab
artifacts for owner review; do not delete namespaces, branches or issues casually.

Official references:
https://docs.gitlab.com/user/project/issue_board/
https://docs.gitlab.com/api/boards/
https://docs.gitlab.com/api/issues/

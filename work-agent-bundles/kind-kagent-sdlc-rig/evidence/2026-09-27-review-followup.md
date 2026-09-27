# Review follow-up: read-only checks

Date: 2026-09-27. No cluster or GitLab object was changed during these checks.
The source changes are on draft PR #102; the running lab still uses the earlier
manifests, so these checks do not establish a successful policy canary.

- The home-lab controller image reports kagent `0.7.13`. Its running pod has
  `app.kubernetes.io/name=kagent` and
  `app.kubernetes.io/component=controller`; the updated policy selects these
  labels in the configured controller namespace. Existing `sdlc-rig` agent
  pods have their respective `app.kubernetes.io/name` labels.
- The lab runs Calico, but `sdlc-rig` has no MCP NetworkPolicy installed yet.
  Its RemoteMCPServer currently reports `Accepted=True` and discovered tools.
  The updated policy still needs a live controller discovery and isolation
  check after application.
- GitLab resource label event reads for existing parent issues #40 and #41
  returned numeric event IDs, `action`, label names, and user IDs. Issue #41
  had 50 events, including repeat `agent:changes` and `agent:test` transitions.
  This confirms the API shape used by the new author guard; the updated poller
  has not yet been exercised against a manual relabel.
- A read-only listing of the sandbox project's `main` tree returned only
  `README.md`. The required human-owned `.gitlab-ci.yml` must be added and
  checked before the next canary issue. It must call `node --test tests/`
  directly rather than a builder-editable npm script.
- The two lab worker nodes were `NotReady` during this check. The existing
  `sdlc-rig` pods were running on the control-plane node. This is not a healthy
  capacity baseline for a fresh installation.

The source bundle still needs a supervised run with policy enforcement, tool
discovery, one manual relabel, and a deliberately timed-out PM turn. The
25-minute replay hold remains a mitigation until the original turn's lifetime
is observed.

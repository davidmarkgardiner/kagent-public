# Workplace SDLC canary evidence

Copy this template to the private workplace evidence store. All checkpoints
start NOT RUN. Record actual observations; never copy the lab results as work
results. Record Secret references only, never values.

- Run marker / timestamp / operator: NOT RECORDED
- Designated kube context / sandbox project / target branch: NOT RECORDED
- Source commit / archive checksum / rendered-manifest checksum: NOT RECORDED
- Kubernetes / kagent / controller / CRD versions: NOT RECORDED
- Gateway route / model / node placement / approved image digests: NOT RECORDED
- GitLab identity / credential expiry / Secret names and keys: NOT RECORDED
- CI runner / human-owned CI command / current target-branch pipeline: NOT RECORDED
- CA/proxy / admission / enforced MCP allow-deny test: NOT RUN
- Server dry-run / 18-resource render / suspended CronJob / narrow Lease RBAC: NOT RUN

| Checkpoint | Status | Actual check and evidence reference |
|---|---|---|
| 1. GitLab identity/project; MCP create/read; unlabelled parent | NOT RUN | |
| 2. Admission labels; one manual Job; picked IID | NOT RUN | |
| 3. Same Job's real PM PLAN; one child; build state | NOT RUN | |
| 4. Real builder delegation; approved-file commit/diff/full SHA | NOT RUN | |
| 5a. Current-head successful pipeline and actual test totals | NOT RUN | |
| 5b. Actual tester delegation; SHA-bound receipt | NOT RUN | |
| 5c. One open draft MR on the same SHA | NOT RUN | |
| 5d. Real reviewer delegation; bot-authored parent/SHA PASS | NOT RUN | |
| 6a. Accepted parent; independent artifact verification | NOT RUN | |
| 6b. Failure/repair/three-failure block/relabel/replay checks | NOT RUN | |
| 6c. Fresh scheduled issue; completed flow; idle; clear Lease | NOT RUN | |

- Parent / child / branch / full SHA / pipeline / job / draft MR / review note: NOT RECORDED
- Final CronJob suspension / active Jobs / Lease holder: NOT RECORDED
- Installed: NOT PROVEN
- Target execution proven: NOT PROVEN
- Unattended-ready: NOT QUALIFIED
- Remaining blockers / rollback owner / retained artifacts: NOT RECORDED

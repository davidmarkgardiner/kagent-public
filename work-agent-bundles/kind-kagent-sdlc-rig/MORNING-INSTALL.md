# Workplace sandbox installation — 2 October 2026

The bundle is ready for a **supervised non-production installation**. Workplace
execution is still to be proven. The source baseline is GitHub main commit
`4f9f3d0168f95b45e5d242df141f9193b3b29074`; this transfer includes the small
handoff corrections described in [the review](evidence/REVIEW-2026-10-02.md).
The model route and environment-owned Secrets are reused, not supplied here.

## Start here

The installer host needs Python 3 with PyYAML, kubectl, jq and curl. The runner
chart is needed only if no eligible approved CI runner already exists.

1. Put the archive and its `.sha256` file together in a trusted local folder.
   Verify the outer checksum, extract, then verify every included file:

```bash
shasum -a 256 -c kagent-sdlc-work-bundle-2026-10-02.tar.gz.sha256
tar -xzf kagent-sdlc-work-bundle-2026-10-02.tar.gz
cd kind-kagent-sdlc-rig
shasum -a 256 -c MANIFEST.sha256
python3 -m unittest discover -s . -p 'test_*.py'
```

2. Give the work-side agent [WORK-AGENT-START-PROMPT.md](WORK-AGENT-START-PROMPT.md).
   It discovers the existing platform, verifies the designated sandbox, installs
   the rig and follows six sequential checkpoints. Copy
   [RUN-WORK.template.md](evidence/RUN-WORK.template.md) into the private workplace
   evidence store to record actual results. Never commit private profiles or URLs.
3. Render with the discovered private profile, inspect the 18 objects and perform
   target server dry-run after namespace creation. Use the renderer, not the raw
   historical lab YAML. The rendered poller starts suspended and requires its
   named Lease. Verify target image access, CRD schema, CA/proxy and enforced MCP
   NetworkPolicy before intake. Reuse an eligible CI runner; if one is missing,
   use [CI-RUNNER-SETUP.md](CI-RUNNER-SETUP.md).
4. Prove one supervised issue from plan to accepted with one child, allowed-file
   diff, successful current-head CI, one open draft MR and a bot-authored review
   naming the full SHA. Verify actual tester delegation. Then run the failure,
   policy and replay checks in [REVIEW-TASKS.md](REVIEW-TASKS.md). Only enable the
   schedule after the supervised proof passes; observe fresh scheduled intake
   and idle. Keep merge authority with the project owner.

The start prompt contains the sandbox installation scope for the work-side
operator. Confirm the designated target through discovery; it does not select
or authorize an arbitrary production context.

## Readiness boundaries

Yesterday's recorded Proxmox demonstration completed a scheduled end-to-end run
with green CI and an accepted issue; its draft MR stayed unmerged. Read
[RUN-2026-10-01.md](evidence/RUN-2026-10-01.md) for the receipts. The lab API was
unreachable during today's read-only refresh, so that record is historical.

Unattended reliability remains unqualified: durable A2A task recovery, per-issue
error isolation, CI wait limits and stronger tester artifacts remain open.
A timed-out client does not cancel the model task. Follow the replay hold and
inspect existing artifacts before retrying. A Kubernetes Lease coordinates
only one cluster; do not point multiple clusters at the same project queue.

The sibling GitLab CI agent quality gate is a separate design requiring its
bridge and isolated generated-test executor. It is not installed by this bundle.

# Demo request: prove a README change reaches a reviewed draft MR

Use a fresh sandbox issue. Before intake, confirm that README.md already has
an exact heading `## Verification`, and target CI is green and human-owned.
Adapt this request to the actual repository if that section does not exist.

## Goal

Demonstrate the SDLC workflow with a small, observable documentation change.

## Acceptance criteria

1. Add exactly one bullet under `## Verification`: `SDLC demo: issue-to-draft-MR evidence is recorded.`
2. Preserve every existing README line and section, with no unrelated edits.
3. Change only README.md. Do not edit .gitlab-ci.yml or CI controls.
4. Current-head GitLab CI must pass. The tester must report its actual evidence.
5. Open one draft MR, with a reviewer note naming this issue and the full head SHA.
6. Keep the MR unmerged and record artifact references on this parent issue.

## Intake labels

sdlc-rig-poc, agent:plan

The installer creates/tags the parent. The PM creates the annotated child and
delegates workers; the poller owns subsequent state transitions. This request
proves documentation orchestration, not the separate generated-test workflow.

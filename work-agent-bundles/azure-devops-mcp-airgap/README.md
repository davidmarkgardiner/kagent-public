# Azure DevOps MCP air-gap replication bundle

## Current code workflow handoff (2026-10-08)

Start with [FRONT-SHEET.md](FRONT-SHEET.md),
[HELM-OCI-WORK-AGENT.md](HELM-OCI-WORK-AGENT.md),
[WORK-AGENT-BUILD-INSTRUCTIONS.md](WORK-AGENT-BUILD-INSTRUCTIONS.md) and
[chart/](chart/).
The current `2.10.0-code1` image adds a bounded PAT-backed file commit/push
tool alongside Microsoft's branch creation and file-read tools. It supports
the scoped branch → read → edit/push → draft-PR workflow. The chart is packaged
and pushed as a Helm OCI artifact. Build its runtime image separately from the
source ZIP with locked npm dependencies, then push it to the internal image
registry. The image archive is an optional fallback.
The earlier v2 release and image tar below do **not** contain the code-push
extension.

## Configuration

The work agent supplies `{{INTERNAL_REGISTRY}}`, `{{CHART_REPOSITORY}}`,
`{{NAMESPACE}}`, `{{EXISTING_APPROVED_MODEL_CONFIG}}`, `{{ADO_ORGANIZATION}}`,
`{{ADO_PROJECT}}`, `{{ADO_REPOSITORY_ID}}`, `{{TARGET_BRANCH}}`,
`{{SOURCE_BRANCH}}`, `{{REVIEWED_BRANCH_PREFIX}}`, and
`{{REVIEWED_PATH_PREFIX}}` through private work values. The chart uses the
destination runtime image digest. The PAT and bridge key come from existing
Secrets, never from the source bundle or Helm values.

## Earlier read/draft-PR bundle (v2)

For the exact image list, versions and build requirements, start with
[IMAGE-IMPORT-REQUEST.md](IMAGE-IMPORT-REQUEST.md).
The fresh local build and offline test receipt is
[evidence/build-2026-10-07.json](evidence/build-2026-10-07.json).

Current release with the source ZIP, complete image archive and checksums:
https://github.com/davidmarkgardiner/kagent-work-bundles/releases/tag/azure-devops-mcp-airgap-v2

Give your work agent the source ZIP and [IMAGE-IMPORT-REQUEST.md](IMAGE-IMPORT-REQUEST.md).
Importing the complete image avoids a work-side Docker build. If image import
is unavailable, [WORK-AGENT-BUILD-INSTRUCTIONS.md](WORK-AGENT-BUILD-INSTRUCTIONS.md)
covers an internal build using approved package/base-image sources or mirrors.

For building and publishing inside work, start with
[WORK-AGENT-BUILD-INSTRUCTIONS.md](WORK-AGENT-BUILD-INSTRUCTIONS.md).
For deployment and the live demo, use [WORK-START-HERE.md](WORK-START-HERE.md).
The Helm chart and code-push handoff above supersede this v2 image for the
branch/edit/push use case.

| File | Purpose |
|---|---|
| Dockerfile | Connected build of complete Linux amd64 image |
| Dockerfile.offline | Offline application rebuild using imported dependencies image |
| build-and-export.sh | Build, test and export images/source/checksums outside the repo |
| app/ | Snapshot of the validated bridge, policy and pinned dependencies lockfile |
| kubernetes.template.json | No-download Deployment, Service, NetworkPolicy, RemoteMCPServer and Agent |
| config.example.json / render.py | Secret-free configuration and reviewed manifest rendering |
| install-secrets.py | Hidden-input PAT installation into the selected cluster |
| scripts/ | Shared kagent readiness and A2A invocation helpers |
| evidence/ | Sanitized lab proof and local image verification |
| chart/ | Helm chart source for the work OCI pipeline; image is separate |

The v2 bundle installed a scoped draft-PR integration alongside an existing kagent
platform. It requires approved network reachability to Azure DevOps Services or
a connected tool zone; a fully disconnected cluster cannot create cloud PRs.

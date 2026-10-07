# Azure DevOps MCP air-gap replication bundle

For the exact image list, versions and build requirements, start with
[IMAGE-IMPORT-REQUEST.md](IMAGE-IMPORT-REQUEST.md).
The fresh local build and offline test receipt is
[evidence/build-2026-10-07.json](evidence/build-2026-10-07.json).

The v2 release contains the complete image archive, checksums, and the
pre-Flux source ZIP:
https://github.com/davidmarkgardiner/kagent-work-bundles/releases/tag/azure-devops-mcp-airgap-v2

Give your work agent this source folder and
[IMAGE-IMPORT-REQUEST.md](IMAGE-IMPORT-REQUEST.md); the v2 source ZIP does not
contain the new `oci/` helpers or Flux guide.
Importing the complete image avoids a work-side Docker build. If image import
is unavailable, [WORK-AGENT-BUILD-INSTRUCTIONS.md](WORK-AGENT-BUILD-INSTRUCTIONS.md)
covers an internal build using approved package/base-image sources or mirrors.

For building and publishing inside work, start with
[WORK-AGENT-BUILD-INSTRUCTIONS.md](WORK-AGENT-BUILD-INSTRUCTIONS.md).
For deployment and the live demo, use [WORK-START-HERE.md](WORK-START-HERE.md).
For Flux delivery from a digest-pinned OCI manifest artifact, use
[OCI-FLUX-DEPLOYMENT.md](OCI-FLUX-DEPLOYMENT.md).

| File | Purpose |
|---|---|
| Dockerfile | Connected build of complete Linux amd64 image |
| Dockerfile.offline | Offline application rebuild using imported dependencies image |
| build-and-export.sh | Build, test and export images/source/checksums outside the repo |
| OCI-FLUX-DEPLOYMENT.md / oci/ | Render secret-free manifests and pin a Flux OCI source |
| app/ | Snapshot of the validated bridge, policy and pinned dependencies lockfile |
| kubernetes.template.json | No-download Deployment, Service, NetworkPolicy, RemoteMCPServer and Agent |
| config.example.json / render.py | Secret-free configuration and reviewed manifest rendering |
| install-secrets.py | Hidden-input PAT installation into the selected cluster |
| scripts/ | Shared kagent readiness and A2A invocation helpers |
| evidence/ | Sanitized lab proof and local image verification |

This bundle installs a scoped draft-PR integration alongside an existing kagent
platform. It requires approved network reachability to Azure DevOps Services or
a connected tool zone; a fully disconnected cluster cannot create cloud PRs.

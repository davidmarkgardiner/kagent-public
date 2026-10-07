# Azure DevOps MCP: image import and build request

Prepared 2026-10-07 from this bundle's Dockerfiles, lockfile, export script and
recorded build evidence. Give this page and the bundle source to the work agent
to prepare the internal import request. This page does not authorize deployment
or repository writes.

## What to request

For an existing kagent platform, the application needs **one complete MCP runtime
image**. Importing that image requires **no additional application Docker build**.
Optionally import the matching dependencies image for future offline source edits.
Importing only the public Node base requires a full build before deployment.

| Artifact | Exact reference/version | Purpose | Build required after import? |
|---|---|---|---|
| Complete application | `azure-devops-mcp:2.10.0-poc1` | Node, locked npm dependencies, native keytar/libsecret, HTTP bridge and policy | No, for unchanged application source |
| Dependencies image | `azure-devops-mcp-dependencies:2.10.0-poc1` | Optional base for offline bridge/policy rebuilds | Yes: `Dockerfile.offline` adds application source |
| Public Node base | `docker.io/library/node:22-bookworm@sha256:17b7fd60fd812617654c64b95f9b2dde94f103313073b672bc40fdad6dccbaa2` | Alternative input when building everything inside work | Yes: normal `Dockerfile`, with npm and Debian dependencies |

The two `azure-devops-mcp` references are **local build tags, not public registry
pull locations**. Do not submit them as Docker Hub download URLs. An approved
builder must produce/export them, or provide an accessible source registry and
manifest digest. The release below carries the image archive separately from
the public source ZIP; verify the downloaded checksums before import.

Published transfer artifacts for this build:

- Source ZIP: https://github.com/davidmarkgardiner/kagent-work-bundles/releases/download/azure-devops-mcp-airgap-v2/azure-devops-mcp-work-bundle-2026-10-07.zip
- Complete image archive: https://github.com/davidmarkgardiner/kagent-work-bundles/releases/download/azure-devops-mcp-airgap-v2/azure-devops-mcp-images.tar
- SHA-256 checksums: https://github.com/davidmarkgardiner/kagent-work-bundles/releases/download/azure-devops-mcp-airgap-v2/SHA256SUMS

Target platform: **linux/amd64**, the only architecture verified in the bundle.
Confirm the work node architecture before requesting imports. For ARM64, select
a verified matching Node digest, rebuild native dependencies and repeat testing.

Record the destination as:

```text
{{INTERNAL_REGISTRY}}/azure-devops-mcp@sha256:{{RUNTIME_MANIFEST_DIGEST}}
{{INTERNAL_REGISTRY}}/azure-devops-mcp-dependencies@sha256:{{DEPENDENCIES_MANIFEST_DIGEST}}
```

The dependencies destination is optional. Obtain registry manifest digests from
the actual publish/import receipt. The `localImageId` fields in
[evidence/build.json](evidence/build.json) are Docker configuration IDs, not
registry pull digests. Do not use them as destination manifest digests.

If work deploys through Flux, use
[OCI-FLUX-DEPLOYMENT.md](OCI-FLUX-DEPLOYMENT.md) after image import. Flux pulls a
separate manifest OCI artifact that references this complete runtime image by
its internal registry digest; the dependencies image remains optional.

## Software versions and non-image dependencies

| Component | Pinned version or source |
|---|---|
| Microsoft official MCP npm package | `@azure-devops/mcp` **2.10.0** |
| Bridge's direct MCP SDK | `@modelcontextprotocol/sdk` **1.31.0** |
| Native keytar | **7.9.0**, from `app/package-lock.json` |
| Node/OS base | Node **22**, Debian **Bookworm**, exact content fixed by the digest above |
| Bridge application package | **0.1.0**, with image release tag **2.10.0-poc1** |
| kagent validation baseline | **0.7.13**; compatibility must be checked against work's installed CRDs |

All transitive npm versions and integrity hashes are in
[app/package-lock.json](app/package-lock.json). The Node tag does not state a
patch version; retain the pinned digest and capture `node --version` from the
selected image for the import receipt rather than guessing one.

The normal Dockerfile installs Debian build packages `libsecret-1-dev`,
`python3`, `make`, `g++`, and runtime package `libsecret-1-0`. Their versions are
not pinned in the recipe. Capture the package inventory/SBOM from the resulting
image; a fresh connected build is not guaranteed byte-for-byte identical.
No separate Java, Python, Azure CLI, kubelogin, database or sidecar image is
required by this application's runtime. The complete image starts with no
`apt`, `npm` or `npx` downloads.

## Choose one delivery route

### A. Import a complete image: no work-side build

On an approved connected build host, from the bundle directory:

```bash
./build-and-export.sh /absolute/path/outside/repo/ado-mcp-transfer
```

This builds both images using [Dockerfile](Dockerfile), tests them, and exports
`azure-devops-mcp-images.tar`, `azure-devops-mcp-source.tar.gz`, `SHA256SUMS` and
`image-ids.txt`. Transfer through the approved intake process. On the receiving
host, verify checksums, load the archive and publish into the internal registry
using the procedure in [WORK-START-HERE.md](WORK-START-HERE.md). Only the complete
runtime image needs to be accessible to Kubernetes.

### B. Import Node and build inside work

Import the exact public Node reference above, then use the normal
[Dockerfile](Dockerfile). It has installer, dependencies and runtime stages,
all based on the same Node image; there is no second public base image to import.

```bash
docker build --platform linux/amd64 \
  --build-arg NODE_IMAGE='{{INTERNAL_REGISTRY}}/node:22-bookworm@sha256:{{APPROVED_BASE_DIGEST}}' \
  -t '{{INTERNAL_REGISTRY}}/azure-devops-mcp:2.10.0-work1' .
```

This route additionally needs approved npm and Debian sources/mirrors, including
every locked npm tarball. Merely importing Node or changing npm's default registry
does not make the existing lockfile URLs available. Follow
[WORK-AGENT-BUILD-INSTRUCTIONS.md](WORK-AGENT-BUILD-INSTRUCTIONS.md) for mirror
adaptations, testing and publishing. PATs are never build inputs.

### C. Import dependencies and build only the application offline

Use this when complete runtime import is unavailable but the dependencies image
can be imported, or when editing bridge source without changing dependencies:

```bash
docker build --platform linux/amd64 --network none --pull=false \
  -f Dockerfile.offline \
  --build-arg DEPENDENCIES_IMAGE=azure-devops-mcp-dependencies:2.10.0-poc1 \
  -t azure-devops-mcp:work-reviewed .
```

Load that exact dependencies tag into the builder first, or substitute its
internal reference. This recipe only copies application files; it needs no npm
or Debian downloads. Package/lockfile or Node ABI changes require rebuilding the
dependencies image. Docker builder metadata resolution is separate from
build-step networking; `--network none` alone does not guarantee zero builder
egress.

For any resulting runtime image, run the following before requesting rollout:

```bash
ADO_IMAGE='{{COMPLETE_RUNTIME_IMAGE_REFERENCE}}'
docker run --rm --platform linux/amd64 --network none --read-only "$ADO_IMAGE" node --test
docker run --rm --platform linux/amd64 --network none --read-only "$ADO_IMAGE" node image-smoke.mjs
docker run --rm --platform linux/amd64 --network none --read-only "$ADO_IMAGE" node -e 'require("keytar"); console.log("native keytar loaded")'
```

These checks prove offline behavior, not Azure DevOps access. The current
[2026-10-07 build receipt](evidence/build-2026-10-07.json) records 11 passing
tests, image IDs, archive hash, native keytar loading, HTTP discovery and an
offline source rebuild. The image was not live-tested against workplace Azure
DevOps.

## Existing platform prerequisites

Reuse installed kagent, its controller-generated Agent runtime, existing
agentgateway (where used), and an approved ModelConfig/model route. Their image
references must come from the workplace deployment; this bundle does not pin
or import the entire platform. Include init-container images in that inventory.
Do not request a platform upgrade merely to match the lab baseline.

The application also needs the rendered Deployment/Service/NetworkPolicy,
RemoteMCPServer and Agent resources, registry pull access, bridge authentication
Secret, PAT Secret and approved DNS/TLS/HTTPS connectivity to Azure DevOps
Services. Start with `dev.azure.com`; selected operations may also use
`vssps.dev.azure.com` and `almsearch.dev.azure.com`. Confirm actual network needs
for the selected tools. A fully disconnected runtime needs an approved connected
tool zone. This pinned integration targets Azure DevOps Services, not internal
Azure DevOps Server/TFS.

## PAT first; identity integration later

Request a short-lived, work-approved PAT with **Code: Read & write**
(`vso.code_write`) for the repository/PR trial, plus the identity's required
repository permissions. Verify Read and Contribute to pull requests on the
nominated repository. Normal Git pushes additionally need Contribute and, when
publishing a new branch, Create branch. Other tool families can require separate
read scopes; do not request Full Access simply because they appear in discovery.
PAT scope does not override repository denies, access levels or branch policies.

Microsoft references:
- PR creation scope: https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-requests/create?view=azure-devops-rest-7.1
- Repository permissions: https://learn.microsoft.com/en-us/azure/devops/repos/git/set-git-repository-permissions?view=azure-devops

**Current application capability:** eight read tools and optional creation of a
draft pull request for one configured project/repository/source/target pair.
Azure DevOps calls these pull requests (PRs). The bridge does not expose arbitrary
file updates, pushes, branch creation, merge/completion, autocomplete or reviewer
changes. A broader PAT cannot enable operations blocked by `app/policy.mjs`.
Prepare the reviewed source branch through the normal Git workflow; then test
repository read, scoped draft-PR creation and independent PR readback. Repository
editing through MCP would be a separately reviewed capability change and image
rebuild, not a permissions-only fix.

Use [install-secrets.py](install-secrets.py) and the deployment handoff for the
expected upstream PAT encoding. Keep the raw PAT out of this request, source,
build arguments, image layers and logs.

UAMI/AKS Workload Identity is a later integration phase, not a prerequisite for
these imports and not validated by this PAT bundle. Assess token acquisition,
refresh, Azure DevOps identity onboarding/permissions and the adapter's auth
path before promising a configuration-only switch. No extra identity-helper
image is included in this request.

## Copy to the work agent

> Prepare an image/dependency import request for this Azure DevOps MCP bundle.
> Prefer importing the complete linux/amd64 runtime image; include the matching
> dependencies image only if offline application rebuilds are required. If our
> intake accepts only public base images, request the pinned Node digest above
> and explicitly list the npm/Debian mirror prerequisites and normal Docker build.
> For each requested image state its real source registry/digest or transfer
> archive/checksum, destination internal repository, architecture and scan/SBOM
> requirements. Mark unavailable source artifacts or digests as unresolved rather
> than inventing public pull URLs. Inventory existing platform images separately.
> Report whether any work-side Docker build remains after import and name the
> exact Dockerfile. Include a PAT-first permission verification plan for repository
> reads and one scoped draft PR; clearly state that generic repo updates and
> merging are not implemented by this bridge. Keep UAMI/Workload Identity as a
> later phase. Prepare the request only; do not deploy or perform writes.

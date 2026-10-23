# Work agent handoff: publish an Azure DevOps MCP Helm OCI chart

This handoff fits a work pipeline that runs `helm package`, logs into an OCI
registry, then runs `helm push`. The chart source is `chart/`. The published
Helm OCI artifact installs the MCP bridge Deployment, Service and kagent
`RemoteMCPServer`. An example Agent and ingress NetworkPolicy are optional.

The chart references a **separately built and pushed container image by its
internal registry manifest digest**. `helm package` does not build the runtime
image, and `helm push` does not publish it. Build the image from the source ZIP
in the approved work builder using `Dockerfile` and its locked npm dependencies.
The image tar is a fallback when the work builder cannot reach approved base,
Debian and npm package sources. The earlier `azure-devops-mcp-images.tar` v2
release has only reads and scoped draft PR creation; it cannot push file changes.

For a disconnected work builder, transfer the **custom** image archive first.
It contains `azure-devops-mcp-dependencies:2.10.0-poc1` (Node, Microsoft's
locked npm package, native dependencies and the MCP SDK) and the complete
`azure-devops-mcp:2.10.0-code1` runtime. There is no Microsoft-published
Azure DevOps MCP container image in this handoff. Import and push the complete
runtime if no adapter change is needed. To rebuild the bridge inside the air
gap, import the matching dependencies image, then use `Dockerfile.offline` to
copy the reviewed `app/` source on top. Validate and push that resulting runtime
image before setting its destination digest in Helm values. Importing only the
Node base image does not supply the npm or Debian packages for an offline build.

Transfer sources:

- Chart, adapter and image-build source: the attached `azure-devops-mcp-code-workflow-2026-10-08.zip`. Extract it, follow `WORK-AGENT-BUILD-INSTRUCTIONS.md` for the image build, and use `azure-devops-mcp-airgap/chart/` as the `helm package` input.
- Optional fallback runtime archive: `azure-devops-mcp-code-images-2026-10-08.tar`.
- Transfer checksums: the attached `SHA256SUMS-ado-mcp-code-2026-10-08`.
- Official Microsoft MCP: https://github.com/microsoft/azure-devops-mcp

## Copy this task to the work agent

> Use the attached `chart/` source in our existing Helm OCI packaging pipeline.
> Preserve our current chart naming, registry login, scan/signing and deployment
> controls. Confirm the work kagent `Agent` and `RemoteMCPServer` CRD schemas
> against the chart before publishing. Package and push the chart to the
> nominated `oci://` chart repository, and report the chart reference, version
> and registry digest. Keep any work values and rendered manifests outside the
> public source. Do not place PATs, bridge keys or registry passwords in chart
> values, artifacts, build arguments or logs.
>
> Separately build Linux amd64 `azure-devops-mcp:2.10.0-code1` from the included
> Dockerfile using the pinned npm lockfile and approved build sources, then push
> it to our approved container image registry. Use the image tar only if a
> source build is unavailable and the imported image passes our controls.
> Run the offline tests and native keytar check. Capture the **destination
> registry manifest digest** and put that `image.ref` in private chart values.
> The image archive is not a chart and
> the chart does not carry the image. Check target node architecture.
>
> First render the chart with `codePush.enabled=true`, the reviewed sandbox
> project, repository, target branch, source branch prefix and path prefix. Enable
> `draftPr.enabled=true` if a draft PR is in scope. If creating the example
> Agent, use an existing approved ModelConfig. Use an existing work-approved
> PAT Secret and separate bridge-key Secret. Server-side dry-run against the
> target cluster, then reconcile through our approved delivery flow. Verify
> `RemoteMCPServer` Accepted/Ready, an actual Agent tool call and an independent
> Azure DevOps repository read. Do not count tool discovery as data access.
>
> For the PAT write trial, use a sandbox repository and reviewed branch/path
> scope. The image exposes the official Microsoft branch create, branch read,
> file read and draft-PR tools plus one bridge `repo_file_push` tool using the
> documented Git Pushes REST API. Its input is one complete UTF-8 file (up to
> 32 KiB), change type add/edit, a commit message and the expected current
> branch head commit ID. The branch must be under the configured prefix; the
> project and repository are fixed by work configuration. Create branch -> read
> branch/file -> push -> read back the
> commit/file -> optional draft PR. Stop on any ambiguous push response and
> inspect the branch before retrying. Do not claim a live code write from offline
> tests; record the work Agent tool trace and independent Azure DevOps readback.

## Image build, then Helm OCI pipeline

The source ZIP contains the Dockerfile, adapter, lockfile, tests and chart. The
Dockerfile runs `npm ci` **at image build time** to install Microsoft's pinned
`@azure-devops/mcp@2.10.0` plus the MCP SDK; it also builds the native `keytar`
module. There is no npm install in the deployed pod. Build and validate the
image first using `WORK-AGENT-BUILD-INSTRUCTIONS.md`, push it to the internal
container image registry, and use its destination manifest digest in private
Helm values. The PAT is needed only at runtime, via a Kubernetes Secret.

The work builder needs approved access to the pinned Node base image, Debian
packages and all npm lockfile URLs, or complete internal mirrors. If those
routes are unavailable, use the optional image tar and report that source
rebuilding remains unproven in work.

The work pipeline supplies the approved OCI chart repository, credentials and
version policy. The chart declares `name: azure-devops-mcp` and `version: 0.2.0`.
If work uses a different chart name/version, edit `Chart.yaml`, then run:

```bash
cd azure-devops-mcp-airgap
helm package chart --destination /absolute/private/work-output
helm push /absolute/private/work-output/azure-devops-mcp-0.2.0.tgz \
  oci://{{INTERNAL_REGISTRY}}/{{CHART_REPOSITORY}}
```

The `helm push` destination omits chart name and version; Helm adds them from
`Chart.yaml`. Login is performed by the existing work job. The chart OCI digest
and runtime image digest are separate values. Do not use a Docker local image ID
as the runtime registry digest.

Copy `work-values.template.yaml` to a private work path and fill each
placeholder. Its intended trial settings are:

```yaml
image:
  ref: "{{INTERNAL_REGISTRY}}/azure-devops-mcp@sha256:{{RUNTIME_MANIFEST_DIGEST}}"
ado:
  organization: "{{ADO_ORGANIZATION}}"
draftPr:
  enabled: true
  project: "{{ADO_PROJECT}}"
  repositoryId: "{{ADO_REPOSITORY_ID}}"
  sourceBranch: "{{SOURCE_BRANCH}}"
  targetBranch: "{{TARGET_BRANCH}}"
codePush:
  enabled: true
  pathPrefix: "{{REVIEWED_PATH_PREFIX}}"
  branchPrefix: "{{REVIEWED_BRANCH_PREFIX}}"
exampleAgent:
  enabled: true
  modelConfig: "{{EXISTING_APPROVED_MODEL_CONFIG}}"
```

Before packaging or installing, render with the concrete private values:

```bash
helm lint chart -f /absolute/private/ado-mcp-values.yaml
helm template azure-devops-mcp chart --namespace '{{NAMESPACE}}' \
  -f /absolute/private/ado-mcp-values.yaml > /absolute/private/work-output/rendered.yaml
```

Existing agents in the same namespace can reference the installed
`RemoteMCPServer` named `azure-devops-scoped`. Grant them only the tool names
needed for this trial: `repo_branch`, `repo_file`, `repo_create_branch`,
`repo_file_push` and optionally `repo_pull_request`/`repo_pull_request_write`.
To install the example Agent, set
`exampleAgent.enabled=true` and `exampleAgent.modelConfig` to an existing
approved ModelConfig. `draftPr.project`, `repositoryId` and `targetBranch`
define the scope. `sourceBranch` is an example branch within the prefix. Code
tools can create, read, push and raise draft PRs for any valid branch beneath
`codePush.branchPrefix`, such as `agent/task-123` beneath `agent/`. Branches are
names without `refs/heads/`. Set `codePush.pathPrefix` to a reviewed absolute path,
such as `/src/` or `/` for an approved whole-repository sandbox trial. The
chart defaults to read-only; the work values explicitly enable writes.

For the first Agent-mediated trial, use a new branch under the reviewed prefix
and one small text file inside the approved path. A copyable task is:

> In project `{{ADO_PROJECT}}`, repository `{{ADO_REPOSITORY_ID}}`, start from
> `{{TARGET_BRANCH}}`. Check whether `{{NEW_BRANCH_UNDER_PREFIX}}` exists. If
> absent, create it with `repo_create_branch`. Read its head with `repo_branch`
> and read `{{FILE_PATH}}` with `repo_file` using versionType `Branch`. Make the
> requested small text edit and call `repo_file_push` once with that branch name,
> complete new content, `changeType=edit` (or `add` for a new file), a short
> commit message and the exact head commit ID as `expectedOldObjectId`. Read the
> branch and file back. If the push response is unclear, inspect the branch
> before retrying. Then, if enabled, check for an existing PR and create one
> draft PR to `{{TARGET_BRANCH}}`. Report the commit ID, file path, branch and
> PR ID, and distinguish tool output from independently checked Azure DevOps
> state.

The PAT Secret defaults to `azure-devops-mcp-pat` with key
`PERSONAL_ACCESS_TOKEN`; the bridge key Secret defaults to
`azure-devops-mcp-bridge-key` with key `key`. The bridge key must be at least 32
characters. The PAT value follows the pinned upstream's base64 `email:PAT`
encoding; this is encoding, not encryption. Use the approved secret manager or
the bundle's hidden-input `install-secrets.py` for a controlled trial.
For branch creation, file pushes and the optional PR, use a short-lived PAT with
Code Read & Write (`vso.code_write`) and confirm the identity's repository Read,
Contribute, Create branch and Contribute to pull requests permissions. A PAT
scope cannot override a repository deny or branch policy. The added push uses
HTTPS to `dev.azure.com` through Node's `fetch`; verify the work proxy and CA
route for that client separately from the upstream Microsoft SDK client.

The push request shape follows Microsoft's Git Pushes API:
https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pushes/create?view=azure-devops-rest-7.1

If an ingress NetworkPolicy is wanted, set `networkPolicy.enabled=true` and
provide `networkPolicy.ingressFrom` with **actual** namespace and pod selectors
for the work Agent/controller. The chart fails rendering if policy is enabled
without peers. Existing egress, proxy, CA and image-pull rules need separate
workplace review. Azure DevOps Services HTTPS reachability is required; a
completely disconnected cluster needs an approved connected tool zone. This
version does not target Azure DevOps Server/TFS.

## Acceptance evidence

1. `helm lint` and `helm template` pass using private concrete values; the
   rendered image is the destination image digest and contains no Secret data.
2. The work pipeline records the Helm OCI chart reference and digest. Its chart
   pull and render match the submitted source.
3. The runtime image build/push (or fallback import/push) records a separate
   destination image digest;
   offline tests, native keytar and target architecture pass.
4. Target CRD schema/server-side dry-run passes before reconciliation. After
   reconciliation, bridge health, RemoteMCPServer Ready and an Agent-mediated
   Azure DevOps data read pass.
5. The PAT trial creates the configured source branch, reads a real file,
   pushes one bounded change with optimistic branch-head matching, then reads
   back the new commit and file independently. A failure identifies whether
   authentication (401), permissions/policy (403), missing target (404), or
   branch conflict (409/412) is involved when Azure DevOps returns that status.
6. For the optional draft PR, verify the exact sandbox repository, branch pair,
   `draft=true`, expected diff and no autocomplete/reviewers independently.

The public lab created a real draft PR. The code-push adapter has offline tests
against the pinned Microsoft tool catalog and a mocked Azure DevOps Pushes API;
workplace installation and live code edits remain to be proven by the PAT trial.

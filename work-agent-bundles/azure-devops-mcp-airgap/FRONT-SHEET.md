# Azure DevOps MCP code-workflow handoff

This release gives the work agent Microsoft's pinned Azure DevOps MCP npm
package, our scoped HTTP bridge and code-push adapter, a Helm chart, and a
complete Linux amd64 image. The intended trial is branch → read → one bounded
file push → independent readback → optional draft PR in a sandbox repository.

## Download these four files

Release page:
https://github.com/davidmarkgardiner/kagent-work-bundles/releases/tag/azure-devops-mcp-code-workflow-v1

| File | Use |
| --- | --- |
| [Source ZIP](https://github.com/davidmarkgardiner/kagent-work-bundles/releases/download/azure-devops-mcp-code-workflow-v1/azure-devops-mcp-code-workflow-2026-10-08.zip) | Bridge, tests, Dockerfiles, chart source, and work instructions. |
| [Image archive](https://github.com/davidmarkgardiner/kagent-work-bundles/releases/download/azure-devops-mcp-code-workflow-v1/azure-devops-mcp-code-images-2026-10-08.tar) | Complete runtime image and optional dependencies base for an offline bridge rebuild. |
| [Helm chart package](https://github.com/davidmarkgardiner/kagent-work-bundles/releases/download/azure-devops-mcp-code-workflow-v1/azure-devops-mcp-0.2.0.tgz) | Preview of the chart that the work pipeline should package and push to Helm OCI. |
| [SHA-256 checksums](https://github.com/davidmarkgardiner/kagent-work-bundles/releases/download/azure-devops-mcp-code-workflow-v1/SHA256SUMS-ado-mcp-code-2026-10-08) | Verify all three files before intake. |

Source review:
https://github.com/davidmarkgardiner/kagent-public/tree/feat/azure-devops-mcp-code-workflow/work-agent-bundles/azure-devops-mcp-airgap

The image archive is our build product, not a Microsoft-published container
image. It includes `azure-devops-mcp:2.10.0-code1` and
`azure-devops-mcp-dependencies:2.10.0-poc1`. The complete runtime already has
the bridge. The dependencies image supports a rebuild using
`Dockerfile.offline` if the reviewed bridge source needs a change. A connected
work builder can instead use the normal Dockerfile and locked `npm ci` route.

## Copy this prompt to the work agent

> Implement the Azure DevOps MCP code-workflow trial from the four files in
> this release. Start with `FRONT-SHEET.md`, `AGENTS.md`,
> `HELM-OCI-WORK-AGENT.md`, and `WORK-AGENT-BUILD-INSTRUCTIONS.md` in the
> extracted source ZIP. Verify `SHA256SUMS-ado-mcp-code-2026-10-08` before
> importing anything. Preserve existing kagent, gateway, ModelConfig, and
> delivery configuration; keep all work-specific values and receipts private.
>
> First import the complete Linux amd64 `azure-devops-mcp:2.10.0-code1` image
> from the tar into our approved internal container registry. This is already
> the bridge runtime, so deploy it without rebuilding if no source change is
> required. If the bridge must be changed inside the air gap, import the
> matching `azure-devops-mcp-dependencies:2.10.0-poc1` image and build with
> `Dockerfile.offline` from the reviewed source ZIP. Alternatively, use the
> normal Dockerfile and locked npm dependencies only if our builder has
> approved Node, Debian, and npm package routes. Run the offline Node tests,
> `image-smoke.mjs`, and native `keytar` load check before pushing. Record the
> **destination registry manifest digest**, not a local image ID.
>
> Use our existing Helm OCI pipeline to run `helm lint`, `helm template`,
> `helm package chart`, authenticate to our OCI registry, and `helm push` the
> chart. Use private chart values with the destination image digest, approved
> Azure DevOps organization, sandbox project/repository, target branch,
> source-branch prefix, and path prefix. Confirm the installed kagent Agent
> and RemoteMCPServer CRD schemas, server-side dry-run, then install through
> our approved delivery flow. The packaged `.tgz` is a reference artifact;
> the pipeline should produce its own package from the source chart.
>
> Supply the PAT and bridge key through approved Kubernetes Secrets at
> runtime. Do not put them in source, Helm values, build args, image layers,
> artifacts, or logs. Give the trial Agent only `repo_branch`, `repo_file`,
> `repo_create_branch`, `repo_file_push`, and optional draft-PR tools. Verify
> RemoteMCPServer Ready and one actual Agent-mediated Azure DevOps read.
>
> In a reviewed sandbox repository, create a branch under the configured
> prefix from the target branch, read its current head and one allowed file,
> make one small UTF-8 add/edit with `repo_file_push` using the exact expected
> head commit ID, then independently read back the branch, commit, and file.
> If enabled, create one draft PR to the target branch and verify it remains
> draft. If a push response is ambiguous, inspect Azure DevOps state before
> retrying. Report the chart OCI reference/digest, runtime image digest, test
> results, kagent tool trace, Azure DevOps readback, commit ID, and optional PR
> ID. Identify any missing package route, CRD mismatch, PAT permission, branch
> policy, or Azure DevOps egress as a specific blocker. Do not treat tool
> discovery or offline tests as proof of a live code write.

The chart and image are separate OCI artifacts. Azure DevOps Services still
needs an approved HTTPS route from the deployed bridge or a connected tool zone.
The local package and chart checks passed; work-side installation and code push
remain the acceptance trial.

# Flux GitOps delivery from OCI

This is an alternative delivery path for the existing Azure DevOps MCP bundle.
It uses two different registry objects:

1. The **complete runtime container image**, imported from the v2 release and
   pushed to an approved internal OCI registry. No Docker rebuild is required.
2. A **Flux OCI artifact containing Kubernetes manifests**. Flux
   `OCIRepository` retrieves that artifact and `Kustomization` reconciles it.

The current GitHub release `.tar` is a Docker transfer archive, not a registry
reference or Flux source. The runtime image digest and manifest-artifact digest
are different values. Use the registry's digest for each after its push; neither
is the SHA-256 of the transfer `.tar`.

This flow assumes Flux source-controller and kustomize-controller already run in
the target cluster. The full artifact also requires the installed kagent CRDs,
controller, and approved ModelConfig. Keep the rendered artifact and values in
a private work directory. No PAT, bridge key, registry password, or actual
Secret object belongs in either OCI artifact or GitOps commit.

## 1. Import and publish the runtime image

Download `azure-devops-mcp-images.tar` and `SHA256SUMS` from the
[v2 release](https://github.com/davidmarkgardiner/kagent-work-bundles/releases/tag/azure-devops-mcp-airgap-v2).
Verify the image archive against the image line in `SHA256SUMS`, then load it.
The archive also contains the optional dependencies image, which does not need
to be pushed for deployment.

```sh
docker load -i azure-devops-mcp-images.tar
docker tag azure-devops-mcp:2.10.0-poc1 \
  '{{INTERNAL_REGISTRY}}/azure-devops-mcp:2.10.0-work-reviewed'
docker push '{{INTERNAL_REGISTRY}}/azure-devops-mcp:2.10.0-work-reviewed'
```

Record the **registry manifest digest** returned by the push. Scan and approve
the image through the work intake process, then use
`{{INTERNAL_REGISTRY}}/azure-devops-mcp@sha256:{{IMAGE_DIGEST}}` in private
configuration. The local `poc1` tag and local Docker image ID are not deployment
proof or a trusted production version. The v2 archive contains only a
`linux/amd64` runtime image; confirm the target nodes support that architecture
before import. An ARM64 target needs a separately built and reviewed image.

## 2. Render a secret-free, read-only artifact

Create a private copy of `config.example.json` with the target namespace,
internal image digest, organization, project, repository, branch names and
existing ModelConfig. Values may identify the workplace, so keep the file and
rendered directory outside this public repository.

```sh
python3 oci/prepare.py \
  --config /absolute/private/work-values.json \
  --output /absolute/private/azure-devops-mcp-manifests
kubectl kustomize /absolute/private/azure-devops-mcp-manifests
```

The default omits the draft-PR tool. Once the PAT scope and selected branch
pair are reviewed, `--allow-draft-pr` renders the already defined, exact-scoped
write path. The `--runtime-only` option removes the kagent CRs for an isolated
container/Flux lab; it is not the workplace configuration.

Before publishing, check the rendered image digest, objects, namespace, ingress
selectors and installed kagent schema. Use server-side dry-run against the
selected cluster when possible. The existing Agent and Gateway resources must
remain unchanged unless the work integration deliberately targets them.

## 3. Push the manifest artifact and pin Flux to its digest

Run on a host with the Flux CLI and approved registry credentials:

```sh
flux push artifact \
  'oci://{{INTERNAL_REGISTRY}}/manifests/azure-devops-mcp:2.10.0-work1' \
  --path=/absolute/private/azure-devops-mcp-manifests \
  --source='{{APPROVED_SOURCE_URL}}' \
  --revision='{{REVIEWED_SOURCE_REVISION}}'
```

Record the registry manifest digest of this **manifest artifact**. Render the
Flux source and Kustomization into a private file:

```sh
python3 oci/render-flux-source.py \
  --url 'oci://{{INTERNAL_REGISTRY}}/manifests/azure-devops-mcp' \
  --digest 'sha256:{{MANIFEST_ARTIFACT_DIGEST}}' \
  --target-namespace '{{NAMESPACE}}' \
  --output /absolute/private/azure-devops-mcp-flux.json
```

Review that file and place it under the **existing work GitOps repository's**
Flux-reconciled path, adding it to that path's `kustomization.yaml` when the
repository uses an explicit resource list. The existing GitRepository and its
parent Flux Kustomization must reconcile this commit. The file creates an
`OCIRepository` and child `Kustomization` in
`flux-system`, pinned to the artifact digest; `prune` starts as `false` to avoid
deleting existing resources on an initial adoption. Do not use
`--insecure-lab-registry` for work; that flag is only for an isolated local HTTP
registry test. If the work registry needs authentication, use the existing
Flux `OCIRepository.spec.secretRef` or approved provider identity and the
Kubernetes image-pull mechanism separately. They serve different consumers.

## 4. Verify the reconciliation and application

Check `OCIRepository` and `Kustomization` Ready conditions, their resolved
revision/digest, the exact managed objects, Deployment Ready status, service
health, direct MCP discovery, kagent Agent readiness and one read-only A2A
question. Only then enable the reviewed draft-PR path and verify the Azure
DevOps PR independently. A Ready Flux source proves manifest delivery, not PAT
permissions, Azure DevOps network access or the agent's answer quality.

The local kind test for this path is recorded in
[`evidence/flux-oci-lab-2026-10-07.json`](evidence/flux-oci-lab-2026-10-07.json).

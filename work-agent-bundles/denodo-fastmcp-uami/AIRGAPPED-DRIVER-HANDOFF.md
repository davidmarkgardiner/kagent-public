# Denodo JDBC driver in an air-gapped MCP image

The MCP Pod needs `denodo-vdp-jdbcdriver.jar` at
`/opt/denodo/denodo-vdp-jdbcdriver.jar`. It does not need a Denodo Platform
installation on the Kubernetes nodes. The public base image deliberately does
not contain this vendor JAR.

## Obtain the JAR privately

1. Ask the DVP owner for the server major version and installed update. Denodo
   documents **Design Studio → File → About → VDP server** as one way to check.
2. Obtain the JDBC driver for that version/update from the authenticated Denodo
   Community driver page or the organization's existing Denodo installation.
   The usual installed location is
   `<DENODO_HOME>/tools/client-drivers/jdbc/denodo-vdp-jdbcdriver.jar`;
   some versioned layouts have a `vdp-jdbcdriver-core/` subdirectory.
3. Prefer the driver shipped with that DVP update. Do not assume a newer driver
   works with an older server. Denodo documents an 8.0↔9 compatibility
   exception, but confirm the exact supported pairing for the installed DVP.
4. Record the driver version and SHA-256 in the private artifact record, and
   transfer it through the organization's approved vendor-artifact process.
   Do not commit the JAR or an internal download URL to this public repository.

Official sources:

- https://community.denodo.com/drivers/jdbc/
- https://community.denodo.com/docs/html/browse/9.1/en/vdp/developer/access_through_jdbc/access_through_jdbc

## Preferred air-gap path: import a complete image

Build the base FastMCP image and then the derived image from
`deploy/Dockerfile.with-driver` in an approved build environment that can reach
its package mirrors. The private derived build context contains the approved
`denodo-vdp-jdbcdriver.jar` and nothing from the work database. Build for the
actual AKS node architecture (often `linux/amd64`); the M4 home-lab image was
built for `linux/arm64` and is not the work artifact. Scan/sign the derived
image and record its digest.

The public base `adapter/Dockerfile` installs Java from Debian and Python
packages from PyPI. It cannot build unmodified on an isolated builder with no
approved package mirrors. The finished derived image already contains Python,
Java, the MCP adapter, and the JDBC driver, so the running Pod does not need
internet access or a package download.

With both build stages on one approved builder (or the base image published to
an approved registry), the build shape is:

```sh
docker build --platform linux/amd64 -t {{APPROVED_BASE_IMAGE_TAG}} adapter
docker build --platform linux/amd64 \
  --build-arg BASE_IMAGE={{APPROVED_BASE_IMAGE_TAG}} \
  -f deploy/Dockerfile.with-driver \
  -t {{APPROVED_IMAGE_TAG}} {{PRIVATE_DRIVER_BUILD_CONTEXT}}
```

`{{PRIVATE_DRIVER_BUILD_CONTEXT}}` contains the renamed
`denodo-vdp-jdbcdriver.jar`. Use the platform of the actual AKS nodes.

For an environment with an internal registry, mirror/push the approved
complete image there and set `DENODO_FASTMCP_IMAGE` to its **internal digest**
in the private values file. For a physically separated network, transfer an
approved image archive and its checksum, then import and push it into that
network's registry. Example commands run in the approved transfer process:

```sh
# Connected build side, after the private image has been scanned and approved.
docker image save -o denodo-fastmcp-linux-amd64.tar {{APPROVED_IMAGE_TAG}}
sha256sum denodo-fastmcp-linux-amd64.tar > denodo-fastmcp-linux-amd64.tar.sha256

# Isolated import side, after approved transfer of both files.
sha256sum -c denodo-fastmcp-linux-amd64.tar.sha256
docker image load -i denodo-fastmcp-linux-amd64.tar
docker tag {{APPROVED_IMAGE_TAG}} {{INTERNAL_REGISTRY_IMAGE_TAG}}
docker push {{INTERNAL_REGISTRY_IMAGE_TAG}}
```

Record the digest returned by the internal registry and use that digest in the
Deployment. Configure its normal image-pull authentication if required. If
policy requires building *inside* the air gap, first mirror the pinned Python
base image, Debian packages, pinned Python wheels, and the Denodo JAR into
approved internal sources and point the build to them. A JDBC JAR alone is not
enough for the base Dockerfile's `apt-get` and `pip install` steps.

Do not use a Kubernetes Secret or ConfigMap to carry the JAR: Denodo's listed
driver downloads are many megabytes, while each Kubernetes Secret/ConfigMap
has a 1 MiB limit. The private image is the intended delivery artifact.

Before routing kagent, run `python /app/verify_live.py` in one authorized
canary Pod. The remaining proof is the real UAMI token audience, TLS trust,
JDBC login, approved view, Gateway path, and A2A call.

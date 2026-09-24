# Offline bundle: everything needed to build the runsc image in an air-gapped environment

The gVisor `runsc` binary is 129 MB, which is above GitHub's 100 MB file
limit, so it cannot live in this folder. It is published as a **release
asset** instead:

**https://github.com/davidmarkgardiner/kagent-public/releases/tag/runsc-asset-20260622**

Download `substrate-runsc-offline-amd64.zip` on a connected machine, carry it
in, and build there. The zip contains the binary plus everything in this
folder.

| File | In the zip | Purpose |
|---|---|---|
| `runsc` | yes | the pinned binary, amd64, release line 20260622 |
| `SHA256SUMS` | yes | `f18a948b…`, must match the cluster `SandboxConfig` |
| `Dockerfile.runsc` | yes | copies the binary in; downloads nothing at build time |
| `build.sh` | yes | verify, build for `linux/amd64`, print next steps |
| `preseed-daemonset.yaml` | yes | copies the binary onto each Substrate node |
| `README.txt` | yes | the four steps, offline |
| `make-bundle.sh` | no | regenerates the zip from upstream on a connected machine |

## In the air-gapped environment

```sh
unzip substrate-runsc-offline-amd64.zip
cd substrate-runsc-offline-amd64
./build.sh <registry>/gvisor/runsc:20260622 <registry>/library/busybox:1.36
docker push <registry>/gvisor/runsc:20260622
```

`build.sh` refuses to continue if the digest does not match. The only things
that touch a network are the base image pull and the push, both against your
own registry.

Then fill the three placeholders in `preseed-daemonset.yaml` and apply it —
[`../PACKAGE-AND-PRESEED.md`](../PACKAGE-AND-PRESEED.md) has the detail and the
troubleshooting table.

## Don't want to depend on the release?

`make-bundle.sh` rebuilds the identical zip from the upstream release on any
connected machine, verifying the digest as it goes. Run it for `aarch64` if a
node pool needs arm64.

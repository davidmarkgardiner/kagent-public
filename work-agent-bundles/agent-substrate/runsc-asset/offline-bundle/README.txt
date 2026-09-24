Substrate gVisor runsc offline bundle (amd64, release line 20260622)
===================================================================

Everything needed to build the runsc pre-seed image inside an air-gapped
environment. Nothing in here reaches the internet except the base image pull
and your registry push.

Contents
  runsc                    the pinned gVisor binary (129 MB, amd64)
  SHA256SUMS               its digest; must match the cluster SandboxConfig
  Dockerfile.runsc         copies the binary into a minimal image
  build.sh                 verify -> build -> show next steps
  preseed-daemonset.yaml   copies the binary onto each Substrate node

Use
  1. Check the digest against your cluster:
       kubectl get sandboxconfig gvisor-default -o jsonpath='{.spec.assets.amd64.runsc}'
     It must equal the value in SHA256SUMS. If it differs, this bundle is for
     the wrong release line; do not use it.

  2. Build and push:
       ./build.sh myregistry.azurecr.io/gvisor/runsc:20260622 myregistry.azurecr.io/library/busybox:1.36
       docker push myregistry.azurecr.io/gvisor/runsc:20260622

  3. Fill in preseed-daemonset.yaml. Three placeholders:
       {{INTERNAL_REGISTRY}}  appears TWICE (runsc image, pause image)
       {{RUNSC_SHA256}}       f18a948bf9c8bbb54eb998549a3a8d719a1c7de2efbe8fdd2ff0ee5fecd06f19
     Then: grep -n '{{' preseed-daemonset.yaml   # must print nothing

  4. Apply and verify:
       kubectl apply -f preseed-daemonset.yaml
       kubectl -n ate-system logs -l app=runsc-preseed -c seed
     Expect: seeded /host/static-files/runsc-f18a948b...

Why this exists
  atelet fetches runsc from gs://gvisor by default. With the binary already at
  /var/lib/ateom-gvisor/static-files/runsc-<sha256> on the node, it uses the
  cache and never touches that URL. Proven: an actor booted with the asset URL
  deliberately pointed at an unreachable bucket.

Full procedure, troubleshooting and the arm64 digest:
  work-agent-bundles/agent-substrate/runsc-asset/PACKAGE-AND-PRESEED.md

gVisor is licensed under Apache 2.0 (https://github.com/google/gvisor).
This bundle redistributes an unmodified upstream release binary.

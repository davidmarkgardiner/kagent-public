# Agent Substrate `runsc` in network-isolated Kubernetes

## Question for the Kubernetes and Agent Substrate teams

> Is there a roadmap item for Agent Substrate to obtain its pinned gVisor
> `runsc` binary from an internal source without first trying public Google
> Storage, or to bundle the binary, so network-isolated AKS and GCP clusters
> do not need to pre-seed every worker node?

## Context

Our kagent `SandboxAgent` evaluation pairs kagent `0.10.1` with Agent
Substrate `0.0.9`. The Substrate chart sets `SandboxConfig/gvisor-default` to
fetch `runsc` from the public `gs://gvisor` bucket. The `ateom-gvisor` worker
image does not include the binary. Substrate's asset fetcher also tries
anonymous Google Storage before its configured object store.

We tested an offline workaround: an internal image carries the pinned binary,
and a DaemonSet copies it into `atelet`'s cache on every eligible node before
an actor starts. A cache hit skips the public download. The workaround adds a
node setup step that must cover replacement nodes as well.

See the [runsc asset guide](runsc-asset/README.md) for the tested workaround
and the [air-gapped AKS runbook](AIRGAPPED-AKS-README.md) for the deployment
context.

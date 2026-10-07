# Question for Microsoft: Agent Substrate sandbox backend on Azure Linux AKS

Copy the text below into the discussion with the Microsoft AKS team.

> We are evaluating kagent **0.10.1** with Agent Substrate **0.0.9** on an
> **AMD64 Azure Linux AKS** node pool. The compatible pairing we have tested
> locally uses Substrate's **gVisor** backend, which fetches the pinned
> `runsc` binary separately from the worker image. We need that runtime asset
> supplied from internal storage in a restricted network.
>
> AKS also offers Kata pod sandboxing through `kata-vm-isolation`. We understand
> that selecting that Kubernetes RuntimeClass does not, by itself, switch a
> Substrate actor to Substrate's microVM backend.
>
> **Which backend do you recommend for this AKS evaluation: Substrate gVisor
> with `runsc`, or Substrate microVM with Cloud Hypervisor/Kata?** If microVM is
> the recommendation, which exact **kagent and Substrate versions**, Azure
> Linux/AKS node and VM sizes, device interface (`/dev/kvm` or `/dev/mshv`),
> worker configuration, and **Data/Full snapshot modes** have been validated
> together? Is there a supported integration with AKS managed pod sandboxing,
> or must Substrate launch and manage its own guests?
>
> For either backend, what is the supported **no-public-egress** procedure for
> supplying all runtime assets from an internal registry or object store and
> verifying actor creation, suspend, restore, and state retention? In
> particular, does the recommended release avoid Substrate 0.0.9's attempt to
> fetch the gVisor `runsc` asset from public Google Storage before trying the
> configured object store?

The current public evaluation plan uses Substrate **gVisor** on Azure Linux.
The microVM path needs a confirmed compatible controller/runtime combination
and AKS device support before it can replace that plan.

# Pod Sandboxing for kagent — Should we use it?

> **TL;DR:** Skip it for controller/UI pods. Consider it for the `kagent-tool-server`
> if your threat model includes container escape via prompt injection.
> Strongly recommended for BYO MCP servers, custom-code agents, or any future
> code-interpreter / arbitrary-execution tool. RBAC and policy tightening give
> more security per dollar than Kata for the typical kagent attack path.

Reference: [AKS Pod Sandboxing (Kata Containers)](https://learn.microsoft.com/en-us/azure/aks/use-pod-sandboxing)

---

## What Pod Sandboxing actually is

AKS Pod Sandboxing runs a pod inside a lightweight Hyper-V microVM with its own
guest kernel, using the Kata Containers runtime (`runtimeClassName:
kata-vm-isolation`). The host kernel never executes the workload's syscalls — the
guest kernel does.

This is a **hardware-virtualisation boundary**, not a namespace/cgroup boundary.

Current AKS requirements:

- Kubernetes 1.27 or newer
- Azure Linux node pool
- Gen2 VM size that supports nested virtualization
- `--workload-runtime KataVmIsolation` on the sandboxed node pool

---

## What you get over a hardened pod on normal nodes

A "hardened pod" here means Pod Security Standard `restricted` + seccomp
`RuntimeDefault` + AppArmor + non-root + read-only rootfs + dropped capabilities.

| Threat | Hardened pod | Kata pod |
|---|---|---|
| Misconfigured capability / privileged container | Blocked by policy if configured | Contained inside the guest VM if allowed |
| Known syscall exploit filtered by seccomp | Blocked | Blocked |
| **Unknown kernel CVE / runc escape (e.g. Leaky Vessels)** | Vulnerable | Isolated |
| **Cross-tenant side channel via shared kernel** | Vulnerable | Mostly isolated |
| Noisy-neighbor kernel resource exhaustion | Shared | Bounded by VM |
| Container runtime zero-day | Vulnerable | Less exposed to `runc`-class escapes |

The single line that matters: **a separate kernel per pod**. Hardening blocks
known techniques; Kata removes an entire attack surface.

---

## What you pay

- ~100-300 MB extra memory floor per pod for the guest kernel and agent
- Slower cold start, typically hundreds of milliseconds
- No host networking
- Avoid `hostPath` because it can weaken the isolation boundary
- Microsoft Defender for Containers does not assess Kata runtime pods
- AKS-only: Azure Linux node pool with `--workload-runtime KataVmIsolation`
- Linux only
- Operational complexity: extra `RuntimeClass`, node selector / taint plumbing
- Dev/prod divergence if your local cluster does not support Kata
- Resource sizing matters: set CPU and memory requests/limits deliberately
  because the pod VM size and Kata overhead are derived from those values

---

## Decision matrix for kagent components

| Component | Recommendation | Reason |
|---|---|---|
| `kagent-controller` | **No** | Trusted infra, calls LLM APIs, no untrusted exec |
| `kagent-ui` | **No** | HTTP frontend, no shell exec |
| `kagent-tool-server` | **Maybe** | Runs `kubectl`, `helm`, `istioctl` driven by LLM output — worth Kata if you cannot tightly bound its RBAC |
| Trusted read-only Agent pods | **No** | Trusted agent runtime; isolation should be RBAC, tool grants, and NetworkPolicy |
| BYO / write-capable / custom-code Agent pods | **Maybe / Yes** | Use Kata when tenants supply images, skills, or tools with broad execution paths |
| MCP servers exposing shell / code exec | **Yes** | This is the textbook Kata use case |
| Future code-interpreter / Python-REPL tool | **Yes** | Untrusted code in pod = exactly what Kata is for |

---

## Why this matters less than people think for an LLM agent

The realistic attack on a kagent deployment is **not** container escape. It is:

> Prompt injection convinces the agent to run a destructive `kubectl` it
> already has RBAC for.

Kata does not help with that. The LLM does not need to escape the container —
it can just use the permissions the container already has. Defences that
actually move the needle here:

1. **Least-privilege RBAC** per agent CRD (read-only vs write split is already
   modelled in this repo's agent conventions — see `AGENTS.md`).
2. **Kyverno / OPA policy** restricting which verbs and resources tool-server
   can touch, regardless of what the LLM asks for.
3. **NetworkPolicy** locking down egress so a compromised tool-server cannot
   exfiltrate or pivot.
4. **Audit logging + anomaly detection** on the tool-server's kubectl calls.
5. **HITL approval** on destructive verbs (delete, scale-to-zero, secret read).

Kata is a useful **fifth or sixth line** of defence. It is rarely the first
thing missing.

---

## When Kata becomes the right answer

Turn it on for BYO MCP quarantine servers, and consider it for `kagent-tool-server`,
when **any** of these are true:

- You are exposing kagent as a multi-tenant SaaS where different customers'
  agents share a cluster.
- You allow tenant-supplied MCP servers, custom agent images, or skill images
  before they are fully trusted.
- You introduce a tool that executes LLM-generated code, shell commands not
  on an allow-list, or arbitrary scripts.
- Regulatory requirement (PCI, HIPAA, FedRAMP High) demands hardware-level
  workload isolation.
- Your threat model explicitly includes a state-level adversary with kernel
  zero-days.

If none of those apply: invest the same effort in RBAC, Kyverno, NetworkPolicy,
and HITL gates first. Revisit Kata when one of them becomes true.

---

## If you do enable it — minimum viable rollout

1. Create an AKS node pool with Kata enabled:

   ```bash
   az aks nodepool add \
     --cluster-name <aks> \
     --resource-group <rg> \
     --name katapool \
     --os-sku AzureLinux \
     --workload-runtime KataVmIsolation \
     --node-vm-size Standard_D4s_v5
   ```

2. Reference the runtime class on the deployment you want isolated:

   ```yaml
   spec:
     template:
       spec:
         runtimeClassName: kata-vm-isolation
   ```

   If you taint or label the Kata node pool, add the verified selector and
   toleration for your cluster. Do not copy an unverified Azure node label into
   GitOps manifests.

3. Scope the rollout: **start with BYO MCP quarantine servers or `kagent-tool-server`
   only.** Measure cold start, memory, and request latency before widening.

4. For kagent `Agent` CRs, verify the installed kagent CRD before adding runtime
   fields. If the CRD does not expose `runtimeClassName`, use a controller-supported
   deployment override or a tested Kyverno mutation, and confirm the kagent
   controller does not revert it.

5. Size the pod explicitly:

   ```yaml
   resources:
     requests:
       cpu: 250m
       memory: 512Mi
     limits:
       cpu: "1"
       memory: 1Gi
   ```

6. Verify the boundary actually exists — run `uname -r` inside the pod and
   compare to the node kernel. Different = working.

---

## Verdict

For trusted single-tenant, read-only kagent agents, Pod Sandboxing is
**defence-in-depth, not a gap-closer**. Worth piloting for BYO MCP quarantine
servers, custom-code/write-capable agents, or `kagent-tool-server` if you can
spare the memory/latency budget; otherwise spend that effort on policy and RBAC
first.

Revisit this decision the moment kagent grows a code-execution tool or
multi-tenant exposure.

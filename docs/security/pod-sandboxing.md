# Pod Sandboxing for kagent — Should we use it?

> **TL;DR:** Skip it for controller/UI pods. Consider it for the `kagent-tool-server`
> if your threat model includes container escape via prompt injection.
> Strongly recommended if you ever add a code-interpreter / arbitrary-execution tool.
> RBAC and policy tightening give more security per dollar than Kata for the typical
> kagent attack path.

Reference: [AKS Pod Sandboxing (Kata Containers)](https://learn.microsoft.com/en-us/azure/aks/use-pod-sandboxing)

---

## What Pod Sandboxing actually is

AKS Pod Sandboxing runs a pod inside a lightweight Hyper-V microVM with its own
guest kernel, using the Kata Containers runtime (`RuntimeClass: kata-mshv-vm-isolation`).
The host kernel never executes the workload's syscalls — the guest kernel does.

This is a **hardware-virtualisation boundary**, not a namespace/cgroup boundary.

---

## What you get over a hardened pod on normal nodes

A "hardened pod" here means Pod Security Standard `restricted` + seccomp
`RuntimeDefault` + AppArmor + non-root + read-only rootfs + dropped capabilities.

| Threat | Hardened pod | Kata pod |
|---|---|---|
| Misconfigured capability / privileged container | Blocked | Blocked |
| Known syscall exploit filtered by seccomp | Blocked | Blocked |
| **Unknown kernel CVE / runc escape (e.g. Leaky Vessels)** | Vulnerable | Isolated |
| **Cross-tenant side channel via shared kernel** | Vulnerable | Mostly isolated |
| Noisy-neighbor kernel resource exhaustion | Shared | Bounded by VM |
| Container runtime (containerd/runc) zero-day | Vulnerable | Out of path |

The single line that matters: **a separate kernel per pod**. Hardening blocks known
techniques; Kata removes an entire attack surface.

---

## What you pay

- ~100–300 MB extra memory floor per pod (guest kernel + agent)
- Slower cold start (hundreds of ms)
- No host networking, restricted volume types, awkward GPU passthrough
- AKS-only — Mariner / AzureLinux node pool with `--workload-runtime KataMshvVmIsolation`
- Linux only
- Operational complexity: extra `RuntimeClass`, node selector / taint plumbing
- Dev/prod divergence if your local cluster (kind, k3s, homelab) doesn't support Kata

---

## Decision matrix for kagent components

| Component | Recommendation | Reason |
|---|---|---|
| `kagent-controller` | **No** | Trusted infra, calls LLM APIs, no untrusted exec |
| `kagent-ui` | **No** | HTTP frontend, no shell exec |
| `kagent-tool-server` | **Maybe** | Runs `kubectl`, `helm`, `istioctl` driven by LLM output — worth Kata if you cannot tightly bound its RBAC |
| Agent pods (per-CRD) | **No** | Trusted agent runtime; isolation should be RBAC |
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
3. **NetworkPolicy** locking down egress so a compromised tool-server can't
   exfiltrate or pivot.
4. **Audit logging + anomaly detection** on the tool-server's kubectl calls.
5. **HITL approval** on destructive verbs (delete, scale-to-zero, secret read).

Kata is a useful **fifth or sixth line** of defence. It is rarely the first
thing missing.

---

## When Kata becomes the right answer

Turn it on (at least for tool-server) when **any** of these are true:

- You are exposing kagent as a multi-tenant SaaS where different customers'
  agents share a cluster.
- You introduce a tool that executes LLM-generated code, shell commands not
  on an allow-list, or arbitrary scripts.
- Regulatory requirement (PCI, HIPAA, FedRAMP High) demands hardware-level
  workload isolation.
- Your threat model explicitly includes a state-level adversary with kernel
  zero-days.

If none of those apply: invest the same effort in RBAC, Kyverno, and HITL
gates first. Revisit Kata when one of them becomes true.

---

## If you do enable it — minimum viable rollout

1. Create an AKS node pool with Kata enabled:

   ```bash
   az aks nodepool add \
     --cluster-name <aks> \
     --resource-group <rg> \
     --name katapool \
     --os-sku AzureLinux \
     --workload-runtime KataMshvVmIsolation \
     --node-vm-size Standard_D4s_v5
   ```

2. Reference the runtime class on the deployment you want isolated:

   ```yaml
   spec:
     template:
       spec:
         runtimeClassName: kata-mshv-vm-isolation
         nodeSelector:
           kubernetes.azure.com/kata-mshv-vm-isolation: "true"
   ```

3. Scope the rollout: **start with `kagent-tool-server` only.** Measure cold
   start, memory, and request latency before widening.

4. Verify the boundary actually exists — run `uname -r` inside the pod and
   compare to the node kernel. Different = working.

---

## Verdict

For this repo's current shape (trusted single-tenant agents, RBAC-scoped tool
server, no in-pod code execution), Pod Sandboxing is **defence-in-depth, not a
gap-closer**. Worth piloting on `kagent-tool-server` only if you can spare the
memory/latency budget; otherwise spend that effort on policy and RBAC first.

Revisit this decision the moment kagent grows a code-execution tool or
multi-tenant exposure.

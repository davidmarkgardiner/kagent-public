# Agent Substrate — Word Handover Summary

## Decision in one sentence

Agent Substrate is a promising **non-production platform evaluation** for a large fleet of idle, bursty agents; the retained lift-and-shift profile proves **Go ADK**, not the newer Python/BYO paths, and is not a production migration for the evidence-first triage runtime.

## What it adds

| Capability | Value |
|---|---|
| Suspend/resume actors | Idle agents snapshot to object storage and release worker RAM/CPU. |
| gVisor actor isolation | Stronger execution boundary for agent code and tools than a plain container. |
| Worker-pool multiplexing | Many intermittent agents can share a small worker pool. |
| Stateful idle sessions | Scratch filesystem and in-memory actor state restore after suspension. |

## What it does not replace

| Existing platform responsibility | Remains owned by |
|---|---|
| Workflow branching, retries, approvals and durable process state | Argo Workflows and kagent orchestration. |
| System access | MCP tools, scoped service accounts and GitOps workflow permissions. |
| LLM inference | Approved internal model route or AI gateway. |
| Paging and incident evidence | LGTM/Alertmanager and the separate Alloy -> Vector -> Kafka -> Argo triage path. |

## Evidence already captured

The retained proofs cover both the original install path and the later
version-bound A2A path:

- An isolated kind proof captured boot, gVisor checkpoint and suspension to object storage.
- A real existing kagent cluster proof installed the substrate runtime additively and created a SandboxAgent declaratively. On kagent 0.9.10 it also proved that the normal controller A2A route did not reach a SandboxAgent.
- The later kagent `0.10.0-beta7` / Substrate `0.0.8` Home Lab run invoked three no-tool SandboxAgents through the sandbox A2A route and proved resume, response, snapshot and suspend.
- A disposable Kubernetes 1.32.2 canary then proved the latest stable kagent `0.10.1` / Substrate `0.0.9` pair, secure ate-api CA trust, all three specialist CRs, and three golden snapshots. It used no model credential, so the provider-backed A2A smoke remains a target-cluster acceptance check.

These prove the runtime lifecycle, not production readiness.

## Critical gates before an AKS evaluation

1. A dedicated non-production, tainted node pool with checkpoint/restore compatibility.
2. Scoped Kyverno/admission and Pod Security approval for required privileged gVisor workloads.
3. Exact AKS service-account issuer and an approved ate-api CA mounted into the kagent controller; do not disable TLS verification.
4. Air-gapped chart and image mirror by digest, including the Go ADK runtime image that is injected at runtime.
5. Internal object/snapshot storage, encryption, retention and model-route approval.
6. A verified version-specific sandbox A2A path; do not reuse the normal Agent route or assume an untested release behaves the same.
7. A controlled proof of Ready -> request -> suspend -> restore with state intact.
8. An explicit rollback and a decision owner for the privileged-runtime risk.

## Recommended first evaluation

Use one disposable Go ADK SandboxAgent on the dedicated node pool. Measure:

- actor ready/restore latency;
- worker memory while idle and during a burst;
- actor-to-worker density;
- image pull, checkpoint/restore and model-route failures;
- policy, network and operational overhead compared with a plain Deployment.

Do not migrate a production triage or remediation agent until the invocation path, kernel behavior, cost model and support model are accepted.

## Next handoff

Use AIRGAPPED-AKS-README.md for the GitOps/air-gap sequence, the copy-ready GitLab issue for ownership and acceptance criteria, and verify-aks-substrate.sh for read-only operational verification.

# AKS Agent Substrate promotion

This is the lift-and-shift path for the fifth listener. It keeps platform ownership of `SandboxAgent`, `ActorTemplate`, `WorkerPool`, and Substrate infrastructure while application teams continue to own only their ordinary Agents, prompts, skills, and MCP workloads.

## Target contract

- kagent `0.10.1`
- Agent Substrate `0.0.9`, the version selected by that kagent release
- agentgateway `v1.5.0`
- one kagent controller owning each SandboxAgent
- immutable internal-mirror images matching `platform/substrate/images.lock.tsv`
- a dedicated Entra A2A audience and `platform-substrate.a2a.invoke` app role

The chart, runtime, worker, and pause-image digests are in `platform/substrate/target-platform.env` and `platform/versions.lock`. Upstream releases are https://github.com/kagent-dev/kagent/releases/tag/v0.10.1, https://github.com/kagent-dev/substrate/releases/tag/v0.0.9, and https://github.com/agentgateway/agentgateway/releases/tag/v1.5.0.

## Promotion order

1. Run `scripts/verify-substrate-target.sh`, then `scripts/verify-substrate-images.sh`. Mirror every image in `platform/substrate/images.lock.tsv`, verify the resolved digest, and enforce immutable tags.
2. Prove the chosen AKS node pool supports the Substrate 0.0.9 gVisor design. The chart renders a privileged atelet and a containerd hostPath; stop if the cluster's admission, node OS, runtime, or security baseline rejects that design.
3. Install or upgrade Substrate CRDs and the Substrate release to `0.0.9` with reviewed values derived from `platform/substrate/substrate-values.work.example.yaml`. Replace the service-account issuer and every registry placeholder.
4. Upgrade the single owning kagent controller to `0.10.1` with values derived from `platform/substrate/kagent-values.work.example.yaml`. Supply the approved CA, external database, ModelConfig, node selection, and exact WorkerPool image digest. Do not leave the old all-namespaces owner running against the same SandboxAgents.
5. Wait for the WorkerPool to reach desired replicas, then apply `platform/substrate/security-review-sandboxagent.yaml`. Require Accepted and Ready, exactly one owned ActorTemplate, and a non-empty golden snapshot.
6. Apply the fifth Gateway listener, exact HTTPRoute, ReferenceGrant, and strict policy produced by `scripts/render.py`. Replace the red policy with `profiles/aks-entra/substrate-a2a-policy.yaml` after substituting approved Entra values.
7. Add target-cluster NetworkPolicies that allow the Gateway data-plane identity to reach only the owning kagent controller port. Deny application and rogue namespaces from direct controller access. Preserve whatever Substrate control-plane and WorkerPool flows its reviewed deployment requires.
8. Run the target equivalent of S01, S03-S05, P04, and N20-N23 from `TEST-MATRIX.md`. Also prove Entra key rotation, wrong-role denial, token expiry, external TLS, logging redaction, snapshot retention, deletion, and recovery.

## Stop conditions

Stop if two controllers can reconcile the same SandboxAgent, a second ActorTemplate appears, the golden snapshot is absent, runtime or worker digests differ from the lock, a direct non-Gateway controller path works, the Entra policy accepts a token without the platform role, or a completed task lacks a successful suspend/snapshot witness.

The red receipt is behavioral evidence for the historical kagent `0.10.0-beta7` plus Substrate `0.0.8` lane. The 2026-09-15 canary is version and credential-free readiness evidence for the target `0.10.1` plus `0.0.9` lane. Neither substitutes for the AKS promotion gates above.

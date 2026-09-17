# Work agent prompt: fresh kagent platform cluster

Use this repository as the source of truth. Build a new disposable cluster and
install the pinned kagent, agentgateway and Agent Substrate platform described
in:

`work-agent-bundles/kagent-agentgateway-tenant-isolation/profiles/fresh-cluster/README.md`

Rules:

1. Read root `AGENTS.md`, the fresh-cluster README, `platform/versions.lock`,
   `platform/substrate/images.lock.tsv`, `ARCHITECTURE.md`, and `TEST-MATRIX.md`
   before acting.
2. Confirm the selected kube context is the newly created disposable cluster.
   Stop if it contains existing kagent, agentgateway, Gateway API or Substrate
   CRDs/releases; do not turn this into an in-place upgrade.
3. Use Kubernetes `1.32.2` for the kind rehearsal. For AKS, query the currently
   supported non-preview versions and record the selected exact patch; it must
   satisfy the tested minimum minor `1.31`.
4. Use exactly Gateway API `v1.6.2` experimental, agentgateway `v1.5.0`,
   kagent `0.10.1`, and Substrate `0.0.9`. Verify every OCI chart digest against
   `platform/versions.lock` before installation. Do not use `latest`.
5. Treat platform agentgateway `v1.5.0` and Substrate's internally pinned
   `v1.3.0-alpha.1` data-plane image as different components. Do not replace
   one with the other.
6. Preserve the two non-overlapping kagent owners:
   `tenant-kagent` watches only `tenant-kagent-system,team-event,team-chat`;
   `kagent` watches only `kagent` and owns SandboxAgents/WorkerPool. Stop if the
   watch sets overlap.
7. Apply the explicit controller and proxy resources/security contexts in this
   profile. Keep Gateway service type `ClusterIP` and the UI disabled. Do not
   add public ingress during the lab run.
8. Never put API keys, bearer tokens, tenant IDs, subscriptions, hostnames or
   private addresses in Git, Helm values, command arguments, logs or evidence.
   Use `{{PLACEHOLDER}}` in committed material and create runtime Secrets through
   the approved secret-delivery mechanism.
9. Substrate deliberately needs privileged atelet/hostPath access. Permit that
   only in the disposable lab namespaces. For AKS, stop until the dedicated
   node pool, policy exception, image mirror, OIDC issuer, CA, external database
   and snapshot-retention decisions have written approval.
10. Do not claim completion from Helm status or Ready conditions. Capture:
    chart digests, rendered manifests, server-side dry-run, CRD Established,
    rollout status, exact images, security contexts, resources, controller
    watch namespaces, Gateway/Route/Policy conditions, WorkerPool readiness,
    one ActorTemplate with golden snapshot, a real provider-backed A2A call,
    and the negative authentication/authorization/direct-path tests.
11. Run `scripts/public-safe-scan.sh` on the scoped bundle before proposing any
    commit. Do not push, merge, deploy to a shared/work cluster, or create cloud
    resources without David's explicit authorization.

Work in gated phases: create cluster; record baseline; install Gateway API;
install/verify CRDs; install/verify controllers; deliver provider Secret and
ModelConfig; apply platform routes/policies; deploy ordinary Agents; deploy the
SandboxAgent; run positive and negative tests; produce a sanitized evidence
receipt. Stop at the first failed gate and report the exact failing layer.

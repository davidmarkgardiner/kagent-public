# MIL-385 Plan — bounded cross-cluster Kubernetes MCP proof

## Scope

Build one self-contained, public-safe proof bundle at
`platform/kubernetes-mcp-server/homelab-cross-cluster`.  The bundle will prove
that a `containers/kubernetes-mcp-server` workload running in the
`kind-homelab` host cluster can make purpose-issued, short-lived Kubernetes
ServiceAccount `TokenRequest` calls to both the host and `proxmox-k8s` target
clusters.  It will expose the two targets to the deterministic client only as
the public-safe aliases `red-homelab` and `proxmox-homelab`.

The proof is strictly read-only.  It will deploy temporary POC resources,
exercise them, collect bounded and sanitized evidence, then remove all POC
resources and ephemeral credential material.  It neither changes application
workloads nor provides a production deployment path.

## Assumptions and preconditions

- The live operator explicitly supplies `HOST_CONTEXT=kind-homelab` and
  `TARGET_CONTEXT=proxmox-k8s`; those context names are input-only and never
  appear in retained evidence.  Evidence and client-visible output use only
  `red-homelab` and `proxmox-homelab`.
- Both contexts are already configured locally and the operator has only the
  minimum authority necessary to create the temporary POC namespace, service
  accounts, RBAC objects, and bound TokenRequests.  The scripts fail closed if
  either context, required API, identity, or cleanup invariant is unavailable.
- Target API reachability is available from the temporary host-cluster MCP pod.
  No private endpoint, certificate, credential, kubeconfig, prompt, request
  body, raw tool result, or cluster address is committed or retained.
- A pinned public image reference and public placeholders will be used; no
  live token or environmental value belongs in a manifest or receipt.
- The POC uses an isolated namespace and a dedicated ServiceAccount per target
  purpose.  It preserves the UID of `default/kubectl-mcp` and validates that
  UID after teardown.

## File-level implementation plan

1. Add `README.md` with the security boundary, prerequisites, placeholder
   inventory, operator invocation, validation command, expected bounded
   evidence, cleanup behavior, and explicit non-production limitations.  It
   will state that no deployed endpoint is externally exposed and that live
   inputs are never persisted.
2. Add sanitized manifests under `manifests/` for the isolated namespace,
   dedicated ServiceAccounts, namespace-scoped read-only RBAC, MCP Deployment,
   ClusterIP Service, and restrictive NetworkPolicy.  The Deployment will set
   `automountServiceAccountToken: false`, a restricted non-root security
   context, read-only root filesystem, dropped capabilities, and explicit CPU
   and memory requests/limits.  The Service will have no ingress, LoadBalancer,
   or NodePort configuration.
3. Add a server configuration and allowlist that enables only the POC's
   read-only inspection tools.  It will remove `configuration_view` and every
   exec, token, RBAC, Secret, and resource-write surface.  Denied-resource
   filters will complement, not replace, the deliberately absent RBAC grants.
4. Add shared shell helpers plus `preflight.sh` to validate required commands,
   contexts, server-side TokenRequest support, distinct host/target identities,
   safe namespace state, expected host/target node cardinality, and absence of
   unsafe exposure.  A failed check must stop before any credential or workload
   action.
5. Add purpose-bound credential and scoped-kubeconfig helpers that request
   short-lived tokens at runtime only, write them into a temporary directory
   with restrictive permissions, construct a minimal two-context kubeconfig
   using alias-only context names, mount it only for the running POC, and
   guarantee deletion via traps and teardown.  The helpers will never echo
   token, certificate, server URL, or kubeconfig data.
6. Add a deterministic MCP client that discovers the advertised tools and
   rejects any tool outside the explicit read-only allowlist.  It will send at
   least 20 alternating alias-addressed requests, assert that `red-homelab`
   resolves exactly one node and `proxmox-homelab` exactly three nodes, and
   fail on an alias crossover.  Its retained output will be counts, aliases,
   tool names, request sequence, and pass/fail status only.
7. Add RBAC/isolation verification that proves required read permissions and
   proves denials for Secrets, RBAC objects, TokenRequests, `pods/exec`, and
   all writes.  It will also check that the advertised MCP surface omits
   configuration and mutation tools independently from API authorization.
8. Add `live-poc.sh` to sequence preflight, temporary credential/Secret
   handling, temporary workload deployment, readiness, deterministic client
   checks, bounded evidence generation, and unconditional teardown.  Add
   `teardown.sh` to remove only resources labeled for this POC, delete temporary
   files, and verify the preserved `default/kubectl-mcp` UID.
9. Add `verify.sh` as the offline/static gate for file structure, placeholder
   safety, manifest posture, tool/RBAC allow- and deny-lists, script guards,
   evidence bounds, and teardown assertions.  It must not contact a cluster or
   require sensitive inputs.
10. Add only sanitized, bounded sample evidence and fixture data needed for
    deterministic verification.  Fixtures will model one and three nodes using
    the two approved aliases and will contain no raw API responses.

## Acceptance mapping

| Acceptance criterion | Planned proof |
| --- | --- |
| Self-contained, public-safe bundle | README, manifests, scripts, fixtures, and `verify.sh` live under the dedicated bundle directory; static verification rejects unsafe values. |
| Purpose-issued short-lived cross-cluster credentials | Runtime-only TokenRequest helpers create scoped, alias-only kubeconfig/Secret inputs and cleanup removes them. |
| Native multi-context read-only routing | Deterministic client alternates at least 20 requests, asserts 1/3 node counts, and fails on any context crossover. |
| Read-only and least privilege | Explicit server tool allowlist plus disabled configuration/write/exec tools, denied resources, namespace RBAC, and negative authorization tests. |
| Host workload hardening and private endpoint | ClusterIP-only Service; no ingress; token automount disabled; restricted security context, read-only filesystem, and resources in Deployment. |
| Bounded evidence and cleanup | Alias/count/status-only receipts; redaction checks; traps and explicit teardown validate no ephemeral material remains and preserve the default ServiceAccount UID. |
| Deterministic validation | The exact command below runs static verification, then the live orchestrator with named input contexts. |

## Exact validation command

```sh
bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/verify.sh && HOST_CONTEXT=kind-homelab TARGET_CONTEXT=proxmox-k8s bash platform/kubernetes-mcp-server/homelab-cross-cluster/scripts/live-poc.sh
```

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Context drift, missing capability, or insufficient operator access | Fail-closed preflight occurs before temporary resources or TokenRequests are created. |
| Credential disclosure | Runtime-only files use restrictive permissions, scripts suppress sensitive output, bounded evidence is allowlisted, and traps/teardown delete temporary files. |
| Alias/cross-cluster confusion | The client owns the two permitted aliases, alternates requests deterministically, and validates expected 1/3 node cardinality for every route. |
| Tool discovery is mistaken for authorization | Tests separately inspect tool exposure and use `kubectl auth can-i`/negative API probes against the scoped identities. |
| Teardown misses a resource | All POC resources have a unique label; teardown lists only that selector and verifies empty results plus unchanged default ServiceAccount UID. |
| Upstream configuration differs from assumptions | Pin and document the selected server version; static verification checks rendered arguments, and preflight/runtime readiness checks fail closed. |

## Explicit non-goals

- No production, shared, internet-facing, Ingress, NodePort, or LoadBalancer deployment.
- No Azure ARM, AKS-MCP, kubelogin, Entra/UAMI, wallet, payment, release, or delivery action.
- No persistent credential, Secret value, kubeconfig, certificate, endpoint, private hostname,
  raw prompt, raw MCP payload, raw log, or raw Kubernetes API response in Git or evidence.
- No mutation of application resources, cluster RBAC outside the isolated POC scope, or
  modification of the existing `default/kubectl-mcp` ServiceAccount.

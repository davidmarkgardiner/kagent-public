## Design review: cluster-health A2A trust boundary

The overall shape (short-lived audience-bound token → route-level JWT policy → fixed rewrite → least-privilege deputy RBAC → RBAC as authoritative boundary → live negative tests) is sound. The defects below are in the gaps between those controls.

### A. Authentication bypass

1. **In-cluster bypass of the gateway (critical).** The AgentgatewayPolicy only sees traffic that traverses the route. Any pod can call the kagent Service directly (ClusterIP/DNS) with no JWT. Control 4 constrains the *workflow's* egress, not kagent's ingress. **Repair:** ingress NetworkPolicy in the kagent namespace allowing only agentgateway pods (plus controller); disable any Gateway/HTTPRoute/Service the kagent chart exposes by default; assert no other HTTPRoute references the Service.
2. **JWT forwarded upstream.** Envoy-based JWT filters forward the validated token to the backend by default — kagent (and its logs) receives a live 1h SA JWT, replayable anywhere it's accepted. **Repair:** `forward: false` / strip `Authorization` after validation; keep claims in metadata only.
3. **No gateway-level default deny.** Route-level policy means any future route/listener on that Gateway inherits nothing. **Repair:** baseline deny-all policy at Gateway/listener scope, or admission-time check that every route to kagent carries the policy.

### B. Confused-deputy paths

4. **Workflow-side namespace validation is self-attestation.** Anyone who can create Workflows in `argo-events` (or reference another template) can skip the validation step. **Repair:** pin to one immutable WorkflowTemplate; restrict Workflow creation to the sensor SA. Fine as defense-in-depth since RBAC stays authoritative — don't let it become the *assumed* boundary in docs/tests.
5. **Prompt injection from cluster contents** (logs/events are attacker-writable strings) steers `call_kubectl`. RBAC bounds it only if the node ClusterRole is exactly `nodes: get/list/watch`. **`nodes/proxy` must be explicitly excluded** — kubelet API access is cluster-admin equivalent (exec into any pod on any node). Also exclude `nodes/log`, `nodes/metrics`, and all nonResourceURLs.
6. **AKS-MCP Azure-plane bypass (critical).** AKS-MCP also talks to ARM. An identity with `Microsoft.ContainerService/managedClusters/listClusterUserCredential/action` returns the admin kubeconfig — the entire read-only RBAC story is void. **Repair:** deny that action (and cluster-config reads) on the ARM identity or strip Azure-facing tools; negative-test it.
7. **`call_kubectl` argument surface.** Arbitrary args allow `exec`, `port-forward`, `--context` pivots, `-f` with manifests. **Repair:** server-side allowlist in the MCP tool config (verbs/subcommands), single in-cluster context, refuse `-f`/`exec`/`port-forward`/`proxy`.
8. **Events must stay namespaced.** Adding `events` to the node ClusterRoleBinding "for convenience" grants all-namespace events — amplification. Keep events in the per-namespace RoleBinding.

### C. RBAC amplification

9. **"Read-only ClusterRole" must be custom-minimal** (`pods`, `pods/log`, `events`, workload kinds: get/list/watch only). Default `view`/aggregates grant ConfigMaps (Secrets on older versions) and grow across Kubernetes releases. No `create` on pod subresources (`pods/exec`, `pods/portforward`, `pods/attach`, `pods/eviction`) — exec into a pod reads its projected SA token, violating the token-read requirement.
10. **RoleBinding creation is itself privileged.** The AKS-MCP SA and the generator/GitOps identity must be disjoint; scope the generator to monitored namespaces only.
11. **Chart residue.** A helm upgrade can silently re-enable the broad default ClusterRoleBinding. Assert its absence in CI and in the negative-test suite.

### D. JWT validation mistakes

12. **Issuer/topology ambiguity.** Projected tokens are signed by the cluster that mounts them. If Argo and agentgateway are both in the management cluster, fine; if Argo runs in a spoke, validation against management JWKS fails closed — and the tempting "fix" (point JWKS at the spoke) lets a same-named spoke SA satisfy the `sub` check. **Repair:** state the topology; pin `remoteJWKS` to the issuing apiserver's `/openid/v1/jwks`; verify `iss`, `aud`, `exp`, `nbf`; confirm `--service-account-issuer`/`--service-account-jwks-uri` are published and reachable from agentgateway.
13. **Sub-allow-list enforcement is version-sensitive (they asked).** agentgateway/kgateway JWT stages originally validated iss/aud only; claims-based ALLOW (`authorization` CEL on `sub`) and field shapes (`remoteJWKS.uri` vs `remote.url`, `claimToHeaders` vs `extractTo`, `AgentgatewayPolicy` vs `SecurityPolicy`) moved across CRD versions. On an older version the design silently degrades to "any SA token with the right audience". **Repair:** pin the CRD/agentgateway version, schema-assert the policy in CI, and include the different-SA-same-audience negative test — that test is the only thing that catches the degradation.
14. **Audience-only token breaks the pod itself.** A pod projecting only the custom-audience token can't authenticate to kube-apiserver. Project both tokens or only hand the custom one to the A2A client. Clients must re-read the rotating token file per request — cached tokens cause 401 storms mid-investigation at the 1h boundary.

### E. Namespace drift and path handling

15. **Drift direction that violates the boundary:** inventory drops a namespace, ConfigMap updates, RoleBinding lingers → a prompt-injected query still succeeds against the stale namespace. **Repair:** generate ConfigMap + RoleBindings from one source in one atomic apply; nightly reconciler diffs inventory ↔ RoleBindings ↔ ConfigMap and deletes orphans; alert; negative-test a recently de-listed namespace.
16. **Prefix-rewrite traversal.** `ReplacePrefixMatch` appends the unmatched suffix: `/a2a/cluster-health/../<other>` (or `%2e%2e`) can arrive at `/api/a2a/kagent/<other-agent>` if anything normalizes — the "caller cannot choose agent/ns" control is path-parsing-dependent (and normalization behavior differs across Gateway API implementations/versions). **Repair:** Exact path match on the single POST endpoint, or anchored regex rejecting dot segments; negative-test traversal payloads.

### F. Operability / public-safety

- Allow agentgateway egress to the apiserver for JWKS; monitor apiserver signing-key rotation vs cached JWKS.
- Scrub Kubernetes 4xx bodies (RBAC denials leak namespace/object names) before they reach the agent's report — public-safe requirement.
- Negative-test matrix (live, pre-promotion, as code): no JWT; wrong audience; expired token; different SA with valid audience; GET on the route; path traversal; direct-to-kagent Service; cross-namespace get; Secrets/ConfigMaps/SA-token reads; any create/patch/delete; `nodes/proxy`; ARM `listClusterUserCredential`; stale-namespace query. Any 200/404-that-should-be-403 blocks promotion.

None of these are unfixable, but the two criticals (in-cluster gateway bypass, ARM credential path) plus the silent-degradation JWT risk mean the design as written does not yet enforce its own stated outcome.

ARCH_STATUS: REVISE

# Authenticated front-door architecture review disposition

The independent GLM-5.3 review returned `REVISE`. Every finding was assessed
before final verification.

| Finding | Disposition |
|---|---|
| Direct gateway bypass | Accepted. Kagent controller ingress is gateway-only, Workflow egress no longer allows kagent, and the live gate rejects additional HTTPRoutes to the controller. Existing additive NetworkPolicies still require live inventory. |
| Caller credential forwarded upstream | Accepted. The HTTPRoute removes `Authorization` after gateway validation; live inspection remains required. |
| Gateway-wide default deny | Rejected for this shared Gateway because it would change unrelated routes. The fixed route has Strict JWT auth; admission/route inventory is a platform prerequisite. |
| Workflow validation bypass | Accepted. The Sensor now uses a dedicated ServiceAccount limited to Workflow create/get. RBAC, not the validation step, remains authoritative. |
| Node subresource/prompt injection risk | Accepted. Node RBAC names only `nodes`; live gates deny `nodes/proxy`, pod exec and port-forward. |
| Azure credential retrieval bypass | Accepted. `call_az` was removed and the runbook makes both AKS credential actions a promotion-blocking negative test. |
| Arbitrary kubectl arguments/context pivot | Accepted for the single-cluster lane. AKS-MCP must use only its in-cluster ServiceAccount context; Kubernetes RBAC denies write subresources. No fleet kubeconfig is permitted. |
| Events accidentally cluster-wide | Accepted. Events exist only in the namespaced role. |
| Growing/default Kubernetes roles | Accepted. The bundle uses custom explicit roles and the verifier rejects sensitive resources and mutating verbs. |
| RBAC generator privilege | Accepted as an operational prerequisite: GitOps owns the generated bindings and must not use the MCP ServiceAccount. |
| Residual broad chart bindings | Accepted. The running-state verifier requires exactly the generated namespace set and exactly one narrow node ClusterRoleBinding. |
| Issuer/topology ambiguity | Accepted. The default explicitly uses a token issued by the management cluster where Argo runs; split-cluster identity mapping is a separate porting step. |
| Version-sensitive JWT/CEL schema | Accepted. Preflight checks both CRD paths, server dry-run is mandatory, and live wrong-audience/wrong-subject tests fail promotion. |
| Custom-audience token lifecycle | Accepted. It is an additional projected volume, not a default API token, and curl reads the rotating file on each call. |
| Namespace removal leaves stale access | Accepted. ConfigMap and RoleBindings derive from one source; offline parity and live exact-set comparisons detect stale bindings. GitOps prune is required. |
| Prefix rewrite traversal | Accepted. The route now uses an Exact path and ReplaceFullPath. Traversal/GET tests remain live promotion gates. |

No architecture-review finding was silently deferred. Runtime claims remain
blocked until the target cluster supplies server dry-run, 401/403, network,
RBAC, Azure-role and end-to-end receipts.

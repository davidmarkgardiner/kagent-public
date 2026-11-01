# Final-review disposition: authenticated front door

The first independent final review returned `REVIEW_STATUS: REVISE`. Every
finding was dispositioned before the single permitted repair review.

1. Accepted. The review bundle omitted untracked files. They are now marked
   intent-to-add before producing the complete base-ref diff.
2. Accepted. NetworkPolicy uses numeric target-port sentinels; Service port,
   target port, and AKS-MCP port are separate values and live-checked.
3. Accepted. The generated investigator runtime permits ingress only from the
   kagent controller.
4. Accepted. Controller ingress permits agentgateway and the one investigator
   runtime callback. The verifier compares exact peers structurally.
5. Accepted. The verifier now compares the one route, match, backend, rewrite,
   credential removal, parent, JWT provider, subject expression, policy target,
   and ReferenceGrant exactly.
6. Accepted. Offline RBAC checks use exact rule and subject allowlists for
   namespaced and node reads and reject non-resource or resource-name rules.
7. Accepted as a documented platform gate. The Sensor has a separate identity;
   the residual pod, Workflow, and TokenRequest authority risk is explicit and
   must be inventoried before promotion.
8. Accepted. Live verification now includes a correct-token positive control,
   wrong token cases, method/path negatives, policy inventory, all-namespace
   RBAC checks, and Service target-port validation. Cross-issuer testing is not
   applicable to the current single-cluster topology and becomes mandatory if
   the topology is split.
9. Accepted. Operational security files were removed from the allowlist and
   credential headers are constructed without a literal scanned form. Only the
   immutable external-review evidence file is exempt because it quotes a
   synthetic example and is not deployable.
10. Accepted. All operator docs now stop a split-cluster deployment pending a
    separately authenticated worker-side MCP design.
11. Accepted. A dedicated MCP NetworkPolicy permits only investigator ingress,
    DNS, and the worker API. The test plan requires rejection of context and
    credential override flags.
12. Accepted. The projected token is group-readable by the non-root Workflow,
    checked with `test -r`, and passed to curl through standard input rather
    than an argument.
13. Accepted. The live verifier checks the Sensor can create Workflows but
    cannot create Pods; the end-to-end trigger remains a required target-cluster
    gate.
14. Accepted. Values now use the dedicated ServiceAccount, separate JWKS URI,
    clarified Kubernetes audience, and exact payload MCP-target validation.

No target cluster was available in this repair pass. Server dry-run, live CRD
schema validation, network reachability, agent invocation, and effective
authorization remain mandatory pre-deployment gates and are not claimed here.

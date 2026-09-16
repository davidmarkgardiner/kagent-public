# Repair-review disposition

The single permitted post-repair review returned `REVIEW_STATUS: REVISE` with
one High and eight Medium findings. The independent result is retained
unchanged. The merge request is not approval to deploy or merge.

- H1 accepted and fixed. Every value now rejects control characters, quotes,
  escapes and excessive length; issuer/JWKS, audience, cluster ID and MCP
  target have full-match allowlists. The jq comparison receives cluster and
  target through `--arg`. Three malicious-value regression cases must fail.
- M1 accepted and fixed offline. Controller ingress now selects only the pod
  labelled for the configured Gateway, plus the one investigator callback.
- M2 accepted and fixed offline. The route is pinned to a configured internal
  listener and in-cluster hostname. Live listener exposure remains a required
  target-cluster check.
- M3 accepted. The uncertain local route rate limit was removed; replay and
  daily admission controls remain in Argo/Kafka. Rate limiting can be restored
  only after evaluation order is proven on the installed agentgateway version.
- M4 accepted and fixed offline. MCP ingress includes the controller for tool
  discovery and the one investigator runtime; controller selectors now include
  the kagent name label. Additive policies remain a live inventory gate.
- M5 accepted and fixed. Full RoleBinding/ClusterRoleBinding roleRefs are
  checked, aggregation is rejected, and the dedicated MCP ServiceAccount may
  appear only in the expected namespace bindings plus one node binding.
- M6 accepted and fixed in the live gate. Every namespace is tested for denied
  Secret/ConfigMap reads and pod/token mutations; cluster RBAC and proxy
  denials are explicit.
- M7 accepted and documented. Promotion inventory now covers port-forward,
  proxy, exec, pod creation and security-object writers in all four namespaces.
- M8 accepted and fixed. README, test plan, quickstart, work-agent prompt and
  both live scripts stop split-cluster use; scripts compare cluster UIDs.
- Low token-argv finding accepted and fixed by streaming headers to curl.
- Low strict-validation finding accepted and fixed with
  `--validate=strict` server dry-runs.
- Low evidence exemption finding accepted and fixed by SHA-256 pinning the
  immutable review files in the public-safety verifier.
- Hard-coded kagent ports and generated labels are deferred to the required
  installed-version live gate; the manifests must not be deployed if the live
  Service/container contract differs.

After these repairs the full deterministic suite passed again. Target cluster
schema, labels, ports, route attachment, policy additivity, JWT flow, MCP
discovery and network enforcement remain explicitly unproven until the
workplace pre-deployment gates run.

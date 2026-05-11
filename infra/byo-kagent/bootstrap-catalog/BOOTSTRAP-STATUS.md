# Bootstrap Catalog Status Patches

These are the one-time `kubectl patch` commands to set `status.verifiedTools` on the
bootstrap ToolCatalogEntry CRs. This is the **only** permitted instance of hand-written
status — all future catalog entries go through the `mcp-onboarding-template` workflow.

Run after applying the CRD and the bootstrap catalog entries.

## aks-mcp-v0-0-12

```bash
kubectl patch toolcatalogentry aks-mcp-v0-0-12 \
  --type=merge --subresource=status \
  -p '{
    "status": {
      "verifiedAt": "2026-05-07T00:00:00Z",
      "verifiedBy": "platform-team",
      "toolCount": 8,
      "verifiedTools": [
        {"name": "k8s_get_resources",       "verbClassification": "read",    "dangerous": false},
        {"name": "k8s_describe_resource",   "verbClassification": "read",    "dangerous": false},
        {"name": "k8s_get_pod_logs",        "verbClassification": "read",    "dangerous": false},
        {"name": "k8s_get_events",          "verbClassification": "read",    "dangerous": false},
        {"name": "k8s_check_service_connectivity", "verbClassification": "network", "dangerous": false},
        {"name": "az_aks_get_credentials",  "verbClassification": "read",    "dangerous": false},
        {"name": "az_aks_list_clusters",    "verbClassification": "read",    "dangerous": false},
        {"name": "az_workload_identity_check", "verbClassification": "read", "dangerous": false}
      ],
      "conditions": [
        {"type": "Verified", "status": "True", "reason": "BootstrapVerified", "message": "Manually verified by platform team"}
      ]
    }
  }'
```

## kagent-tool-server-v1

```bash
kubectl patch toolcatalogentry kagent-tool-server-v1 \
  --type=merge --subresource=status \
  -p '{
    "status": {
      "verifiedAt": "2026-05-07T00:00:00Z",
      "verifiedBy": "platform-team",
      "toolCount": 4,
      "verifiedTools": [
        {"name": "k8s_get_resources",     "verbClassification": "read", "dangerous": false},
        {"name": "k8s_describe_resource", "verbClassification": "read", "dangerous": false},
        {"name": "k8s_get_pod_logs",      "verbClassification": "read", "dangerous": false},
        {"name": "k8s_get_events",        "verbClassification": "read", "dangerous": false}
      ],
      "conditions": [
        {"type": "Verified", "status": "True", "reason": "BootstrapVerified", "message": "Built-in kagent tools, verified by platform team"}
      ]
    }
  }'
```

## Orchestrator-internal tools (gitlab-mcp, kagent-introspect-mcp, kyverno-cli-mcp, yaml-lint-mcp)

```bash
for entry in gitlab-mcp-v1 kagent-introspect-mcp-v1 kyverno-cli-mcp-v1 yaml-lint-mcp-v1; do
  kubectl patch toolcatalogentry $entry \
    --type=merge --subresource=status \
    -p "{
      \"status\": {
        \"verifiedAt\": \"2026-05-07T00:00:00Z\",
        \"verifiedBy\": \"platform-team\",
        \"toolCount\": 1,
        \"conditions\": [{\"type\": \"Verified\", \"status\": \"True\", \"reason\": \"BootstrapVerified\", \"message\": \"Orchestrator-internal tool verified by platform team\"}]
      }
    }"
done
```

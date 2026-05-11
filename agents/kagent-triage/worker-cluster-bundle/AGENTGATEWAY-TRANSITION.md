# Transitioning from LiteLLM to agentgateway

## Why

LiteLLM works for homelab PoCs but doesn't fit the production AKS environment:

- **LiteLLM requires API keys** — you manage secrets, rotate them, store them in Key Vault
- **agentgateway supports UAMI natively** — pod authenticates to Azure OpenAI via managed identity, same pattern as every other Azure workload on the cluster. No API keys to manage.

Additionally, agentgateway gives us guardrails, unified A2A/MCP gateway, and OTel observability — all things we'd otherwise have to bolt on separately.

## What Changes

| Layer | LiteLLM (current) | agentgateway (target) |
|-------|-------------------|----------------------|
| **LLM proxy** | LiteLLM Python proxy, port 4000 | agentgateway Rust proxy |
| **Azure auth** | API key in K8s Secret | UAMI or Workload Identity — no keys |
| **Token tracking** | PostgreSQL + `/ui` dashboard | OpenTelemetry → Prometheus/Grafana |
| **Spend controls** | Per-key budget in LiteLLM | Per-route budget in agentgateway config |
| **Guardrails** | None | Regex, OpenAI moderation, custom webhooks |
| **MCP gateway** | N/A — agents reference MCP servers directly | Centralised MCP gateway with auth + federation |
| **A2A gateway** | N/A — kagent handles A2A directly | Centralised A2A routing with auth + discovery |
| **Auth on inbound** | Single master API key | JWT, API keys, OAuth, CEL policy engine |
| **Observability** | LiteLLM Prometheus callback (flaky) | Native OpenTelemetry (metrics, logs, traces) |
| **K8s integration** | Helm chart, manual config | Built-in controller + Gateway API CRDs |

## What Stays the Same

- **kagent agents** — no changes. Agents still reference a `ModelConfig` CRD. We just point the ModelConfig at agentgateway instead of LiteLLM.
- **A2A protocol** — kagent still exposes agents via A2A. agentgateway can optionally sit in front for auth/routing.
- **Argo Workflows** — workflows still call kagent via A2A. No change.
- **PostgreSQL** — still needed for kagent memory (when re-enabled). Not needed for agentgateway (uses OTel instead of DB for metrics).

## Azure Auth Configuration

### UAMI (User-Assigned Managed Identity)

```yaml
# agentgateway backend config
backends:
  - name: azure-openai
    provider: azure.openai
    host: <your-instance>.openai.azure.com
    model: gpt-4o                          # deployment name
    auth:
      azure:
        explicitConfig:
          managedIdentity:
            userAssignedIdentity:
              clientId: "<uami-client-id>"
```

The agentgateway pod needs:
- The UAMI assigned to the pod (via pod identity or workload identity federation)
- `Cognitive Services OpenAI User` role on the Azure OpenAI resource

### Workload Identity (preferred on AKS)

```yaml
backends:
  - name: azure-openai
    provider: azure.openai
    host: <your-instance>.openai.azure.com
    model: gpt-4o
    auth:
      azure:
        explicitConfig:
          workloadIdentity: {}             # uses the pod's federated credential
```

The agentgateway pod needs:
- Service account annotated with `azure.workload.identity/client-id`
- Federated credential linking the K8s SA to the Azure AD app
- Same role assignment as above

### No Auth (system-assigned managed identity)

```yaml
backends:
  - name: azure-openai
    provider: azure.openai
    host: <your-instance>.openai.azure.com
    model: gpt-4o
    auth:
      azure:
        implicit: {}                       # uses VM's system-assigned identity
```

## kagent ModelConfig Change

The only change to kagent is pointing the ModelConfig at agentgateway instead of LiteLLM:

```yaml
# Before (LiteLLM)
apiVersion: kagent.dev/v1alpha2
kind: ModelConfig
metadata:
  name: default-model-config
  namespace: kagent
spec:
  provider: OpenAI
  model: gpt-4o
  apiKeySecret: litellm-key                  # API key needed
  apiKeySecretKey: api-key
  openAI:
    baseUrl: http://litellm-proxy.kagent:4000/v1

---
# After (agentgateway)
apiVersion: kagent.dev/v1alpha2
kind: ModelConfig
metadata:
  name: default-model-config
  namespace: kagent
spec:
  provider: OpenAI
  model: gpt-4o
  apiKeySecret: agentgateway-key             # can be a passthrough token
  apiKeySecretKey: api-key
  openAI:
    baseUrl: http://agentgateway.kagent:8080/v1
```

agentgateway handles Azure auth on the backend — kagent doesn't need to know about UAMI.

## Deployment

### Standalone (quick start)

```bash
# Deploy agentgateway
kubectl apply -f agentgateway-deployment.yaml

# Verify
kubectl port-forward svc/agentgateway 8080:8080
curl http://localhost:8080/healthz
```

### Kubernetes Controller (production)

agentgateway has a built-in K8s controller that uses Gateway API CRDs:

```bash
# Install CRDs
kubectl apply -f agentgateway/manifests/

# Deploy controller
kubectl apply -f agentgateway/controller/
```

See: https://agentgateway.dev/docs/kubernetes/latest

## Migration Steps

### Phase 1: Deploy alongside LiteLLM (parallel)

```bash
# Deploy agentgateway in kagent namespace
kubectl apply -f agentgateway-deployment.yaml -n kagent

# Create a second ModelConfig pointing at agentgateway
kubectl apply -f - <<EOF
apiVersion: kagent.dev/v1alpha2
kind: ModelConfig
metadata:
  name: agentgateway-model-config
  namespace: kagent
spec:
  provider: OpenAI
  model: gpt-4o
  apiKeySecret: agentgateway-key
  apiKeySecretKey: api-key
  openAI:
    baseUrl: http://agentgateway.kagent:8080/v1
EOF

# Test with one agent (e.g. test-ns-agent)
kubectl patch agent test-ns-agent -n kagent --type=merge \
  -p '{"spec":{"declarative":{"modelConfig":"agentgateway-model-config"}}}'

# Verify agent still works
# If good, migrate more agents
```

### Phase 2: Migrate all agents

```bash
# Update all agents to use agentgateway ModelConfig
for agent in $(kubectl get agents -n kagent -o name); do
  kubectl patch $agent -n kagent --type=merge \
    -p '{"spec":{"declarative":{"modelConfig":"agentgateway-model-config"}}}'
done
```

### Phase 3: Remove LiteLLM

```bash
# Only after all agents are confirmed working on agentgateway
kubectl delete deployment litellm-proxy -n kagent
kubectl delete svc litellm-proxy -n kagent
kubectl delete deployment litellm-postgres -n kagent  # keep if needed for kagent memory
kubectl delete modelconfig litellm-model-config -n kagent
```

## Observability After Migration

| What | How |
|------|-----|
| Token usage | OTel metrics → Prometheus → Grafana |
| Request logs | OTel logs → Loki |
| Latency/traces | OTel traces → Tempo (if deployed) |
| Spend tracking | agentgateway budget controls + OTel metrics |
| Guardrails logs | agentgateway logs blocked/flagged requests |

### ServiceMonitor for Prometheus

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: agentgateway
  namespace: kagent
  labels:
    release: kube-prom
spec:
  selector:
    matchLabels:
      app: agentgateway
  endpoints:
    - port: metrics
      path: /metrics
      interval: 30s
```

## Decision Matrix

| Environment | Recommendation | Reason |
|-------------|---------------|--------|
| **Homelab** | Keep LiteLLM | Simple, already running, no Azure auth needed |
| **Work (AKS, non-prod)** | agentgateway | UAMI/workload identity, fits existing auth pattern |
| **Work (AKS, prod)** | agentgateway | UAMI + guardrails + OTel + rate limiting |

## References

- agentgateway docs: https://agentgateway.dev/docs
- agentgateway K8s docs: https://agentgateway.dev/docs/kubernetes/latest
- Azure auth source: `agentgateway/crates/agentgateway/src/http/auth.rs`
- Azure OpenAI provider: `agentgateway/crates/agentgateway/src/llm/azureopenai.rs`
- Config schema: `agentgateway/schema/config.md`

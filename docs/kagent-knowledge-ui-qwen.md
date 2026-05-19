# KAgent Knowledge UI Qwen Gateway Wiring

The `kagent-knowledge-ui` Agent uses the shared Qwen `ModelConfig` defined in
`platform/agentgateway/modelconfig-qwen.yaml`:

```yaml
spec:
  declarative:
    modelConfig: agentgateway-qwen
```

That `ModelConfig` points kagent at the OpenAI-compatible
`agentgateway/qwen/v1/...` request path:

```text
https://{{AGENTGATEWAY_HOSTNAME}}/qwen/v1
```

agentgateway rewrites `/qwen/v1/...` to `/v1/...` before forwarding to the
vLLM-hosted Qwen backend declared in `platform/agentgateway/backend-vllm-qwen.yaml`.
The knowledge UI service still retrieves Markdown chunks locally; any kagent
model response for the knowledge agent goes through `agentgateway-qwen`.

## Local Verification

Render the knowledge-agent manifests and confirm only this agent points at the
Qwen gateway model config:

```bash
kubectl kustomize agents/kagent-knowledge-ui/k8s | rg -n "name: kagent-knowledge-ui|modelConfig: agentgateway-qwen"
```

This repo has deterministic UI smoke tests, but no automated test that can
reach a live agentgateway deployment. Port-forward agentgateway and prove the
Qwen route completes an OpenAI-compatible round trip:

```bash
kubectl -n agentgateway-system port-forward svc/ai-gateway 8080:80
curl -fsS http://127.0.0.1:8080/qwen/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer not-required' \
  -d '{
    "model": "{{VLLM_SERVED_MODEL_NAME}}",
    "messages": [
      {
        "role": "user",
        "content": "Reply with: kagent knowledge qwen gateway ok"
      }
    ],
    "max_tokens": 16
  }'
```

For a deployed knowledge agent, confirm the Agent CR references the same
ModelConfig:

```bash
kubectl -n kagent get agent kagent-knowledge-ui \
  -o jsonpath='{.spec.declarative.modelConfig}{"\n"}'
```

Expected output:

```text
agentgateway-qwen
```

## Rollback

If Qwen or the vLLM backend is unavailable, roll this single agent back to the
previous kagent model config while leaving other agents unchanged:

```bash
kubectl -n kagent patch agent kagent-knowledge-ui --type merge \
  -p '{"spec":{"declarative":{"modelConfig":"default-model-config"}}}'
```

To make the rollback persistent in Git, change
`agents/kagent-knowledge-ui/k8s/kagent-agent.yaml` back to:

```yaml
spec:
  declarative:
    modelConfig: default-model-config
```

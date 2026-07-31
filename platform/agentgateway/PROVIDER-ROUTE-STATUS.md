# Provider route status

This records a live, low-token verification of the direct Agent Gateway routes
used by kagent. Provider credentials remain Kubernetes Secrets and are never
printed in this document or in smoke output.

| Route | ModelConfig | Live result | Status |
| --- | --- | --- | --- |
| `/minimax/v1` | `agentgateway-minimax` → `MiniMax-M3` | Gateway completion reported `model: MiniMax-M3`; the dedicated kagent A2A smoke agent returned `MINIMAX_M3_A2A_OK`. | Working |
| `/zai/v1` | `agentgateway-zai-glm` → `glm-5.2` | Provider model discovery lists `glm-5.2`; Gateway and kagent calls reached Z.ai but returned provider error `1113` (insufficient balance or no resource package). | Configuration valid; provider entitlement blocked |

## Safety and readiness rules

- Do not switch `default-model-config` to either route. Use named profiles and
  dedicated agents until a full task proves successful.
- A kagent Agent is ready only when its Deployment has an available replica and
  its Service has at least one endpoint. The historical `Ready=True` condition
  on zero-replica agents is not sufficient.
- The dedicated smoke agents declare `deployment.replicas: 1` so they cannot
  claim readiness while their A2A Service has no backend.
- MiniMax-M3 may return provider thinking tags in its visible text. Consumers
  must extract the final structured verdict/artifact rather than treating raw
  text as a protocol contract.

## Next provider action

Top up or attach a Z.ai resource package to the existing `zai-api-secret`
account, then rerun the GLM A2A smoke. Do not rotate or print the key merely to
resolve a billing/entitlement response.

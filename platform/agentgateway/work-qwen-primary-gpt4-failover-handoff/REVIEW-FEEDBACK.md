# Review Feedback - Qwen Primary / GPT-4 Secondary Failover Handoff

Reviewed: 2026-06-03. Scope: handoff folder. This is a design/correctness
review, not a live applied test.

## Must Validate In The Work Cluster

1. Confirm retry reaches the fallback priority group.

   The design uses two `AgentgatewayBackend.spec.ai.groups` entries:
   group 0 is Qwen primary and group 1 is GPT-4 secondary. The local upstream
   `../agentgateway` clone has an e2e failover test, but that test depends on
   backend health eviction. The local validation CRD rejected
   `AgentgatewayPolicy.spec.backend.health`, so this bundle uses route retry on
   `429,500,502,503,504`.

   Before production rollout, prove in the installed work version that a
   retryable upstream response advances from group 0 to group 1. If it retries
   only the same primary provider, add version-gated backend health eviction or
   a different failover mechanism.

2. Confirm agentgateway metric names and labels.

   Alerts and dashboard queries assume metrics such as
   `agentgateway_requests_total`, `agentgateway_request_duration_seconds_bucket`,
   and `agentgateway_gen_ai_client_token_usage_*`. Verify the live `/metrics`
   endpoint before applying rules, because labels such as `status`, `route`,
   `backend`, and `model` can vary by build.

3. Confirm `secretRef` auth key shape.

   The token refreshers write provider tokens into Secrets under:

   ```yaml
   stringData:
     Authorization: "Bearer <token>"
   ```

   `schema-gate.sh` prints the installed CRD auth shape. Confirm the runtime
   reads the `Authorization` key as expected before first rollout.

4. Interpret benchmark `429`s carefully.

   `20-agentgateway-failover-route.yaml` sets a local gateway rate limit of
   20 requests per second with burst 60. `bench-agentgateway.sh` prints that
   configured limit when it can read the policy. For an upstream-capacity test,
   temporarily raise or remove the local gateway limit and record that change.

## Fixed During Review

- `smoke-failover.sh --mode mock-429` now removes the provider TLS block when it
  patches the primary to the plaintext mock service, so the mock can return a
  real upstream `429` instead of causing a TLS transport failure.
- `smoke-failover.sh` now restores the full original primary provider object
  and deletes the temporary mock Deployment/Service during cleanup.
- `bench-agentgateway.sh` now prints the configured local rate limit when it can
  read the `AgentgatewayPolicy`.
- `README.md` now points to `00-FRONT-SHEET.md` as the source of truth for full
  run order and includes the Prometheus alert apply step.

## Solid Pieces

- Gateway-level model selection is the right control point: kagent gets one
  stable `ModelConfig`, while retry, fallback, telemetry, and alerting live at
  agentgateway.
- The token refresher shape cleanly supports both auth paths: Qwen service
  principal and GPT-4 UAMI.
- `schema-gate.sh` is the key guardrail. It checks the installed CRDs, prints
  relevant auth/retry fields, and server-dry-runs the Kubernetes manifests that
  can be validated locally.

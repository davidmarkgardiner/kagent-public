# Checkout API CrashLoop Runbook

Chunk: `chunk-1`

This public-safe runbook is the demo corpus for the smart-triage knowledge
specialist. It intentionally uses placeholder service names and contains no
private endpoints or credentials.

## Scope

- Namespace: `demo-payments`
- Workload: `checkout-api`
- Symptom: container restarts after a configuration rollout

## Triage Steps

1. Confirm the alert labels identify `namespace`, `workload`, `pod`, and
   `container`.
2. Compare the deployment revision with the latest GitOps revision.
3. Check recent pod events and logs for missing or malformed environment values.
4. Inspect Grafana restart metrics for blast radius.
5. Hold remediation behind HITL; use GitOps or an approved workflow for any
   fix.

## Recommendation

If the deployment revision changed immediately before restarts began, prepare a
reviewed GitOps MR or approved workflow action. Do not run direct cluster
mutation from a chat agent.

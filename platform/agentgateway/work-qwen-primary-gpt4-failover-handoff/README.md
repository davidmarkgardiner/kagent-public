# Work Qwen Capacity Handoff

Start here: [`80-QWEN-CAPACITY-CONTROL.md`](80-QWEN-CAPACITY-CONTROL.md).

This folder is self-contained for handing to another agent. The current work
recommendation is to measure and control Qwen capacity first, not to duplicate
every kagent agent for model failover.

```text
alerts/events -> kagent A2A API -> Qwen model path -> completed agent response
```

Capacity run order:

```bash
./schema-gate.sh
# Replace all {{PLACEHOLDER}} values before applying anything that touches a cluster.
kubectl apply -f 10-token-refreshers.yaml
kubectl apply -f 20-agentgateway-failover-route.yaml
kubectl apply -f 30-kagent-modelconfig.yaml
kubectl apply -f 40-observability-alerts.yaml
TOTAL=20 CONCURRENCY=20 AGENT_NAME=<agent> ./bench-kagent-a2a.sh
CONCURRENCY_LEVELS="1 2 4 8 12 16 20" REQUESTS_PER_LEVEL=40 AGENT_NAME=<agent> ./capacity-sweep-kagent-a2a.sh
```

Use `81-QWEN-CAPACITY-BENCH-RUNBOOK.md` for the test matrix and
`82-WORKFLOW-RATE-LIMITING-PATTERNS.md` for Argo/Kafka/Alloy controls.
Use `83-HOMELAB-KAGENT-A2A-EVIDENCE.md` as the local evidence note: the harness
ran, but the home-lab `k8s-agent` single-call baseline did not complete, so it
is not a Qwen capacity number.

Use `capacity-sweep-agentgateway.sh` only as a lower-level diagnostic if the
kagent-facing benchmark fails and you need to separate kagent/controller
capacity from gateway/provider capacity.

The older failover manifests remain in this folder as reference material, but
automatic backend failover is not the current recommendation until the work
agentgateway runtime and Qwen TLS-session dependencies are fixed.

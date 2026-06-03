# Work LLM Failover Handoff

Start here: [`00-FRONT-SHEET.md`](00-FRONT-SHEET.md).

This folder is self-contained for handing to another agent. It implements the
target pattern:

```text
kagent -> agentgateway /llm/v1 -> Qwen primary -> GPT-4 secondary
```

Run order:

```bash
./schema-gate.sh
# Replace all {{PLACEHOLDER}} values before applying anything.
kubectl apply -f 10-token-refreshers.yaml
kubectl apply -f 20-agentgateway-failover-route.yaml
kubectl apply -f 30-kagent-modelconfig.yaml
kubectl apply -f 40-observability-alerts.yaml
./smoke-failover.sh --mode bad-host
./smoke-failover.sh --mode mock-429
TOTAL=50 CONCURRENCY=5 ./bench-agentgateway.sh
TOTAL=20 CONCURRENCY=2 AGENT_NAME=<agent> ./bench-kagent-a2a.sh
```

Use `00-FRONT-SHEET.md` as the source of truth for the full implementation order,
including token-refresh job checks and managed-Loki rule-sync validation.

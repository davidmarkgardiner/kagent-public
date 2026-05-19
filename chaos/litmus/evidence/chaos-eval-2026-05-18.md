# Kagent Chaos Eval Report
**Date:** 2026-05-18 21:03 UTC
**Cluster:** homelab Kubernetes validation cluster (private address redacted)
**Judge model:** Qwen2.5:7b via AgentGateway (local, no external tokens)

## Health Score
**0.95** / 1.0  (workflow_stability avg: 0.67)

| Score | Meaning |
|-------|---------|
| >0.9  | Healthy production |
| >0.7  | Usable, monitor |
| <0.5  | Needs attention |

## Scenarios
### pod_restart
- Recovery: **151.5s**
- Stability score: **0.4**
- Notes: k8s-agent restarted and recovered in 152s

### scale_zero_restore
- Recovery: **121.2s**
- Stability score: **0.6**
- Notes: chaos-triage-agent scaled to 0 then restored in 121s

### clickhouse_outage
- Recovery: **5.1s**
- Stability score: **1.0**
- Notes: ClickHouse 20s outage, recovered in 5s, Langfuse ok=True

## Next Steps
- [ ] Wire Phoenix LLM-as-judge (Qwen) for reasoning_quality scoring on real agent traces
- [ ] Add network partition scenario (tc netem or Litmus)
- [ ] Set alert: health_score < 0.7 and route it to the approved incident queue
- [ ] Schedule the chaos suite through the approved cluster scheduler

## Public Repo Note

The raw run log was retained locally and not committed because this is a public/sanitized repository. This report preserves the evidence needed to reproduce the validation without exposing local host details.

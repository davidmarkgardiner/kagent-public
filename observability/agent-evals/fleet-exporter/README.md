# Kagent Fleet Metrics Exporter

This is the first live collector for the `Kagent Fleet Overview` Grafana
dashboard. It exposes Prometheus metrics for:

- kagent `Agent` inventory and Ready condition
- Argo incident workflow counts
- lifecycle eval scores parsed from completed workflow logs when present

It is intentionally read-only. The exporter lists kagent Agent CRs, Argo
Workflow CRs, workflow pods, and pod logs. It does not mutate cluster state.

## Install

```bash
kubectl apply -k observability/agent-evals/fleet-exporter
```

The `ServiceMonitor` has `release: kube-prom` because the Proxmox
Prometheus selects ServiceMonitors with that label.

## Metrics

```prometheus
kagent_agent_info{cluster,namespace,agent,role,capability,env_tier} 1
kagent_agent_ready{cluster,namespace,agent,role,capability,env_tier} 0|1
kagent_incident_received_total{cluster,namespace,agent,workflow_name,run_id,failure_mode,env_tier}
kagent_incident_triaged_total{cluster,namespace,agent,workflow_name,run_id,failure_mode,env_tier}
kagent_remediation_attempted_total{cluster,namespace,agent,workflow_name,run_id,failure_mode,env_tier}
kagent_remediation_verified_total{cluster,namespace,agent,workflow_name,run_id,failure_mode,env_tier}
kagent_hitl_pending{cluster,namespace,workflow_name,run_id,approval_type,env_tier}
agent_lifecycle_eval_score{cluster,namespace,agent,case_id,run_id,workflow_name,env_tier}
agent_lifecycle_eval_passed{cluster,namespace,agent,case_id,run_id,workflow_name,env_tier}
agent_lifecycle_eval_hard_failures{cluster,namespace,agent,case_id,run_id,workflow_name,env_tier}
```

Agent response scores (`agent_eval_score`) still come from the deterministic
eval result publisher. This exporter focuses on fleet inventory and lifecycle
workflow evidence.

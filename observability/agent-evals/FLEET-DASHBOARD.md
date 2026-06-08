# Kagent Fleet Overview Dashboard

## TLDR

`grafana/kagent-fleet-overview-dashboard.json` is the first fleet-scale
Grafana dashboard for answering:

- Which kagent agents are installed across clusters?
- Which agents are Ready?
- What score is each agent getting, displayed out of 10?
- How many incidents are received, triaged, remediated, and verified?
- Which agents or workflows have hard failures?
- Where are HITL approvals currently pending?

The dashboard is intentionally metric-contract first. It works with the sample
Prometheus text file in `results/sample/kagent-fleet-overview.sample.prom`, and
the same metric names can later be emitted by kube-state-metrics custom resource
scraping, an Alloy textfile collector, or a small inventory exporter.

## Import

Import this file into Grafana:

```text
observability/agent-evals/grafana/kagent-fleet-overview-dashboard.json
```

Use a Prometheus or Mimir datasource that receives the metric families below.

## Score Convention

The scorer still emits normalized scores from `0.0` to `1.0`. The fleet
dashboard displays them as operator-friendly scores out of 10 by multiplying
the PromQL value by 10:

```promql
agent_eval_score * 10
agent_lifecycle_eval_score * 10
```

Keep the stored metric normalized so existing alert thresholds and scorers stay
consistent. Convert only at the dashboard/presentation layer.

## Metric Contract

### Agent Inventory

```prometheus
kagent_agent_info{cluster,namespace,agent,role,capability,env_tier} 1
kagent_agent_ready{cluster,namespace,agent,role,capability,env_tier} 0|1
```

Recommended source: kube-state-metrics custom resource config for kagent
`Agent` resources, or a small collector that runs `kubectl get agents -A -o
json` per cluster.

### Incident Funnel

```prometheus
kagent_incident_received_total{cluster,namespace,agent,workflow_name,run_id,failure_mode,env_tier}
kagent_incident_triaged_total{cluster,namespace,agent,workflow_name,run_id,failure_mode,env_tier}
kagent_remediation_attempted_total{cluster,namespace,agent,workflow_name,run_id,failure_mode,env_tier}
kagent_remediation_verified_total{cluster,namespace,agent,workflow_name,run_id,failure_mode,env_tier}
kagent_hitl_pending{cluster,namespace,workflow_name,run_id,approval_type,env_tier}
```

Recommended source: Argo Workflow labels/phase data, lifecycle proof markers,
and HITL suspend/resume events.

### Scores

```prometheus
agent_eval_score{cluster,namespace,agent,case_id,run_id,env_tier}
agent_eval_hard_failures{cluster,namespace,agent,case_id,run_id,env_tier}
agent_lifecycle_eval_score{cluster,namespace,agent,case_id,run_id,workflow_name,env_tier}
agent_lifecycle_eval_passed{cluster,namespace,agent,case_id,run_id,workflow_name,env_tier}
agent_lifecycle_eval_hard_failures{cluster,namespace,agent,case_id,run_id,workflow_name,env_tier}
```

Recommended source: `summarize-agent-scores.py` for eval results, with cluster
and namespace labels added by the publishing path if they are not present in
the original result JSON.

## Dashboard Panels

The first version includes:

- total agents
- Ready agents
- average score out of 10
- HITL pending
- agent inventory table
- latest agent scores out of 10
- lifecycle scores out of 10
- incident triage and remediation funnel
- hard failures by agent/workflow
- lifecycle pass/fail trend
- BYO ToolGrant inventory
- BYO tool denials and Kyverno/policy violations

### BYO Agent Governance

```prometheus
kagent_byo_agent_request_total{cluster,team,namespace,status}
kagent_toolcatalogentry_verified{cluster,tool,version,verified_by} 0|1
kagent_toolgrant_info{cluster,namespace,agent,tool_catalog_ref,expires_at} 1
kagent_toolgrant_expiring_total{cluster,namespace,agent,tool_catalog_ref}
kagent_agent_tool_denied_total{cluster,namespace,agent,tool,reason}
kagent_policy_violation_total{cluster,namespace,policy,resource_kind,reason}
```

Recommended source: `ToolCatalogEntry` and `ToolGrant` custom resources,
Kyverno PolicyReports, Agent Gateway MCP authorization logs, and the
BYO-kagent onboarding workflow. The dashboard now includes starter panels for
`kagent_toolgrant_info`, `kagent_agent_tool_denied_total`, and
`kagent_policy_violation_total`; the request/catalog/expiry metrics should be
added when the BYO exporter or kube-state-metrics custom-resource scrape is
wired.

## Next Wiring Step

For a live multi-cluster rollout, add one of these collectors:

1. kube-state-metrics custom resource config for kagent `Agent` inventory.
2. Alloy textfile scrape of a CronJob that writes `kagent_agent_*` and
   `kagent_incident_*` metrics.
3. Direct Mimir remote write from a small controller/exporter.

Start with option 2 for the home lab or work demo because it is easiest to
audit, sanitize, and replace.

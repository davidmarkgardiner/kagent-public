# MIL-124 Observability Review — Code-Review Findings

Reviewed nine artifacts under `k8s/observability/`, `observability/grafana/`, `docs/observability/`, and `scripts/observability/`. Findings below are ordered by severity. No secrets, private IPs, internal hostnames, or tenant/subscription IDs were found — public-safety is clean.

---

## CRITICAL

### C1. `loki.source.kubernetes` lacks `pods/log` RBAC — log collection will 403
`k8s/observability/k-agent-alloy.yaml:23-35` grants `pods`, `services`, `endpoints`, `namespaces`, `nodes`, `nodes/proxy`, and `endpointslices`. The `loki.source.kubernetes` component declared at line 96 streams logs via the Kubernetes API `pods/log` subresource and requires explicit `get/list/watch` on `pods/log`. As written, log collection from kagent and kgateway-system will fail with `forbidden ... cannot get resource "pods/log"`.

Fix:
```yaml
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get", "list", "watch"]
```

This invalidates the "logs are collected" claim in `docs/observability/MIL-124-POC-EVIDENCE.md:10-11` for *this bundle*. The existing in-cluster Alloy works because it presumably has its own (different) RBAC; the new `k-agent-alloy` will not.

### C2. `CLUSTER_NAME` default is the literal placeholder `{{CLUSTER_NAME}}`
`k8s/observability/k-agent-alloy.yaml:15` ships `CLUSTER_NAME: "{{CLUSTER_NAME}}"`. `sys.env("CLUSTER_NAME")` at lines 91, 141, 184, 219 will write the literal string `{{CLUSTER_NAME}}` as a label on every shipped metric and log stream until an operator runs `kubectl set env`. Result: dashboards and alerts that filter by `cluster=` silently produce empty results, and storage is poisoned with a junk label that must be cleaned up later.

Recommendation: leave the value empty and add an Alloy startup assertion, or set `CLUSTER_NAME: "unset"` so the failure is obvious instead of looking like correct data with a weird name.

### C3. kube-state-metrics dependency is undeclared
The alerts and dashboard depend on:
- `kube_deployment_status_replicas_available` — `k-agent-alerts.yaml:83`
- `kube_pod_container_status_restarts_total` — `k-agent-alerts.yaml:94-98`, dashboard panel 4 (`k-agent-metrics.json:160`)
- `kube_pod_status_phase` — dashboard panel 3 (`k-agent-metrics.json:119`)

These metrics come from kube-state-metrics, which is not part of this bundle and is not mentioned in `docs/observability/k-agent-alloy-grafana.md`. In environments without kube-state-metrics installed, `KagentControllerDown` never fires and the kagent health panels stay empty — without any visible error. The runbook in §"Live Lab Findings" implies the kagent runtime/container metrics are "covered by the Alloy and alert bundle" (`MIL-124-POC-EVIDENCE.md:14`) which is misleading.

---

## HIGH

### H1. `cluster` label is set twice and the relabel copy is dead code
`k-agent-alloy.yaml:90-93` and `:183-186` set a `cluster` label via relabel rules, while `:140-142` and `:218-220` also set `external_labels.cluster`. On `prometheus.remote_write` and `loki.write`, the `external_labels` are applied *after* relabel and silently overwrite the relabel result, making the inline rules dead code. No correctness bug, but it confused me reading it — keep one or the other.

### H2. Promoting `path`, `status`, `agent`, `model` to Loki stream labels is a cardinality time bomb
`k-agent-alloy.yaml:123-133` promotes `status`, `path`, `agent`, `model` (and `level`, `logger`, `method`) to *stream* labels via `stage.labels`. Loki best practice is to keep stream labels to the dozen-or-so low-cardinality dimensions; `path` and `status` from kagent API logs can easily explode (request IDs in paths, every distinct HTTP code). This will cause:
- Loki ingester memory growth in any realistic kagent workload.
- "too many streams" rejections from the Loki tenant.

Move these to structured-metadata or leave them inside the JSON body and rely on `| json` at query time. Only namespace/pod/container/app/cluster belong as labels.

### H3. Cadvisor scrape ships *all* cluster container metrics, not just kagent
`k-agent-alloy.yaml:199-212` discovers all nodes and scrapes their full `/metrics/cadvisor`, then forwards everything to remote_write without a relabel filter. For a small cluster that's fine; for a shared work cluster it floods the metrics backend and may violate tenant limits. None of the downstream queries that use `container_cpu_usage_seconds_total{namespace="kagent"}` (`k-agent-alloy-grafana.md:90-97`) need any container data outside `kagent` and `kgateway-system`.

Add a `metric_relabel_configs`-style filter:
```alloy
rule {
  source_labels = ["namespace"]
  regex         = "kagent|kgateway-system"
  action        = "keep"
}
```
(applied as a separate `prometheus.relabel` between scrape and remote_write).

### H4. Token-metric assumptions are not as well handled as the runbook claims
The playbook (`k-agent-alloy-grafana.md:126-129`) tells operators "a blank result means no model calls happened *or* this gateway build is not emitting `agentgateway_gen_ai_client_token_usage_*`." That is a graceful note in the doc, but the *system* doesn't degrade gracefully:

- `AgentgatewayNoTokenActivity` (`k-agent-alerts.yaml:36-46`) silently never fires when the metric is missing entirely, because `rate(missing[30m])` is empty and `sum(empty) == 0` is also empty. So the alert designed to catch "we lost token signal" actually requires the metric to exist first.
- Dashboard panel "kagent Token Fields From Structured Logs" (`k-agent-metrics.json:299-308`) is the documented fallback, but `unwrap total_tokens` will fail silently when logs don't include the field — there's no annotation on the panel telling operators "this is the fallback path."

Recommend: rename panel 8 to "Token fallback (from kagent logs)" and add a `description` field clarifying when each panel is authoritative.

### H5. `KagentA2AParseErrors` regex is broader than its name
`k-agent-alerts.yaml:127`:
```
(?i)(json-rpc|a2a|parse).*error|missing.*kind
```
Operator precedence: this is `((json-rpc|a2a|parse).*error) | (missing.*kind)`. The second alternative matches *any* line containing `missing` then `kind`, anywhere in any kagent pod — including innocuous lines like "missing optional kind". Tighten with grouping:
```
(?i)((json-rpc|a2a|parse).*error|missing\s+kind\s+field)
```
or whatever the actual error template is.

---

## MEDIUM

### M1. `AgentgatewayMetricsMissing` depends on Alloy emitting `up{pod=~"ai-gateway-.+"}`
`k-agent-alerts.yaml:67-69` relies on the synthetic `up` series carrying `pod=~"ai-gateway-.+"`. Alloy's `prometheus.scrape` does emit `up`, and the relabel rules at lines 178-181 set `pod`, so this should work — but only if the gateway pod has `prometheus.io/scrape: "true"` (the `keep` action at `:148-152` drops it otherwise). The runbook never says "ensure the ai-gateway pod has the scrape annotation," and that's a likely silent breakage in another environment.

Add an explicit precondition step in `k-agent-alloy-grafana.md` §Deployment.

### M2. `clamp_min(..., 1)` masks low-traffic 5xx bursts
`k-agent-alerts.yaml:54-57` (and the matching `k-agent-metrics.json:201` stat panel) clamp the denominator to 1 to avoid div-by-zero. At low rate (denominator 0.0001), this under-reports the actual ratio by 4 orders of magnitude — a 100% 5xx burst on 1 request/min reads as 0.017. For runaway-failure detection that's OK; for "is the gateway broken right now?" it isn't. Consider gating on `denominator > 0.01` instead, or pair the ratio alert with an absolute-rate alert (`5xx rate > 0.1/s` for the same window).

### M3. Loki rules require Loki ruler — not explained
`k-agent-alerts.yaml:108-150` ships LogQL inside a `monitoring.coreos.com/v1 PrometheusRule`. This is the right shape *when* the cluster's Loki ruler is configured to read from `PrometheusRule` CRDs (Grafana Cloud, kube-prometheus-stack with Loki rule sync, or Mimir/Loki rule sync sidecars). On a vanilla Prometheus Operator install with no Loki ruler, Prometheus tries to evaluate `count_over_time({...} |~ ...)` as PromQL and rejects it — alerts won't load. Document the precondition or split into a `LokiRule` CRD path if the target stack supports one.

### M4. Datasource provisioning has no auth, no env-substitution guarantee
`observability/grafana/provisioning/datasources/k-agent-lgtm.yaml:8,19` uses `${PROMETHEUS_URL}` and `${LOKI_URL}`. Grafana only interpolates these if the env var is exported at the Grafana process and provisioning interpolation is enabled (default behavior since Grafana 7.1). It also has no `basicAuth`, no `httpHeaderName1: Authorization`, no tenant header (`X-Scope-OrgID` for Mimir/Loki multi-tenant). Operators pointing this at a real LGTM stack will hit 401/anonymous-tenant errors. Either:
- Add a commented-out auth block as an example, or
- Document explicitly in §Deployment step 4 that auth must be added per environment.

### M5. CRI-only log parsing
`stage.cri {}` at `k-agent-alloy.yaml:104` is correct for containerd/CRI-O nodes, which is fine for modern K8s. If a target environment still runs dockershim or has mixed runtimes, the JSON parse stage gets fed log lines wrapped in Docker-JSON format and silently fails. Worth a one-line note in the playbook (CRI stage assumes containerd/CRI-O).

### M6. `insecure_skip_verify: true` on kubelet TLS
`k-agent-alloy.yaml:207-209`. Standard practice in many clusters but worth flagging — managed clusters (AKS, EKS, GKE) and on-prem environments with proper CA chains can omit this. Make it a configurable env var (`KUBELET_INSECURE_SKIP_VERIFY`) defaulting to `true` to ease deployment but allow strict mode.

---

## LOW

### L1. Doc/playbook inconsistency: `.ts` field is never extracted
`k-agent-alloy-grafana.md:144` and `k-agent-observability-playbook.html:330` both use `{{.ts}}` in `line_format`, but `stage.json` at `k-agent-alloy.yaml:106-121` extracts `level, logger, msg, method, path, status, duration, agent, model, input_tokens, output_tokens, total_tokens` — no `ts`. The dashboard's panel 6 (`k-agent-metrics.json:233`) gets it right with `{{.level}}`. Pick one source-of-truth and use it everywhere.

### L2. `unit: "tpm"` is not a valid Grafana unit
`k-agent-metrics.json:18`. Grafana will render the value with a "tpm" suffix from the legend but no unit transformation. Use `"short"` or define a custom unit; the actual rate is already `tokens/min` from the `* 60` math.

### L3. `wget` assumption in verify script
`scripts/observability/verify-k-agent-observability.sh:43`. The ai-gateway image may not include `wget` (distroless images often don't). Prefer `curl` with a fallback, or `kubectl run` an ephemeral debug pod. Currently the script `|| true`'s the whole block so it silently passes — false-OK.

### L4. `verify-k-agent-observability.sh` misses validations
- No PromQL validation (`promtool check rules`).
- No Alloy config syntax check (`alloy fmt` / `alloy run --check`).
- Doesn't grep for the missing `pods/log` RBAC bug from C1.
- Doesn't verify the Grafana datasource UIDs match between dashboard and provisioning file (they do currently — `kagent-mimir`/`kagent-loki` — but a refactor would silently break the dashboard).

### L5. Hard-coded deployment name in verify script
`scripts/observability/verify-k-agent-observability.sh:33` assumes `kagent-controller`. In another environment with a Helm release name prefix, this fails. Use `kubectl get deploy -l app.kubernetes.io/name=kagent-controller` instead.

### L6. HTML playbook adds one fact not in the markdown
The HTML's "What To Prove" tiles imply token usage already works ("Should move after an LLM-backed request") but don't carry the explicit "or token metrics aren't being emitted by this gateway build" fallback. Compared to `k-agent-alloy-grafana.md:126-129`, this slightly overclaims. The "Tokens" card at `k-agent-observability-playbook.html:291` does mention the fallback — so it's a partial fix; consider also adding a small note under the Tokens panel description.

---

## Residual risks (no fix required, just flagging)

- The bundle assumes Prometheus Operator CRDs are installed. `k-agent-alerts.yaml` will be rejected on a cluster without `PrometheusRule` CRD. Documented requirement, but worth a script-level precheck (`kubectl api-resources | grep prometheusrules`).
- Cluster label cardinality is fine for one cluster; if this is replayed across many work environments with the same Mimir tenant, ensure `external_labels.cluster` is genuinely unique per cluster.
- `agentgateway_gen_ai_client_token_usage_*` is forward-compatible naming. If the upstream gateway renames these (e.g., `agentgateway_genai_*` without underscore split, or moves to OpenTelemetry semconv `gen_ai.client.token.usage`), all token panels and alerts break. Pin the gateway image version in the work environment and re-verify on upgrade.

---

## Summary

Two issues block correctness in a fresh deployment (C1 RBAC and C2 placeholder cluster label) and one is a documentation gap that will silently degrade alerts (C3 kube-state-metrics). The repo is otherwise solid and the public-safety review is clean.

If only the three CRITICAL items are addressed, the bundle is in good shape to replay in another environment.

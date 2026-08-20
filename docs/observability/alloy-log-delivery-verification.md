# Verify Grafana Alloy Log Delivery

Use this runbook after installing or upgrading Grafana Alloy on a Kubernetes
cluster. It distinguishes three different checks that are often incorrectly
treated as equivalent:

1. the rendered Helm chart contains a complete log pipeline;
2. Alloy is reading and sending log entries;
3. the log backend stored a specific test entry and can return it.

The third check is the acceptance gate. A healthy Alloy process or a non-zero
lifetime counter does not, by itself, prove current end-to-end delivery.

All examples are public-safe. Replace `{{PLACEHOLDER}}` values at deployment
time and keep authentication material in the environment or an approved
Kubernetes Secret.

## TL;DR

Generate a unique log marker, leave the Pod running long enough for discovery,
then query the log backend for that exact marker:

```bash
RUN_ID="alloy-e2e-$(date +%s)"

kubectl create namespace alloy-smoke \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n alloy-smoke run alloy-log-smoke \
  --image=busybox:1.36 \
  --restart=Never \
  --labels=app=alloy-log-smoke \
  --command -- sh -c \
  "echo '${RUN_ID}'; sleep 60"

echo "Search the log backend for: ${RUN_ID}"
```

For Loki, query the read endpoint rather than the push endpoint:

```bash
LOKI_QUERY_URL="https://{{LOKI_HOST}}/loki/api/v1/query_range"
LOGQL="{namespace=\"alloy-smoke\"} |= \"${RUN_ID}\""

curl -fsSG "${LOKI_QUERY_URL}" \
  --data-urlencode "query=${LOGQL}" \
  --data-urlencode "limit=20" |
jq --arg marker "${RUN_ID}" -e \
  '[.data.result[].values[]?[1] | select(contains($marker))] | length > 0'
```

Add the approved authentication and tenant headers for the target environment.
Exit status `0` from `jq` proves the unique marker was returned. An empty result
or a request error fails the deployment verification.

Clean up after capturing the result:

```bash
kubectl delete namespace alloy-smoke
```

## What Each Check Proves

| Check | Proves | Does not prove |
|---|---|---|
| `helm template` or `helm lint` | The chart renders and passes static chart checks. | Alloy discovered logs or reached the backend. |
| Alloy `/-/ready` | Alloy loaded its initial configuration. | Every component is healthy or data is flowing. |
| Alloy `/-/healthy` | Alloy currently considers its components healthy. | A useful target exists or the backend stored a log. |
| `loki_write_sent_entries_total` increases | Alloy sent entries to a Loki ingester. | The specific cluster marker is queryable. |
| Unique marker returned by Loki | The tested write and read path worked end to end. | Future delivery will remain healthy without monitoring. |

Do not configure `/-/healthy` as an Alloy liveness probe. Grafana documents it
as a diagnostic endpoint rather than a suitable Kubernetes liveness signal.

## Gate 1: Check the Rendered Helm Chart

Render the exact values used for a cluster:

```bash
helm lint {{CHART_PATH}} -f {{CLUSTER_VALUES_FILE}}

helm template {{RELEASE_NAME}} {{CHART_PATH}} \
  --namespace {{ALLOY_NAMESPACE}} \
  -f {{CLUSTER_VALUES_FILE}} > /tmp/alloy-rendered.yaml
```

Inspect the rendered Alloy configuration and RBAC. Component names vary by
chart, but the rendered graph must contain all of these links:

```text
Kubernetes discovery
  -> Kubernetes or file log source
  -> optional processing/relabel stages
  -> log writer/exporter
  -> approved backend endpoint
```

Quick searches:

```bash
rg -n 'loki.source.(kubernetes|file)|loki.process|loki.write' \
  /tmp/alloy-rendered.yaml

rg -n 'pods/log|LOKI|loki/api/v1/push|12345|ServiceMonitor' \
  /tmp/alloy-rendered.yaml
```

Confirm all of the following before rollout:

- the log source receives non-empty discovery targets;
- every `forward_to` points to the intended next receiver;
- the final writer/exporter uses the log ingestion endpoint, not a metrics
  remote-write endpoint;
- pod-log collection has the required read-only `pods` and `pods/log` RBAC;
- filters and namespace selectors include the smoke-test workload;
- useful labels such as `cluster`, `namespace`, `pod`, and `container` survive
  processing without exposing secret values;
- Alloy port `12345` is available to the approved metrics scraper;
- credentials come from an approved secret mechanism and are not rendered into
  a committed values file.

Static rendering is necessary but is not the delivery acceptance test.

## Gate 2: Check Alloy Runtime Metrics

Port-forward an Alloy Pod. Adjust the label selector to match the chart:

```bash
ALLOY_POD="$(kubectl -n {{ALLOY_NAMESPACE}} get pod \
  -l app.kubernetes.io/name=alloy \
  -o jsonpath='{.items[0].metadata.name}')"

kubectl -n {{ALLOY_NAMESPACE}} port-forward \
  "pod/${ALLOY_POD}" 12345:12345
```

In another terminal:

```bash
curl -fsS http://localhost:12345/-/ready
curl -fsS http://localhost:12345/-/healthy

curl -fsS http://localhost:12345/metrics |
  rg 'loki_write_(sent_entries|dropped_entries|batch_retries|stream_lag_seconds)'
```

For a Loki writer, use these signals:

| Metric | Expected behaviour |
|---|---|
| `loki_write_sent_entries_total` | Increases after fresh logs are emitted. |
| `loki_write_dropped_entries_total` | Does not increase. |
| `loki_write_batch_retries_total` | Does not increase continuously. |
| `loki_write_stream_lag_seconds` | Remains bounded rather than continually rising. |
| `loki_write_request_duration_seconds_count` | Successful status-code series increase. |

A lifetime value greater than zero can hide a current outage. Compare values
before and after the smoke workload, or query a recent window from Prometheus
or Mimir:

```promql
sum by (cluster) (
  increase(loki_write_sent_entries_total[10m])
)
```

```promql
sum by (cluster, reason) (
  increase(loki_write_dropped_entries_total[10m])
)
```

Use the fleet's real cluster identity label in place of `cluster`. Alert on
missing series as well as zero increases; otherwise an Alloy instance that is
not being scraped can disappear silently.

If Alloy runs as a DaemonSet or uses target sharding, checking one arbitrary Pod
is insufficient. Query the central metrics backend across every expected Alloy
instance.

## Gate 3: Prove Backend Arrival

The unique-marker test from the TL;DR is the required end-to-end gate:

```text
test Pod stdout
  -> Kubernetes log discovery
  -> Alloy source
  -> processing and relabeling
  -> network and authentication
  -> backend ingestion
  -> backend query
```

Record the following evidence for each cluster or rollout cohort:

```text
cluster: {{CLUSTER_NAME}}
run_id: alloy-e2e-{{RUN_ID}}
alloy_release_revision: {{HELM_REVISION}}
alloy_image: {{ALLOY_IMAGE_DIGEST}}
emitted_at_utc: {{TIMESTAMP}}
backend_first_seen_at_utc: {{TIMESTAMP}}
delivery_latency_seconds: {{NUMBER}}
result: PASS | FAIL
```

Do not record credentials, private endpoints, subscription IDs, or raw logs
that may contain sensitive data.

## Add the Check to a Helm Chart

The lowest-effort chart integration is a Helm test Job that:

1. emits a unique marker to its own standard output;
2. stays alive so Alloy has time to discover and tail it;
3. repeatedly queries the backend for the marker;
4. exits non-zero if the marker is absent at the timeout.

Put the Job under `templates/tests/` and annotate it as a Helm test:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: "{{ include \"CHART.fullname\" . }}-alloy-log-delivery"
  namespace: "{{ .Values.alloyLogVerification.namespace }}"
  annotations:
    "helm.sh/hook": test
    "helm.sh/hook-delete-policy": before-hook-creation
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 600
  template:
    metadata:
      labels:
        app: alloy-log-smoke
    spec:
      restartPolicy: Never
      containers:
        - name: verify
          image: "{{ .Values.alloyLogVerification.image }}"
          env:
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
            - name: CLUSTER_NAME
              value: "{{ .Values.cluster.name }}"
            - name: LOKI_QUERY_URL
              valueFrom:
                secretKeyRef:
                  name: "{{ .Values.alloyLogVerification.querySecret.name }}"
                  key: query-url
          command: ["/bin/sh", "-ec"]
          args:
            - |
              marker="ALLOY_LOG_E2E_${CLUSTER_NAME}_$(date +%s)_${HOSTNAME}"
              printf '%s\n' "${marker}"

              attempt=1
              while [ "${attempt}" -le 24 ]; do
                query="{namespace=\"${POD_NAMESPACE}\"} |= \"${marker}\""
                if curl -fsSG "${LOKI_QUERY_URL}" \
                    --data-urlencode "query=${query}" \
                    --data-urlencode "limit=20" | grep -Fq "${marker}"; then
                  printf 'ALLOY_LOG_DELIVERY: PASS marker=%s attempt=%s\n' \
                    "${marker}" "${attempt}"
                  exit 0
                fi
                attempt=$((attempt + 1))
                sleep 5
              done

              printf 'ALLOY_LOG_DELIVERY: FAIL marker=%s\n' "${marker}" >&2
              exit 1
```

Adapt the chart helper name, image, authentication, tenant header, backend
labels, namespace, and Secret keys to the deployment. The selected namespace
must be included by Alloy's pod-log discovery configuration. The test image
must contain a POSIX shell, `curl`, and `grep`. Do not place a token directly in
the template or values file.

Run it explicitly after the release is ready:

```bash
helm upgrade --install {{RELEASE_NAME}} {{CHART_PATH}} \
  --namespace {{ALLOY_NAMESPACE}} \
  -f {{CLUSTER_VALUES_FILE}} \
  --wait

helm test {{RELEASE_NAME}} \
  --namespace {{ALLOY_NAMESPACE}} \
  --logs \
  --timeout 5m
```

`helm test` is not run automatically by `helm upgrade`. Make it a required
post-deployment pipeline step and preserve its output as rollout evidence.

## Continuous Fleet Canary

The Helm test proves a deployment at one point in time. For ongoing assurance,
deploy one low-volume canary per cluster that emits a stable marker every one
to five minutes, then alert when the backend cannot find it.

Example LogQL shape:

```logql
sum by (cluster) (
  count_over_time(
    {namespace="alloy-smoke", app="alloy-log-canary"}
      |= "ALLOY_LOG_CANARY" [10m]
  )
) < 1
```

Keep the canary line small, non-sensitive, and low-cardinality. The runtime
marker may contain a run ID in the log body, but do not create a new indexed
label for every run.

## Fast Failure Diagnosis

| Observation | Likely boundary to inspect |
|---|---|
| No discovered targets | Namespace selector, pod discovery, sharding, RBAC, or missing node-log mount. |
| Targets exist but sent-entry counter does not increase | Source-to-process wiring, drop filters, parsing, or `forward_to`. |
| Retries or drops increase | Endpoint, DNS, TLS, tenant, authentication, rate limit, or backend rejection. |
| Sent-entry counter increases but marker is absent | Wrong backend/tenant, label mismatch, query time range, ingestion delay, or backend read-path failure. |
| Only some clusters fail | Cluster-specific values, network policy, identity, endpoint, or fleet-label mismatch. |
| Alloy metrics are absent | ServiceMonitor/scrape configuration or Alloy port exposure, not necessarily log delivery itself. |

Use Alloy's component graph and Kubernetes log-source target details to inspect
the most recent read time and tailing errors. Component health is independent;
one healthy component does not guarantee every downstream component is working.

## Acceptance Criteria

A cluster passes only when all of these are true:

- the exact deployed chart revision renders the expected end-to-end pipeline;
- every expected Alloy instance exposes current runtime metrics;
- sent-entry counters increase during the test window;
- dropped-entry counters do not increase during the test window;
- the backend returns the unique marker before the timeout;
- the result records the cluster, release revision, image digest, run ID, and
  UTC timestamps without recording secrets.

## References

- [Grafana Alloy HTTP endpoints](https://grafana.com/docs/alloy/latest/reference/http/)
- [Grafana Alloy `loki.source.kubernetes`](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.kubernetes/)
- [Grafana Alloy `loki.write` metrics](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.write/)
- [Helm chart tests](https://helm.sh/docs/topics/chart_tests/)
- [Helm `test` command](https://helm.sh/docs/helm/helm_test/)

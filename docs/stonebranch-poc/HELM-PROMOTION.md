# Promoting Stonebranch UAG With Helm

This folder now includes a Helm chart at `chart/` for promoting the Stonebranch Universal Agent Gateway pattern through environments. The chart keeps the POC behavior intact while making the environment-specific parts explicit in values files.

## Why Helm Here

Use Helm for this application because the important promotion boundary is not just image tag selection. The Stonebranch container does not reliably consume the Kubernetes environment variables shown in the reference ConfigMap, so the chart must render the init-container patch commands that write the real Stonebranch config files:

- `/etc/universal/comp/oms` enables OMS `auto_start`.
- `/etc/universal/uags.conf` sets `oms_servers`.
- `/etc/universal/uags.conf` sets the unique agent `netname`.

That means `values.yaml` should drive the rendered config patching, resource sizing, namespace, replica count, service exposure, and network policy.

## Chart Layout

| Path | Purpose |
|---|---|
| `chart/Chart.yaml` | Chart metadata and version. |
| `chart/values.yaml` | Shared defaults used by every environment. |
| `chart/values-dev.yaml` | Small dev deployment. |
| `chart/values-test.yaml` | Test deployment with production-like namespace and replica shape. |
| `chart/values-prod.yaml` | Production override example with placeholder OMS hostname. |
| `chart/templates/oms.yaml` | OMS Deployment and Service. |
| `chart/templates/agent.yaml` | UAG agent Deployment and Service. |
| `chart/templates/networkpolicy.yaml` | Same-namespace and optional worker-namespace traffic policy. |
| `chart/templates/tests/smoke-test.yaml` | Helm test job for deployment smoke checks. |

## What To Variablise

| Setting | Values key | Example |
|---|---|---|
| Namespace | `global.namespace` | `stonebranch-dev`, `stonebranch-test`, `stonebranch` |
| Universal Agent image | `image.repository`, `image.tag` | `stonebranch/universal-agent:8.0.0.0-debian` |
| OMS identity | `oms.netname` | `OMS-TEST-001` |
| OMS service type | `oms.service.type` | `ClusterIP`, `LoadBalancer` |
| Agent replicas | `agent.replicas` | `1` in dev, `2` in test, `3+` in prod |
| Agent name prefix | `agent.namePrefix` | `UAG-DEV`, `UAG-TEST`, `UAG-PROD` |
| Agent OMS target | `agent.oms.host`, `agent.oms.port` | `oms-server.stonebranch-test.svc.cluster.local`, `{{OMS_HOSTNAME}}` |
| CPU/memory | `oms.resources`, `agent.resources` | Environment-specific requests and limits |
| Cross-namespace traffic | `networkPolicy.allowWorkerNamespaces` | `false` for dev/test, `true` when worker namespaces need OMS access |
| Smoke timeout | `smokeTest.timeout` | Longer in prod because first image pull can be slow |

Keep real internal DNS names, private IPs, tenant IDs, subscription IDs, and credentials out of the public values files. Use placeholders such as `{{OMS_HOSTNAME}}` and override them in a private deployment repo or CI variable set.

## Promotion Flow

Render before installing:

```bash
helm template stonebranch-dev ./chart \
  -f ./chart/values.yaml \
  -f ./chart/values-dev.yaml
```

Install or upgrade one environment:

```bash
helm upgrade --install stonebranch-dev ./chart \
  --namespace stonebranch-dev \
  --create-namespace \
  -f ./chart/values.yaml \
  -f ./chart/values-dev.yaml \
  --wait \
  --timeout 5m
```

Run the smoke test:

```bash
helm test stonebranch-dev \
  --namespace stonebranch-dev \
  --logs \
  --timeout 5m
```

Promote by changing only the values file and release identity:

```bash
helm upgrade --install stonebranch-test ./chart \
  --namespace stonebranch-test \
  --create-namespace \
  -f ./chart/values.yaml \
  -f ./chart/values-test.yaml \
  --wait \
  --timeout 5m

helm test stonebranch-test --namespace stonebranch-test --logs --timeout 5m
```

In GitOps, commit the chart and environment values into the platform repo, then let Flux or Argo CD reconcile the Helm release. CI should still run `helm template`, `helm lint`, and the live `helm test` after the controller reports the release healthy.

## Smoke Test Contract

The Helm test job fails unless all of these checks pass:

1. `deployment/oms-server` rolls out successfully.
2. `deployment/uag-agent` rolls out successfully.
3. The agent init-container logs show the expected rendered `oms_servers` value.
4. The agent init-container logs show the expected rendered agent `netname` prefix.
5. The UAG container logs include `Transport connected`.

This is intentionally narrow. It proves the rendered Helm values made it into Stonebranch config files and that agents connected to OMS. It does not prove licensed Universal Controller job execution, because the existing POC results show command execution needs a valid Stonebranch license path.

## CI Gate

Use this as the minimum promotion gate before merging an environment change:

```bash
helm lint ./chart -f ./chart/values.yaml -f ./chart/values-test.yaml
helm template stonebranch-test ./chart -f ./chart/values.yaml -f ./chart/values-test.yaml >/tmp/stonebranch-test.yaml
kubectl apply --dry-run=server -f /tmp/stonebranch-test.yaml
```

After merge and reconciliation:

```bash
helm status stonebranch-test --namespace stonebranch-test
helm test stonebranch-test --namespace stonebranch-test --logs --timeout 5m
```

For production, add a Stonebranch-side confirmation step: the Universal Controller team should confirm the expected agent names are visible and assigned to the correct agent cluster.

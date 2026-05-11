# Option A — Managed AlertManager → Argo EventSource webhook

**Status:** core pipeline already tested end-to-end on `{{CLUSTER_NAME}}`. Only the network ingress + auth layer is new.
**Date:** 2026-04-30
**Owner:** David Gardiner

---

## TL;DR

We do **not** need to build this from scratch. The exact pattern — Prometheus AlertManager POSTing JSON to an Argo Events `webhook` EventSource that triggers a Sensor → triage Workflow → kagent A2A → Mattermost / GitLab — **is already deployed and tested** on `{{CLUSTER_NAME}}`. See `aks-mgmt-stack/k8s-event-triage/prometheus-alerting/`.

The **only** thing Option A changes vs. what we already run is **where the AlertManager lives**:

| | Already tested (in-cluster) | Option A (managed LGTM) |
|---|---|---|
| AlertManager | `kube-prom` Helm release in `monitoring` ns | Managed LGTM, outside our cluster |
| Webhook URL | `http://alertmanager-eventsource-svc.argo-events.svc.cluster.local:12000/alerts` | `https://<our-public-host>/alerts` |
| Network path | ClusterIP, no TLS | Ingress + TLS |
| Auth | None (cluster-internal) | Bearer token (or mTLS) |
| EventSource | unchanged | unchanged |
| Sensor | unchanged | unchanged |
| WorkflowTemplate | unchanged | unchanged |
| RBAC | unchanged | unchanged |

Everything in the right column past "Auth" is **literally the same files**.

---

## What's already proven (on the proxmox Prometheus stack)

Files under `aks-mgmt-stack/k8s-event-triage/prometheus-alerting/`:

| File | Status | What it does |
|---|---|---|
| `01-alertmanager-values.yaml` | TESTED | Adds `argo-events-webhook` receiver to AlertManager, routes `KubePod.*\|KubeContainer.*\|OOMKilled\|...` to it |
| `02-custom-alerting-rules.yaml` | TESTED | Custom PrometheusRule (OOMKilled, PodHighRestarts, FailedScheduling, CPU/Memory High, PVCNearCapacity) |
| `03-eventsource-alertmanager.yaml` | **TESTED — reuse as-is** | Argo Events `webhook` EventSource on `:12000/alerts` |
| `04-workflow-template.yaml` | TESTED | `alertmanager-triage` DAG: fetch pod logs/events → GitLab issue → Mattermost |
| `05-sensor.yaml` | **TESTED — reuse as-is** | Filters `status: firing`, rate-limits to 5/min, triggers `alertmanager-triage` |
| `08-workflow-rbac.yaml` | TESTED | RBAC for `argo-events-sa` to read pods/logs/events |
| `deploy.sh` | TESTED | One-shot deploy with prereq checks |
| `test-alerts.sh` | TESTED | `--webhook-test`, `--create-oom`, `--create-crashloop`, `--create-imagepull`, `--verify`, `--all` |

**Validation evidence (from memory):**
- Real `KubePodCrashLooping` alerts caught from `gitea` namespace
- Test script `test-alerts.sh --all` runs: webhook injection → failing pod creation → wait 60s → workflow verification
- Sensor confirmed routing `status: firing` only, rate limit 5/min holding

**Reusable verbatim from this dir:**
- `03-eventsource-alertmanager.yaml`
- `05-sensor.yaml`
- `04-workflow-template.yaml` (or its sibling `managed-lgtm-integration/alerts/workflow-template-alerts.yaml` for the slightly richer alert-shape parser)
- `08-workflow-rbac.yaml`
- `test-alerts.sh` — works against a remote AlertManager too, just point its webhook at our public ingress

---

## What's new for Option A

Three additions on top of the tested stack:

### 1. Public-ish Ingress for the EventSource service

```yaml
# managed-lgtm-integration/ingress/01-alertmanager-eventsource-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: alertmanager-eventsource
  namespace: argo-events
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/backend-protocol: HTTP
    # Reject anything without our shared bearer token
    nginx.ingress.kubernetes.io/configuration-snippet: |
      if ($http_authorization != "Bearer ${ALERTMANAGER_WEBHOOK_TOKEN}") {
        return 401;
      }
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - alerts.lab.{{INGRESS_DOMAIN}}
      secretName: alertmanager-eventsource-tls
  rules:
    - host: alerts.lab.{{INGRESS_DOMAIN}}
      http:
        paths:
          - path: /alerts
            pathType: Prefix
            backend:
              service:
                name: alertmanager-eventsource-svc
                port:
                  number: 12000
```

Notes:
- `alertmanager-eventsource-svc` is the Service auto-created by Argo Events for the `alertmanager` EventSource (`{eventsource-name}-eventsource-svc` — see memory).
- Bearer-token check via nginx snippet is the cheapest auth. For production swap for **mTLS** at the ingress (managed AlertManager supports a client cert under `webhook_configs.tls_config`).
- Token lives in Secret `alertmanager-webhook-token` in `argo-events`, materialised into the snippet at template time. Rotation = update Secret + re-apply Ingress + update managed AM webhook config.

### 2. Managed AlertManager webhook config (platform team applies)

```yaml
# What the platform team needs to add to the managed AlertManager config
receivers:
  - name: argo-events-webhook
    webhook_configs:
      - url: https://alerts.lab.{{INGRESS_DOMAIN}}/alerts
        send_resolved: true
        max_alerts: 10
        http_config:
          authorization:
            type: Bearer
            credentials: <token from alertmanager-webhook-token secret>
          # Or mTLS:
          # tls_config:
          #   cert_file: /etc/am/client.crt
          #   key_file:  /etc/am/client.key
          #   ca_file:   /etc/am/ca.crt

route:
  routes:
    - receiver: argo-events-webhook
      matchers:
        - alertname =~ "KubePod.*|KubeContainer.*|OOMKilled.*|PodHighRestarts|FailedScheduling|ContainerCPUHigh|ContainerMemoryHigh|PVCNearCapacity"
      continue: true
```

This is **identical** to `prometheus-alerting/01-alertmanager-values.yaml` — same matchers, same receiver name. Only the URL changes from cluster-internal to public.

### 3. Bearer-token Secret + ExternalSecret

```bash
# One-shot — generate and store
TOKEN=$(openssl rand -hex 32)
kubectl create secret generic alertmanager-webhook-token \
  --namespace argo-events \
  --from-literal=token="${TOKEN}"

# Hand the same token to the platform team to put in the managed AM config
echo "Token (give to platform team for managed AM webhook auth):"
echo "${TOKEN}"
```

For long-term we wire this through Key Vault + External Secrets — same pattern as `eventhub-otlp-pipeline/01-secrets.yaml` already does for Event Hub credentials.

---

## Deploy steps

Assumes the tested in-cluster pipeline (`prometheus-alerting/`) is already deployed. If not, run that `deploy.sh` first; the EventSource, Sensor, WorkflowTemplate, and RBAC are shared.

```bash
# 1. Generate and store the bearer token
TOKEN=$(openssl rand -hex 32)
kubectl create secret generic alertmanager-webhook-token \
  --namespace argo-events \
  --from-literal=token="${TOKEN}"

# 2. Apply the Ingress (substitute ${ALERTMANAGER_WEBHOOK_TOKEN} first)
envsubst < ingress/01-alertmanager-eventsource-ingress.yaml | kubectl apply -f -

# 3. Wait for cert-manager to issue the TLS cert
kubectl wait --for=condition=ready certificate/alertmanager-eventsource-tls \
  -n argo-events --timeout=180s

# 4. Send the URL + token to the platform team:
#      URL:   https://alerts.lab.{{INGRESS_DOMAIN}}/alerts
#      Token: ${TOKEN}
#    They add the webhook receiver to the managed AlertManager.

# 5. Smoke-test from outside the cluster (proves managed AM can reach us)
curl -X POST https://alerts.lab.{{INGRESS_DOMAIN}}/alerts \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d @../prometheus-alerting/test-payload-firing.json   # any AM-shaped payload

# 6. Verify a workflow was triggered
kubectl get workflows -n argo-events -l event-type=prometheus-alert \
  --sort-by=.metadata.creationTimestamp | tail -5
```

---

## Test plan (reuses `test-alerts.sh`)

The existing `prometheus-alerting/test-alerts.sh` already covers everything we need. We just need a second mode that targets the public ingress:

```bash
# Already supported — webhook test against in-cluster service
./test-alerts.sh --context {{CLUSTER_NAME}} --webhook-test

# Already supported — webhook test against localhost:12000 port-forward
./test-alerts.sh --context {{CLUSTER_NAME}} --webhook-mode local --webhook-test

# NEW — webhook test against public ingress (proves Option A end-to-end)
WEBHOOK_TOKEN=$(kubectl get secret alertmanager-webhook-token \
  -n argo-events -o jsonpath='{.data.token}' | base64 -d)

curl -X POST https://alerts.lab.{{INGRESS_DOMAIN}}/alerts \
  -H "Authorization: Bearer ${WEBHOOK_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "version":"4","status":"firing","receiver":"argo-events-webhook",
    "alerts":[{
      "status":"firing",
      "labels":{"alertname":"OptionATest","severity":"warning","namespace":"default","pod":"test-pod"},
      "annotations":{"summary":"Option A end-to-end test","description":"Public ingress + bearer auth"},
      "startsAt":"2026-04-30T00:00:00.000Z"
    }]
  }'

# Negative test — wrong token must return 401
curl -i -X POST https://alerts.lab.{{INGRESS_DOMAIN}}/alerts \
  -H "Authorization: Bearer wrong-token" \
  -H "Content-Type: application/json" -d '{}'
# Expect: HTTP/2 401

# Verify the workflow ran
./test-alerts.sh --context {{CLUSTER_NAME}} --verify
```

For the full loop test once managed AM is wired up:
```bash
# Trigger a real failure on a worker cluster, watch managed AM fire,
# watch workflow show up in the mgmt cluster
./test-alerts.sh --context {{CLUSTER_NAME}} --create-crashloop
./test-alerts.sh --context {{CLUSTER_NAME}} --verify
```

---

## What can fail and how to debug

| Symptom | Likely cause | Check |
|---|---|---|
| `curl` returns 401 even with right token | Nginx snippet not reading `$http_authorization` correctly | `kubectl logs -n ingress-nginx <controller-pod>` for the request line |
| `curl` returns 503 | EventSource pod not running or service has no endpoints | `kubectl get pods -n argo-events -l eventsource-name=alertmanager` |
| 200 OK but no workflow | Sensor filter rejecting payload (e.g. `status != firing`) | `kubectl logs -n argo-events -l sensor-name=alertmanager-triage-sensor` |
| Workflow created but stuck | RBAC missing for pod logs/events | `kubectl logs <wf-pod>` — look for `forbidden` |
| Managed AM cannot reach us | Egress firewall on platform side | Run `curl` from a pod inside their network if they'll let us; otherwise platform team has to confirm outbound allowlist |
| Cert won't issue | DNS not pointing at ingress IP | `kubectl describe certificate alertmanager-eventsource-tls -n argo-events` |

Same troubleshooting commands as `prometheus-alerting/README.md` — the EventSource, Sensor, Workflow layers are identical.

---

## Outstanding decisions

Before wiring this up, confirm with the platform team (open question Q4 in `OPEN-QUESTIONS.md`):

1. **Can managed AlertManager reach a public HTTPS endpoint we own?** If no, we fall back to Option C (NATS JetStream as the queue).
2. **Auth method:** Bearer token (cheap) vs mTLS (more secure, more setup). We'll start with bearer; switch to mTLS in v2 if platform requires.
3. **DNS / hostname:** does `alerts.lab.{{INGRESS_DOMAIN}}` work, or do we need to register a hostname under a corporate-controlled zone?
4. **Source IP allowlist:** if the managed AM has a known egress range, add an `nginx.ingress.kubernetes.io/whitelist-source-range` annotation as defence-in-depth.

---

## File checklist for shipping Option A

To deploy, we only need to add **one new file** on top of the existing tested pipeline:

```
managed-lgtm-integration/
├── OPTION-A-README.md                                     ← this file
├── ingress/
│   └── 01-alertmanager-eventsource-ingress.yaml           ← NEW (the only new manifest)
└── (everything else reused from prometheus-alerting/ as-is)
```

The Secret + token-rotation script can stay shell-only for now — promote to ExternalSecret + Vault when this exits POC.

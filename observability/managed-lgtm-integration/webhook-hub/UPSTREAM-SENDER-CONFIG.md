# Upstream sender configs — what to ask the platform team to add

The Hub is a plain HTTPS POST endpoint. Two flavours of upstream sender, depending on which option the platform team approves. Either works.

| If they say… | They configure… | Section below |
|---|---|---|
| "We can add a Grafana Contact Point" | Grafana Alerting → Webhook contact point | [Option 1](#option-1--grafana-alerting-contact-point) |
| "We can add an AlertManager receiver" | AlertManager `webhook_configs` | [Option 2](#option-2--alertmanager-webhook_configs) |
| "Both are available" | Either — pick Option 1 (faster, more direct) | — |

Common to both:
- **URL:** `https://webhook-hub.<your-domain>/inbound`
- **Auth:** `Authorization: Bearer <token>` (token from `webhook-hub-token` Secret)
- **Method:** `POST`, `Content-Type: application/json`

---

## Option 1 — Grafana Alerting Contact Point

### Via the Grafana UI

1. Navigate to **Alerting → Contact points → + Add contact point**
2. **Name:** `webhook-hub` (or whatever your team prefers)
3. **Integration:** select **Webhook**
4. **URL:** `https://webhook-hub.<your-domain>/inbound`
5. **HTTP Method:** `POST`
6. **Authorization Header — Scheme:** `Bearer`
7. **Authorization Header — Credentials:** *(paste the token)*
8. **Optional settings:**
   - **Max Alerts:** `0` (unlimited) or set a per-batch cap
   - **Disable resolved message:** unchecked (we want resolved notifications too)
9. **Test** → expect HTTP 200 (or your configured success code). Verify a workflow appears: `kubectl get workflows -n argo-events -l app.kubernetes.io/part-of=webhook-hub`
10. **Save contact point**

Then create a **Notification Policy**:
- *Alerting → Notification policies → + New nested policy*
- **Matching labels:** `route_to = triage` (or whatever convention you adopt)
- **Default contact point:** `webhook-hub`
- **Continue matching:** check this if you also want BigPanda to receive these alerts (so the Hub *augments* BP, doesn't replace it)

### Via Grafana provisioning (file or API)

If platform team uses provisioning (preferred — it's GitOps-able):

```yaml
# /etc/grafana/provisioning/alerting/contact-points.yaml
apiVersion: 1
contactPoints:
  - orgId: 1
    name: webhook-hub
    receivers:
      - uid: webhook-hub
        type: webhook
        settings:
          url: https://webhook-hub.<your-domain>/inbound
          httpMethod: POST
          authorization_scheme: Bearer
          authorization_credentials: "$WEBHOOK_HUB_TOKEN"   # from env / secret
          maxAlerts: 0
          # Optional — Grafana lets you template the payload, but the Hub
          # accepts the default shape so leave message/title unset.
        disableResolveMessage: false
```

```yaml
# /etc/grafana/provisioning/alerting/policies.yaml
apiVersion: 1
policies:
  - orgId: 1
    receiver: BigPanda                # default — incidents still go to BP
    routes:
      - receiver: webhook-hub
        object_matchers:
          - ["route_to", "=", "triage"]
        continue: true                # keep evaluating — BP also gets it
```

The `continue: true` is the political magic: BigPanda's policy is unchanged; the Hub gets a duplicate stream for triage automation. Platform team doesn't lose anything.

---

## Option 2 — AlertManager `webhook_configs`

If the upstream is a vanilla Prometheus AlertManager (or one fronting Loki Ruler / Mimir Ruler):

```yaml
# Goes into alertmanager.yaml (their managed AM config)
route:
  receiver: bigpanda                    # default — leave their existing config alone
  routes:
    - receiver: webhook-hub
      matchers:
        - route_to = "triage"
      continue: true                    # BP still gets these too

receivers:
  - name: bigpanda
    # ... their existing BP config — unchanged ...

  - name: webhook-hub
    webhook_configs:
      - url: https://webhook-hub.<your-domain>/inbound
        send_resolved: true
        max_alerts: 0
        http_config:
          authorization:
            type: Bearer
            credentials_file: /etc/alertmanager/secrets/webhook-hub-token
            # OR inline (less safe — only if they don't have a secrets mount):
            # credentials: <token>
```

Notes for the platform team if they ask:
- `send_resolved: true` means we get notified when alerts clear — useful for closing GitLab issues automatically.
- `max_alerts: 0` = unlimited per batch. Set a number (e.g. 50) if they want a cap.
- `credentials_file` over `credentials` so the token never appears in their config repo.
- The webhook URL is reached over public internet (or via their egress proxy) — they should confirm egress allow-list (this is what blocked the Grafana UI test with 407).

---

## Payload shape — what the Hub receives

The two upstreams emit slightly different JSON. The `parse-alerts` step in `06-workflow-template-triage.yaml` is written to handle both.

### AlertManager (Option 2) — canonical shape

```json
{
  "version": "4",
  "status": "firing",
  "receiver": "webhook-hub",
  "groupKey": "{}:{alertname=\"...\"}",
  "groupLabels": { "alertname": "..." },
  "commonLabels": { "alertname": "...", "severity": "critical", "team": "..." },
  "commonAnnotations": { "summary": "..." },
  "externalURL": "https://alertmanager.../",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "PodCrashLooping",
        "severity": "critical",
        "namespace": "foo",
        "pod": "bar-xyz",
        "team": "platform",
        "cluster": "..."
      },
      "annotations": {
        "summary": "...",
        "description": "...",
        "runbook_url": "..."
      },
      "startsAt": "2026-05-01T...Z",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "https://prometheus/...",
      "fingerprint": "abc123"
    }
  ]
}
```

### Grafana Alerting (Option 1) — close but not identical

```json
{
  "receiver": "webhook-hub",
  "status": "firing",
  "orgId": 1,
  "alerts": [
    {
      "status": "firing",
      "labels": { "alertname": "...", "severity": "critical", "team": "..." },
      "annotations": { "summary": "...", "description": "..." },
      "startsAt": "2026-05-01T...Z",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "https://grafana/.../alert-rule-uid",
      "fingerprint": "...",
      "silenceURL": "https://grafana/silences/new?...",
      "dashboardURL": "",
      "panelURL": "",
      "values": { "B": 1, "C": 1 },
      "valueString": "[ var='B' labels={...} value=1 ]"
    }
  ],
  "groupLabels": {},
  "commonLabels": { ... },
  "commonAnnotations": { ... },
  "externalURL": "https://grafana.../",
  "version": "1",
  "groupKey": "{}/{}:{}",
  "truncatedAlerts": 0,
  "title": "[FIRING:1] PodCrashLooping",
  "state": "alerting",
  "message": "..."
}
```

### What the Hub workflow uses

`06-workflow-template-triage.yaml` reads only fields that exist in **both** shapes:

- `.alerts[]` — array of individual alerts
- `.alerts[].labels.{alertname,severity,namespace,pod,service,cluster,team}`
- `.alerts[].annotations.{summary,description,runbook_url}`
- `.alerts[].status`
- `.alerts[].startsAt`
- `.alerts[].generatorURL`

Grafana's extras (`silenceURL`, `dashboardURL`, `valueString`) are useful but not depended on. The `panelURL` and `dashboardURL` are nice-to-have — adding them to the Mattermost card is a one-line `jq` change if you want them.

### Sensor filter compatibility

The Sensor filters in `07-sensor-ai-triage.yaml` and `08-sensor-slack-example.yaml` use:

- `body.status` → present in both
- `body.alerts.0.labels.severity` → present in both
- `body.commonLabels.team` → present in both

Both senders work with the existing filters. No filter changes needed.

---

## Smoke tests — one per sender shape

```bash
TOKEN=$(kubectl get secret webhook-hub-token -n argo-events -o jsonpath='{.data.token}' | base64 -d)
HUB_URL=https://webhook-hub.<your-domain>/inbound
# OR for in-cluster test:
# kubectl port-forward -n argo-events svc/webhook-hub-eventsource-svc 12000:12000 &
# HUB_URL=http://localhost:12000/inbound
```

### Test 1 — AlertManager-shaped payload

```bash
curl -X POST "${HUB_URL}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "version":"4","status":"firing","receiver":"webhook-hub",
    "groupLabels":{"alertname":"AmShapeTest"},
    "commonLabels":{"alertname":"AmShapeTest","severity":"warning","team":"team-x"},
    "alerts":[{
      "status":"firing",
      "labels":{
        "alertname":"AmShapeTest","severity":"warning",
        "namespace":"default","pod":"test-pod","team":"team-x","cluster":"{{CLUSTER_NAME}}"
      },
      "annotations":{
        "summary":"AlertManager-shaped smoke test",
        "description":"Confirms AM payload parses",
        "runbook_url":"https://runbooks.example.com/AmShapeTest"
      },
      "startsAt":"2026-05-01T00:00:00Z",
      "generatorURL":"https://prometheus/..."
    }]
  }'
```

### Test 2 — Grafana-shaped payload

```bash
curl -X POST "${HUB_URL}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "receiver":"webhook-hub","status":"firing","orgId":1,"version":"1",
    "title":"[FIRING:1] GrafanaShapeTest",
    "state":"alerting",
    "message":"Grafana-shaped smoke test",
    "groupLabels":{},
    "commonLabels":{"alertname":"GrafanaShapeTest","severity":"warning","team":"team-x"},
    "alerts":[{
      "status":"firing",
      "labels":{
        "alertname":"GrafanaShapeTest","severity":"warning",
        "namespace":"default","pod":"test-pod","team":"team-x","cluster":"{{CLUSTER_NAME}}"
      },
      "annotations":{
        "summary":"Grafana-shaped smoke test",
        "description":"Confirms Grafana payload parses"
      },
      "startsAt":"2026-05-01T00:00:00Z",
      "generatorURL":"https://grafana/alerting/grafana/abc/view",
      "silenceURL":"https://grafana/alerting/silence/new?..."
    }]
  }'
```

### Negative tests

```bash
# No token → 401 from Argo Events EventSource (or 403 from Istio AuthZ)
curl -i -X POST "${HUB_URL}" -H "Content-Type: application/json" -d '{}'

# Wrong token → 401
curl -i -X POST "${HUB_URL}" -H "Authorization: Bearer wrong" -H "Content-Type: application/json" -d '{}'

# Wrong path → 404 from Istio VirtualService (route doesn't match)
curl -i -X POST "https://webhook-hub.<your-domain>/wrong" -H "Authorization: Bearer ${TOKEN}" -d '{}'
```

### Verify a workflow ran

```bash
kubectl get workflows -n argo-events \
  -l app.kubernetes.io/part-of=webhook-hub \
  --sort-by=.metadata.creationTimestamp | tail -5

# Look at the parse-alerts step output
kubectl logs -n argo-events $(kubectl get pods -n argo-events \
  -l workflows.argoproj.io/workflow-template=webhook-hub-ai-triage \
  -o jsonpath='{.items[-1].metadata.name}') \
  -c main --tail=100
```

---

## Which to ask for first

If the platform team gives you the choice: **ask for Option 1 (Grafana Contact Point).**

Reasoning:
- Grafana Alerting is per-tenant by design — adding a Webhook Contact Point in your tenant doesn't affect other tenants. Lower governance bar.
- You author the alert rules in the same Grafana UI, so end-to-end ownership lives in one place.
- AlertManager `webhook_configs` is a global-config change — every tenant's alerts run through that one AM, so adding a receiver typically requires a more formal change-request process.
- The 407 you saw today is the same network path either way — solving it for one solves it for both.

If they refuse Option 1 (locked-down to BigPanda only) but offer Option 2, take it. If they refuse both, the conversation moves to "you need to provide an outbound queue we can subscribe to" — see `LGTM-TO-ARGO-EVENTS-RECAP.md` Option C.

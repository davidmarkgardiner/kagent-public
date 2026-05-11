# Option A — Istio AKS add-on variant

**Use this instead of `OPTION-A-README.md` (nginx variant) on AKS.**
**Pattern source:** mirrors `ai-platform/teams-hitl/istio-{virtualservice,authorization-policy}.yaml` — already shipping in this repo.
**Date:** 2026-04-30

---

## TL;DR

On AKS with the Istio add-on we don't deploy nginx-ingress. We expose the existing Argo Events EventSource through the **shared wildcard Istio Gateway**, route to it via a `VirtualService`, and lock it down with a layered `AuthorizationPolicy` (source-IP allow-list + bearer token check). TLS is terminated at the Istio ingress gateway via the wildcard cert that's already provisioned for the cluster.

The HITL callback work (commit `f5fbdb1`) already proved this pattern end-to-end. The AlertManager webhook is the same shape — external HTTPS POST → Argo EventSource — so we can copy-paste those manifests with three names changed.

---

## How this compares to the nginx version

| | nginx-ingress (`OPTION-A-README.md`) | Istio AKS add-on (this doc) |
|---|---|---|
| Public entry point | `Ingress` resource → nginx controller | Shared Istio `Gateway` (already exists, in `aks-istio-ingress` ns) |
| Routing | `Ingress` rules | `VirtualService` |
| TLS | cert-manager + per-host Cert | Wildcard cert on the shared Gateway (already configured) |
| Auth | nginx config snippet (bearer check) | `AuthorizationPolicy` — source IP + JWT/header rules |
| mTLS pod-to-pod | not applied | Free (sidecar, mesh-wide STRICT) |
| New components to deploy | nginx-ingress controller + cert-manager + Ingress | Just two Istio CRs |
| Pattern in repo? | new | already proven (HITL) |

The Istio variant is **less new infra and more secure for free**. On AKS you should always pick this.

---

## Architecture

```
                                                Managed LGTM
                                          (in platform-team network)
                                                    │
                                                    │  AlertManager webhook
                                                    │  POST https://alerts.<wildcard>/alerts
                                                    │  Authorization: Bearer <token>
                                                    ▼
              ┌─────────────────────────────────────────────────────────────┐
              │ AKS cluster (mgmt cluster)                                  │
              │                                                             │
              │   ┌─────────────────────────────────────────────────────┐   │
              │   │ aks-istio-ingress namespace (Istio AKS add-on)      │   │
              │   │                                                     │   │
              │   │  Gateway: shared wildcard *.lab.{{INGRESS_DOMAIN}}        │   │
              │   │  Service: aks-istio-ingressgateway-external (LB)    │   │
              │   │             ▲                                       │   │
              │   │             │ TLS terminates here (wildcard cert)   │   │
              │   └─────────────┼───────────────────────────────────────┘   │
              │                 │                                           │
              │     attached via gateways:                                  │
              │                 │                                           │
              │   ┌─────────────▼───────────────────────────────────────┐   │
              │   │ argo-events namespace                               │   │
              │   │                                                     │   │
              │   │  VirtualService alertmanager-webhook-vs             │   │
              │   │    host: alerts.lab.{{INGRESS_DOMAIN}}                    │   │
              │   │    /alerts → alertmanager-eventsource-svc:12000     │   │
              │   │                                                     │   │
              │   │  AuthorizationPolicy alertmanager-webhook-allow     │   │
              │   │    Layer 1: source IP allow-list (managed AM NAT)   │   │
              │   │    Layer 2: require Authorization: Bearer header    │   │
              │   │  AuthorizationPolicy alertmanager-webhook-deny      │   │
              │   │    default DENY for everything else                 │   │
              │   │                                                     │   │
              │   │  ┌─────────────────────────────────────────────┐    │   │
              │   │  │ EventSource alertmanager (port 12000)       │    │   │
              │   │  │   ↓ NATS EventBus                           │    │   │
              │   │  │ Sensor alertmanager-triage-sensor           │    │   │
              │   │  │   ↓ create Workflow                         │    │   │
              │   │  │ alertmanager-triage WorkflowTemplate        │    │   │
              │   │  │   ↓                                         │    │   │
              │   │  │ kagent A2A → Mattermost / GitLab            │    │   │
              │   │  └─────────────────────────────────────────────┘    │   │
              │   └─────────────────────────────────────────────────────┘   │
              │                                                             │
              └─────────────────────────────────────────────────────────────┘
```

The boxed-in argo-events namespace is **already deployed and tested on {{CLUSTER_NAME}}** (see `OPTION-A-README.md`). The only AKS-specific change is the two Istio CRs at the top.

---

## Discover your existing wildcard Gateway first

Before applying anything, find the cluster's shared Gateway and the wildcard host pattern. The HITL doc has these exact commands — repeat here for self-containment.

```bash
# Find shared wildcard Gateway(s)
kubectl get gateway.networking.istio.io -A \
  -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}{"\t"}{.spec.servers[*].hosts}{"\n"}{end}' \
  | grep '\*'

# Example output:
#   aks-istio-ingress/shared-wildcard-gateway    [*.lab.example.com]

# Find the external ingress LB hostname/IP (this is what DNS for our subdomain points at)
kubectl get svc -n aks-istio-ingress aks-istio-ingressgateway-external \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}{.status.loadBalancer.ingress[0].ip}{"\n"}'
```

Outcomes you should write down:
- **Wildcard pattern** — e.g. `*.lab.example.com`. Your AlertManager hostname must match (e.g. `alerts.lab.example.com`).
- **Gateway namespace + name** — e.g. `aks-istio-ingress/shared-wildcard-gateway`.
- **Ingress LB hostname/IP** — what to point your DNS A/CNAME at (or the platform-team's allow-list at).

---

## VirtualService — `istio/01-virtualservice.yaml`

Mirrors `ai-platform/teams-hitl/istio-virtualservice.yaml` with three substitutions:
- host changes from `hitl-callback.<wildcard>` → `alerts.<wildcard>`
- path changes from `/approval-callback` → `/alerts`
- destination changes from `teams-hitl-callback-eventsource-svc` → `alertmanager-eventsource-svc`

```yaml
# Istio VirtualService — expose the AlertManager → Argo Events webhook
#
# DEPLOY ON: management cluster (where Argo Events runs)
#
# Path:
#   Managed AlertManager (external)
#     ↓ HTTPS POST to https://alerts.<wildcard-domain>/alerts
#   Istio ingress gateway (terminates TLS via wildcard cert)
#     ↓ matched by VirtualService host
#   VirtualService (this file)
#     ↓ forwards to EventSource Service
#   alertmanager-eventsource-svc.argo-events:12000
#     ↓
#   Argo Events webhook → Sensor → alertmanager-triage Workflow
#
# Substitute placeholders before applying:
#   REPLACE_WITH_ALERTS_HOST          e.g. alerts.lab.example.com
#   REPLACE_WITH_SHARED_GATEWAY_NS    e.g. aks-istio-ingress
#   REPLACE_WITH_SHARED_GATEWAY_NAME  the wildcard Gateway's name
# ---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: alertmanager-webhook-vs
  namespace: argo-events
spec:
  hosts:
    - "REPLACE_WITH_ALERTS_HOST"

  # Attach ONLY to the shared ingress Gateway — not `mesh`. The managed
  # AlertManager is not in our mesh.
  gateways:
    - REPLACE_WITH_SHARED_GATEWAY_NS/REPLACE_WITH_SHARED_GATEWAY_NAME

  http:
    - match:
        - uri:
            exact: /alerts
        - uri:
            exact: /alerts/
        - method:
            exact: POST
      route:
        - destination:
            # EventSource service name pattern: <eventsource-name>-eventsource-svc
            host: alertmanager-eventsource-svc.argo-events.svc.cluster.local
            port:
              number: 12000
      timeout: 10s
      retries:
        attempts: 2
        perTryTimeout: 5s
        retryOn: 5xx,reset,connect-failure,refused-stream
```

---

## AuthorizationPolicy — `istio/02-authorization-policy.yaml`

Two layers, same pattern as HITL:
- **Layer 1:** source-IP allow-list of the managed AlertManager egress NAT range. Always on.
- **Layer 2:** require `Authorization: Bearer <token>` header. Always on (since the webhook crosses public internet).
- **Default DENY:** anything not matching above gets dropped at the sidecar.

```yaml
# Istio AuthorizationPolicy — restrict who can POST to the AlertManager webhook
#
# Layered approach:
#   Layer 1: source IP allow-list (managed AlertManager egress NAT)
#   Layer 2: require Authorization: Bearer <shared token>
#   Default: DENY everything else
#
# Find the managed AM's egress IPs:
#   - Ask the platform team for their AlertManager outbound NAT ranges
#   - Confirm by checking access logs after a real test webhook
# ---

# ─── Layer 1: source IP allow-list ─────────────────────────────────────────
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: alertmanager-webhook-allow-source
  namespace: argo-events
spec:
  selector:
    matchLabels:
      # EventSource pods are labelled by Argo Events with the eventsource name
      eventsource-name: alertmanager
  action: ALLOW
  rules:
    - from:
        - source:
            remoteIpBlocks:
              - "REPLACE_WITH_MANAGED_AM_EGRESS_CIDR"   # e.g. 20.1.2.3/32
              # - "OTHER_AM_EGRESS_CIDR"
      to:
        - operation:
            methods: ["POST"]
            paths:
              - "/alerts"
              - "/alerts/"
      when:
        - key: request.headers[authorization]
          values: ["Bearer *"]
        # Tighter (exact match against the secret-stored token):
        # - key: request.headers[authorization]
        #   values: ["Bearer REPLACE_WITH_TOKEN"]
        # ⚠ Don't put the token in plain YAML — wire via EnvoyFilter +
        # secret reference, OR keep "Bearer *" here and verify the exact
        # token value in the EventSource's filter (see note below).

---
# ─── Default DENY — drop anything not explicitly allowed ───────────────────
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: alertmanager-webhook-default-deny
  namespace: argo-events
spec:
  selector:
    matchLabels:
      eventsource-name: alertmanager
  action: DENY
  rules:
    - to:
        - operation:
            paths: ["*"]
```

**Where the token is actually checked:**

Two options for verifying the *exact* token value (since putting the secret in the AuthorizationPolicy YAML is bad hygiene):

1. **At Istio with `RequestAuthentication` + JWT.** Cleaner if the platform team can sign a JWT. Probably overkill for a static webhook.
2. **At Argo Events with EventSource filter.** The Argo Events `webhook` EventSource supports `authSecret` — set the bearer token there, and Argo Events itself rejects unauthenticated requests *after* the Istio sidecar has done the IP + presence check. This is the simplest path.

Add to `03-eventsource-alertmanager.yaml`:

```yaml
spec:
  webhook:
    alertmanager:
      port: "12000"
      endpoint: /alerts
      method: POST
      authSecret:
        name: alertmanager-webhook-token
        key: token        # the bearer token; Argo Events checks Authorization: Bearer <token>
```

That keeps the secret in a `Secret` only and the AuthorizationPolicy just enforces *presence* of an Authorization header.

---

## Deploy steps

Assumes the prometheus-alerting/ stack is already deployed and tested (it is, on proxmox; on AKS run `prometheus-alerting/deploy.sh` first).

```bash
# 1. Discover the wildcard Gateway (see commands above) and pick a hostname
WILDCARD_GW_NS=aks-istio-ingress
WILDCARD_GW_NAME=shared-wildcard-gateway   # whatever your cluster has
ALERTS_HOST=alerts.lab.example.com

# 2. Generate and store the bearer token
TOKEN=$(openssl rand -hex 32)
kubectl create secret generic alertmanager-webhook-token \
  --namespace argo-events \
  --from-literal=token="${TOKEN}"

# 3. Patch the EventSource to require the token (one-shot edit — see snippet above)
kubectl edit eventsource alertmanager -n argo-events
# add the authSecret block under spec.webhook.alertmanager

# 4. Apply VirtualService
sed -e "s|REPLACE_WITH_ALERTS_HOST|${ALERTS_HOST}|" \
    -e "s|REPLACE_WITH_SHARED_GATEWAY_NS|${WILDCARD_GW_NS}|" \
    -e "s|REPLACE_WITH_SHARED_GATEWAY_NAME|${WILDCARD_GW_NAME}|" \
    istio/01-virtualservice.yaml | kubectl apply -f -

# 5. Get the managed AM egress CIDRs from platform team, then apply AuthZ
sed -e "s|REPLACE_WITH_MANAGED_AM_EGRESS_CIDR|20.1.2.3/32|" \
    istio/02-authorization-policy.yaml | kubectl apply -f -

# 6. Verify Istio routing picked up the VirtualService
kubectl get virtualservice -n argo-events alertmanager-webhook-vs
istioctl proxy-config route -n aks-istio-ingress \
  deploy/aks-istio-ingressgateway-external --name https.443 \
  | grep alerts

# 7. Verify AuthorizationPolicy is enforced on the EventSource pod
istioctl authz check deploy/alertmanager-eventsource -n argo-events

# 8. Hand the URL + token to the platform team for their AlertManager config:
echo "URL:   https://${ALERTS_HOST}/alerts"
echo "Token: ${TOKEN}"
```

---

## Test plan

```bash
# 1. Smoke test from outside the cluster — proves Istio Gateway → VirtualService → EventSource
TOKEN=$(kubectl get secret alertmanager-webhook-token -n argo-events -o jsonpath='{.data.token}' | base64 -d)

curl -X POST https://${ALERTS_HOST}/alerts \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "version":"4","status":"firing","receiver":"argo-events-webhook",
    "alerts":[{
      "status":"firing",
      "labels":{"alertname":"IstioOptionATest","severity":"warning","namespace":"default","pod":"test"},
      "annotations":{"summary":"Istio path test","description":"Gateway + VS + AuthZ + EventSource"},
      "startsAt":"2026-04-30T00:00:00Z"
    }]
  }'

# Expect: 200 OK, then a workflow shortly after:
kubectl get workflows -n argo-events -l event-type=prometheus-alert --sort-by=.metadata.creationTimestamp | tail -5

# 2. Negative test — no token → AuthorizationPolicy denies
curl -i -X POST https://${ALERTS_HOST}/alerts -d '{}'
# Expect: HTTP/2 403 (RBAC: access denied) from the Istio sidecar

# 3. Negative test — wrong source IP (run from outside the allow-list)
# Expect: HTTP/2 403 from Layer 1 of the AuthorizationPolicy

# 4. Negative test — wrong path
curl -i -X POST https://${ALERTS_HOST}/wrong-path -H "Authorization: Bearer ${TOKEN}" -d '{}'
# Expect: HTTP/2 404 (Istio VirtualService doesn't match) — never reaches the EventSource
```

For the loop test once the platform team wires in their AlertManager:

```bash
# Trigger a real failure that the managed AM will fire on
./test-alerts.sh --create-crashloop
./test-alerts.sh --verify
```

Same script as proxmox — only the upstream AlertManager has changed.

---

## Troubleshooting

Same table as `OPTION-A-README.md` plus Istio-specific diagnostics:

| Symptom | Where to look |
|---|---|
| 404 from Istio Gateway | VirtualService host doesn't match the hostname in the request — check `Host:` header and `spec.hosts` |
| 503 from Istio Gateway | EventSource Service has no endpoints — `kubectl get endpointslice -n argo-events \| grep alertmanager-eventsource` |
| 403 with valid token | AuthorizationPolicy IP layer denying; confirm caller IP via `istioctl proxy-config log -n aks-istio-ingress deploy/aks-istio-ingressgateway-external --level rbac:debug`, then watch logs |
| 403 with no token | Layer 2 of AuthorizationPolicy doing its job — expected for unauthenticated callers |
| Token check passes Istio but EventSource rejects | EventSource `authSecret` value doesn't match what the caller sent — `kubectl get secret alertmanager-webhook-token -n argo-events -o yaml` |
| Cert error / TLS handshake fail | Wildcard cert on the shared Gateway doesn't cover this host — Gateway only covers `*.<single-level>.<domain>`. `alerts.lab.example.com` is fine; `alerts.foo.lab.example.com` is **not** |
| Reaches EventSource but no workflow | Same as proxmox path — Sensor filter / rate limit |

The HITL doc has a layered test sequence (`docs/HITL-VALIDATION-RUNBOOK.md` if it exists) that's worth adapting if you want a structured runbook.

---

## Cross-cluster note (mgmt cluster vs worker clusters)

You mentioned this in commit `906085c` already — AKS Istio add-on clusters are **separate meshes by default**. So:

- The webhook receiver (Argo EventSource) lives on the **management cluster** mesh.
- The managed AlertManager is in **another mesh** (the platform team's).
- We **cannot** use Istio mTLS between them — the cert chains aren't shared.
- That's why TLS at the Istio Gateway terminates with a public/wildcard cert and authentication happens via the bearer token, not mesh identity.

If the worker clusters' Prometheus instances also need to fire alerts directly into the same webhook (bypassing the managed LGTM for any reason), the same applies: they cross-mesh, so TLS+bearer auth, not Istio mTLS.

---

## What changed vs the nginx variant

If you're cross-referencing `OPTION-A-README.md`:

| Section | nginx variant | Istio variant (this doc) |
|---|---|---|
| New manifest count | 1 (Ingress) | 2 (VirtualService + AuthorizationPolicy) — but they replace nginx + cert-manager + Ingress |
| TLS termination | nginx + cert-manager | shared Istio Gateway wildcard cert |
| Auth mechanism | nginx config snippet | Istio AuthorizationPolicy + EventSource `authSecret` |
| DNS | A/CNAME → nginx LB IP | A/CNAME → Istio ingress LB hostname |
| What needs ratifying with platform | webhook URL + token | webhook URL + token + their egress CIDR (because we can IP-allow-list at Istio) |

---

## Files to ship

```
managed-lgtm-integration/
├── OPTION-A-ISTIO-README.md                            ← this file
└── istio/
    ├── 01-virtualservice.yaml                          ← VirtualService manifest above
    └── 02-authorization-policy.yaml                    ← AuthZ manifest above

(and edit ../prometheus-alerting/03-eventsource-alertmanager.yaml to add `authSecret`)
```

Reference / source pattern:
- `ai-platform/teams-hitl/istio-virtualservice.yaml`
- `ai-platform/teams-hitl/istio-authorization-policy.yaml`
- `ai-platform/teams-hitl/README.md` — full HITL writeup, near-identical pattern

---

## See also

- `OPTION-A-README.md` — nginx-ingress variant (use only if not on AKS / no Istio)
- `README-METRICS-EVENTS-ALERTING.md` — metrics path that lands at the same webhook
- `README-LOG-ALERTING.md` — logs path that lands at the same webhook
- `LGTM-TO-ARGO-EVENTS-RECAP.md` — top-level decision tree
